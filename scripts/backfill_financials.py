#!/usr/bin/env python3
"""
One-time backfill of historical financial data from yfinance.

Reads configs/companies.yml for all companies with tickers, calls
yf.Ticker(ticker).quarterly_balance_sheet, and writes one file per
quarter: data/financials/backfill-{quarter_date}.json.

Each file contains AR and Inventory for all companies that reported
that quarter, with ar_prev/inv_prev set to null and QoQ set to "N/A"
since cross-quarter comparison is handled by generate_financials_history.py.
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
    print("yfinance not installed, cannot backfill")
    sys.exit(1)

BASE_DIR = Path(__file__).parent.parent
CONFIG_FILE = BASE_DIR / "configs" / "companies.yml"
FINANCIALS_DIR = BASE_DIR / "data" / "financials"


def safe_int(val):
    """Convert value to int, returning None for NaN."""
    if val != val:  # NaN check
        return None
    return int(val)


def get_short_name(company: dict) -> str:
    """Pick short Chinese name from aliases if available, else use name."""
    aliases = company.get("aliases") or []
    for a in aliases:
        if a and re.search(r"[\u4e00-\u9fff]", a):
            return a
    return company["name"]


def main():
    # Load company config
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    companies = config.get("companies", [])
    FINANCIALS_DIR.mkdir(parents=True, exist_ok=True)

    # {quarter_date_str: [company_entry, ...]}
    quarters: dict[str, list[dict]] = {}
    processed = 0
    skipped = 0

    for company in companies:
        ticker = company.get("ticker")
        if not ticker:
            skipped += 1
            continue

        cid = company["id"]
        currency = company.get("currency", "USD")
        short_name = get_short_name(company)

        print(f"Fetching {cid} ({ticker})...")
        try:
            t = yf.Ticker(ticker)
            bs = t.quarterly_balance_sheet
            if bs is None or bs.empty:
                print(f"  No balance sheet data, skipping")
                skipped += 1
                continue
        except Exception as e:
            print(f"  WARNING: Failed to fetch {ticker}: {e}")
            skipped += 1
            continue

        # Find AR and Inventory rows
        ar_row = None
        inv_row = None
        for idx in bs.index:
            s = str(idx).lower()
            if "accounts receivable" in s and ar_row is None:
                ar_row = idx
            elif "inventor" in s and inv_row is None:
                inv_row = idx

        if ar_row is None and inv_row is None:
            print(f"  No AR or Inventory rows found, skipping")
            skipped += 1
            continue

        processed += 1

        # Iterate all available quarter columns
        for col in bs.columns:
            quarter_date = col.strftime("%Y-%m-%d")

            ar_val = safe_int(bs.loc[ar_row, col]) if ar_row is not None else None
            inv_val = safe_int(bs.loc[inv_row, col]) if inv_row is not None else None

            # Skip if both are null
            if ar_val is None and inv_val is None:
                continue

            entry = {
                "id": cid,
                "name": short_name,
                "ticker": ticker,
                "currency": currency,
                "quarter_date": quarter_date,
                "ar": ar_val,
                "inventory": inv_val,
                "ar_prev": None,
                "ar_qoq": "N/A",
                "inv_prev": None,
                "inv_qoq": "N/A",
                "alert": False,
            }

            if quarter_date not in quarters:
                quarters[quarter_date] = []
            quarters[quarter_date].append(entry)

        print(f"  Found {len(bs.columns)} quarters")

    # Write one file per quarter
    written = 0
    skipped_files = 0
    for quarter_date in sorted(quarters.keys()):
        filename = f"backfill-{quarter_date}.json"
        filepath = FINANCIALS_DIR / filename

        if filepath.exists():
            print(f"  Skipping {filename} (already exists)")
            skipped_files += 1
            continue

        output = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "quarter": quarter_date,
            "companies": sorted(quarters[quarter_date], key=lambda x: x["id"]),
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        print(f"  Wrote {filename} ({len(quarters[quarter_date])} companies)")
        written += 1

    print(f"\nSummary:")
    print(f"  Companies processed: {processed}")
    print(f"  Companies skipped: {skipped}")
    print(f"  Quarters found: {len(quarters)}")
    print(f"  Files written: {written}")
    print(f"  Files skipped (existing): {skipped_files}")


if __name__ == "__main__":
    main()
