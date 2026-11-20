from euroleague_api.shot_data import ShotData

shotdata = ShotData("E")
df = shotdata.get_game_shot_data(2024, 1)

print("Rows:", len(df))
print("Columns:", list(df.columns))
print(df.head())

df.to_csv("test_game1_shots.csv", index=False)
print("Saved test_game1_shots.csv")
