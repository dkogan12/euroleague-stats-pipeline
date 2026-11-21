-- Players whose points per game rose the most between seasons (min 15 games each)
WITH per_season AS (
  SELECT player_id, player_name, season,
         COUNT(*) AS games, AVG(points) AS ppg
  FROM boxscores
  WHERE minutes > 0
  GROUP BY player_id, player_name, season
  HAVING COUNT(*) >= 15
)
SELECT a.player_name,
       ROUND(a.ppg, 1) AS ppg_2023,
       ROUND(b.ppg, 1) AS ppg_2024,
       ROUND(b.ppg - a.ppg, 1) AS change
FROM per_season a
JOIN per_season b
  ON a.player_id = b.player_id AND a.season = 2023 AND b.season = 2024
ORDER BY change DESC
LIMIT 10;
