"""
Apple 官網爬蟲

抓取來源：
- Apple Newsroom RSS: https://www.apple.com/newsroom/rss-feed.rss
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


class AppleFetcher(CompanyFetcher):
    """Apple 官網爬蟲 - RSS"""

    company_id = "apple"
    company_name = "Apple"

    rss_url = "https://www.apple.com/newsroom/rss-feed.rss"

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
        """解析 RSS XML (支援 Atom 和傳統 RSS 格式)"""
        documents = []

        try:
            root = ET.fromstring(xml_content)

            # Atom 命名空間
            ns = {'atom': 'http://www.w3.org/2005/Atom'}

            # 支援 Atom (entry) 和傳統 RSS (item)
            items = root.findall('.//atom:entry', ns)
            is_atom = len(items) > 0

            if not is_atom:
                items = root.findall(".//item")

            for item in items[:30]:
                try:
                    if is_atom:
                        # Atom 格式
                        title = item.findtext("atom:title", "", ns).strip()
                        # Atom link 在 href 屬性中
                        link_elem = item.find("atom:link", ns)
                        url = link_elem.get("href", "") if link_elem is not None else ""
                        pub_date = item.findtext("atom:updated", "", ns)
                        description = item.findtext("atom:content", "", ns) or item.findtext("atom:summary", "", ns)
                    else:
                        # 傳統 RSS 格式
                        title = item.findtext("title", "").strip()
                        url = item.findtext("link", "").strip()
                        pub_date = item.findtext("pubDate", "")
                        description = item.findtext("description", "")

                    if not title or not url:
                        continue

                    # 解析日期
                    published_at = self._parse_rss_date(pub_date)

                    # 清理 HTML
                    clean_content = self._strip_html(description)

                    # 分類標籤
                    tags = ["news"]

                    # 自動標籤
                    title_lower = title.lower()
                    if any(kw in title_lower for kw in ['iphone', 'ipad', 'mac', 'watch']):
                        tags.append('product')
                    if any(kw in title_lower for kw in ['m1', 'm2', 'm3', 'm4', 'm5', 'chip', 'silicon']):
                        tags.append('chip')
                    if any(kw in title_lower for kw in ['ai', 'intelligence', 'siri']):
                        tags.append('ai')
                    if any(kw in title_lower for kw in ['earnings', 'quarter', 'results', 'revenue']):
                        tags.append('earnings')
                    if any(kw in title_lower for kw in ['memory', 'ram', 'storage']):
                        tags.append('memory')

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

        logger.info(f"Parsed {len(documents)} news from Apple RSS")
        return documents

    def _parse_rss_date(self, date_str: str) -> Optional[datetime]:
        """解析 RSS 日期格式 (支援 Atom ISO 8601 和傳統 RSS 格式)"""
        formats = [
            "%Y-%m-%dT%H:%M:%S.%fZ",     # 2026-03-14T03:12:58.944Z (Atom)
            "%Y-%m-%dT%H:%M:%SZ",         # 2026-03-14T03:12:58Z (Atom)
            "%Y-%m-%dT%H:%M:%S%z",        # 2026-03-14T03:12:58+00:00
            "%a, %d %b %Y %H:%M:%S %Z",   # RFC 822 (RSS)
            "%a, %d %b %Y %H:%M:%S %z",
            "%Y-%m-%d",
        ]

        date_str = date_str.strip()

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        # 嘗試 fromisoformat (Python 3.11+)
        try:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except ValueError:
            pass

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
    fetcher = AppleFetcher()
    result = fetcher.fetch_all()

    print(f"=== Apple News ({len(result.get('news', []))} items) ===")
    for doc in result.get("news", [])[:10]:
        print(f"  [{doc.published_at}] {doc.title[:60]}...")
        print(f"    Tags: {doc.tags}")
