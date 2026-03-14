"""
Lam Research 官網爬蟲

抓取來源：
- Lam Research Newsroom: https://newsroom.lamresearch.com/press-releases
"""

from datetime import datetime
from typing import Optional
import re
import logging

from .base import CompanyFetcher, CompanyDocument

logger = logging.getLogger(__name__)


class LamResearchFetcher(CompanyFetcher):
    """Lam Research 官網爬蟲 - Playwright"""

    company_id = "lam_research"
    company_name = "Lam Research"

    ir_url = None
    news_url = "https://newsroom.lamresearch.com/press-releases"

    wait_for_selector = "a[href*='20'], article, .content, body"
    timeout = 90000  # 增加超時時間

    def parse_ir(self, html: str) -> list[CompanyDocument]:
        return []

    def parse_news(self, html: str) -> list[CompanyDocument]:
        """解析 Lam Research Newsroom 頁面"""
        soup = self._parse_html(html)
        documents = []

        try:
            # 找所有新聞連結 - 匹配任何年份 (格式: /20XX-MM-DD-Title)
            news_links = soup.select('a[href*="/20"]')
            # 過濾只保留日期格式的連結
            news_links = [link for link in news_links if re.search(r'/\d{4}-\d{2}-\d{2}', link.get('href', ''))]

            seen_urls = set()
            logger.info(f"Found {len(news_links)} news links")

            for link in news_links[:50]:
                try:
                    url = link.get('href', '')
                    if not url or url in seen_urls:
                        continue

                    # 補全 URL
                    if url.startswith('/'):
                        url = 'https://newsroom.lamresearch.com' + url

                    # 只要新聞稿連結
                    if 'newsroom.lamresearch.com' not in url:
                        continue

                    seen_urls.add(url)

                    # 取得標題
                    raw_text = link.get_text(strip=True)
                    if not raw_text or len(raw_text) < 10:
                        continue

                    # 從 URL 提取日期 (格式: /2026-03-14-Title)
                    published_at = None
                    date_match = re.search(r'/(\d{4})-(\d{2})-(\d{2})-', url)
                    if date_match:
                        year, month, day = date_match.groups()
                        try:
                            published_at = datetime(int(year), int(month), int(day))
                        except ValueError:
                            pass

                    # 自動標籤
                    tags = ["news"]
                    title_lower = raw_text.lower()
                    if any(kw in title_lower for kw in ['etch', 'etching']):
                        tags.append('etch')
                    if any(kw in title_lower for kw in ['deposition', 'cvd', 'ald']):
                        tags.append('deposition')
                    if any(kw in title_lower for kw in ['earnings', 'quarter', 'results', 'revenue', 'financial']):
                        tags.append('earnings')
                    if any(kw in title_lower for kw in ['ai', 'artificial intelligence']):
                        tags.append('ai')
                    if any(kw in title_lower for kw in ['3d nand', 'advanced packaging']):
                        tags.append('advanced_packaging')

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
            logger.error(f"Error parsing Lam Research page: {e}")

        logger.info(f"Parsed {len(documents)} news from Lam Research")
        return documents


# CLI 測試
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    fetcher = LamResearchFetcher()
    result = fetcher.fetch_all()

    print(f"=== Lam Research News ({len(result.get('news', []))} items) ===")
    for doc in result.get("news", [])[:10]:
        print(f"  [{doc.published_at}] {doc.title[:60]}...")
        print(f"    Tags: {doc.tags}")
