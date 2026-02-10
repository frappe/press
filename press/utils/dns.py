from __future__ import annotations

from typing import TYPE_CHECKING

import boto3
import frappe
import requests
from dns.exception import DNSException
from dns.rdatatype import AAAA, CAA, CNAME, SOA, A
from dns.resolver import NoAnswer, Resolver
from frappe.core.utils import find
from frappe.utils.caching import redis_cache

from press.exceptions import (
	AAAARecordExists,
	ConflictingCAARecord,
	ConflictingDNSRecord,
	DNSValidationError,
	DomainProxied,
	MultipleARecords,
	MultipleCNAMERecords,
)
from press.utils import log_error

if TYPE_CHECKING:
	from press.press.doctype.root_domain.root_domain import RootDomain

NAMESERVERS = ["1.1.1.1", "1.0.0.1", "8.8.8.8", "8.8.4.4"]


@frappe.whitelist()
def create_dns_record(doc, record_name=None):
	"""Check if site needs dns records and creates one."""
	domain: RootDomain = frappe.get_doc("Root Domain", doc.domain)

	if domain.generic_dns_provider:
		return

	if frappe.flags.in_test:
		return

	proxy_server, is_standalone = frappe.get_value("Server", doc.server, ["proxy_server", "is_standalone"])

	if doc.cluster == domain.default_cluster and not is_standalone:
		# Check if the cluster has multiple proxy servers
		proxy_servers = frappe.get_all(
			"Proxy Server",
			{"cluster": doc.cluster, "status": "Active"},
			pluck="name",
		)
		if len(proxy_servers) == 1 or (
			len(proxy_servers) > 1 and domain.default_proxy_server == proxy_server
		):
			"""
			If we have a single proxy server
			Or, in case of multiple proxy server, the site is using the default proxy server

			We can skip creating dns record
			"""
			return

	if is_standalone:
		_change_dns_record("UPSERT", domain, doc.server, record_name=record_name)
	else:
		_change_dns_record("UPSERT", domain, proxy_server, record_name=record_name)


def _change_dns_record(method: str, domain: RootDomain, proxy_server: str, record_name: str | None = None):
	"""
	Change dns record of site

	method: CREATE | DELETE | UPSERT
	"""
	if domain.generic_dns_provider:
		return

	client = boto3.client(
		"route53",
		aws_access_key_id=domain.aws_access_key_id,
		aws_secret_access_key=domain.get_password("aws_secret_access_key"),
		region_name=domain.aws_region,
	)
	try:
		zones = client.list_hosted_zones_by_name()["HostedZones"]
		hosted_zone = find(reversed(zones), lambda x: domain.name.endswith(x["Name"][:-1]))["Id"]
		client.change_resource_record_sets(
			ChangeBatch={
				"Changes": [
					{
						"Action": method,
						"ResourceRecordSet": {
							"Name": record_name,
							"Type": "CNAME",
							"TTL": 600,
							"ResourceRecords": [{"Value": proxy_server}],
						},
					}
				]
			},
			HostedZoneId=hosted_zone,
		)
	except client.exceptions.InvalidChangeBatch as e:
		# If we're attempting to DELETE and record is not found, ignore the error
		# e.response["Error"]["Message"] looks like
		# [Tried to delete resource record set [name='xxx.frappe.cloud.', type='CNAME'] but it was not found]
		if method == "DELETE" and "but it was not found" in e.response["Error"]["Message"]:
			return
		log_error(
			"Route 53 Record Creation Error",
			domain=domain.name,
			site=record_name,
			proxy_server=proxy_server,
		)
	except Exception:
		log_error(
			"Route 53 Record Creation Error",
			domain=domain.name,
			site=record_name,
			proxy_server=proxy_server,
		)


def get_dns_provider_mname_rname(domain):
	from tldextract import extract

	resolver = Resolver(configure=False)
	resolver.nameservers = NAMESERVERS
	try:
		answer = resolver.query(domain, SOA)
		if len(answer) > 0:
			mname = answer[0].mname.to_text()
			rname = answer[0].rname.to_text()
			return extract(mname).registered_domain, extract(rname).registered_domain
	except NoAnswer:
		pass
	except DNSException:
		pass
	return None


