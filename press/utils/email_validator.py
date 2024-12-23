"""
Customized function of validate-email package

RFC 2822 - style email validation for Python

(c) 2012 Syrus Akbary <me@syrusakbary.com>
Extended from (c) 2011 Noel Bush <noel@aitools.org> for support of mx and user check

This code is made available to you under the GNU LGPLv3.

This module provides a single method, valid_email_address(), which returns True or False to indicate
whether a given address is valid according to the 'addr-spec' part of the specification given in RFC
2822.  Ideally, we would like to find this in some other library, already thoroughly tested and
well-maintained.  The standard Python library email.utils contains a parse_addr() function, but it
is not sufficient to detect many malformed addresses.

This implementation aims to be faithful to the RFC, with the
exception of a circular definition (see comments below), and
with the omission of the pattern components marked as "obsolete".
"""

import contextlib
import re
import smtplib

from dns.resolver import Resolver

# All we are really doing is comparing the input string to one
# gigantic regular expression.  But building that regexp, and
# ensuring its correctness, is made much easier by assembling it
# from the "tokens" defined by the RFC.  Each of these tokens is
# tested in the accompanying unit test file.
#
# The section of RFC 2822 from which each pattern component is
# derived is given in an accompanying comment.
#
# (To make things simple, every string below is given as 'raw',
# even when it's not strictly necessary.  This way we don't forget
# when it is necessary.)

WSP = r"[ \t]"  # see 2.2.2. Structured Header Field Bodies
CRLF = r"(?:\r\n)"  # see 2.2.3. Long Header Fields
NO_WS_CTL = r"\x01-\x08\x0b\x0c\x0f-\x1f\x7f"  # see 3.2.1. Primitive Tokens
QUOTED_PAIR = r"(?:\\.)"  # see 3.2.2. Quoted characters
FWS = r"(?:(?:" + WSP + r"*" + CRLF + r")?" + WSP + r"+)"  # see 3.2.3. Folding white space and comments
CTEXT = r"[" + NO_WS_CTL + r"\x21-\x27\x2a-\x5b\x5d-\x7e]"  # see 3.2.3
CCONTENT = r"(?:" + CTEXT + r"|" + QUOTED_PAIR + r")"  # see 3.2.3 (NB: The RFC includes COMMENT here
# as well, but that would be circular.)
COMMENT = r"\((?:" + FWS + r"?" + CCONTENT + r")*" + FWS + r"?\)"  # see 3.2.3
CFWS = r"(?:" + FWS + r"?" + COMMENT + ")*(?:" + FWS + "?" + COMMENT + "|" + FWS + ")"  # see 3.2.3
ATEXT = r"[\w!#$%&\'\*\+\-/=\?\^`\{\|\}~]"  # see 3.2.4. Atom
ATOM = CFWS + r"?" + ATEXT + r"+" + CFWS + r"?"  # see 3.2.4
DOT_ATOM_TEXT = ATEXT + r"+(?:\." + ATEXT + r"+)*"  # see 3.2.4
DOT_ATOM = CFWS + r"?" + DOT_ATOM_TEXT + CFWS + r"?"  # see 3.2.4
QTEXT = r"[" + NO_WS_CTL + r"\x21\x23-\x5b\x5d-\x7e]"  # see 3.2.5. Quoted strings
QCONTENT = r"(?:" + QTEXT + r"|" + QUOTED_PAIR + r")"  # see 3.2.5
QUOTED_STRING = CFWS + r"?" + r'"(?:' + FWS + r"?" + QCONTENT + r")*" + FWS + r"?" + r'"' + CFWS + r"?"
LOCAL_PART = r"(?:" + DOT_ATOM + r"|" + QUOTED_STRING + r")"  # see 3.4.1. Addr-spec specification
DTEXT = r"[" + NO_WS_CTL + r"\x21-\x5a\x5e-\x7e]"  # see 3.4.1
DCONTENT = r"(?:" + DTEXT + r"|" + QUOTED_PAIR + r")"  # see 3.4.1
DOMAIN_LITERAL = (
	CFWS + r"?" + r"\[" + r"(?:" + FWS + r"?" + DCONTENT + r")*" + FWS + r"?\]" + CFWS + r"?"
)  # see 3.4.1
DOMAIN = r"(?:" + DOT_ATOM + r"|" + DOMAIN_LITERAL + r")"  # see 3.4.1
ADDR_SPEC = LOCAL_PART + r"@" + DOMAIN  # see 3.4.1

