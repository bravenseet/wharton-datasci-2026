import pandas as pd
import numpy as np

# ----------------------------
# 1) Read raw data
# ----------------------------
df = pd.read_excel("unclean_whl.xlsx")

# Ensure numeric
df["home_xg"] = pd.to_numeric(df["home_xg"], errors="coerce")
df["away_xg"] = pd.to_numeric(df["away_xg"], errors="coerce")
df["toi"] = pd.to_numeric(df["toi"], errors="coerce")

# Drop bad rows
df = df.dropna(subset=["home_xg", "away_xg", "toi"])

# ----------------------------
# 2) Build long format dataset (home + away)
# ----------------------------
home = df[["home_team", "away_team", "home_off_line", "home_xg", "toi"]].copy()
home.columns = ["team", "opponent", "off_line", "xg", "toi"]

away = df[["away_team", "home_team", "away_off_line", "away_xg", "toi"]].copy()
away.columns = ["team", "opponent", "off_line", "xg", "toi"]

data = pd.concat([home, away], ignore_index=True)

# ----------------------------
# 3) Keep only first & second lines
# ----------------------------
data = data[data["off_line"].isin(["first_off", "second_off"])].copy()

mapping = {"first_off": 1, "second_off": 2}
data["off_line"] = data["off_line"].map(mapping)

data = data.dropna(subset=["off_line", "xg", "toi"])

# ----------------------------
# 4) Compute opponent defensive strength
#    (season-level xG allowed per 60)
# ----------------------------
home_allowed = df[["home_team", "away_xg", "toi"]].copy()
home_allowed.columns = ["team", "xg_allowed", "toi"]

away_allowed = df[["away_team", "home_xg", "toi"]].copy()
away_allowed.columns = ["team", "xg_allowed", "toi"]

opp_def = pd.concat([home_allowed, away_allowed], ignore_index=True)

opp_def = (
    opp_def
    .groupby("team")[["xg_allowed", "toi"]]
    .sum()
    .reset_index()
)

opp_def["xg_allowed_per_60"] = (
    opp_def["xg_allowed"] / opp_def["toi"] * 3600
)

# ----------------------------
# 5) Merge opponent strength into each game row
# ----------------------------
data = data.merge(
    opp_def[["team", "xg_allowed_per_60"]],
    left_on="opponent",
    right_on="team",
    how="left",
    suffixes=("", "_opp")
)

data = data.rename(columns={
    "xg_allowed_per_60": "opp_xg_allowed_per_60"
}).drop(columns=["team_opp"])

# ----------------------------
# 6) Compute raw xG per 60 (game level)
# ----------------------------
data["xg_per_60"] = data["xg"] / data["toi"] * 3600

# ----------------------------
# 7) Opponent-adjusted performance (ratio method)
# ----------------------------
data["adj_xg_per_60"] = (
    data["xg_per_60"] / data["opp_xg_allowed_per_60"]
)

# ----------------------------
# 8) Aggregate AFTER opponent adjustment
#    Weight by TOI
# ----------------------------
grouped = (
    data
    .groupby(["team", "off_line"])
    .apply(lambda x: np.average(
        x["adj_xg_per_60"],
        weights=x["toi"]
    ))
    .reset_index(name="adj_xg_per_60_weighted")
)

# ----------------------------
# 9) Optional: minimum TOI filter (recommended)
# ----------------------------
toi_totals = (
    data.groupby(["team", "off_line"])["toi"]
    .sum()
    .reset_index()
)

grouped = grouped.merge(toi_totals, on=["team", "off_line"])

MIN_TOI = 300  # adjust if needed
grouped = grouped[grouped["toi"] >= MIN_TOI]

# ----------------------------
# 10) Split first & second lines
# ----------------------------
first = grouped[grouped["off_line"] == 1][
    ["team", "adj_xg_per_60_weighted"]
].copy()

first.columns = ["team", "first_line_adj"]

second = grouped[grouped["off_line"] == 2][
    ["team", "adj_xg_per_60_weighted"]
].copy()

second.columns = ["team", "second_line_adj"]

# ----------------------------
# 11) Compute disparity (log ratio)
# ----------------------------
result = pd.merge(first, second, on="team", how="inner")

eps = 1e-6
result["disparity_log_ratio"] = np.log(
    (result["first_line_adj"] + eps) /
    (result["second_line_adj"] + eps)
)

# ----------------------------
# 12) Rank teams
# ----------------------------
result = result.sort_values(
    "disparity_log_ratio",
    ascending=False
)

# Save
result.to_csv("total_line_disparity_new.csv", index=False)

print(result)