def accessible_link_substr(provider: str):
	try:
		res = requests.head(f"http://{provider}", timeout=3)
		res.raise_for_status()
	except requests.RequestException:
		return None
	else:
		return f'<a class=underline href="http://{provider}" target="_blank">{provider}</a>'


@redis_cache()
def get_dns_provider_link_substr(domain: str):
	# get link to dns provider as html a tag if link is accessible
	provider = get_dns_provider_mname_rname(domain)
	if not provider:
		return ""
	mname, rname = provider
	return f" at your DNS provider (hint: {accessible_link_substr(mname) or accessible_link_substr(rname) or rname})"  # likely rname has meaningful link


def throw_for_caa_record(domain):
	resolver = Resolver(configure=False)
	resolver.nameservers = NAMESERVERS
	try:
		answer = resolver.query(domain, CAA)
		for rdata in answer:
			if "letsencrypt.org" in rdata.to_text():
				return True
	except NoAnswer:
		pass  # no CAA record. Anything goes
	except DNSException:
		pass  # We have other problems
	else:
		frappe.throw(
			f"Domain {domain} does not allow Let's Encrypt certificates. Please update or remove <b>CAA</b> record{get_dns_provider_link_substr(domain)}.",
			ConflictingCAARecord,
		)


def check_domain_allows_letsencrypt_certs(domain):
	# Check if domain is allowed to get letsencrypt certificates
	# This is a security measure to prevent unauthorized certificate issuance
	from tldextract import extract

	throw_for_caa_record(domain)
	naked_domain = extract(domain).registered_domain
	if naked_domain != domain:
		throw_for_caa_record(naked_domain)


def check_dns_cname(name, domain):
	result = {"type": "CNAME", "exists": True, "matched": False, "answer": ""}
	try:
		resolver = Resolver(configure=False)
		resolver.nameservers = NAMESERVERS
		answer = resolver.query(domain, CNAME)
		if len(answer) > 1:
			raise MultipleCNAMERecords
		mapped_domain = answer[0].to_text().rsplit(".", 1)[0]
		result["answer"] = answer.rrset.to_text()
		other_domains = frappe.db.get_all(
			"Site Domain", {"site": name, "status": "Active", "domain": ("!=", name)}, pluck="domain"
		)
		if mapped_domain == name or mapped_domain in other_domains:
			result["matched"] = True
	except MultipleCNAMERecords:
		multiple_domains = ", ".join(part.to_text() for part in answer)
		frappe.throw(
			f"Domain <b>{domain}</b> has multiple CNAME records: <b>{multiple_domains}</b>. Please keep only one{get_dns_provider_link_substr(domain)}.",
			MultipleCNAMERecords,
		)
	except NoAnswer as e:
		result["exists"] = False
		result["answer"] = str(e)
	except DNSException as e:
		result["answer"] = str(e)
	except Exception as e:
		result["answer"] = str(e)
		log_error("DNS Query Exception - CNAME", site=name, domain=domain, exception=e)
	return result


def check_for_ip_match(site_name: str, site_ip: str | None, domain_ip: str | None):
	if domain_ip == site_ip:
		return True
	if site_ip:
		# We can issue certificates even if the domain points to the secondary proxies
		server = frappe.db.get_value("Site", site_name, "server")
		proxy = frappe.db.get_value("Server", server, "proxy_server")
		secondary_ips = frappe.get_all(
			"Proxy Server",
			{"status": "Active", "primary": proxy, "is_replication_setup": True},
			pluck="ip",
		)
		if domain_ip in secondary_ips:
			return True
	return False


def check_dns_a(name, domain):
	result = {"type": "A", "exists": True, "matched": False, "answer": ""}
	try:
		resolver = Resolver(configure=False)
		resolver.nameservers = NAMESERVERS
		answer = resolver.query(domain, A)
		if len(answer) > 1:
			raise MultipleARecords
		domain_ip = answer[0].to_text()
		site_ip = resolver.query(name, A)[0].to_text()
		result["answer"] = answer.rrset.to_text()
		result["matched"] = check_for_ip_match(name, site_ip, domain_ip)
	except MultipleARecords:
		multiple_ips = ", ".join(part.to_text() for part in answer)
		frappe.throw(
			f"Domain {domain} has multiple A records: {multiple_ips}. Please keep only one{get_dns_provider_link_substr(domain)}.",
			MultipleARecords,
		)
	except NoAnswer as e:
		result["exists"] = False
		result["answer"] = str(e)
	except DNSException as e:
		result["answer"] = str(e)
	except Exception as e:
		result["answer"] = str(e)
		log_error("DNS Query Exception - A", site=name, domain=domain, exception=e)
	return result


