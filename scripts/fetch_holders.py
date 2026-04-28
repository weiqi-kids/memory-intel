#!/usr/bin/env python3
"""
抓取追蹤公司的機構持股人資料

從 configs/companies.yml 讀取 ticker，用 yfinance 抓取 institutional_holders，
輸出到 data/holders/latest.json 和 site/data/holders.json。
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

try:
    import yfinance as yf
except ImportError:
    print("yfinance not installed, skipping holders fetch")
    sys.exit(0)

BASE_DIR = Path(__file__).parent.parent
CONFIG_FILE = BASE_DIR / "configs" / "companies.yml"
DATA_DIR = BASE_DIR / "data" / "holders"
SITE_DIR = BASE_DIR / "site" / "data"


def _fingerprint(company_data: dict) -> tuple:
    """Fingerprint a single company's holder data: top 5 holders by (name, rounded pct)."""
    holders = company_data.get("holders", [])
    top5 = holders[:5]
    return tuple((h["holder"], round(h["pct_held"], 1)) for h in top5)


def _should_write_history(new_data: dict, history_dir: Path) -> bool:
    """Determine whether to write a new holders history file.

    Compares top 5 holders per company (holder name + pct_held rounded to 1 decimal)
    against the latest dated history file.
    Returns True if data changed or no history exists, False if identical.
    """
    if not history_dir.exists():
        return True

    history_files = sorted(
        [f for f in history_dir.glob("*.json") if f.name != "latest.json"],
        reverse=True,
    )
    if not history_files:
        return True

    with open(history_files[0], "r", encoding="utf-8") as f:
        old_data = json.load(f)

    old_companies = old_data.get("companies", {})
    new_companies = new_data.get("companies", {})

    # Check if company set changed
    if set(old_companies.keys()) != set(new_companies.keys()):
        return True

    # Compare fingerprints per company
    for cid, new_comp in new_companies.items():
        old_comp = old_companies.get(cid, {})
        if _fingerprint(new_comp) != _fingerprint(old_comp):
            return True

    return False


def _pick_short_name(company: dict) -> str:
    """優先選中文別名作為顯示名稱，沒有則用 name"""
    aliases = company.get("aliases") or []
    # 找第一個含中文字的 alias
    for a in aliases:
        if a and re.search(r"[\u4e00-\u9fff]", a):
            return a
    # 沒有中文 alias，用 name（可能本身就是中文）
    name = company.get("name", "")
    if re.search(r"[\u4e00-\u9fff]", name):
        return name
    # 都沒有中文，取第一個 alias 或 name
    return aliases[0] if aliases else name


def fetch_holders(ticker: str) -> list[dict] | None:
    """抓取單一公司的機構持股人資料"""
    try:
        t = yf.Ticker(ticker)
        holders = t.institutional_holders
        if holders is None or holders.empty:
            return None

        results = []
        for _, row in holders.iterrows():
            holder_name = row.get("Holder", "")
            shares = row.get("Shares", 0)
            pct = row.get("pctHeld", 0)
            value = row.get("Value", 0)

            # 清理數值
            def safe_num(val, as_int=False):
                if val != val:  # NaN check
                    return 0
                try:
                    return int(val) if as_int else round(float(val), 4)
                except (ValueError, TypeError):
                    return 0

            results.append({
                "holder": str(holder_name),
                "shares": safe_num(shares, as_int=True),
                "pct_held": round(safe_num(pct) * 100, 2),
                "value": safe_num(value, as_int=True),
            })

        return results if results else None

    except Exception as e:
        print(f"  Error fetching holders for {ticker}: {e}")
        return None


def main():
    # 讀取公司設定
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    companies = config.get("companies", [])
    output_companies = {}
    success_count = 0
    skip_count = 0
    error_count = 0

    for company in companies:
        ticker = company.get("ticker")
        if not ticker:
            skip_count += 1
            continue

        cid = company["id"]
        name = company["name"]
        short_name = _pick_short_name(company)

        print(f"Fetching holders for {cid} ({ticker})...")
        holders = fetch_holders(ticker)

        if holders:
            output_companies[cid] = {
                "name": name,
                "short_name": short_name,
                "ticker": ticker,
                "holders": holders,
            }
            success_count += 1
            print(f"  Found {len(holders)} institutional holders")
        else:
            error_count += 1
            print(f"  No holder data")

    # 組裝輸出
    output = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "companies": output_companies,
    }

    # 輸出到 data/holders/
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    data_path = DATA_DIR / "latest.json"
    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\nSaved to {data_path}")

    # Write history file if data changed
    if _should_write_history(output, DATA_DIR):
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        history_path = DATA_DIR / f"{today_str}.json"
        with open(history_path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"History written: {history_path}")
    else:
        print("History skipped: data unchanged from latest history file")

    # 同步到 site/data/
    SITE_DIR.mkdir(parents=True, exist_ok=True)
    site_path = SITE_DIR / "holders.json"
    with open(site_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"Saved to {site_path}")

    print(f"\nTotal: {success_count} companies with holder data, "
          f"{skip_count} skipped (no ticker), {error_count} no data")


if __name__ == "__main__":
    main()
