#!/usr/bin/env python3
"""
Aggregate dated history files into frontend-ready JSON.

Reads data/financials/*.json and data/holders/*.json (excluding latest.json),
produces site/data/financials_history.json and site/data/holders_history.json.

financials_history.json: per-company quarterly AR/inventory time series.
holders_history.json: per-company institutional holder snapshots (only when changed).
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import yaml

BASE_DIR = Path(__file__).parent.parent
CONFIG_FILE = BASE_DIR / "configs" / "companies.yml"
FINANCIALS_DIR = BASE_DIR / "data" / "financials"
HOLDERS_DIR = BASE_DIR / "data" / "holders"
SITE_DIR = BASE_DIR / "site" / "data"


def load_company_currencies() -> dict[str, str]:
    """Read configs/companies.yml and return {company_id: currency}."""
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return {c["id"]: c.get("currency", "USD") for c in config.get("companies", [])}


def _dated_files(directory: Path) -> list[Path]:
    """Return dated JSON files in directory, sorted ascending by filename.

    Excludes latest.json. Only includes files matching YYYY-MM-DD.json pattern.
    """
    if not directory.exists():
        return []
    files = [
        f
        for f in directory.glob("*.json")
        if f.name != "latest.json"
        and (f.stem[:4].isdigit() or f.name.startswith("backfill-"))
    ]
    return sorted(files, key=lambda p: p.name)


def generate_financials_history() -> dict:
    """Process all dated financials files into per-company quarterly series.

    Dedup logic: for each (company_id, quarter_date), the value from the
    later-dated file overwrites any earlier value (last-write-wins).

    Returns:
        {
            "updated_at": "...",
            "companies": {
                "micron": {
                    "currency": "USD",
                    "quarters": [
                        {"quarter": "2025-06-30", "ar": ..., "inventory": ...},
                        ...
                    ]
                }
            }
        }
    """
    currencies = load_company_currencies()
    files = _dated_files(FINANCIALS_DIR)

    # {company_id: {quarter_date: {"ar": ..., "inventory": ...}}}
    company_quarters: dict[str, dict[str, dict]] = {}

    for fpath in files:
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)

        for entry in data.get("companies", []):
            cid = entry.get("id")
            qdate = entry.get("quarter_date")
            if not cid or not qdate:
                continue

            if cid not in company_quarters:
                company_quarters[cid] = {}

            # Later files overwrite earlier ones (last-write-wins)
            company_quarters[cid][qdate] = {
                "quarter": qdate,
                "ar": entry.get("ar"),
                "inventory": entry.get("inventory"),
            }

    # Build output
    companies_out = {}
    for cid in sorted(company_quarters.keys()):
        quarters = company_quarters[cid]
        sorted_quarters = sorted(quarters.values(), key=lambda q: q["quarter"])
        companies_out[cid] = {
            "currency": currencies.get(cid, "USD"),
            "quarters": sorted_quarters,
        }

    return {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "companies": companies_out,
    }


def generate_holders_history() -> dict:
    """Process all dated holders files into per-company snapshot series.

    Dedup logic: only keep snapshots where the top-5 holder composition
    changed (holder name + pct_held rounded to 1 decimal).

    Returns:
        {
            "updated_at": "...",
            "companies": {
                "micron": [
                    {
                        "date": "2026-03-15",
                        "total_institutional_pct": 78.5,
                        "top5": [
                            {"holder": "Vanguard Group", "pct": 8.2},
                            ...
                        ]
                    }
                ]
            }
        }
    """
    files = _dated_files(HOLDERS_DIR)

    # {company_id: [{"date": ..., "fingerprint": ..., "snapshot": ...}]}
    company_snapshots: dict[str, list[dict]] = {}

    for fpath in files:
        fetch_date = fpath.stem  # YYYY-MM-DD

        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)

        companies = data.get("companies", {})
        for cid, comp_data in companies.items():
            holders = comp_data.get("holders", [])
            if not holders:
                continue

            # Compute total institutional pct
            total_pct = round(sum(h.get("pct_held", 0) for h in holders), 1)

            # Top 5
            top5 = [
                {"holder": h["holder"], "pct": round(h.get("pct_held", 0), 1)}
                for h in holders[:5]
            ]

            # Fingerprint: tuple of (name, rounded_pct) for dedup
            fingerprint = tuple((h["holder"], h["pct"]) for h in top5)

            snapshot = {
                "date": fetch_date,
                "total_institutional_pct": total_pct,
                "top5": top5,
            }

            if cid not in company_snapshots:
                company_snapshots[cid] = []

            company_snapshots[cid].append({
                "fingerprint": fingerprint,
                "snapshot": snapshot,
            })

    # Dedup: only keep snapshots where fingerprint changed
    companies_out = {}
    for cid in sorted(company_snapshots.keys()):
        entries = company_snapshots[cid]
        deduped = []
        prev_fingerprint = None

        for entry in entries:
            if entry["fingerprint"] != prev_fingerprint:
                deduped.append(entry["snapshot"])
                prev_fingerprint = entry["fingerprint"]

        if deduped:
            companies_out[cid] = deduped

    return {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "companies": companies_out,
    }


def main():
    SITE_DIR.mkdir(parents=True, exist_ok=True)

    # Generate financials history
    fin_history = generate_financials_history()
    fin_count = len(fin_history["companies"])
    fin_path = SITE_DIR / "financials_history.json"
    with open(fin_path, "w", encoding="utf-8") as f:
        json.dump(fin_history, f, ensure_ascii=False, indent=2)
    print(f"Financials history: {fin_count} companies -> {fin_path}")

    # Generate holders history
    holders_history = generate_holders_history()
    holders_count = len(holders_history["companies"])
    holders_path = SITE_DIR / "holders_history.json"
    with open(holders_path, "w", encoding="utf-8") as f:
        json.dump(holders_history, f, ensure_ascii=False, indent=2)
    print(f"Holders history: {holders_count} companies -> {holders_path}")


if __name__ == "__main__":
    main()
