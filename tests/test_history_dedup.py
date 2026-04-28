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
