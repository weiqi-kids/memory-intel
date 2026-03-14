"""
NVIDIA 官網爬蟲

抓取來源：
- NVIDIA Newsroom RSS: https://nvidianews.nvidia.com/releases.xml
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


class NVIDIAFetcher(CompanyFetcher):
    """NVIDIA 官網爬蟲 - RSS"""

    company_id = "nvidia"
    company_name = "NVIDIA"

    rss_url = "https://nvidianews.nvidia.com/releases.xml"

    def fetch_all(self) -> dict[str, list[CompanyDocument]]:
        """使用 RSS 抓取"""
        news = self._fetch_rss()
        return {"news": news} if news else {}

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

            for item in root.findall(".//item")[:30]:
                try:
                    title = item.findtext("title", "").strip()
                    url = item.findtext("link", "").strip()
                    pub_date = item.findtext("pubDate", "")
                    description = item.findtext("description", "")

                    if not title or not url:
                        continue

                    # 解析日期
                    published_at = self._parse_rss_date(pub_date)

                    # 清理 HTML
                    clean_content = self._strip_html(description)[:500]

                    # 分類標籤
                    tags = ["news"]

                    # 從 categories 取得標籤
                    for category in item.findall("categories/category"):
                        if category.text:
                            tags.append(category.text.lower())

                    # 自動標籤
                    title_lower = title.lower()
                    if 'hbm' in title_lower:
                        tags.append('hbm')
                    if any(kw in title_lower for kw in ['gpu', 'geforce', 'rtx']):
                        tags.append('gpu')
                    if any(kw in title_lower for kw in ['ai', 'inference', 'training']):
                        tags.append('ai')
                    if any(kw in title_lower for kw in ['earnings', 'quarter', 'results', 'revenue', 'profit']):
                        tags.append('earnings')
                    if any(kw in title_lower for kw in ['gtc', 'keynote']):
                        tags.append('gtc')

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

        logger.info(f"Parsed {len(documents)} news from NVIDIA RSS")
        return documents

    def _parse_rss_date(self, date_str: str) -> Optional[datetime]:
        """解析 RSS 日期格式"""
        formats = [
            "%a, %d %b %Y %H:%M:%S %Z",
            "%a, %d %b %Y %H:%M:%S %z",
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
        clean = re.sub(r'<[^>]+>', '', html)
        clean = re.sub(r'\s+', ' ', clean)
        return clean.strip()

    def parse_ir(self, html: str) -> list[CompanyDocument]:
        return []

    def parse_news(self, html: str) -> list[CompanyDocument]:
        return []


# CLI 測試
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    fetcher = NVIDIAFetcher()
    result = fetcher.fetch_all()

    print(f"=== NVIDIA News ({len(result.get('news', []))} items) ===")
    for doc in result.get("news", [])[:10]:
        print(f"  [{doc.published_at}] {doc.title[:60]}...")
        print(f"    Tags: {doc.tags}")
