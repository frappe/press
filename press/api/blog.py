# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import re

import frappe
import requests
from frappe.utils.caching import redis_cache

from press.press.doctype.blog_read_status.blog_read_status import get_blog_read_status, has_read_blog


@frappe.whitelist()
def latest_blog():
	url = frappe.db.get_single_value("Press Settings", "latest_blog_url")
	if not url:
		return {"url": None, "show": False}

	metadata = get_blog_metadata(url)
	if not metadata:
		return {"url": url, "show": False}

	return {
		"url": url,
		"title": metadata["title"],
		"description": metadata["description"],
		"show": not has_read_blog(frappe.session.user, url),
	}


@frappe.whitelist()
def mark_read(blog: str):
	get_blog_read_status(frappe.session.user).mark_read(blog)


@redis_cache(ttl=60 * 60)
def get_blog_metadata(url: str) -> dict | None:
	try:
		response = requests.get(url, timeout=10)
		response.raise_for_status()
	except requests.RequestException:
		return None

	title = extract_meta_tag(response.text, "og:title")
	return {
		"title": title.split(" | ")[0].strip() if title else None,
		"description": extract_meta_tag(response.text, "og:description"),
	}


def extract_meta_tag(html: str, property: str) -> str | None:
	match = re.search(rf'<meta[^>]*property="{property}"[^>]*content="([^"]*)"', html)
	return match.group(1).strip() if match else None
