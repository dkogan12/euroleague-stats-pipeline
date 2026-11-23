"""Weekly EuroLeague pipeline: fetch new rounds, check quality, rebuild season file, transform.

Test events (Lambda console):
    {}                      normal weekly run
    {"fire_drill": true}    load saved data, break it on purpose, run checks and alert.
                            Saves nothing except the quality results.
"""
import io
import os
import time
from datetime import datetime, timezone

import boto3
import pandas as pd
from euroleague_api.boxscore_data import BoxScoreData

import checks     # quality/checks.py
import transform  # transform/transform.py

BUCKET = os.environ.get("BUCKET", "dlogan-euroleague-data")
SEASON = int(os.environ.get("SEASON", "2026"))
MAX_NEW_ROUNDS = int(os.environ.get("MAX_NEW_ROUNDS", "3"))
PAUSE_SECONDS = int(os.environ.get("PAUSE_SECONDS", "20"))
ALERT_TOPIC_ARN = os.environ.get("ALERT_TOPIC_ARN", "")

s3 = boto3.client("s3")
ROUNDS_PREFIX = f"raw/boxscores_rounds/season={SEASON}/"
SEASON_KEY = f"raw/boxscores/season={SEASON}/boxscores.csv"


def saved_rounds():
    """Return (sorted round numbers, S3 keys) already saved for this season."""
    keys = []
    for page in s3.get_paginator("list_objects_v2").paginate(Bucket=BUCKET, Prefix=ROUNDS_PREFIX):
        keys += [obj["Key"] for obj in page.get("Contents", [])]
    rounds = sorted(int(k.split("round=")[1].split(".")[0]) for k in keys if "round=" in k)
    return rounds, keys


def read_csv(key):
    return pd.read_csv(io.BytesIO(s3.get_object(Bucket=BUCKET, Key=key)["Body"].read()))


def save_csv(df, key):
    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    s3.put_object(Bucket=BUCKET, Key=key, Body=buffer.getvalue())


def previous_row_count():
    """Rows in the season file from the last good run (0 if there isn't one yet)."""
    try:
        return len(read_csv(SEASON_KEY))
    except s3.exceptions.NoSuchKey:
        return 0


def fetch_new_rounds():
    boxscore = BoxScoreData("E")
    rounds, _ = saved_rounds()
    start = rounds[-1] if rounds else 1  # re-check the last saved round
    fetched = []
    for rnd in range(start, start + MAX_NEW_ROUNDS + 1):
        try:
            df = boxscore.get_players_boxscore_stats_round(SEASON, rnd)
        except Exception as e:
            print(f"Round {rnd}: no data ({e})")
            break
        if df is None or df.empty:
            print(f"Round {rnd}: not played yet")
            break
        save_csv(df, f"{ROUNDS_PREFIX}round={rnd:02d}.csv")
        print(f"Round {rnd}: {len(df)} rows, {df['Gamecode'].nunique()} games")
        fetched.append(rnd)
        time.sleep(PAUSE_SECONDS)
    return fetched


def break_on_purpose(df):
    """Fire drill: add a duplicate player row and a negative score."""
    df = df.copy()
    is_player = df["Player_ID"].astype(str).str.strip().str.startswith("P")
    first_player = df[is_player].index[0]
    df.loc[first_player, "Points"] = -5
    return pd.concat([df, df.loc[[first_player]]], ignore_index=True)


def save_results(results, run_type):
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
    out = pd.DataFrame(results)
    out.insert(0, "run_at_utc", stamp)
    out.insert(1, "run_type", run_type)
    out.insert(2, "season", SEASON)
    key = f"quality/results/season={SEASON}/{run_type}_{stamp}.csv"
    save_csv(out, key)
    print(f"Quality results saved to s3://{BUCKET}/{key}")


def send_alert(subject, message):
    if not ALERT_TOPIC_ARN:
        print("No ALERT_TOPIC_ARN set, skipping email alert")
        return
    boto3.client("sns").publish(TopicArn=ALERT_TOPIC_ARN, Subject=subject[:100], Message=message)
    print("Alert sent")


def lambda_handler(event, context):
    fire_drill = bool((event or {}).get("fire_drill"))
    run_type = "fire_drill" if fire_drill else "weekly"

    fetched = [] if fire_drill else fetch_new_rounds()
    if not fetched and not fire_drill:
        return {"status": "no new data"}

    _, keys = saved_rounds()
    season_df = pd.concat([read_csv(k) for k in keys], ignore_index=True)
    if fire_drill:
        season_df = break_on_purpose(season_df)
    print(f"Season data: {len(season_df)} rows, {season_df['Gamecode'].nunique()} games")

    results = checks.run_checks(season_df, previous_row_count())
    critical_failed, any_failed, summary = checks.summarize(results)
    print(summary)
    save_results(results, run_type)

    if any_failed:
        label = "FIRE DRILL - " if fire_drill else ""
        level = "CRITICAL - run stopped" if critical_failed else "warning - run continued"
        send_alert(f"{label}EuroLeague pipeline {level}",
                   f"Season {SEASON}, rounds fetched: {fetched}\n\n{summary}")

    if fire_drill:
        return {"status": "fire drill done", "critical_failed": critical_failed}
    if critical_failed:
        return {"status": "stopped by quality checks", "rounds_fetched": fetched}

    save_csv(season_df, SEASON_KEY)
    transform.run_transform(SEASON)
    return {"status": "ok", "rounds_fetched": fetched, "rows": len(season_df),
            "warnings": any_failed}


if __name__ == "__main__":
    import json
    import sys
    event = {"fire_drill": True} if "--fire-drill" in sys.argv else {}
    print(lambda_handler(event, None))
