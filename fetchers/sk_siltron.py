"""
SK Siltron 官網爬蟲

SK Siltron 是 SK hynix 的子公司，專門生產矽晶圓。
由於 SK Siltron 沒有獨立的公開新聞頁面，
此爬蟲會從 SK 集團相關新聞中過濾 SK Siltron 相關消息。

抓取來源：
- SK hynix Newsroom (過濾 Siltron 相關)
"""

from datetime import datetime
from typing import Optional
import re
import logging

from .base import CompanyFetcher, CompanyDocument

logger = logging.getLogger(__name__)


class SKSiltronFetcher(CompanyFetcher):
    """SK Siltron 爬蟲 - 從 SK 相關來源過濾"""

    company_id = "sk_siltron"
    company_name = "SK Siltron"

    # SK Siltron 沒有獨立新聞頁面
    # 改為從 SK hynix 或 SK 集團新聞過濾
    ir_url = None
    news_url = None  # 無獨立新聞頁面

    def fetch_all(self) -> dict[str, list[CompanyDocument]]:
        """
        SK Siltron 沒有獨立的公開新聞頁面。
        相關新聞通常會出現在：
        - SK hynix 新聞稿
        - SK 集團新聞
        - 產業新聞網站

        目前返回空列表，未來可以考慮：
        1. 從 SK hynix 新聞中過濾 "Siltron" 關鍵字
        2. 使用 Google News API 搜尋
        """
        logger.info("SK Siltron has no dedicated news page, returning empty list")
        return {"news": []}

    def parse_ir(self, html: str) -> list[CompanyDocument]:
        return []

    def parse_news(self, html: str) -> list[CompanyDocument]:
        return []


# CLI 測試
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    fetcher = SKSiltronFetcher()
    result = fetcher.fetch_all()

    print(f"=== SK Siltron News ({len(result.get('news', []))} items) ===")
    print("  (No dedicated news page available)")
