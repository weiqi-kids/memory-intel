"""
Applied Materials 官網爬蟲
"""

from datetime import datetime
from typing import Optional
import logging

from .base import CompanyFetcher, CompanyDocument

logger = logging.getLogger(__name__)


class AppliedMaterialsFetcher(CompanyFetcher):
    """Applied Materials 爬蟲"""

    company_id = "applied_materials"
    company_name = "Applied Materials"
    news_url = "https://ir.appliedmaterials.com/news-releases"
    ir_rss_url = "https://ir.appliedmaterials.com/rss/news-releases.xml"
    fetch_mode = "rss"
    http_timeout = 60
    ir_url = "https://ir.appliedmaterials.com/quarterly-results"

    def parse_news(self, html: str) -> list[CompanyDocument]:
        """解析新聞頁面"""
        soup = self._parse_html(html)
        documents = []

        # 嘗試多種常見 CSS selector
        selectors = [
            "article",
            "[class*='press']",
            "[class*='news-item']",
            "[class*='release']",
            ".media-item",
            ".post-item",
            "li.item",
        ]

        articles = []
        for sel in selectors:
            articles = soup.select(sel)
            if articles:
                break

        for article in articles[:30]:
            # 找標題和連結
            title_elem = article.select_one("h2 a, h3 a, h4 a, a.title, .title a, a[class*='title']")
            if not title_elem:
                # 嘗試直接找 h2/h3
                heading = article.select_one("h2, h3, h4")
                link = article.select_one("a[href]")
                if heading and link:
                    title = heading.get_text(strip=True)
                    url = link.get("href", "")
                elif link:
                    title = link.get_text(strip=True)
                    url = link.get("href", "")
                else:
                    continue
            else:
                title = title_elem.get_text(strip=True)
                url = title_elem.get("href", "")

            if not title or len(title) < 5:
                continue

            # 補全相對 URL
            if url and not url.startswith("http"):
                url = "https://www.appliedmaterials.com" + url

            # 找日期
            date_elem = article.select_one("time, .date, [class*='date'], [datetime]")
            published_at = None
            if date_elem:
                dt_str = date_elem.get("datetime") or date_elem.get_text(strip=True)
                if dt_str:
                    try:
                        published_at = datetime.fromisoformat(dt_str[:10])
                    except (ValueError, TypeError):
                        pass

            doc = CompanyDocument(
                company_id=self.company_id,
                doc_type="news",
                title=title,
                url=url,
                published_at=published_at,
                language="en",
                tags=["news"],
            )
            documents.append(doc)

        logger.info(f"Parsed {len(documents)} news from Applied Materials")
        return documents

    def parse_ir(self, html: str) -> list[CompanyDocument]:
        """解析 IR 頁面"""
        soup = self._parse_html(html)
        documents = []
        for item in soup.select("a[href*='quarter'], a[href*='earnings'], a[href*='.pdf']")[:20]:
            title = item.get_text(strip=True)
            url = item.get("href", "")
            if not title or len(title) < 5:
                continue
            if not url.startswith("http"):
                url = "https://www.appliedmaterials.com" + url
            doc = CompanyDocument(
                company_id=self.company_id,
                doc_type="ir",
                title=title,
                url=url,
                language="en",
                tags=["ir", "earnings"],
            )
            documents.append(doc)
        return documents


if __name__ == "__main__":
    fetcher = AppliedMaterialsFetcher()
    result = fetcher.fetch_all()
    for doc_type, docs in result.items():
        print(f"{doc_type}: {len(docs)} documents")
        for doc in docs[:5]:
            print(f"  [{doc.published_at}] {doc.title[:80]}")
