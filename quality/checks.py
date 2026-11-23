"""Data quality checks for raw EuroLeague box scores.

Each check returns a dict:
    check     - short name
    severity  - "critical" (stop the run) or "warning" (alert, keep going)
    passed    - True / False
    bad_rows  - how many rows broke the rule
    detail    - one line explaining the result
"""
import pandas as pd

from transform import minutes_to_decimal

MAX_MINUTES = 50  # regulation is 40; overtime games can run longer


def split_rows(df):
    """Return (player rows, team 'Total' rows) with IDs and names trimmed."""
    df = df.copy()
    df["Player_ID"] = df["Player_ID"].astype(str).str.strip()
    df["Player"] = df["Player"].astype(str).str.strip()
    df["Team"] = df["Team"].astype(str).str.strip()
    players = df[df["Player_ID"].str.startswith("P")]
    totals = df[df["Player"] == "Total"]
    return players, totals


def result(check, severity, bad_rows, detail):
    return {
        "check": check,
        "severity": severity,
        "passed": bad_rows == 0,
        "bad_rows": int(bad_rows),
        "detail": detail,
    }


def check_row_count(df, previous_rows):
    """The season file only grows: fewer rows than last time means data was lost."""
    missing = max(previous_rows - len(df), 0)
    return result("row_count", "critical", missing,
                  f"{len(df)} rows now, {previous_rows} rows last run")


def check_required_fields(players):
    required = ["Player_ID", "Gamecode", "Team"]
    bad = players[required].isna().any(axis=1) | (players["Team"] == "") | (players["Team"] == "nan")
    return result("required_fields", "critical", bad.sum(),
                  f"player rows missing one of {required}")


def check_duplicates(players):
    dupes = players.duplicated(subset=["Gamecode", "Player_ID"], keep=False)
    return result("duplicates", "critical", dupes.sum(),
                  "rows sharing the same game and player")


def check_valid_ranges(players):
    minutes = players["Minutes"].apply(minutes_to_decimal)
    stat_cols = ["Points", "TotalRebounds", "Assistances", "Steals", "Turnovers"]
    negative = (players[stat_cols] < 0).any(axis=1)
    too_long = minutes > MAX_MINUTES
    bad = negative | too_long
    return result("valid_ranges", "warning", bad.sum(),
                  f"negative stats or more than {MAX_MINUTES} minutes")


def check_points_reconcile(players, totals):
    """Each team's player points should add up to its 'Total' row for that game."""
    player_sum = players.groupby(["Gamecode", "Team"])["Points"].sum()
    team_total = totals.groupby(["Gamecode", "Team"])["Points"].sum()
    joined = pd.concat([player_sum.rename("players"), team_total.rename("total")], axis=1)
    mismatched = joined[joined["players"] != joined["total"]]
    return result("points_reconcile", "warning", len(mismatched),
                  f"team-games where player points != team total (of {len(joined)})")


def run_checks(df, previous_rows=0):
    players, totals = split_rows(df)
    return [
        check_row_count(df, previous_rows),
        check_required_fields(players),
        check_duplicates(players),
        check_valid_ranges(players),
        check_points_reconcile(players, totals),
    ]


def summarize(results):
    """Return (critical_failed, any_failed, text summary)."""
    critical_failed = any(not r["passed"] and r["severity"] == "critical" for r in results)
    any_failed = any(not r["passed"] for r in results)
    lines = [
        f"[{'PASS' if r['passed'] else 'FAIL'}] {r['check']} ({r['severity']}): "
        f"{r['bad_rows']} bad rows - {r['detail']}"
        for r in results
    ]
    return critical_failed, any_failed, "\n".join(lines)
