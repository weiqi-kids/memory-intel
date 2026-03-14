"""
AWS 官網爬蟲

抓取來源：
- AWS News Blog: https://aws.amazon.com/blogs/aws/
- About Amazon AWS News: https://www.aboutamazon.com/news/aws
"""

from datetime import datetime
from typing import Optional
import re
import logging

from .base import CompanyFetcher, CompanyDocument

logger = logging.getLogger(__name__)


class AWSFetcher(CompanyFetcher):
    """AWS 官網爬蟲 - Playwright"""

    company_id = "aws"
    company_name = "Amazon Web Services"

    ir_url = None
    news_url = "https://www.aboutamazon.com/news/aws"

    wait_for_selector = "article, a[href*='news'], .content, body"
    timeout = 90000

    def parse_ir(self, html: str) -> list[CompanyDocument]:
        return []

    def parse_news(self, html: str) -> list[CompanyDocument]:
        """解析 AWS 新聞頁面"""
        soup = self._parse_html(html)
        documents = []

        try:
            # 找所有新聞連結 - 多種選擇器
            news_links = soup.select('a[href*="/news/aws/"]')
            if not news_links:
                news_links = soup.select('a[href*="/news/"]')
            if not news_links:
                news_links = soup.select('article a, .news a')

            seen_urls = set()
            logger.info(f"Found {len(news_links)} news links")

            for link in news_links[:50]:
                try:
                    url = link.get('href', '')
                    if not url or url in seen_urls:
                        continue

                    # 補全 URL
                    if url.startswith('/'):
                        url = 'https://www.aboutamazon.com' + url

                    # 跳過非文章連結
                    if '/news/aws' not in url and '/news/' not in url:
                        continue

                    # 跳過分類頁面
                    if url.endswith('/aws') or url.endswith('/news'):
                        continue

                    seen_urls.add(url)

                    # 取得標題 - 如果連結文字太短，嘗試從父元素取得
                    raw_text = link.get_text(strip=True)
                    if not raw_text or len(raw_text) < 5:
                        # 嘗試從父元素找標題
                        parent = link.find_parent(['article', 'div', 'li'])
                        if parent:
                            h_elem = parent.select_one('h2, h3, h4, .title')
                            if h_elem:
                                raw_text = h_elem.get_text(strip=True)

                    if not raw_text or len(raw_text) < 5:
                        continue

                    # 跳過導覽連結
                    if raw_text.lower() in ['aws', 'read more', 'learn more', 'amazon web services', 'see all']:
                        continue

                    # 嘗試從上層元素取得日期
                    published_at = None
                    parent = link.find_parent(['article', 'div', 'li'])
                    if parent:
                        # 方法 1: time 或 datetime 屬性
                        date_elem = parent.select_one('time, [datetime], .date, .published, [data-publish-date]')
                        if date_elem:
                            date_text = date_elem.get('datetime') or date_elem.get('data-publish-date') or date_elem.get_text(strip=True)
                            published_at = self._parse_date(date_text)

                        # 方法 2: 從 JSON-LD 或 data 屬性取得
                        if not published_at:
                            for elem in parent.select('[data-date], [data-published]'):
                                date_text = elem.get('data-date') or elem.get('data-published')
                                if date_text:
                                    published_at = self._parse_date(date_text)
                                    break

                        # 方法 3: 從父元素文字中提取
                        if not published_at:
                            parent_text = parent.get_text()
                            date_match = re.search(r'(\w+ \d{1,2}, \d{4})', parent_text)
                            if date_match:
                                published_at = self._parse_date(date_match.group(1))

                    # 自動標籤
                    tags = ["news"]
                    title_lower = raw_text.lower()
                    if any(kw in title_lower for kw in ['ai', 'bedrock', 'sagemaker', 'machine learning']):
                        tags.append('ai')
                    if any(kw in title_lower for kw in ['ec2', 'instance', 'compute']):
                        tags.append('compute')
                    if any(kw in title_lower for kw in ['trainium', 'inferentia', 'graviton']):
                        tags.append('chip')
                    if any(kw in title_lower for kw in ['nvidia', 'gpu']):
                        tags.append('gpu')
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
            logger.error(f"Error parsing AWS page: {e}")

        logger.info(f"Parsed {len(documents)} news from AWS")
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
    fetcher = AWSFetcher()
    result = fetcher.fetch_all()

    print(f"=== AWS News ({len(result.get('news', []))} items) ===")
    for doc in result.get("news", [])[:10]:
        print(f"  [{doc.published_at}] {doc.title[:60]}...")
        print(f"    Tags: {doc.tags}")
