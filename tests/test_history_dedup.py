#!/usr/bin/env python3
"""
Tests for financial history dedup logic.

The function should_write_financials_history(new_companies, history_dir) returns:
- True if no history files exist (first run)
- True if any company's quarter_date, ar, or inventory differs from the latest history file
- False if all companies match the latest history file
"""

import json
import os
import tempfile
from pathlib import Path


def should_write_financials_history(new_companies: list[dict], history_dir: str) -> bool:
    """Determine whether to write a new history file based on data changes.

    Compares new_companies against the latest history file in history_dir.
    Returns True if data changed or no history exists, False if identical.
    """
    history_path = Path(history_dir)
    if not history_path.exists():
        return True

    # Find history files: YYYY-MM-DD.json, exclude latest.json
    history_files = sorted(
        [f for f in history_path.glob("*.json") if f.name != "latest.json"],
        reverse=True,
    )
    if not history_files:
        return True

    # Load the latest history file
    with open(history_files[0], "r", encoding="utf-8") as f:
        latest_data = json.load(f)

    old_companies = latest_data.get("companies", [])

    # Build lookup by company id
    old_lookup = {c["id"]: c for c in old_companies}

    # Compare each new company
    for comp in new_companies:
        cid = comp["id"]
        if cid not in old_lookup:
            return True
        old = old_lookup[cid]
        if comp.get("quarter_date") != old.get("quarter_date"):
            return True
        if comp.get("ar") != old.get("ar"):
            return True
        if comp.get("inventory") != old.get("inventory"):
            return True

    # Also check if a company was removed
    new_ids = {c["id"] for c in new_companies}
    for old_id in old_lookup:
        if old_id not in new_ids:
            return True

    return False


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def _make_companies(*overrides):
    """Helper: create a minimal companies list. Each override is a dict merged
    into the base template."""
    base = {
        "id": "micron",
        "quarter_date": "2025-12-31",
        "ar": 15389000000,
        "inventory": 8267000000,
    }
    if not overrides:
        return [base]
    result = []
    for ov in overrides:
        entry = {**base, **ov}
        result.append(entry)
    return result


def _write_history(directory: Path, filename: str, companies: list[dict]):
    """Helper: write a history JSON file."""
    path = directory / filename
    data = {"updated_at": "2026-04-27T00:00:00Z", "quarter": "2025-12-31", "companies": companies}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)


