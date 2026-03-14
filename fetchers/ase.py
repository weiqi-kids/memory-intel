"""
日月光投控官網爬蟲

抓取來源：
- ASE Global Press Room: https://www.aseglobal.com/press-room/
"""

from datetime import datetime
from typing import Optional
import re
import logging

from .base import CompanyFetcher, CompanyDocument

logger = logging.getLogger(__name__)


class ASEFetcher(CompanyFetcher):
    """日月光投控官網爬蟲 - Playwright"""

    company_id = "ase"
    company_name = "日月光投控"

    ir_url = None
    news_url = "https://ase.aseglobal.com/en/press_room"

    wait_for_selector = "a[href*='press'], article, .content, body"
    timeout = 90000  # 增加超時時間

    def parse_ir(self, html: str) -> list[CompanyDocument]:
        return []

    def parse_news(self, html: str) -> list[CompanyDocument]:
        """解析日月光新聞頁面"""
        soup = self._parse_html(html)
        documents = []

        try:
            # 嘗試多種選擇器
            news_links = soup.select('a[href*="/press_room/content/"]')
            if not news_links:
                news_links = soup.select('a[href*="/press-room/"]')
            if not news_links:
                news_links = soup.select('a[href*="press"]')

            seen_urls = set()
            logger.info(f"Found {len(news_links)} news links")

            for link in news_links[:50]:
                try:
                    url = link.get('href', '')
                    if not url or url in seen_urls:
                        continue

                    # 補全 URL
                    if url.startswith('/'):
                        url = 'https://ase.aseglobal.com' + url
                    elif not url.startswith('http'):
                        url = 'https://ase.aseglobal.com/' + url

                    seen_urls.add(url)

                    # 取得標題
                    raw_text = link.get_text(strip=True)
                    if not raw_text or len(raw_text) < 10:
                        continue

                    # 跳過導覽連結
                    if raw_text.lower() in ['press room', 'more', '更多', 'press', 'news']:
                        continue

                    # 嘗試從上層元素取得日期
                    published_at = None
                    parent = link.find_parent(['li', 'div', 'article', 'tr'])
                    if parent:
                        # 方法 1: 標準日期元素
                        date_elem = parent.select_one('.date, time, .news-date, span.time')
                        if date_elem:
                            date_text = date_elem.get_text(strip=True)
                            published_at = self._parse_date(date_text)

                        # 方法 2: 相鄰的 span 或 div
                        if not published_at:
                            for sibling in parent.find_all(['span', 'div'], recursive=False):
                                text = sibling.get_text(strip=True)
                                if len(text) < 15 and any(c.isdigit() for c in text):
                                    parsed = self._parse_date(text)
                                    if parsed:
                                        published_at = parsed
                                        break

                        # 方法 3: 從父元素文字提取
                        if not published_at:
                            parent_text = parent.get_text()
                            date_match = re.search(r'(\d{4}[-/\.]\d{1,2}[-/\.]\d{1,2})', parent_text)
                            if date_match:
                                published_at = self._parse_date(date_match.group(1))
                            else:
                                # 英文格式 March 14, 2026
                                date_match = re.search(r'(\w+ \d{1,2}, \d{4})', parent_text)
                                if date_match:
                                    published_at = self._parse_date(date_match.group(1))

                    # 自動標籤
                    tags = ["news"]
                    title_lower = raw_text.lower()
                    if any(kw in title_lower for kw in ['packaging', 'package', '封裝']):
                        tags.append('packaging')
                    if any(kw in title_lower for kw in ['hbm', 'advanced packaging', 'vipack']):
                        tags.append('advanced_packaging')
                    if any(kw in title_lower for kw in ['ai', 'hpc']):
                        tags.append('ai')
                    if any(kw in title_lower for kw in ['earnings', 'quarter', 'results', 'revenue']):
                        tags.append('earnings')
                    if any(kw in title_lower for kw in ['focos', 'chiplet', 'tsv']):
                        tags.append('chiplet')

                    doc = CompanyDocument(
                        company_id=self.company_id,
                        doc_type="news",
                        title=raw_text,
                        url=url,
                        published_at=published_at,
                        language="en",
                        tags=list(set(tags))
                    )
                    documents.append(doc)

                except Exception as e:
                    logger.warning(f"Error parsing link: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error parsing ASE page: {e}")

        logger.info(f"Parsed {len(documents)} news from ASE")
        return documents

    def _parse_date(self, date_text: str) -> Optional[datetime]:
        """解析日期字串"""
        formats = [
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%Y.%m.%d",
            "%B %d, %Y",
            "%b %d, %Y",
        ]

        date_text = date_text.strip()

        for fmt in formats:
            try:
                return datetime.strptime(date_text, fmt)
            except ValueError:
                continue

        return None


# CLI 測試
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    fetcher = ASEFetcher()
    result = fetcher.fetch_all()

    print(f"=== ASE News ({len(result.get('news', []))} items) ===")
    for doc in result.get("news", [])[:10]:
        print(f"  [{doc.published_at}] {doc.title[:60]}...")
        print(f"    Tags: {doc.tags}")
