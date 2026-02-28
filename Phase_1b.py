import pandas as pd

# 1) Read the raw file
df = pd.read_excel("unclean_whl.xlsx") 

# 2) Two tables: one for home, one for away
home = df[["home_team", "home_off_line", "home_xg", "toi"]].copy()
home.columns = ["team", "off_line", "xg", "toi"]

away = df[["away_team", "away_off_line", "away_xg", "toi"]].copy()
away.columns = ["team", "off_line", "xg", "toi"]

# 3) Combine into one table
data = pd.concat([home, away], ignore_index=True)

# 4) Keep only 1st and 2nd lines, ignoring Powerplay and other things
data = data[(data["off_line"] == "first_off") | (data["off_line"] == "second_off")].copy()

# 5) Turn line labels into numbers and ensure numeric type
mapping = {"first_off": 1, "second_off": 2}
data["off_line"] = data["off_line"].replace(mapping)

# 6) Ensure all relevant columns are numeric (critical for math later)
data["off_line"] = pd.to_numeric(data["off_line"], errors="coerce")
data["xg"] = pd.to_numeric(data["xg"], errors="coerce")
data["toi"] = pd.to_numeric(data["toi"], errors="coerce")

# Drop any rows that couldn't be converted to numbers to avoid errors in step 7
data = data.dropna(subset=["off_line", "xg", "toi"])

# 7) Sum xG and TOI per team + line
grouped = data.groupby(["team", "off_line"])[["xg", "toi"]].sum().reset_index()

# 8) Calculate xG per 60
grouped["xg_per_60"] = grouped["xg"] / grouped["toi"] * 3600

# 9) Split lines into first and second 
first = grouped[grouped["off_line"] == 1][["team", "xg_per_60"]].copy()
first.columns = ["team", "first_line_xg60"]

second = grouped[grouped["off_line"] == 2][["team", "xg_per_60"]].copy()
second.columns = ["team", "secondary_xg60"]

# 10) Calculate disparity ratio
result = pd.merge(first, second, on="team", how="inner")
result["disparity_ratio"] = result["first_line_xg60"] / result["secondary_xg60"]

# 11) Rank + save top 10
result = result.sort_values("disparity_ratio", ascending=False)
top10 = result.head(10)

result.to_csv("total_line_disparity.csv", index=False)
print(result)