class TestShouldWriteFinancialsHistory:
    """Tests for should_write_financials_history."""

    def test_first_run_no_history_dir(self):
        """Returns True when the history directory does not exist."""
        result = should_write_financials_history(
            _make_companies(), "/tmp/nonexistent_dir_12345"
        )
        assert result is True

    def test_first_run_empty_dir(self):
        """Returns True when the history directory exists but has no history files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = should_write_financials_history(_make_companies(), tmpdir)
            assert result is True

    def test_first_run_only_latest(self):
        """Returns True when only latest.json exists (no dated history files)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _write_history(Path(tmpdir), "latest.json", _make_companies())
            result = should_write_financials_history(_make_companies(), tmpdir)
            assert result is True

    def test_identical_skips(self):
        """Returns False when new data matches the latest history file exactly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            companies = _make_companies()
            _write_history(Path(tmpdir), "2026-04-27.json", companies)
            result = should_write_financials_history(companies, tmpdir)
            assert result is False

    def test_changed_quarter(self):
        """Returns True when a company's quarter_date has changed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old = _make_companies()
            _write_history(Path(tmpdir), "2026-04-27.json", old)
            new = _make_companies({"quarter_date": "2026-03-31"})
            result = should_write_financials_history(new, tmpdir)
            assert result is True

    def test_changed_ar(self):
        """Returns True when a company's AR value has changed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old = _make_companies()
            _write_history(Path(tmpdir), "2026-04-27.json", old)
            new = _make_companies({"ar": 99999999999})
            result = should_write_financials_history(new, tmpdir)
            assert result is True

    def test_changed_inventory(self):
        """Returns True when a company's inventory value has changed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old = _make_companies()
            _write_history(Path(tmpdir), "2026-04-27.json", old)
            new = _make_companies({"inventory": 11111111111})
            result = should_write_financials_history(new, tmpdir)
            assert result is True

    def test_new_company_added(self):
        """Returns True when a new company appears in the data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old = _make_companies()
            _write_history(Path(tmpdir), "2026-04-27.json", old)
            new = _make_companies({}, {"id": "samsung", "ar": 500, "inventory": 600})
            result = should_write_financials_history(new, tmpdir)
            assert result is True

    def test_company_removed(self):
        """Returns True when a company is removed from the data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old = _make_companies({}, {"id": "samsung", "ar": 500, "inventory": 600})
            _write_history(Path(tmpdir), "2026-04-27.json", old)
            new = _make_companies()  # only micron
            result = should_write_financials_history(new, tmpdir)
            assert result is True

    def test_uses_latest_history_file(self):
        """Compares against the most recent history file (sorted descending)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_data = _make_companies({"ar": 1000})
            new_data = _make_companies({"ar": 2000})

            # older file has ar=1000, newer file has ar=2000
            _write_history(Path(tmpdir), "2026-04-25.json", old_data)
            _write_history(Path(tmpdir), "2026-04-27.json", new_data)

            # new_companies matches the latest (2026-04-27) -> should skip
            result = should_write_financials_history(new_data, tmpdir)
            assert result is False

            # new_companies matches older (2026-04-25) but not latest -> should write
            result2 = should_write_financials_history(old_data, tmpdir)
            assert result2 is True


# ---------------------------------------------------------------------------
# Holders history dedup
# ---------------------------------------------------------------------------

def _holders_fingerprint(company_data: dict) -> tuple:
    """Fingerprint a single company's holder data: top 5 holders by (name, rounded pct)."""
    holders = company_data.get("holders", [])
    top5 = holders[:5]
    return tuple((h["holder"], round(h["pct_held"], 1)) for h in top5)


def should_write_holders_history(new_data: dict, history_dir: str) -> bool:
    """Determine whether to write a new holders history file.

    Compares top 5 holders per company (holder name + pct_held rounded to 1 decimal)
    against the latest dated history file.
    Returns True if data changed or no history exists, False if identical.
    """
    history_path = Path(history_dir)
    if not history_path.exists():
        return True

    history_files = sorted(
        [f for f in history_path.glob("*.json") if f.name != "latest.json"],
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
        if _holders_fingerprint(new_comp) != _holders_fingerprint(old_comp):
            return True

    return False


def _make_holders_data(*company_defs):
    """Helper: create holders data dict.

    Each company_def is (company_id, holders_list).
    If no args, returns a default single-company dataset.
    """
    if not company_defs:
        company_defs = [("micron", [
            {"holder": "Vanguard Group", "shares": 100000, "pct_held": 8.21, "value": 5000000},
            {"holder": "BlackRock", "shares": 90000, "pct_held": 7.55, "value": 4500000},
            {"holder": "State Street", "shares": 50000, "pct_held": 4.10, "value": 2500000},
            {"holder": "Capital Group", "shares": 40000, "pct_held": 3.22, "value": 2000000},
            {"holder": "Fidelity", "shares": 30000, "pct_held": 2.80, "value": 1500000},
        ])]
    companies = {}
    for cid, holders in company_defs:
        companies[cid] = {
            "name": cid.title(),
            "short_name": cid.title(),
            "ticker": f"{cid.upper()}",
            "holders": holders,
        }
    return {"updated_at": "2026-04-28T00:00:00Z", "companies": companies}


def _write_holders_history(directory: Path, filename: str, data: dict):
    """Helper: write a holders history JSON file."""
    path = directory / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)


