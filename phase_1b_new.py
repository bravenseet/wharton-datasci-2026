import pandas as pd
import numpy as np

# 1) Read and Clean
df = pd.read_excel("unclean_whl.xlsx")

# Ensure numeric and remove non-playing rows
for col in ["home_xg", "away_xg", "toi"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# toi > 0 is vital to avoid Infinite values in xG/60
df = df.dropna(subset=["home_xg", "away_xg", "toi"])
df = df[df["toi"] > 0]

# 2) Build Long Format
home = df[["home_team", "away_team", "home_off_line", "home_xg", "toi"]].copy()
home.columns = ["team", "opponent", "off_line", "xg", "toi"]

away = df[["away_team", "home_team", "away_off_line", "away_xg", "toi"]].copy()
away.columns = ["team", "opponent", "off_line", "xg", "toi"]

data = pd.concat([home, away], ignore_index=True)

# 3) Categorize: First Line vs. Secondary (Depth)
# This captures the disparity across the whole roster
data["line_cat"] = np.where(data["off_line"] == "first_off", "First", "Secondary")

# 4) Compute Opponent Defensive Strength (Baseline)
# How much xG does each team allow on average?
opp_def = data.groupby("opponent").agg({"xg": "sum", "toi": "sum"}).reset_index()
opp_def["opp_xg_allowed_per_60"] = (opp_def["xg"] / opp_def["toi"]) * 3600
opp_def = opp_def.rename(columns={"opponent": "lookup_team"})

# 5) Merge Opponent Strength
data = data.merge(
    opp_def[["lookup_team", "opp_xg_allowed_per_60"]],
    left_on="opponent",
    right_on="lookup_team",
    how="left"
).drop(columns=["lookup_team"])

# 6) Compute Adjusted xG
# 1.0 means they performed exactly at the opponent's average allowed rate
data["xg_per_60"] = (data["xg"] / data["toi"]) * 3600
data["adj_xg_per_60"] = data["xg_per_60"] / data["opp_xg_allowed_per_60"]

# 7) Aggregate by Team and Category (Weighted by TOI)
def weighted_avg(group):
    d = group["adj_xg_per_60"]
    w = group["toi"]
    return (d * w).sum() / w.sum()

grouped = data.groupby(["team", "line_cat"]).apply(weighted_avg).reset_index(name="adj_xg_weighted")
toi_totals = data.groupby(["team", "line_cat"])["toi"].sum().reset_index()
grouped = grouped.merge(toi_totals, on=["team", "line_cat"])

# 8) Filter for Significance
MIN_TOI = 300 
grouped = grouped[grouped["toi"] >= MIN_TOI]

# 9) Pivot and Calculate Disparity
# We need both 'First' and 'Secondary' rows for a team to calculate a ratio
result = grouped.pivot(index="team", columns="line_cat", values="adj_xg_weighted").dropna()

# Disparity = ln(First / Secondary)
result["disparity_log_ratio"] = abs(np.log(result["First"] / result["Secondary"]))

# 10) Rank and Export
result = result.sort_values("disparity_log_ratio", ascending=False)
result.to_csv("total_line_disparity_new.csv")

print(result)