# A valid address will match exactly the 3.4.1 addr-spec.
VALID_ADDRESS_REGEXP = re.compile(r"^" + ADDR_SPEC + r"$")

MX_DNS_CACHE = {}
MX_CHECK_CACHE = {}


def get_mx_ip(mx_host):
	"""
	Get the IP address of a given MX host

	:param mx_host: The host being looked up
	:type mx_host: str
	:return: A list of IP addresses
	:rtype: list
	"""
	if mx_host not in MX_DNS_CACHE:
		try:
			resolver = Resolver(configure=False)
			resolver.nameservers = ["1.1.1.1", "1.0.0.1", "8.8.8.8", "8.8.4.4"]
			answers = resolver.query(mx_host, "MX")

			mx_lookup_result = []

			for answer in answers:
				mx_lookup_result.append((answer.preference, answer.exchange.to_text()[:-1]))
			MX_DNS_CACHE[mx_host] = mx_lookup_result
		except Exception:
			raise
	return MX_DNS_CACHE[mx_host]


def check_mx_record(email, verify=False, smtp_timeout=10):
	"""
	Checks for an MX record on the given email addresses' hostname.

	:param email: The email address
	:type email: str
	:param verify: Whether the email address' existence should be verified
	:type verify: bool
	:param smtp_timeout: Maximum wait time on an SMTP connection
	:type smtp_timeout: int
	:return: bool or None
	"""
	hostname = email[email.find("@") + 1 :]
	mx_hosts = get_mx_ip(hostname)
	if mx_hosts is None:
		return False
	for mx_host in mx_hosts:
		with contextlib.suppress(Exception):
			if not verify and mx_host[1] in MX_CHECK_CACHE:
				return MX_CHECK_CACHE[mx_host[1]]
			smtp = smtplib.SMTP(timeout=smtp_timeout)
			smtp.connect(mx_host[1])
			MX_CHECK_CACHE[mx_host[1]] = True
			if not verify:
				try:  # noqa: SIM105
					smtp.quit()
				except smtplib.SMTPServerDisconnected:
					pass
				return True
			status, _ = smtp.helo()
			if status != 250:
				smtp.quit()
				continue
			smtp.mail("")
			status, _ = smtp.rcpt(email)
			if status == 250:
				smtp.quit()
				return True
			smtp.quit()
	return None


def validate_email(email, check_mx=False, verify=False, smtp_timeout=10, **kwargs):
	"""
	Indicate whether the given string is a valid email address according to the 'addr-spec' portion
	of RFC 2822 (see section 3.4.1).  Parts of the spec that are marked obsolete are *not* included
	in this test, and certain arcane constructions that depend on circular definitions in the spec
	may not pass, but in general this should correctly identify any email address likely to be in
	use as of 2011.

	:param email: The email address to be validated
	:type email: str
	:param check_mx: Whether or not MX records should be verified
	:type check_mx: bool
	:param verify: Whether or not the email addresses' actual existence should be verified
	:type verify: bool
	:param smtp_timeout: Maximum wait time on an SMTP connection
	:type smtp_timeout: int
	:return: The validity of the given email address
	:rtype: bool or None
	"""
	try:
		if re.match(VALID_ADDRESS_REGEXP, email) is not None:
			check_mx |= verify
			if check_mx:
				return check_mx_record(email, verify=verify, smtp_timeout=smtp_timeout)
		else:
			return False
	except Exception:
		return None
	else:
		return True
