"""
Samsung 官網爬蟲

抓取來源：
- Samsung Newsroom RSS: https://news.samsung.com/global/feed (主要)
- Samsung IR: https://www.samsung.com/global/ir/ (備用，需 Playwright)
"""

from datetime import datetime
from typing import Optional
import xml.etree.ElementTree as ET
import re
import logging

try:
    import requests
except ImportError:
    requests = None

from .base import CompanyFetcher, CompanyDocument

logger = logging.getLogger(__name__)


class SamsungFetcher(CompanyFetcher):
    """Samsung 官網爬蟲 - 優先使用 RSS"""

    company_id = "samsung"
    company_name = "Samsung Electronics"

    # RSS Feed（優先使用）
    rss_url = "https://news.samsung.com/global/category/semiconductor/feed"

    # 備用 Playwright
    ir_url = "https://www.samsung.com/global/ir/financial-information/earnings-release/"
    news_url = "https://news.samsung.com/global/"

    def fetch_all(self) -> dict[str, list[CompanyDocument]]:
        """優先使用 RSS 抓取"""
        result = {}

        # 先嘗試 RSS
        news = self._fetch_rss()
        if news:
            result["news"] = news
        else:
            # RSS 失敗，嘗試 Playwright
            logger.info("RSS failed, trying Playwright...")
            with self:
                result["news"] = self.fetch_news()

        return result

    def _fetch_rss(self) -> list[CompanyDocument]:
        """從 RSS Feed 抓取新聞"""
        if requests is None:
            logger.warning("requests not installed")
            return []

        try:
            logger.info(f"Fetching RSS: {self.rss_url}")
            response = requests.get(
                self.rss_url,
                headers={"User-Agent": "Mozilla/5.0 (compatible; MemoryIntel/1.0)"},
                timeout=30
            )
            response.raise_for_status()

            return self._parse_rss(response.text)

        except Exception as e:
            logger.error(f"RSS fetch failed: {e}")
            return []

    def _parse_rss(self, xml_content: str) -> list[CompanyDocument]:
        """解析 RSS XML"""
        documents = []

        try:
            root = ET.fromstring(xml_content)

            # RSS 2.0 格式
            for item in root.findall(".//item")[:30]:
                try:
                    title = item.findtext("title", "").strip()
                    url = item.findtext("link", "").strip()
                    pub_date = item.findtext("pubDate", "")
                    description = item.findtext("description", "")

                    # 從 content:encoded 取得完整內容
                    content_ns = "{http://purl.org/rss/1.0/modules/content/}"
                    content = item.findtext(f"{content_ns}encoded", "")

                    if not title or not url:
                        continue

                    # 解析日期
                    published_at = self._parse_rss_date(pub_date)

                    # 清理 HTML，取得完整內文
                    clean_content = self._strip_html(content or description)

                    # 分類標籤
                    tags = ["news"]
                    for category in item.findall("category"):
                        tag = category.text
                        if tag:
                            tags.append(tag.lower())

                    # 自動標籤
                    title_lower = title.lower()
                    if 'hbm' in title_lower:
                        tags.append('hbm')
                    if any(kw in title_lower for kw in ['memory', 'dram', 'nand', 'semiconductor']):
                        tags.append('memory')
                    if any(kw in title_lower for kw in ['earnings', 'quarter', 'results', 'revenue', 'profit']):
                        tags.append('earnings')

                    doc = CompanyDocument(
                        company_id=self.company_id,
                        doc_type="news",
                        title=title,
                        url=url,
                        published_at=published_at,
                        content=clean_content,
                        language="en",
                        tags=list(set(tags))
                    )
                    documents.append(doc)

                except Exception as e:
                    logger.warning(f"Error parsing RSS item: {e}")
                    continue

        except ET.ParseError as e:
            logger.error(f"XML parse error: {e}")

        logger.info(f"Parsed {len(documents)} news from Samsung RSS")
        return documents

    def _parse_rss_date(self, date_str: str) -> Optional[datetime]:
        """解析 RSS 日期格式"""
        # RSS 日期格式: "Wed, 11 Mar 2026 08:00:00 +0000"
        formats = [
            "%a, %d %b %Y %H:%M:%S %z",
            "%a, %d %b %Y %H:%M:%S %Z",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%d",
        ]

        date_str = date_str.strip()

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        return None

    def _strip_html(self, html: str) -> str:
        """移除 HTML 標籤"""
        # 簡單的 HTML 清理
        import re
        clean = re.sub(r'<[^>]+>', '', html)
        clean = re.sub(r'\s+', ' ', clean)
        return clean.strip()

    def parse_ir(self, html: str) -> list[CompanyDocument]:
        """解析 Samsung IR 頁面（備用）"""
        soup = self._parse_html(html)
        documents = []

        try:
            # 找所有法說會連結
            items = soup.select('a[href*="conference"], a[href*="earnings"], a[href*=".pdf"]')

            for item in items[:20]:
                title = item.get_text(strip=True)
                url = item.get('href', '')

                if not title or not url:
                    continue

                if not any(kw in title.lower() for kw in ['quarter', 'q1', 'q2', 'q3', 'q4', 'earnings', 'conference']):
                    continue

                if not url.startswith('http'):
                    url = 'https://www.samsung.com' + url

                doc = CompanyDocument(
                    company_id=self.company_id,
                    doc_type="ir",
                    title=title,
                    url=url,
                    language="en",
                    tags=["earnings", "ir"]
                )
                documents.append(doc)

        except Exception as e:
            logger.error(f"Error parsing IR: {e}")

        return documents

    def parse_news(self, html: str) -> list[CompanyDocument]:
        """解析 Samsung Newsroom（備用）"""
        soup = self._parse_html(html)
        documents = []

        try:
            articles = soup.select('article, .post-item, [class*="post"]')

            for article in articles[:30]:
                title_elem = article.select_one('h2 a, h3 a, .title a')
                if not title_elem:
                    continue

                title = title_elem.get_text(strip=True)
                url = title_elem.get('href', '')

                if not title or not url:
                    continue

                if not url.startswith('http'):
                    url = 'https://news.samsung.com' + url

                doc = CompanyDocument(
                    company_id=self.company_id,
                    doc_type="news",
                    title=title,
                    url=url,
                    language="en",
                    tags=["news"]
                )
                documents.append(doc)

        except Exception as e:
            logger.error(f"Error parsing news: {e}")

        return documents


# CLI 測試
if __name__ == "__main__":
    fetcher = SamsungFetcher()
    result = fetcher.fetch_all()

    print("=== Samsung News (from RSS) ===")
    for doc in result.get("news", [])[:10]:
        print(f"  [{doc.published_at}] {doc.title[:60]}...")
        print(f"    URL: {doc.url}")
        print(f"    Tags: {doc.tags}")
