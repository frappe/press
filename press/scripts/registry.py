import grequests
import requests
import frappe
from tqdm import tqdm

frappe.init(site="frappe.cloud")
frappe.connect()
settings = frappe.get_single("Press Settings")

REGISTRY_URL = settings.docker_registry_url


headers = {"Accept": "application/vnd.docker.distribution.manifest.list.v2+json"}
auth = (settings.docker_registry_username, settings.docker_registry_password)


def _url(url):
	return f"https://{REGISTRY_URL}/v2/{url}"


def get(url, params=None):
	if params is None:
		params = {}
	return requests.get(_url(url), auth=auth, headers=headers, params=params)


def gget(url):
	return grequests.get(_url(url), auth=auth, headers=headers)


def ghead(url):
	return grequests.head(_url(url), auth=auth, headers=headers)


def get_repositories():
	repositories = []
	last = None
	params = {"n": 1000}
	while True:
		params.update({"last": last} if last else {})
		current = get("_catalog", params=params).json()["repositories"]

		if not current:
			break
		last = current[-1]
		repositories.extend(current)

	return repositories


def get_tags(repositories):
	tags = []
	tag_requests = []
	print("Generating tags/list Requests")
	for repository in tqdm(repositories):
		tag_requests.append(gget(f"{repository}/tags/list"))

	print("Sending tags/list Requests")
	for tag_response in tqdm(
		grequests.imap(tag_requests, size=None), total=len(tag_requests)
	):
		tag_response = tag_response.json()
		current = [
			{"repository": tag_response["name"], "tag": tag}
			for tag in tag_response.get("tags") or []
		]
		tags.extend(current)

	return tags


def get_layers(tags):
	layers = []
	layer_requests = []
	print("Generating manifest Requests")
	for tag in tqdm(tags):
		layer_requests.append(gget(f"{tag['repository']}/manifests/{tag['tag']}"))

	print("Sending manifest Requests")
	for layer_response in tqdm(
		grequests.imap(layer_requests, size=None), total=len(layer_requests)
	):
		layer_response = layer_response.json()
		current = [
			{
				"repository": layer_response["name"],
				"tag": layer_response["tag"],
				"digest": layer["blobSum"],
			}
			for layer in layer_response.get("fsLayers") or []
		]
		layers.extend(current)
	return layers


def exception_handler(request, exception):
	print("Request failed", request, exception)


def check_layers(layers):
	checked_layers = set()
	failed_layers = set()
	layer_requests = []
	print("Generating blob Requests")
	for layer in tqdm(layers):
		if layer["digest"] in checked_layers:
			continue
		layer_requests.append(ghead(f"{layer['repository']}/blobs/{layer['digest']}"))
		checked_layers.add(layer["digest"])

	print("Sending blob Requests")
	for layer_response in tqdm(
		grequests.imap(layer_requests, size=None, exception_handler=exception_handler),
		total=len(layer_requests),
	):
		if layer_response.status_code != 200:
			current = layer_response.request.url
			failed_layers.add(current)

	return failed_layers


if __name__ == "__main__":
	repositories = get_repositories()
	print(f"Found {len(repositories)} repositories")

	tags = get_tags(repositories)
	print(f"Found {len(tags)} tags")

	layers = get_layers(tags)
	print(f"Found {len(layers)} layers")

	failed_layers = check_layers(layers)
	print(f"Failure: {len(failed_layers)} layers")
	for layer in failed_layers:
		print(layer)
