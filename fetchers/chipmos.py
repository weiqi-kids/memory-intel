"""
南茂科技官網爬蟲

抓取來源：
- 南茂科技投資人關係: https://www.chipmos.com/investor.php
"""

from datetime import datetime
from typing import Optional
import re
import logging

from .base import CompanyFetcher, CompanyDocument

logger = logging.getLogger(__name__)


class ChipMOSFetcher(CompanyFetcher):
    """南茂科技官網爬蟲 - Playwright"""

    company_id = "ptc"  # 使用 companies.yml 中的 id
    company_name = "南茂科技"

    ir_url = None
    news_url = "https://www.chipmos.com/investor.php"

    wait_for_selector = ".news-list, .ir-list, article, table"
    timeout = 60000

    def parse_ir(self, html: str) -> list[CompanyDocument]:
        return []

    def parse_news(self, html: str) -> list[CompanyDocument]:
        """解析南茂科技投資人關係頁面"""
        soup = self._parse_html(html)
        documents = []

        try:
            # 找所有新聞/公告連結 - 限定在表格和特定區域
            news_links = soup.select('table a, .news a, .ir a, a[href*=".pdf"]')

            seen_urls = set()
            logger.info(f"Found {len(news_links)} news links")

            for link in news_links[:50]:
                try:
                    url = link.get('href', '')
                    if not url or url in seen_urls:
                        continue

                    # 補全 URL
                    if url.startswith('/'):
                        url = 'https://www.chipmos.com' + url
                    elif not url.startswith('http'):
                        url = 'https://www.chipmos.com/' + url

                    seen_urls.add(url)

                    # 取得標題
                    raw_text = link.get_text(strip=True)
                    if not raw_text or len(raw_text) < 5:
                        continue

                    # 跳過導覽連結
                    if raw_text in ['首頁', 'Home', '更多', 'More', '下載']:
                        continue

                    # 嘗試從上層元素取得日期
                    published_at = None
                    parent = link.find_parent(['li', 'div', 'tr', 'td'])
                    if parent:
                        # 先嘗試標準日期元素
                        date_elem = parent.select_one('.date, time')
                        if date_elem:
                            date_text = date_elem.get_text(strip=True)
                            published_at = self._parse_date(date_text)

                        # 找相鄰的 td
                        if not published_at:
                            for sibling in [link.find_previous('td'), link.find_next('td')]:
                                if sibling and sibling != link.parent:
                                    date_text = sibling.get_text(strip=True)
                                    parsed = self._parse_date(date_text)
                                    if parsed:
                                        published_at = parsed
                                        break

                        # 從父元素文字中提取日期
                        if not published_at:
                            parent_text = parent.get_text()
                            date_match = re.search(r'(\d{4}[-/\.]\d{1,2}[-/\.]\d{1,2})', parent_text)
                            if date_match:
                                published_at = self._parse_date(date_match.group(1))

                    # 自動標籤
                    tags = ["news"]
                    title_lower = raw_text.lower()
                    if any(kw in title_lower for kw in ['memory', '記憶體', 'dram']):
                        tags.append('memory')
                    if any(kw in title_lower for kw in ['driver', '驅動']):
                        tags.append('driver_ic')
                    if any(kw in title_lower for kw in ['營收', 'revenue', '財報']):
                        tags.append('earnings')

                    doc = CompanyDocument(
                        company_id=self.company_id,
                        doc_type="news",
                        title=raw_text,
                        url=url,
                        published_at=published_at,
                        language="zh-TW",
                        tags=list(set(tags))
                    )
                    documents.append(doc)

                except Exception as e:
                    logger.warning(f"Error parsing link: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error parsing ChipMOS page: {e}")

        logger.info(f"Parsed {len(documents)} news from ChipMOS")
        return documents

    def _parse_date(self, date_text: str) -> Optional[datetime]:
        """解析日期字串"""
        formats = [
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%Y年%m月%d日",
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
    fetcher = ChipMOSFetcher()
    result = fetcher.fetch_all()

    print(f"=== 南茂科技 News ({len(result.get('news', []))} items) ===")
    for doc in result.get("news", [])[:10]:
        print(f"  [{doc.published_at}] {doc.title[:60]}...")
        print(f"    Tags: {doc.tags}")
