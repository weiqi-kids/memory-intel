"""
華邦電子官網爬蟲

抓取來源：
- 華邦電子新聞櫥窗: https://www.winbond.com/hq/about-winbond/news-and-events/news/?__locale=zh_TW
"""

from datetime import datetime
from typing import Optional
import re
import logging

from .base import CompanyFetcher, CompanyDocument

logger = logging.getLogger(__name__)


class WinbondFetcher(CompanyFetcher):
    """華邦電子官網爬蟲 - Playwright"""

    company_id = "winbond"
    company_name = "華邦電子"

    ir_url = None
    news_url = "https://www.winbond.com/hq/about-winbond/news-and-events/news/?__locale=zh_TW"

    wait_for_selector = ".news-list, .newsItem, article"
    timeout = 60000

    def parse_ir(self, html: str) -> list[CompanyDocument]:
        return []

    def parse_news(self, html: str) -> list[CompanyDocument]:
        """解析華邦電子新聞頁面"""
        soup = self._parse_html(html)
        documents = []

        try:
            # 找所有新聞連結
            news_links = soup.select('a[href*="/news/"], a[href*="news-and-events"]')

            seen_urls = set()
            logger.info(f"Found {len(news_links)} news links")

            for link in news_links[:50]:
                try:
                    url = link.get('href', '')
                    if not url or url in seen_urls:
                        continue

                    # 補全 URL
                    if url.startswith('/'):
                        url = 'https://www.winbond.com' + url

                    seen_urls.add(url)

                    # 取得標題
                    raw_text = link.get_text(strip=True)
                    if not raw_text or len(raw_text) < 10:
                        continue

                    # 跳過導覽連結
                    if raw_text in ['新聞櫥窗', 'News', '更多']:
                        continue

                    # 嘗試從上層元素取得日期
                    published_at = None
                    parent = link.find_parent(['li', 'div', 'article', 'tr', 'td'])
                    if parent:
                        # 先嘗試標準日期選擇器
                        date_elem = parent.select_one('.date, time, .news-date')
                        if date_elem:
                            date_text = date_elem.get_text(strip=True)
                            published_at = self._parse_date(date_text)

                        # 如果沒找到，嘗試找相鄰的 td 或 span
                        if not published_at:
                            next_td = link.find_next(['td', 'span'])
                            if next_td and next_td != link:
                                date_text = next_td.get_text(strip=True)
                                published_at = self._parse_date(date_text)

                        # 嘗試從父元素的所有文字中提取日期
                        if not published_at:
                            parent_text = parent.get_text()
                            # 搜索 YYYY-MM-DD 或 YYYY/MM/DD 模式
                            date_match = re.search(r'(\d{4}[-/\.]\d{1,2}[-/\.]\d{1,2})', parent_text)
                            if date_match:
                                published_at = self._parse_date(date_match.group(1))

                    # 自動標籤
                    tags = ["news"]
                    title_lower = raw_text.lower()
                    if any(kw in title_lower for kw in ['dram', 'ddr4', 'ddr5']):
                        tags.append('dram')
                    if any(kw in title_lower for kw in ['flash', 'nor', 'nand']):
                        tags.append('flash')
                    if any(kw in title_lower for kw in ['營收', 'revenue', '財報', '營運']):
                        tags.append('earnings')
                    if any(kw in title_lower for kw in ['esg', '永續', 'cdp']):
                        tags.append('esg')

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
            logger.error(f"Error parsing Winbond page: {e}")

        logger.info(f"Parsed {len(documents)} news from Winbond")
        return documents

    def _parse_date(self, date_text: str) -> Optional[datetime]:
        """解析日期字串"""
        formats = [
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%Y.%m.%d",
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
    fetcher = WinbondFetcher()
    result = fetcher.fetch_all()

    print(f"=== 華邦電子 News ({len(result.get('news', []))} items) ===")
    for doc in result.get("news", [])[:10]:
        print(f"  [{doc.published_at}] {doc.title[:60]}...")
        print(f"    Tags: {doc.tags}")
