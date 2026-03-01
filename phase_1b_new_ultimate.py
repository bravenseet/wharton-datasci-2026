import pandas as pd
import numpy as np

# ----------------------------
# 1) Read and Sanitize
# ----------------------------
df = pd.read_excel("unclean_whl.xlsx")

# Convert to numeric and drop rows with missing or zero TOI
cols = ["home_xg", "away_xg", "toi"]
for col in cols:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# SAFETY: We filter TOI > 0 here to prevent 'inf' values in our xG/60 calculations
df = df.dropna(subset=cols)
df = df[df["toi"] > 0]

# ----------------------------
# 2) Build Long Format (One row per team-matchup)
# ----------------------------
home = df[["home_team", "away_team", "home_off_line", "home_xg", "toi"]].copy()
home.columns = ["team", "opponent", "off_line", "xg", "toi"]

away = df[["away_team", "home_team", "away_off_line", "away_xg", "toi"]].copy()
away.columns = ["team", "opponent", "off_line", "xg", "toi"]

data = pd.concat([home, away], ignore_index=True)

# ----------------------------
# 3) Categorize "First" vs "Secondary"
# ----------------------------
# The prompt asks for "secondary lines" (plural). By using np.where, we 
# categorize "first_off" as 'First' and EVERYTHING else as 'Secondary'.
data["line_cat"] = np.where(data["off_line"] == "first_off", "First", "Secondary")

# ----------------------------
# 4) Compute Opponent Defensive Strength
# ----------------------------
# Since team quality is constant (WHL context), this season-long baseline is perfect.
opp_def = data.groupby("opponent").agg({"xg": "sum", "toi": "sum"}).reset_index()
opp_def["opp_xg_allowed_per_60"] = (opp_def["xg"] / opp_def["toi"]) * 3600
opp_def = opp_def.rename(columns={"opponent": "lookup_team"})

# Merge baseline back into game data
data = data.merge(
    opp_def[["lookup_team", "opp_xg_allowed_per_60"]],
    left_on="opponent",
    right_on="lookup_team",
    how="left"
).drop(columns=["lookup_team"])

# ----------------------------
# 5) Compute Adjusted Performance
# ----------------------------
data["xg_per_60"] = (data["xg"] / data["toi"]) * 3600
data["adj_xg_per_60"] = data["xg_per_60"] / data["opp_xg_allowed_per_60"]

# ----------------------------
# 6) Aggregate with TOI Weighting
# ----------------------------
# We use np.average(weights=...) for accuracy.
def weighted_stats(group):
    return pd.Series({
        "adj_xg": np.average(group["adj_xg_per_60"], weights=group["toi"]),
        "total_toi": group["toi"].sum()
    })

grouped = data.groupby(["team", "line_cat"]).apply(weighted_stats).reset_index()

# ----------------------------
# 7) Significance Filter & Pivot
# ----------------------------
MIN_TOI = 300
grouped = grouped[grouped["total_toi"] >= MIN_TOI]

# Pivot creates columns for 'First' and 'Secondary' automatically
result = grouped.pivot(index="team", columns="line_cat", values="adj_xg").dropna()

# ----------------------------
# 8) Compute Disparity (Ratio & Log Ratio)
# ----------------------------
# We provide both: Raw Ratio for intuition, Log Ratio for ranking.
result["disparity_ratio"] = result["First"] / result["Secondary"]
result["disparity_log_ratio"] = abs(np.log(result["disparity_ratio"]))

# Rank from largest disparity to smallest
result = result.sort_values("disparity_log_ratio", ascending=False)

# Save
result.to_csv("whl_line_disparity_new.csv")
print(result)