class TestShouldWriteHoldersHistory:
    """Tests for should_write_holders_history."""

    def test_first_run_no_history(self):
        """Returns True when no history directory exists."""
        result = should_write_holders_history(
            _make_holders_data(), "/tmp/nonexistent_holders_dir_12345"
        )
        assert result is True

    def test_first_run_empty_dir(self):
        """Returns True when history directory exists but is empty."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = should_write_holders_history(_make_holders_data(), tmpdir)
            assert result is True

    def test_identical_skips(self):
        """Returns False when holder data matches exactly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data = _make_holders_data()
            _write_holders_history(Path(tmpdir), "2026-04-27.json", data)
            result = should_write_holders_history(data, tmpdir)
            assert result is False

    def test_pct_change_writes(self):
        """Returns True when a holder's pct_held changes enough to affect rounding."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_data = _make_holders_data()
            _write_holders_history(Path(tmpdir), "2026-04-27.json", old_data)

            # Change Vanguard from 8.21 -> 8.35 (rounds to 8.2 vs 8.4 at 1 decimal)
            new_holders = [
                {"holder": "Vanguard Group", "shares": 100000, "pct_held": 8.35, "value": 5000000},
                {"holder": "BlackRock", "shares": 90000, "pct_held": 7.55, "value": 4500000},
                {"holder": "State Street", "shares": 50000, "pct_held": 4.10, "value": 2500000},
                {"holder": "Capital Group", "shares": 40000, "pct_held": 3.22, "value": 2000000},
                {"holder": "Fidelity", "shares": 30000, "pct_held": 2.80, "value": 1500000},
            ]
            new_data = _make_holders_data(("micron", new_holders))
            result = should_write_holders_history(new_data, tmpdir)
            assert result is True

    def test_tiny_pct_change_skips(self):
        """Returns False when pct_held changes are too small to affect 1-decimal rounding."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_data = _make_holders_data()
            _write_holders_history(Path(tmpdir), "2026-04-27.json", old_data)

            # Change Vanguard from 8.21 -> 8.24 (both round to 8.2 at 1 decimal)
            new_holders = [
                {"holder": "Vanguard Group", "shares": 100000, "pct_held": 8.24, "value": 5000000},
                {"holder": "BlackRock", "shares": 90000, "pct_held": 7.55, "value": 4500000},
                {"holder": "State Street", "shares": 50000, "pct_held": 4.10, "value": 2500000},
                {"holder": "Capital Group", "shares": 40000, "pct_held": 3.22, "value": 2000000},
                {"holder": "Fidelity", "shares": 30000, "pct_held": 2.80, "value": 1500000},
            ]
            new_data = _make_holders_data(("micron", new_holders))
            result = should_write_holders_history(new_data, tmpdir)
            assert result is False

    def test_holder_composition_change_writes(self):
        """Returns True when a holder name changes in top 5."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_data = _make_holders_data()
            _write_holders_history(Path(tmpdir), "2026-04-27.json", old_data)

            # Replace "Fidelity" with "T. Rowe Price" in position 5
            new_holders = [
                {"holder": "Vanguard Group", "shares": 100000, "pct_held": 8.21, "value": 5000000},
                {"holder": "BlackRock", "shares": 90000, "pct_held": 7.55, "value": 4500000},
                {"holder": "State Street", "shares": 50000, "pct_held": 4.10, "value": 2500000},
                {"holder": "Capital Group", "shares": 40000, "pct_held": 3.22, "value": 2000000},
                {"holder": "T. Rowe Price", "shares": 30000, "pct_held": 2.80, "value": 1500000},
            ]
            new_data = _make_holders_data(("micron", new_holders))
            result = should_write_holders_history(new_data, tmpdir)
            assert result is True

    def test_new_company_added_writes(self):
        """Returns True when a new company appears in the data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_data = _make_holders_data()
            _write_holders_history(Path(tmpdir), "2026-04-27.json", old_data)

            samsung_holders = [
                {"holder": "National Pension", "shares": 200000, "pct_held": 10.5, "value": 8000000},
            ]
            new_data = _make_holders_data(
                ("micron", old_data["companies"]["micron"]["holders"]),
                ("samsung", samsung_holders),
            )
            result = should_write_holders_history(new_data, tmpdir)
            assert result is True
