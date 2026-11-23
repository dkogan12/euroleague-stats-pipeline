"""Weekly EuroLeague pipeline: fetch new rounds, rebuild season file, run transform."""
import io
import os
import time

import boto3
import pandas as pd
from euroleague_api.boxscore_data import BoxScoreData

import transform  # reuses run_transform() from transform/transform.py

BUCKET = os.environ.get("BUCKET", "dlogan-euroleague-data")
SEASON = int(os.environ.get("SEASON", "2026"))
MAX_NEW_ROUNDS = int(os.environ.get("MAX_NEW_ROUNDS", "3"))
PAUSE_SECONDS = int(os.environ.get("PAUSE_SECONDS", "20"))

s3 = boto3.client("s3")
ROUNDS_PREFIX = f"raw/boxscores_rounds/season={SEASON}/"


def saved_rounds():
    """Return (sorted round numbers, S3 keys) already saved for this season."""
    keys = []
    for page in s3.get_paginator("list_objects_v2").paginate(Bucket=BUCKET, Prefix=ROUNDS_PREFIX):
        keys += [obj["Key"] for obj in page.get("Contents", [])]
    rounds = sorted(int(k.split("round=")[1].split(".")[0]) for k in keys if "round=" in k)
    return rounds, keys


def save_csv(df, key):
    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    s3.put_object(Bucket=BUCKET, Key=key, Body=buffer.getvalue())


def lambda_handler(event, context):
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

    if not fetched:
        return {"status": "no new data"}

    # Combine every saved round into the season file that transform.py reads
    _, keys = saved_rounds()
    frames = [pd.read_csv(io.BytesIO(s3.get_object(Bucket=BUCKET, Key=k)["Body"].read()))
              for k in keys]
    season_df = pd.concat(frames, ignore_index=True)
    save_csv(season_df, f"raw/boxscores/season={SEASON}/boxscores.csv")
    print(f"Season file: {len(season_df)} rows, {season_df['Gamecode'].nunique()} games")

    transform.run_transform(SEASON)
    return {"status": "ok", "rounds_fetched": fetched, "rows": len(season_df)}


if __name__ == "__main__":
    print(lambda_handler({}, None))
