import os
import re
import urllib.request
from selenium import webdriver
import requests
import subprocess

import click
import frappe
from bs4 import BeautifulSoup, SoupStrainer
from selenium.webdriver.chrome.options import Options
from urllib.parse import urlsplit, urlunsplit

CHROMEDRIVER_PATH = os.path.expanduser("~/chromedriver")

try:
	WEBSITE = frappe.utils.get_url()
except Exception:
	WEBSITE = "https://frappecloud.com"


def checks():
	if os.environ.get("CI"):
		return

	print("Running sanity checks...")

	try:
		if not initialize_webdriver():
			return
		test_browser_assets()
		test_signup_flow()
	except Exception as e:
		click.secho(f"An error occurred: {e}", fg="yellow")
		return


def initialize_webdriver():
	if not os.path.exists(CHROMEDRIVER_PATH):
		click.secho(
			f"Chromedriver not found at {CHROMEDRIVER_PATH}, Downloading from https://chromedriver.chromium.org/",
			fg="yellow",
		)
		download_chromedriver()

	global chrome

	options = Options()
	options.add_argument("--headless")
	options.add_argument("--no-sandbox")
	options.add_argument("--disable-dev-shm-usage")
	options.add_argument("--disable-setuid-sandbox")
	try:
		chrome = webdriver.Chrome(CHROMEDRIVER_PATH, options=options)
	except Exception as e:
		version = re.search(r"is (\d+.\d+.\d+.\d+) with", e.msg).group(1)
		download_chromedriver(version=version.rsplit(".", 1)[0])
		chrome = webdriver.Chrome(CHROMEDRIVER_PATH, options=options)
	return True


def download_chromedriver(version=None):
	if version:
		latest_release_url = (
			f"https://chromedriver.storage.googleapis.com/LATEST_RELEASE_{version}"
		)
	else:
		latest_release_url = "https://chromedriver.storage.googleapis.com/LATEST_RELEASE"

	latest_release = requests.get(latest_release_url).text
	subprocess.check_output(
		f"curl -o chromedriver.zip https://chromedriver.storage.googleapis.com/{latest_release}/chromedriver_linux64.zip".split()
	)
	subprocess.check_output(
		f"unzip -o chromedriver.zip -d {os.path.expanduser('~')}".split()
	)


def test_browser_assets():
	print(f"\nChecking health of assets and links for {WEBSITE}")
	hyperlinks = extract_hyperlinks(WEBSITE)

	for url in hyperlinks:
		Link(url).check()


def test_signup_flow():
	print(f"\nTesting signup flow for {WEBSITE}")
	click.secho("NOT IMPLEMENTED!", fg="yellow")


class Link:
	def __init__(self, address):
		self.address = address

	def check(self, address=None):
		if not address:
			address = self.address
		try:
			res = urllib.request.Request(
				url=address,
				headers={
					"user-agent": (
						"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6)"
						" AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.90"
						" Safari/537.36"
					)
				},
			)
			resp = urllib.request.urlopen(res)
			if resp.status in [400, 404, 403, 408, 409, 501, 502, 503]:
				click.secho(f"{address} ❌ ({resp.status}: {resp.reason})", fg="red")
			else:
				click.secho(f"{address} ✅", fg="green")

		except Exception as err:
			click.secho(f"{address} ⚠️  ({err})", fg="yellow")


def pattern_adjust(a, address):
	if a.startswith("/"):
		return f"{WEBSITE}{a}"

	try:
		if re.match("^#", a):
			return 0
		r = urlsplit(a)
		if r.scheme == "" and (r.netloc != "" or r.path != ""):
			d = urlunsplit(r)
			if re.match("^//", d):
				m = re.search(r"(?<=//)\S+", d)
				d = m.group(0)
				m = "https://" + d
				return m
		elif r.scheme == "" and r.netloc == "":
			return address + a
		else:
			return a
	except Exception:
		pass


def extract_hyperlinks(address):
	chrome.get(WEBSITE)
	chrome.implicitly_wait(5)
	response = chrome.page_source
	hyperlinks = set()
	tags = {"a": "href", "img": "src", "script": "src", "link": "href"}

	for key, value in iter(tags.items()):
		try:
			for link in BeautifulSoup(response, "html.parser", parse_only=SoupStrainer(key)):
				if link.has_attr(value):
					p = pattern_adjust(link[value], address)
					if p:
						if p not in hyperlinks:
							hyperlinks.add(p)

		except Exception as err:
			click.secho(f"{address} ⚠️  ({err})", fg="yellow")

	return hyperlinks


if __name__ == "__main__":
	checks()
