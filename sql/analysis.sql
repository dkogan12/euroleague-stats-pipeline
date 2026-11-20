-- Top 10 scorers, 2024-25 season (all phases), minimum 15 games played
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
