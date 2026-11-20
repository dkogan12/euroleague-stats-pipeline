"""Clean raw box scores and save curated Parquet files to S3."""
import argparse
import io

import boto3
import pandas as pd

BUCKET = "dlogan-euroleague-data"
s3 = boto3.client("s3")

RENAME = {
    "Season": "season", "Phase": "phase", "Round": "round", "Gamecode": "game_code",
    "Home": "is_home", "Player_ID": "player_id", "IsStarter": "is_starter",
    "IsPlaying": "is_playing", "Team": "team", "Dorsal": "jersey_number",
    "Player": "player_name", "Minutes": "minutes_raw", "Points": "points",
    "FieldGoalsMade2": "fg2_made", "FieldGoalsAttempted2": "fg2_att",
    "FieldGoalsMade3": "fg3_made", "FieldGoalsAttempted3": "fg3_att",
    "FreeThrowsMade": "ft_made", "FreeThrowsAttempted": "ft_att",
    "OffensiveRebounds": "off_reb", "DefensiveRebounds": "def_reb",
    "TotalRebounds": "total_reb", "Assistances": "assists", "Steals": "steals",
    "Turnovers": "turnovers", "BlocksFavour": "blocks", "BlocksAgainst": "blocks_against",
    "FoulsCommited": "fouls_committed", "FoulsReceived": "fouls_received",
    "Valuation": "pir", "Plusminus": "plus_minus",
}


def minutes_to_decimal(value):
    """Turn '25:30' into 25.5. Anything else (DNP, blank) becomes 0."""
    text = str(value).strip()
    if ":" not in text:
        return 0.0
    mins, secs = text.split(":")[:2]
    try:
        return round(int(mins) + int(secs) / 60, 2)
    except ValueError:
        return 0.0


def read_raw(season):
    key = f"raw/boxscores/season={season}/boxscores.csv"
    obj = s3.get_object(Bucket=BUCKET, Key=key)
    return pd.read_csv(io.BytesIO(obj["Body"].read()))


def write_parquet(df, key):
    buffer = io.BytesIO()
    df.to_parquet(buffer, index=False)
    s3.put_object(Bucket=BUCKET, Key=key, Body=buffer.getvalue())
    print(f"Saved {len(df)} rows to s3://{BUCKET}/{key}")


def run_transform(season):
    df = read_raw(season).rename(columns=RENAME)

    # Trim stray spaces from text columns
    for col in ["player_id", "player_name", "team", "phase"]:
        df[col] = df[col].astype(str).str.strip()

    # Split rows: players vs. team totals; drop the "Team" helper rows
    totals = df[df["player_name"] == "Total"].copy()
    players = df[df["player_id"].str.startswith("P")].copy()

    # Players: fix types and add useful columns
    players["minutes"] = players["minutes_raw"].apply(minutes_to_decimal)
    players["is_starter"] = players["is_starter"].fillna(0).astype(int)
    players["is_playing"] = players["is_playing"].fillna(0).astype(int)
    players["jersey_number"] = players["jersey_number"].astype("Int64")
    players["fg_made"] = players["fg2_made"] + players["fg3_made"]
    players["fg_att"] = players["fg2_att"] + players["fg3_att"]
    players = players.drop(columns=["minutes_raw", "season"])

    # Team totals: keep game-level team stats only
    totals = totals.drop(columns=["player_id", "player_name", "is_starter",
                                  "is_playing", "jersey_number", "plus_minus",
                                  "minutes_raw", "season"])

    print(f"Season {season}: {len(players)} player rows, {len(totals)} team-total rows")
    write_parquet(players, f"curated/boxscores/season={season}/boxscores.parquet")
    write_parquet(totals, f"curated/team_totals/season={season}/team_totals.parquet")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", type=int, required=True)
    args = parser.parse_args()
    run_transform(args.season)
