-- Database
CREATE DATABASE euroleague;

-- Player box scores: one row per player per game
CREATE EXTERNAL TABLE boxscores (
  phase string, `round` bigint, game_code bigint, is_home bigint,
  player_id string, is_starter bigint, is_playing bigint, team string,
  jersey_number bigint, player_name string, points bigint,
  fg2_made bigint, fg2_att bigint, fg3_made bigint, fg3_att bigint,
  ft_made bigint, ft_att bigint, off_reb bigint, def_reb bigint,
  total_reb bigint, assists bigint, steals bigint, turnovers bigint,
  blocks bigint, blocks_against bigint, fouls_committed bigint,
  fouls_received bigint, pir bigint, plus_minus double,
  minutes double, fg_made bigint, fg_att bigint
)
PARTITIONED BY (season int)
STORED AS PARQUET
LOCATION 's3://dlogan-euroleague-data/curated/boxscores/';

MSCK REPAIR TABLE boxscores;

-- Team totals: one row per team per game
CREATE EXTERNAL TABLE team_totals (
  phase string, `round` bigint, game_code bigint, is_home bigint,
  team string, points bigint,
  fg2_made bigint, fg2_att bigint, fg3_made bigint, fg3_att bigint,
  ft_made bigint, ft_att bigint, off_reb bigint, def_reb bigint,
  total_reb bigint, assists bigint, steals bigint, turnovers bigint,
  blocks bigint, blocks_against bigint, fouls_committed bigint,
  fouls_received bigint, pir bigint
)
PARTITIONED BY (season int)
STORED AS PARQUET
LOCATION 's3://dlogan-euroleague-data/curated/team_totals/';

MSCK REPAIR TABLE team_totals;
