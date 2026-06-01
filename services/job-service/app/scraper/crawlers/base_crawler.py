"""
Abstract base class for all job board crawlers.
Each crawler implements `fetch_job_listings` and `parse_job_detail`.
"""
import asyncio
import hashlib
import logging
import random
from abc import ABC, abstractmethod
from datetime import datetime

import httpx
from playwright.async_api import async_playwright

from shared.models.job import RawJob

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
]

PROXY_POOL: list[str] = []  # Populated from env: PROXY_LIST=http://user:pass@host:port,...


class BaseCrawler(ABC):
    def __init__(self, source_name: str, use_playwright: bool = False):
        self.source_name = source_name
        self.use_playwright = use_playwright

    @abstractmethod
    async def fetch_job_listings(self, query: str, location: str, page: int = 1) -> list[str]:
        """Return list of job detail URLs."""
        ...

    @abstractmethod
    async def parse_job_detail(self, url: str, html: str) -> dict:
        """Extract structured fields from raw HTML."""
        ...

    async def crawl(self, query: str, location: str, max_pages: int = 5) -> list[RawJob]:
        jobs: list[RawJob] = []
        for page in range(1, max_pages + 1):
            try:
                urls = await self.fetch_job_listings(query, location, page)
                if not urls:
                    break
                for url in urls:
                    html = await self._fetch_html(url)
                    job = RawJob(
                        job_id=hashlib.sha256(url.encode()).hexdigest()[:16],
                        source=self.source_name,
                        raw_html=html,
                        scraped_at=datetime.utcnow(),
                        idempotency_key=hashlib.sha256(
                            f"{url}:{datetime.utcnow().date()}".encode()
                        ).hexdigest(),
                    )
                    jobs.append(job)
                    await self._human_delay()
            except Exception as e:
                logger.warning("Page %d crawl error for %s: %s", page, self.source_name, e)
                break
        return jobs

    async def _fetch_html(self, url: str) -> str:
        if self.use_playwright:
            return await self._fetch_playwright(url)
        return await self._fetch_httpx(url)

    async def _fetch_httpx(self, url: str) -> str:
        proxy = random.choice(PROXY_POOL) if PROXY_POOL else None
        async with httpx.AsyncClient(
            proxy=proxy,
            headers={"User-Agent": random.choice(USER_AGENTS)},
            follow_redirects=True,
            timeout=15.0,
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.text

    async def _fetch_playwright(self, url: str) -> str:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"],
            )
            context = await browser.new_context(
                user_agent=random.choice(USER_AGENTS),
                viewport={"width": 1920, "height": 1080},
                locale="en-US",
            )
            page = await context.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=20000)
            content = await page.content()
            await browser.close()
            return content

    async def _human_delay(self) -> None:
        delay = random.uniform(1.5, 4.0) + random.gauss(0, 0.3)
        await asyncio.sleep(max(delay, 0.5))
