"""Unit tests for the data quality checks. Run with:  pytest tests/ -v"""
import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "transform"))
sys.path.insert(0, os.path.join(ROOT, "quality"))

import checks  # noqa: E402
from transform import minutes_to_decimal  # noqa: E402


def make_game():
    """One clean game: two players and a Total row per team (raw column names)."""
    rows = []
    for team, pts in [("PAN", (20, 10)), ("BER", (15, 12))]:
        for i, p in enumerate(pts):
            rows.append({"Gamecode": 1, "Team": team, "Player_ID": f"P00{team}{i}  ",
                         "Player": f"PLAYER {team} {i}", "Minutes": "25:30", "Points": p,
                         "TotalRebounds": 4, "Assistances": 2, "Steals": 1, "Turnovers": 1})
        rows.append({"Gamecode": 1, "Team": team, "Player_ID": "", "Player": "Total",
                     "Minutes": "200:00", "Points": sum(pts), "TotalRebounds": 8,
                     "Assistances": 4, "Steals": 2, "Turnovers": 2})
    return pd.DataFrame(rows)


def by_name(results):
    return {r["check"]: r for r in results}


def test_minutes_conversion():
    assert minutes_to_decimal("25:30") == 25.5
    assert minutes_to_decimal("DNP") == 0.0
    assert minutes_to_decimal(None) == 0.0


def test_clean_game_passes_everything():
    results = checks.run_checks(make_game(), previous_rows=0)
    assert all(r["passed"] for r in results), results


def test_duplicate_row_is_critical():
    df = make_game()
    df = pd.concat([df, df.iloc[[0]]], ignore_index=True)
    r = by_name(checks.run_checks(df))["duplicates"]
    assert not r["passed"] and r["severity"] == "critical" and r["bad_rows"] == 2


def test_negative_points_caught():
    df = make_game()
    df.loc[0, "Points"] = -5
    results = by_name(checks.run_checks(df))
    assert not results["valid_ranges"]["passed"]
    assert not results["points_reconcile"]["passed"]


def test_shrinking_data_is_critical():
    r = by_name(checks.run_checks(make_game(), previous_rows=100))["row_count"]
    assert not r["passed"] and r["severity"] == "critical"


def test_summary_flags_critical():
    df = make_game()
    df = pd.concat([df, df.iloc[[0]]], ignore_index=True)
    critical_failed, any_failed, text = checks.summarize(checks.run_checks(df))
    assert critical_failed and any_failed and "[FAIL] duplicates" in text
