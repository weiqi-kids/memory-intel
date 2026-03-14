"""
Microsoft 官網爬蟲

抓取來源：
- Microsoft News: https://news.microsoft.com/source/
"""

from datetime import datetime
from typing import Optional
import re
import logging

from .base import CompanyFetcher, CompanyDocument

logger = logging.getLogger(__name__)


class MicrosoftFetcher(CompanyFetcher):
    """Microsoft 官網爬蟲 - Playwright"""

    company_id = "microsoft"
    company_name = "Microsoft"

    ir_url = None
    news_url = "https://news.microsoft.com/source/"

    wait_for_selector = "article, .news-item, .post"
    timeout = 60000

    def parse_ir(self, html: str) -> list[CompanyDocument]:
        return []

    def parse_news(self, html: str) -> list[CompanyDocument]:
        """解析 Microsoft 新聞頁面"""
        soup = self._parse_html(html)
        documents = []

        try:
            # 找所有新聞連結 - 多種選擇器
            news_links = soup.select('a[href*="/source/20"]')
            if not news_links:
                # 嘗試其他選擇器
                news_links = soup.select('article a, .news a, .post a')
            if not news_links:
                # 更通用的選擇器
                news_links = soup.select('a[href*="news.microsoft.com"]')

            seen_urls = set()
            logger.info(f"Found {len(news_links)} news links")

            for link in news_links[:50]:
                try:
                    url = link.get('href', '')
                    if not url or url in seen_urls:
                        continue

                    # 補全 URL
                    if url.startswith('/'):
                        url = 'https://news.microsoft.com' + url

                    seen_urls.add(url)

                    # 取得標題
                    raw_text = link.get_text(strip=True)
                    if not raw_text or len(raw_text) < 10:
                        continue

                    # 跳過導覽連結
                    if raw_text.lower() in ['read more', 'learn more', 'source']:
                        continue

                    # 從 URL 提取日期
                    published_at = None
                    date_match = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', url)
                    if date_match:
                        year, month, day = date_match.groups()
                        try:
                            published_at = datetime(int(year), int(month), int(day))
                        except ValueError:
                            pass

                    # 自動標籤
                    tags = ["news"]
                    title_lower = raw_text.lower()
                    if any(kw in title_lower for kw in ['ai', 'copilot', 'azure ai']):
                        tags.append('ai')
                    if any(kw in title_lower for kw in ['azure', 'cloud']):
                        tags.append('cloud')
                    if any(kw in title_lower for kw in ['windows', 'office', 'teams']):
                        tags.append('product')
                    if any(kw in title_lower for kw in ['earnings', 'quarter', 'results', 'revenue', 'dividend']):
                        tags.append('earnings')
                    if any(kw in title_lower for kw in ['nvidia', 'gpu', 'datacenter']):
                        tags.append('infrastructure')

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
            logger.error(f"Error parsing Microsoft page: {e}")

        logger.info(f"Parsed {len(documents)} news from Microsoft")
        return documents


# CLI 測試
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    fetcher = MicrosoftFetcher()
    result = fetcher.fetch_all()

    print(f"=== Microsoft News ({len(result.get('news', []))} items) ===")
    for doc in result.get("news", [])[:10]:
        print(f"  [{doc.published_at}] {doc.title[:60]}...")
        print(f"    Tags: {doc.tags}")
