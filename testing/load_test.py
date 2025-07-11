import asyncio
import json
import uuid

import aiohttp
import click

API_SITE_NEW = "/api/method/press.api.site.new"
API_SITE_NEW_SAAS = "/api/method/press.api.saas.new_saas_site"
API_SITE_ARCHIVE = "/api/method/press.api.site.archive"


async def _post(session: aiohttp.ClientSession, url: str, payload: dict) -> tuple[int, str]:
        async with session.post(url, json=payload) as response:
                text = await response.text()
                return response.status, text


async def create_site(session: aiohttp.ClientSession, base_url: str, token: str, site: dict, saas: bool) -> str:
        headers = {"Authorization": f"token {token}"}
        site_name = site.get("name") or uuid.uuid4().hex
        payload: dict[str, dict] | dict[str, str] = {}
        if saas:
                payload = {"subdomain": site_name, "app": site.get("app")}
                endpoint = API_SITE_NEW_SAAS
        else:
                payload = {"site": {**site, "name": site_name}}
                endpoint = API_SITE_NEW

        status, text = await _post(session, f"{base_url}{endpoint}", payload)
        if status != 200:
                raise Exception(f"Failed to create {site_name}: {text}")
        return site_name


async def archive_site(session: aiohttp.ClientSession, base_url: str, token: str, site_name: str) -> None:
        headers = {"Authorization": f"token {token}"}
        payload = {"name": site_name, "force": True}
        status, _ = await _post(session, f"{base_url}{API_SITE_ARCHIVE}", payload)
        if status != 200:
                raise Exception(f"Failed to archive {site_name}")


async def run_load_test(base_url: str, token: str, count: int, concurrency: int, saas: bool, cleanup: bool, site_template: str) -> None:
        sem = asyncio.Semaphore(concurrency)
        async with aiohttp.ClientSession(headers={"Authorization": f"token {token}"}) as session:
                site_payload = json.loads(site_template) if site_template else {}
                tasks = []
                for _ in range(count):
                        site = site_payload.copy()
                        site["name"] = uuid.uuid4().hex
                        tasks.append(asyncio.create_task(bound_sem(sem, create_site(session, base_url, token, site, saas))))

                created_sites = await asyncio.gather(*tasks)

                if cleanup:
                        cleanup_tasks = [
                                asyncio.create_task(bound_sem(sem, archive_site(session, base_url, token, name)))
                                for name in created_sites
                        ]
                        await asyncio.gather(*cleanup_tasks)


async def bound_sem(sem: asyncio.Semaphore, coro):
        async with sem:
                return await coro


@click.command()
@click.option("--base-url", required=True, help="Base URL of Press instance")
@click.option("--token", required=True, help="API token")
@click.option("--count", default=10, show_default=True, help="Number of sites to create")
@click.option("--concurrency", default=5, show_default=True, help="Number of concurrent requests")
@click.option("--saas", is_flag=True, help="Use SaaS site creation API")
@click.option("--cleanup", is_flag=True, help="Archive created sites after creation")
@click.option("--site-template", default="{}", help="JSON template for site payload")
def main(base_url: str, token: str, count: int, concurrency: int, saas: bool, cleanup: bool, site_template: str) -> None:
        """Load test helper to create multiple sites."""
        asyncio.run(run_load_test(base_url, token, count, concurrency, saas, cleanup, site_template))


if __name__ == "__main__":
        main()
