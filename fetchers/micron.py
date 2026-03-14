"""
Micron 官網爬蟲

抓取來源：
- Micron Newsroom: https://www.micron.com/about/newsroom
- Micron IR: https://investors.micron.com/news-releases
"""

from datetime import datetime
from typing import Optional
import re
import logging

from .base import CompanyFetcher, CompanyDocument

logger = logging.getLogger(__name__)


class MicronFetcher(CompanyFetcher):
    """Micron 官網爬蟲 - Playwright"""

    company_id = "micron"
    company_name = "Micron Technology"

    ir_url = "https://investors.micron.com/news-releases"
    news_url = None

    wait_for_selector = "article, .news-item, a[href*='news-release']"
    timeout = 60000

    def parse_ir(self, html: str) -> list[CompanyDocument]:
        """解析 Micron IR 頁面"""
        soup = self._parse_html(html)
        documents = []

        try:
            # 嘗試多種選擇器
            items = soup.select('.nir-widget--news-releases a[href*="news-release"]')
            if not items:
                items = soup.select('a[href*="news-release-details"]')
            if not items:
                items = soup.select('a[href*="news-releases"]')
            if not items:
                # 更通用的選擇器
                items = soup.select('article a, .news a, .press-release a')

            logger.info(f"Found {len(items)} news items")

            seen_urls = set()
            for item in items[:30]:
                try:
                    title = item.get_text(strip=True)
                    url = item.get('href', '')

                    if not title or not url or len(title) < 10:
                        continue

                    # 跳過導覽連結
                    if title.lower() in ['read more', 'learn more', 'view all']:
                        continue

                    # 補全 URL
                    if not url.startswith('http'):
                        url = 'https://investors.micron.com' + url

                    if url in seen_urls:
                        continue
                    seen_urls.add(url)

                    # 嘗試從父元素找日期
                    parent = item.find_parent(['div', 'li', 'tr', 'article'])
                    published_at = None
                    if parent:
                        # 方法 1: time 或 datetime 屬性
                        date_elem = parent.select_one('time, .date, [datetime], .nir-widget--date')
                        if date_elem:
                            date_text = date_elem.get('datetime') or date_elem.get_text(strip=True)
                            published_at = self._parse_date(date_text)

                        # 方法 2: 從 span 或 div 提取
                        if not published_at:
                            for elem in parent.select('span, div'):
                                text = elem.get_text(strip=True)
                                if len(text) < 20 and any(c.isdigit() for c in text):
                                    parsed = self._parse_date(text)
                                    if parsed:
                                        published_at = parsed
                                        break

                        # 方法 3: 從父元素文字中用正則提取
                        if not published_at:
                            parent_text = parent.get_text()
                            date_match = re.search(r'(\w+ \d{1,2}, \d{4})', parent_text)
                            if date_match:
                                published_at = self._parse_date(date_match.group(1))

                    # 自動標籤
                    tags = ["news", "ir", "press-release"]
                    title_lower = title.lower()
                    if 'hbm' in title_lower:
                        tags.append('hbm')
                    if any(kw in title_lower for kw in ['dram', 'nand', 'memory']):
                        tags.append('memory')
                    if any(kw in title_lower for kw in ['earnings', 'quarter', 'results', 'revenue', 'fiscal']):
                        tags.append('earnings')
                    if any(kw in title_lower for kw in ['ai', 'data center']):
                        tags.append('ai')

                    doc = CompanyDocument(
                        company_id=self.company_id,
                        doc_type="ir",
                        title=title,
                        url=url,
                        published_at=published_at,
                        language="en",
                        tags=list(set(tags))
                    )
                    documents.append(doc)

                except Exception as e:
                    logger.warning(f"Error parsing item: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error parsing Micron page: {e}")

        logger.info(f"Parsed {len(documents)} news from Micron")
        return documents

    def parse_news(self, html: str) -> list[CompanyDocument]:
        """Micron 不使用 news_url"""
        return []

    def _parse_date(self, date_text: str) -> Optional[datetime]:
        """解析日期字串"""
        formats = [
            "%Y-%m-%d",
            "%B %d, %Y",
            "%b %d, %Y",
            "%m/%d/%Y",
            "%d %B %Y",
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
    fetcher = MicronFetcher()
    result = fetcher.fetch_all()

    print(f"=== Micron News ({len(result.get('ir', []))} items) ===")
    for doc in result.get("ir", [])[:10]:
        print(f"  [{doc.published_at}] {doc.title[:60]}...")
        print(f"    Tags: {doc.tags}")
