"""
SK hynix 官網爬蟲

抓取來源：
- SK hynix Press Release: https://news.skhynix.com/press-center/press-release/

功能：
1. 從列表頁取得文章 URL
2. 進入每篇文章頁抓取完整內文
"""

from datetime import datetime
from typing import Optional
import re
import logging
import time

from .base import CompanyFetcher, CompanyDocument

logger = logging.getLogger(__name__)

# 是否抓取完整內文（設為 False 可加速測試）
FETCH_FULL_CONTENT = True
# 每篇文章間隔秒數（避免被封）
FETCH_DELAY = 1.0


class SKHynixFetcher(CompanyFetcher):
    """SK hynix 官網爬蟲"""

    company_id = "skhynix"
    company_name = "SK hynix"

    ir_url = None
    news_url = "https://news.skhynix.com/press-center/press-release/"

    # 等待 AJAX 載入的文章
    wait_for_selector = ".alm-listing article, .alm-listing .alm-item"
    timeout = 60000

    def parse_ir(self, html: str) -> list[CompanyDocument]:
        """SK hynix IR - 暫不支援"""
        return []

    def parse_news(self, html: str) -> list[CompanyDocument]:
        """解析 SK hynix Press Release"""
        soup = self._parse_html(html)
        documents = []

        try:
            # SK hynix 使用 AJAX Load More，文章在 .alm-listing > article
            alm_listing = soup.select_one('.alm-listing')
            if not alm_listing:
                logger.warning("No .alm-listing found")
                return []

            articles = alm_listing.select('article')
            logger.info(f"Found {len(articles)} articles in .alm-listing")

            for article in articles[:30]:
                try:
                    # 從 article 的 class 取得分類
                    classes = article.get('class', [])

                    # 找標題連結
                    title_elem = article.select_one('.entry-title a, h2 a, h3 a')
                    if not title_elem:
                        continue

                    title = title_elem.get_text(strip=True)
                    url = title_elem.get('href', '')

                    if not title or not url:
                        continue

                    # 補全 URL
                    if not url.startswith('http'):
                        url = 'https://news.skhynix.com' + url

                    # 日期
                    date_elem = article.select_one('.entry-date, time, .post-date')
                    published_at = None
                    if date_elem:
                        # 嘗試從 datetime 屬性
                        if date_elem.get('datetime'):
                            try:
                                dt_str = date_elem['datetime']
                                published_at = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
                            except:
                                pass

                        # 嘗試從文字
                        if not published_at:
                            date_text = date_elem.get_text(strip=True)
                            published_at = self._parse_date(date_text)

                    # 摘要（從列表頁取得）
                    excerpt_elem = article.select_one('.entry-excerpt, .excerpt, .entry-content p')
                    excerpt = excerpt_elem.get_text(strip=True)[:500] if excerpt_elem else ""

                    # 抓取完整內文
                    content = excerpt
                    if FETCH_FULL_CONTENT and url:
                        full_content = self._fetch_article_content(url)
                        if full_content:
                            content = full_content
                        time.sleep(FETCH_DELAY)

                    # 從 class 提取標籤
                    tags = ["news", "press-release"]
                    for cls in classes:
                        if cls.startswith('tag-'):
                            tag = cls.replace('tag-', '').replace('-', ' ')
                            tags.append(tag)
                        elif cls.startswith('category-'):
                            cat = cls.replace('category-', '').replace('-', ' ')
                            tags.append(cat)

                    # 自動標籤
                    title_lower = title.lower()
                    if 'hbm' in title_lower:
                        tags.append('hbm')
                    if any(kw in title_lower for kw in ['memory', 'dram', 'nand']):
                        tags.append('memory')
                    if any(kw in title_lower for kw in ['earnings', 'quarter', 'results', 'revenue']):
                        tags.append('earnings')

                    doc = CompanyDocument(
                        company_id=self.company_id,
                        doc_type="news",
                        title=title,
                        url=url,
                        published_at=published_at,
                        content=content,
                        language="en",
                        tags=list(set(tags))
                    )
                    documents.append(doc)

                except Exception as e:
                    logger.warning(f"Error parsing article: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error parsing SK hynix page: {e}")

        logger.info(f"Parsed {len(documents)} news from SK hynix")
        return documents

    def _fetch_article_content(self, url: str) -> Optional[str]:
        """抓取單篇文章的完整內文"""
        try:
            logger.info(f"Fetching article: {url}")
            html = self._get_page(url, wait_selector=".entry-content, article")
            if not html:
                return None

            soup = self._parse_html(html)

            # SK hynix 文章頁的內文通常在 .entry-content
            content_elem = soup.select_one('.entry-content')
            if not content_elem:
                # 備用選擇器
                content_elem = soup.select_one('article .content, .post-content, .article-body')

            if content_elem:
                # 移除不需要的元素（分享按鈕、相關文章等）
                for unwanted in content_elem.select('.share-buttons, .related-posts, .post-tags, script, style'):
                    unwanted.decompose()

                # 取得純文字，保留段落
                paragraphs = []
                for p in content_elem.find_all(['p', 'h2', 'h3', 'li']):
                    text = p.get_text(strip=True)
                    if text and len(text) > 10:  # 過濾太短的
                        paragraphs.append(text)

                if paragraphs:
                    return '\n\n'.join(paragraphs)

            return None

        except Exception as e:
            logger.warning(f"Error fetching article content from {url}: {e}")
            return None

    def _parse_date(self, date_text: str) -> Optional[datetime]:
        """解析日期字串"""
        formats = [
            "%Y-%m-%d",
            "%Y.%m.%d",
            "%B %d, %Y",
            "%b %d, %Y",
            "%d %B %Y",
            "%Y/%m/%d",
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
    fetcher = SKHynixFetcher()
    result = fetcher.fetch_all()

    print(f"=== SK hynix News ({len(result.get('news', []))} items) ===")
    for doc in result.get("news", [])[:10]:
        print(f"  [{doc.published_at}]")
        print(f"    {doc.title[:70]}")
        print(f"    Tags: {doc.tags[:5]}")
        print()
