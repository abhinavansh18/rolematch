from bs4 import BeautifulSoup
from .base_crawler import BaseCrawler


class IndeedCrawler(BaseCrawler):
    BASE_URL = "https://www.indeed.com/jobs"

    def __init__(self):
        super().__init__(source_name="indeed", use_playwright=False)

    async def fetch_job_listings(self, query: str, location: str, page: int = 1) -> list[str]:
        start = (page - 1) * 10
        url = f"{self.BASE_URL}?q={query.replace(' ', '+')}&l={location.replace(' ', '+')}&start={start}"
        html = await self._fetch_httpx(url)
        soup = BeautifulSoup(html, "html.parser")
        links = soup.select("a[data-jk]")
        return [f"https://www.indeed.com/viewjob?jk={a['data-jk']}" for a in links if a.get("data-jk")]

    async def parse_job_detail(self, url: str, html: str) -> dict:
        soup = BeautifulSoup(html, "html.parser")
        title   = soup.select_one("h1.jobsearch-JobInfoHeader-title")
        company = soup.select_one("div[data-company-name]")
        desc    = soup.select_one("div#jobDescriptionText")
        return {
            "title":            title.text.strip() if title else "",
            "company":          company.text.strip() if company else "",
            "description_text": desc.get_text(separator="\n") if desc else "",
            "source_url":       url,
            "source_domain":    "indeed.com",
        }
