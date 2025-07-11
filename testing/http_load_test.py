import json
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed

import click
import requests

API_SITE_NEW = "/api/method/press.api.site.new"
API_SITE_NEW_SAAS = "/api/method/press.api.saas.new_saas_site"
API_SITE_ARCHIVE = "/api/method/press.api.site.archive"


def create_site(base_url: str, token: str, site: dict, saas: bool) -> str:
    """Create a site using the HTTP API."""
    headers = {"Authorization": f"token {token}"}
    site_name = site.get("name") or uuid.uuid4().hex

    if saas:
        payload = {"subdomain": site_name, "app": site.get("app")}
        endpoint = API_SITE_NEW_SAAS
    else:
        payload = {"site": {**site, "name": site_name}}
        endpoint = API_SITE_NEW

    resp = requests.post(f"{base_url}{endpoint}", json=payload, headers=headers, timeout=30)
    if resp.status_code != 200:
        raise Exception(f"Failed to create {site_name}: {resp.text}")
    return site_name


def archive_site(base_url: str, token: str, site_name: str) -> None:
    """Archive a site via the HTTP API."""
    headers = {"Authorization": f"token {token}"}
    payload = {"name": site_name, "force": True}
    resp = requests.post(f"{base_url}{API_SITE_ARCHIVE}", json=payload, headers=headers, timeout=30)
    if resp.status_code != 200:
        raise Exception(f"Failed to archive {site_name}: {resp.text}")


def run_load_test(base_url: str, token: str, count: int, concurrency: int, saas: bool, cleanup: bool, site_template: str) -> None:
    """Create multiple sites concurrently for load testing."""
    site_payload = json.loads(site_template) if site_template else {}
    created_sites: list[str] = []

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [
            executor.submit(create_site, base_url, token, {**site_payload, "name": uuid.uuid4().hex}, saas)
            for _ in range(count)
        ]
        for future in as_completed(futures):
            created_sites.append(future.result())

    if cleanup:
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = [executor.submit(archive_site, base_url, token, name) for name in created_sites]
            for future in as_completed(futures):
                future.result()


@click.command()
@click.option("--base-url", required=True, help="Base URL of Press instance")
@click.option("--token", required=True, help="API token")
@click.option("--count", default=10, show_default=True, help="Number of sites to create")
@click.option("--concurrency", default=5, show_default=True, help="Number of concurrent requests")
@click.option("--saas", is_flag=True, help="Use SaaS site creation API")
@click.option("--cleanup", is_flag=True, help="Archive created sites after creation")
@click.option("--site-template", default="{}", help="JSON template for site payload")
def main(base_url: str, token: str, count: int, concurrency: int, saas: bool, cleanup: bool, site_template: str) -> None:
    """Run the load test using simple requests."""
    run_load_test(base_url, token, count, concurrency, saas, cleanup, site_template)


if __name__ == "__main__":
    main()
