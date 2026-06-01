"""
LinkedIn Jobs crawler (public listing pages only – respects ToS for public data).
Uses Playwright for JS-rendered content.
"""
import re

from bs4 import BeautifulSoup

from .base_crawler import BaseCrawler


class LinkedInCrawler(BaseCrawler):
    BASE_URL = "https://www.linkedin.com/jobs/search"

    def __init__(self):
        super().__init__(source_name="linkedin", use_playwright=True)

    async def fetch_job_listings(self, query: str, location: str, page: int = 1) -> list[str]:
        start = (page - 1) * 25
        url = (
            f"{self.BASE_URL}?keywords={query.replace(' ', '%20')}"
            f"&location={location.replace(' ', '%20')}&start={start}"
        )
        html = await self._fetch_playwright(url)
        soup = BeautifulSoup(html, "html.parser")
        links = soup.select("a.base-card__full-link")
        return [a["href"].split("?")[0] for a in links if a.get("href")]

    async def parse_job_detail(self, url: str, html: str) -> dict:
        soup = BeautifulSoup(html, "html.parser")

        title = soup.select_one("h1.top-card-layout__title")
        company = soup.select_one("a.topcard__org-name-link")
        location = soup.select_one("span.topcard__flavor--bullet")
        description = soup.select_one("div.show-more-less-html__markup")

        salary_text = ""
        criteria = soup.select("li.description__job-criteria-item")
        for c in criteria:
            header = c.select_one("h3")
            if header and "salary" in header.text.lower():
                salary_text = c.select_one("span").text.strip()

        return {
            "title": title.text.strip() if title else "",
            "company": company.text.strip() if company else "",
            "location": location.text.strip() if location else "",
            "description_text": description.get_text(separator="\n") if description else "",
            "source_url": url,
            "source_domain": "linkedin.com",
            "salary_raw": salary_text,
        }
