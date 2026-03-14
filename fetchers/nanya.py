"""
南亞科技官網爬蟲

抓取來源：
- 南亞科技新聞稿: https://www.nanya.com/tw/IR/15
"""

from datetime import datetime
from typing import Optional
import re
import logging

from .base import CompanyFetcher, CompanyDocument

logger = logging.getLogger(__name__)


class NanyaFetcher(CompanyFetcher):
    """南亞科技官網爬蟲 - Playwright"""

    company_id = "nanya"
    company_name = "南亞科技"

    ir_url = None
    news_url = "https://www.nanya.com/tw/IR/15"

    wait_for_selector = ".news-list, .ir-list, article, table"
    timeout = 60000

    def parse_ir(self, html: str) -> list[CompanyDocument]:
        return []

    def parse_news(self, html: str) -> list[CompanyDocument]:
        """解析南亞科技新聞稿頁面"""
        soup = self._parse_html(html)
        documents = []

        try:
            # 找所有新聞連結 - 更寬泛的選擇器
            news_links = soup.select('a[href*="/IR/"], a[href*="IRId="], table a')

            seen_urls = set()
            logger.info(f"Found {len(news_links)} news links")

            for link in news_links[:50]:
                try:
                    url = link.get('href', '')
                    if not url or url in seen_urls:
                        continue

                    # 補全 URL
                    if url.startswith('/'):
                        url = 'https://www.nanya.com' + url

                    # 只保留新聞相關連結
                    if not any(x in url for x in ['IR', 'News', 'news', 'IRId']):
                        continue

                    seen_urls.add(url)

                    # 取得標題
                    raw_text = link.get_text(strip=True)
                    if not raw_text or len(raw_text) < 5:
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

                        # 如果是表格，找相鄰的 td
                        if not published_at:
                            prev_td = link.find_previous('td')
                            if prev_td and prev_td != link.parent:
                                date_text = prev_td.get_text(strip=True)
                                published_at = self._parse_date(date_text)

                        # 從父元素文字中提取日期
                        if not published_at:
                            parent_text = parent.get_text()
                            date_match = re.search(r'(\d{4}[-/\.]\d{1,2}[-/\.]\d{1,2})', parent_text)
                            if date_match:
                                published_at = self._parse_date(date_match.group(1))

                    # 自動標籤
                    tags = ["news"]
                    title_lower = raw_text.lower()
                    if any(kw in title_lower for kw in ['dram', 'ddr4', 'ddr5']):
                        tags.append('dram')
                    if any(kw in title_lower for kw in ['營收', 'revenue', '財報']):
                        tags.append('earnings')
                    if any(kw in title_lower for kw in ['產能', 'capacity', '擴產']):
                        tags.append('capacity')

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
            logger.error(f"Error parsing Nanya page: {e}")

        logger.info(f"Parsed {len(documents)} news from Nanya")
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
    fetcher = NanyaFetcher()
    result = fetcher.fetch_all()

    print(f"=== 南亞科技 News ({len(result.get('news', []))} items) ===")
    for doc in result.get("news", [])[:10]:
        print(f"  [{doc.published_at}] {doc.title[:60]}...")
        print(f"    Tags: {doc.tags}")