def ensure_dns_aaaa_record_doesnt_exist(domain: str):
	"""
	Ensure that the domain doesn't have an AAAA record

	LetsEncrypt has issues with IPv6, so we need to ensure that the domain doesn't have an AAAA record
	ref: https://letsencrypt.org/docs/ipv6-support/#incorrect-ipv6-addresses
	"""
	try:
		resolver = Resolver(configure=False)
		resolver.nameservers = NAMESERVERS
		answer = resolver.query(domain, AAAA)
		if answer:
			frappe.throw(
				f"Domain {domain} has an AAAA record. This causes issues with https certificate generation. Please remove the same{get_dns_provider_link_substr(domain)}.",
				AAAARecordExists,
			)
	except NoAnswer:
		pass
	except DNSException:
		pass  # We have other problems


DNS_HELP_ARTICLE = "https://developers.cloudflare.com/dns/manage-dns-records/"


def check_domain_proxied(domain) -> str | None:
	try:
		res = requests.head(f"http://{domain}", timeout=3)
	except requests.exceptions.RequestException as e:
		frappe.msgprint(
			f"Unable to connect to the domain. Is the DNS correct{get_dns_provider_link_substr(domain)}? <a href='{DNS_HELP_ARTICLE}' target='_blank' class='underline' >Learn more</a>.",
		)
		raise DNSValidationError from e
	else:
		if (server := res.headers.get("server")) not in ("Frappe Cloud", None):  # eg: cloudflare
			return server
		return None


def _check_dns_cname_a(name, domain, ignore_proxying=False):
	check_domain_allows_letsencrypt_certs(domain)
	ensure_dns_aaaa_record_doesnt_exist(domain)
	cname = check_dns_cname(name, domain)
	result = {"CNAME": cname} | cname

	a = check_dns_a(name, domain)
	result |= {"A": a} | a

	if cname["matched"] and a["exists"] and not a["matched"]:
		frappe.throw(
			f"""
			Domain <b>{domain}</b> has correct CNAME record <b>{cname["answer"].strip().split()[-1]}</b>, but also an A record that points to an incorrect IP address <b>{a["answer"].strip().split()[-1]}</b>.
			<br>Please remove or update the <b>A</b> record{get_dns_provider_link_substr(domain)}.
			""",
			ConflictingDNSRecord,
		)
	if a["matched"] and cname["exists"] and not cname["matched"]:
		frappe.throw(
			f"""
			Domain <b>{domain}</b> has correct A record <b>{a["answer"].strip().split()[-1]}</b>, but also a CNAME record that points to an incorrect domain <b>{cname["answer"].strip().split()[-1]}</b>.
			<br>Please remove or update the <b>CNAME</b> record{get_dns_provider_link_substr(domain)}.
			""",
			ConflictingDNSRecord,
		)

	proxy = check_domain_proxied(domain)
	if proxy:
		if ignore_proxying:  # no point checking the rest if proxied
			return {"CNAME": {}, "A": {}, "matched": True, "type": "A"}  # assume A
		frappe.throw(
			f"""Domain <b>{domain}</b> appears to be proxied (server: <b>{proxy}</b>). Please turn off proxying{get_dns_provider_link_substr(domain)} and try again in some time.
			<br>You may enable it once the domain is verified.""",
			DomainProxied,
		)

	result["valid"] = cname["matched"] or a["matched"]
	return result


def check_dns_cname_a(name, domain, ignore_proxying=False, throw_error=True):
	if throw_error:
		return _check_dns_cname_a(name, domain, ignore_proxying)

	result = {}
	try:
		result = _check_dns_cname_a(name, domain, ignore_proxying)

	except Exception as e:
		result["exc_type"] = e.__class__.__name__
		result["exc_message"] = str(e)
		result["valid"] = False

	return result
