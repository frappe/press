# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

from io import BytesIO

import frappe
import requests
from PIL import Image
from tqdm import tqdm


def execute():
	IMAGE_FORMATS_TO_CONVERT = ["png", "jpeg", "jpg"]

	def convert_to_webp(screenshot):
		if screenshot.startswith("files") or screenshot.startswith("/files"):
			image_content = frappe.get_doc("File", {"file_url": screenshot}).get_content()
			image = Image.open(BytesIO(image_content))
		else:
			# load from url
			url = screenshot
			response = requests.get(url, stream=True)
			image = Image.open(response.raw)

		image = image.convert("RGB")
		filename = f"{screenshot.split('/')[-1].split('.')[0]}.webp"

		# convert to bytes
		image_bytes = BytesIO()
		image.save(image_bytes, "webp")
		image_bytes = image_bytes.getvalue()
		_file = frappe.get_doc(
			{
				"doctype": "File",
				"attached_to_field": "image",
				"folder": "Home/Attachments",
				"file_name": filename,
				"is_private": 0,
				"content": image_bytes,
			}
		)
		_file.save(ignore_permissions=True)
		return _file.file_url

	marketplace_app_names = frappe.get_all("Marketplace App", pluck="name")

	for app_name in tqdm(marketplace_app_names):
		app = frappe.get_doc("Marketplace App", app_name)

		if app.image and app.image.split(".")[-1] in IMAGE_FORMATS_TO_CONVERT:
			app.image = convert_to_webp(app.image)

		screenshots = app.screenshots

		for screenshot in screenshots:
			if screenshot.image.split(".")[-1] not in IMAGE_FORMATS_TO_CONVERT:
				continue

			screenshot.image = convert_to_webp(screenshot.image)

		app.save()
