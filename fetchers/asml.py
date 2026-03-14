"""
ASML 官網爬蟲

抓取來源：
- ASML News: https://www.asml.com/en/news
"""

from datetime import datetime
from typing import Optional
import re
import logging

from .base import CompanyFetcher, CompanyDocument

logger = logging.getLogger(__name__)


class ASMLFetcher(CompanyFetcher):
    """ASML 官網爬蟲 - Playwright"""

    company_id = "asml"
    company_name = "ASML"

    ir_url = None
    news_url = "https://www.asml.com/en/news/press-releases"

    wait_for_selector = "a[href*='/press-releases/20']"
    timeout = 60000

    def parse_ir(self, html: str) -> list[CompanyDocument]:
        return []

    def parse_news(self, html: str) -> list[CompanyDocument]:
        """解析 ASML Press Releases 頁面"""
        soup = self._parse_html(html)
        documents = []

        try:
            # 找所有實際的新聞稿連結（含年份路徑）
            news_links = soup.select('a[href*="/press-releases/20"]')

            seen_urls = set()
            logger.info(f"Found {len(news_links)} press release links")

            for link in news_links[:50]:
                try:
                    url = link.get('href', '')
                    if not url or url in seen_urls:
                        continue

                    # 補全 URL
                    if url.startswith('/'):
                        url = 'https://www.asml.com' + url

                    # 跳過非新聞連結
                    if '/news/news-subscription' in url or '/news/media-' in url:
                        continue

                    seen_urls.add(url)

                    # 取得標題
                    raw_text = link.get_text(strip=True)
                    if not raw_text or len(raw_text) < 15:
                        continue

                    # 嘗試從文字中提取日期（格式：March 9, 2026Title...）
                    published_at = None
                    title = raw_text

                    # 匹配日期格式：Month DD, YYYY
                    date_pattern = r'^((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4})'
                    date_match = re.match(date_pattern, raw_text)
                    if date_match:
                        date_str = date_match.group(1)
                        published_at = self._parse_date(date_str)
                        # 移除日期部分取得標題
                        title = raw_text[len(date_str):].strip()

                    if not title or len(title) < 10:
                        continue

                    # 自動標籤
                    tags = ["news"]
                    title_lower = title.lower()
                    if 'euv' in title_lower:
                        tags.append('euv')
                    if any(kw in title_lower for kw in ['lithography', 'scanner']):
                        tags.append('equipment')
                    if any(kw in title_lower for kw in ['earnings', 'quarter', 'results', 'revenue', 'annual']):
                        tags.append('earnings')
                    if any(kw in title_lower for kw in ['agm', 'shareholder', 'investor']):
                        tags.append('ir')

                    doc = CompanyDocument(
                        company_id=self.company_id,
                        doc_type="news",
                        title=title,
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
            logger.error(f"Error parsing ASML page: {e}")

        logger.info(f"Parsed {len(documents)} news from ASML")
        return documents

    def _parse_date(self, date_text: str) -> Optional[datetime]:
        """解析日期字串"""
        formats = [
            "%Y-%m-%d",
            "%B %d, %Y",
            "%b %d, %Y",
            "%d %B %Y",
            "%d %b %Y",
            "%m/%d/%Y",
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
    fetcher = ASMLFetcher()
    result = fetcher.fetch_all()

    print(f"=== ASML News ({len(result.get('news', []))} items) ===")
    for doc in result.get("news", [])[:10]:
        print(f"  [{doc.published_at}] {doc.title[:60]}...")
        print(f"    Tags: {doc.tags}")
