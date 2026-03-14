"""
SUMCO 官網爬蟲

抓取來源：
- SUMCO IR News: https://www.sumcosi.com/english/ir/news/
"""

from datetime import datetime
from typing import Optional
import re
import logging

from .base import CompanyFetcher, CompanyDocument

logger = logging.getLogger(__name__)


class SUMCOFetcher(CompanyFetcher):
    """SUMCO 官網爬蟲 - Playwright"""

    company_id = "sumco"
    company_name = "SUMCO"

    ir_url = None
    news_url = "https://www.sumcosi.com/english/ir/news/"

    wait_for_selector = "a[href*='news'], a[href*='ir'], table, .content, body"
    timeout = 90000

    def parse_ir(self, html: str) -> list[CompanyDocument]:
        return []

    def parse_news(self, html: str) -> list[CompanyDocument]:
        """解析 SUMCO IR News 頁面"""
        soup = self._parse_html(html)
        documents = []

        try:
            # 找所有新聞連結 - 多種選擇器
            news_links = soup.select('a[href*="/news/"]')
            if not news_links:
                news_links = soup.select('a[href*="/ir/"]')
            if not news_links:
                # 更通用的選擇器
                news_links = soup.select('table a, .news a, article a')

            seen_urls = set()
            logger.info(f"Found {len(news_links)} news links")

            for link in news_links[:50]:
                try:
                    url = link.get('href', '')
                    if not url or url in seen_urls:
                        continue

                    # 補全 URL
                    if url.startswith('/'):
                        url = 'https://www.sumcosi.com' + url
                    elif not url.startswith('http'):
                        url = 'https://www.sumcosi.com/' + url

                    # 跳過導覽連結
                    if any(x in url for x in ['#', 'javascript:', 'mailto:']):
                        continue

                    seen_urls.add(url)

                    # 取得標題
                    raw_text = link.get_text(strip=True)
                    if not raw_text or len(raw_text) < 10:
                        continue

                    # 跳過導覽文字
                    if raw_text.lower() in ['news', 'ir', 'top', 'home', 'more', 'back']:
                        continue

                    # 嘗試從上層元素取得日期
                    published_at = None
                    parent = link.find_parent(['li', 'div', 'tr', 'td', 'dl', 'dd'])
                    if parent:
                        # 方法 1: 標準日期元素
                        date_elem = parent.select_one('.date, .news-date, time, dt')
                        if date_elem:
                            date_text = date_elem.get_text(strip=True)
                            published_at = self._parse_date(date_text)

                        # 方法 2: 相鄰的 td 或 dt
                        if not published_at:
                            for sibling in [link.find_previous(['td', 'dt']), link.find_next(['td', 'dt'])]:
                                if sibling and sibling != link.parent:
                                    text = sibling.get_text(strip=True)
                                    parsed = self._parse_date(text)
                                    if parsed:
                                        published_at = parsed
                                        break

                        # 方法 3: 從父元素文字中用正則提取
                        if not published_at:
                            parent_text = parent.get_text()
                            # 支援多種日期格式
                            for pattern in [
                                r'(\d{4}[-/\.]\d{1,2}[-/\.]\d{1,2})',  # 2026-03-14, 2026/03/14
                                r'(\d{4}年\d{1,2}月\d{1,2}日)',          # 日文格式
                                r'(\w+ \d{1,2}, \d{4})',              # March 14, 2026
                            ]:
                                date_match = re.search(pattern, parent_text)
                                if date_match:
                                    published_at = self._parse_date(date_match.group(1))
                                    if published_at:
                                        break

                    # 自動標籤
                    tags = ["news"]
                    title_lower = raw_text.lower()
                    if any(kw in title_lower for kw in ['wafer', 'silicon']):
                        tags.append('wafer')
                    if any(kw in title_lower for kw in ['earnings', 'quarter', 'results', 'revenue', 'financial']):
                        tags.append('earnings')
                    if any(kw in title_lower for kw in ['capacity', 'production', 'plant']):
                        tags.append('capacity')

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
            logger.error(f"Error parsing SUMCO page: {e}")

        logger.info(f"Parsed {len(documents)} news from SUMCO")
        return documents

    def _parse_date(self, date_text: str) -> Optional[datetime]:
        """解析日期字串 - 支援英文和日文格式"""
        formats = [
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%Y.%m.%d",
            "%B %d, %Y",
            "%b %d, %Y",
            "%Y年%m月%d日",  # 日文格式
        ]

        date_text = date_text.strip()

        for fmt in formats:
            try:
                return datetime.strptime(date_text, fmt)
            except ValueError:
                continue

        # 嘗試從文字中提取數字格式的日期
        date_match = re.search(r'(\d{4})[-/年\.](\d{1,2})[-/月\.](\d{1,2})', date_text)
        if date_match:
            try:
                year, month, day = date_match.groups()
                return datetime(int(year), int(month), int(day))
            except ValueError:
                pass

        return None


# CLI 測試
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    fetcher = SUMCOFetcher()
    result = fetcher.fetch_all()

    print(f"=== SUMCO News ({len(result.get('news', []))} items) ===")
    for doc in result.get("news", [])[:10]:
        print(f"  [{doc.published_at}] {doc.title[:60]}...")
        print(f"    Tags: {doc.tags}")
