"""Greenhouse job board API crawler — uses their public JSON API (no scraping needed)."""
import httpx
from .base_crawler import BaseCrawler
from shared.models.job import RawJob
import json
from datetime import datetime
import hashlib


class GreenhouseCrawler(BaseCrawler):
    def __init__(self):
        super().__init__(source_name="greenhouse", use_playwright=False)

    async def fetch_job_listings(self, query: str, location: str, page: int = 1) -> list[str]:
        # Greenhouse has a public board API; returns JSON directly
        # This crawler aggregates known company boards
        COMPANY_BOARDS = ["airbnb", "stripe", "notion", "figma", "vercel"]
        urls = []
        for company in COMPANY_BOARDS:
            urls.append(f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs?content=true")
        return urls

    async def parse_job_detail(self, url: str, html: str) -> dict:
        data = json.loads(html)
        return {
            "title":            data.get("title", ""),
            "company":          data.get("company_name", ""),
            "description_text": data.get("content", ""),
            "location":         data.get("location", {}).get("name", ""),
            "source_url":       data.get("absolute_url", url),
            "source_domain":    "greenhouse.io",
        }

    async def crawl(self, query: str, location: str, max_pages: int = 1) -> list[RawJob]:
        jobs = []
        urls = await self.fetch_job_listings(query, location)
        for url in urls:
            try:
                html = await self._fetch_httpx(url)
                import json as j
                data = j.loads(html)
                for job in data.get("jobs", []):
                    raw = RawJob(
                        job_id=hashlib.sha256(str(job.get("id", "")).encode()).hexdigest()[:16],
                        source=self.source_name,
                        raw_html=j.dumps(job),
                        scraped_at=datetime.utcnow(),
                        idempotency_key=hashlib.sha256(
                            f"{job.get('absolute_url', '')}:{datetime.utcnow().date()}".encode()
                        ).hexdigest(),
                    )
                    jobs.append(raw)
            except Exception as e:
                import logging; logging.getLogger(__name__).warning("Greenhouse crawl error: %s", e)
        return jobs
