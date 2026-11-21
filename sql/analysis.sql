-- =========================================
-- EuroLeague analysis queries (Amazon Athena)
-- =========================================

-- 1. Top 10 scorers, 2024-25 (all phases), minimum 15 games
SELECT player_name, team,
       COUNT(*)               AS games,
       ROUND(AVG(points), 1)  AS ppg,
       ROUND(AVG(minutes), 1) AS mpg
FROM boxscores
WHERE season = 2024 AND minutes > 0
GROUP BY player_name, team
HAVING COUNT(*) >= 15
ORDER BY ppg DESC
LIMIT 10;

-- 2. Most improved scorers, 2023-24 to 2024-25 (min 15 games each season)
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

-- 3. Most efficient scorers: true shooting %, 2024-25, min 10 ppg and 15 games
SELECT player_name, team,
       COUNT(*) AS games,
       ROUND(AVG(points), 1) AS ppg,
       ROUND(100.0 * SUM(points) / (2 * (SUM(fg_att) + 0.44 * SUM(ft_att))), 1) AS ts_pct
FROM boxscores
WHERE season = 2024 AND minutes > 0
GROUP BY player_name, team
HAVING COUNT(*) >= 15 AND AVG(points) >= 10
ORDER BY ts_pct DESC
LIMIT 10;

-- 4. Home vs. away scoring by team, 2024-25, biggest home edge first
SELECT team,
       ROUND(AVG(CASE WHEN is_home = 1 THEN points END), 1) AS home_ppg,
       ROUND(AVG(CASE WHEN is_home = 0 THEN points END), 1) AS away_ppg,
       ROUND(AVG(CASE WHEN is_home = 1 THEN points END)
           - AVG(CASE WHEN is_home = 0 THEN points END), 1) AS home_edge
FROM team_totals
WHERE season = 2024
GROUP BY team
ORDER BY home_edge DESC;

-- 5. Data check: player points should add up to team totals (expect 0 rows)
SELECT p.season, p.game_code, p.team,
       SUM(p.points) AS player_sum, MAX(t.points) AS team_total
FROM boxscores p
JOIN team_totals t
  ON p.season = t.season AND p.game_code = t.game_code AND p.team = t.team
GROUP BY p.season, p.game_code, p.team
HAVING SUM(p.points) <> MAX(t.points);
