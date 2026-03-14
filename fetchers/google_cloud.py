"""
Google Cloud 官網爬蟲

抓取來源：
- Google Cloud Blog: https://cloud.google.com/blog
"""

from datetime import datetime
from typing import Optional
import re
import logging

from .base import CompanyFetcher, CompanyDocument

logger = logging.getLogger(__name__)


class GoogleCloudFetcher(CompanyFetcher):
    """Google Cloud 官網爬蟲 - Playwright"""

    company_id = "google"
    company_name = "Google Cloud"

    ir_url = None
    news_url = "https://cloud.google.com/blog/topics/inside-google-cloud/whats-new-google-cloud"

    wait_for_selector = "a[href*='/blog/'], article, .content, body"
    timeout = 90000

    def parse_ir(self, html: str) -> list[CompanyDocument]:
        return []

    def parse_news(self, html: str) -> list[CompanyDocument]:
        """解析 Google Cloud Blog 頁面"""
        soup = self._parse_html(html)
        documents = []

        try:
            # 找所有新聞連結 - 優先找有文章內容的連結
            news_links = soup.select('a[href*="/blog/products/"], a[href*="/blog/topics/"]')
            if not news_links:
                news_links = soup.select('a[href*="/blog/"]')

            seen_urls = set()
            logger.info(f"Found {len(news_links)} news links")

            for link in news_links[:50]:
                try:
                    url = link.get('href', '')
                    if not url or url in seen_urls:
                        continue

                    # 補全 URL
                    if url.startswith('/'):
                        url = 'https://cloud.google.com' + url

                    # 跳過分類頁面 (topics 下且只有 3 段路徑)
                    if '/blog/topics/' in url and url.count('/') < 6:
                        continue

                    seen_urls.add(url)

                    # 取得標題
                    raw_text = link.get_text(strip=True)
                    if not raw_text or len(raw_text) < 10:
                        continue

                    # 跳過導覽連結
                    if raw_text.lower() in ['blog', 'read more', 'learn more', 'google cloud blog', 'view all', 'see all']:
                        continue

                    # 嘗試從上層元素取得日期
                    published_at = None
                    parent = link.find_parent(['article', 'div', 'li', 'section'])
                    if parent:
                        # 方法 1: time 或 datetime 屬性
                        date_elem = parent.select_one('time, [datetime], .date, .published')
                        if date_elem:
                            date_text = date_elem.get('datetime') or date_elem.get_text(strip=True)
                            published_at = self._parse_date(date_text)

                        # 方法 2: 從 span 或 div 文字中提取
                        if not published_at:
                            for elem in parent.select('span, div'):
                                text = elem.get_text(strip=True)
                                # 檢查是否像日期 (例如 "Mar 14, 2026")
                                if len(text) < 20 and re.match(r'^[A-Z][a-z]{2}\s+\d{1,2},?\s+\d{4}$', text):
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
                    tags = ["news"]
                    title_lower = raw_text.lower()
                    if any(kw in title_lower for kw in ['ai', 'gemini', 'vertex', 'machine learning']):
                        tags.append('ai')
                    if any(kw in title_lower for kw in ['tpu', 'gpu', 'compute']):
                        tags.append('compute')
                    if any(kw in title_lower for kw in ['bigquery', 'data', 'analytics']):
                        tags.append('data')
                    if any(kw in title_lower for kw in ['kubernetes', 'gke', 'container']):
                        tags.append('kubernetes')
                    if any(kw in title_lower for kw in ['earnings', 'quarter', 'results', 'revenue']):
                        tags.append('earnings')

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
            logger.error(f"Error parsing Google Cloud page: {e}")

        logger.info(f"Parsed {len(documents)} news from Google Cloud")
        return documents

    def _parse_date(self, date_text: str) -> Optional[datetime]:
        """解析日期字串"""
        if not date_text:
            return None

        formats = [
            "%Y-%m-%d",
            "%Y-%m-%dT%H:%M:%S%z",
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
    fetcher = GoogleCloudFetcher()
    result = fetcher.fetch_all()

    print(f"=== Google Cloud News ({len(result.get('news', []))} items) ===")
    for doc in result.get("news", [])[:10]:
        print(f"  [{doc.published_at}] {doc.title[:60]}...")
        print(f"    Tags: {doc.tags}")
