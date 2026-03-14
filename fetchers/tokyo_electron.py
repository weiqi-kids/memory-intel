"""
Tokyo Electron 官網爬蟲

抓取來源：
- TEL News Room: https://www.tel.com/news/
"""

from datetime import datetime
from typing import Optional
import re
import logging

from .base import CompanyFetcher, CompanyDocument

logger = logging.getLogger(__name__)


class TokyoElectronFetcher(CompanyFetcher):
    """Tokyo Electron 官網爬蟲 - Playwright"""

    company_id = "tokyo_electron"
    company_name = "Tokyo Electron"

    ir_url = None
    news_url = "https://www.tel.com/news/"

    wait_for_selector = ".news-list, .newsItem, article"
    timeout = 60000

    def parse_ir(self, html: str) -> list[CompanyDocument]:
        return []

    def parse_news(self, html: str) -> list[CompanyDocument]:
        """解析 TEL News Room 頁面"""
        soup = self._parse_html(html)
        documents = []

        try:
            # 找所有新聞連結
            news_links = soup.select('a[href*="/news/"]')

            seen_urls = set()
            logger.info(f"Found {len(news_links)} news links")

            for link in news_links[:50]:
                try:
                    url = link.get('href', '')
                    if not url or url in seen_urls:
                        continue

                    # 只要實際的新聞文章（含日期路徑）
                    if not re.search(r'/news/(topics|ir|event)/\d{4}/', url):
                        continue

                    # 補全 URL
                    if url.startswith('/'):
                        url = 'https://www.tel.com' + url

                    seen_urls.add(url)

                    # 取得標題
                    raw_text = link.get_text(strip=True)
                    if not raw_text or len(raw_text) < 10:
                        continue

                    # 從 URL 提取日期
                    published_at = None
                    date_match = re.search(r'/(\d{4})(\d{2})(\d{2})_', url)
                    if date_match:
                        year, month, day = date_match.groups()
                        try:
                            published_at = datetime(int(year), int(month), int(day))
                        except ValueError:
                            pass

                    # 自動標籤
                    tags = ["news"]
                    title_lower = raw_text.lower()
                    if 'euv' in title_lower:
                        tags.append('euv')
                    if any(kw in title_lower for kw in ['etch', 'deposition', 'coater']):
                        tags.append('equipment')
                    if any(kw in title_lower for kw in ['earnings', 'quarter', 'results', 'revenue', 'financial']):
                        tags.append('earnings')
                    if any(kw in title_lower for kw in ['3d', 'advanced packaging', 'bonding']):
                        tags.append('advanced_packaging')
                    if 'semicon' in title_lower:
                        tags.append('event')

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
            logger.error(f"Error parsing TEL page: {e}")

        logger.info(f"Parsed {len(documents)} news from Tokyo Electron")
        return documents


# CLI 測試
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    fetcher = TokyoElectronFetcher()
    result = fetcher.fetch_all()

    print(f"=== Tokyo Electron News ({len(result.get('news', []))} items) ===")
    for doc in result.get("news", [])[:10]:
        print(f"  [{doc.published_at}] {doc.title[:60]}...")
        print(f"    Tags: {doc.tags}")
