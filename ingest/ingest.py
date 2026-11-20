"""Pull one EuroLeague season of player box scores, round by round, and save to S3."""
import argparse
import io
import time

import boto3
import pandas as pd
from euroleague_api.boxscore_data import BoxScoreData

BUCKET = "dlogan-euroleague-data"
PAUSE_SECONDS = 20   # wait between rounds so the server doesn't block us


def run_ingest(season, max_rounds=50):
    boxscore = BoxScoreData("E")
    frames = []
    empty_in_a_row = 0

    for rnd in range(1, max_rounds + 1):
        try:
            df = boxscore.get_players_boxscore_stats_round(season, rnd)
        except Exception as e:
            print(f"Round {rnd}: error {e}")
            df = pd.DataFrame()

        if df is None or df.empty:
            empty_in_a_row += 1
            print(f"Round {rnd}: no data")
            if empty_in_a_row >= 2:
                print("Two empty rounds in a row, season is over.")
                break
        else:
            empty_in_a_row = 0
            games = df["Gamecode"].nunique() if "Gamecode" in df.columns else "?"
            print(f"Round {rnd}: {len(df)} rows, {games} games")
            frames.append(df)

        time.sleep(PAUSE_SECONDS)

    full = pd.concat(frames, ignore_index=True)
    print("Total rows:", len(full))
    if "Gamecode" in full.columns:
        print("Total games:", full["Gamecode"].nunique())

    key = f"raw/boxscores/season={season}/boxscores.csv"
    buffer = io.StringIO()
    full.to_csv(buffer, index=False)
    boto3.client("s3").put_object(Bucket=BUCKET, Key=key, Body=buffer.getvalue())
    print(f"Saved to s3://{BUCKET}/{key}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", type=int, required=True)
    args = parser.parse_args()
    run_ingest(args.season)
