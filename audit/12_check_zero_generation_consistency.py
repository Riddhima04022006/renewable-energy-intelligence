import pandas as pd

df = pd.read_csv("../india_monthly.csv")
df["Value"] = pd.to_numeric(df["Value"], errors="coerce")

df = df[
    (df["Category"] == "Electricity generation") &
    (df["Unit"] == "GWh")
]

wide = df.pivot(
    index=["State", "Date"],
    columns="Variable",
    values="Value"
)

fuels = [
    "Solar", "Wind", "Hydro", "Bioenergy",
    "Coal", "Gas", "Nuclear", "Other Fossil",
    "Other Renewables"
]

print("=== ZERO FUEL WITH POSITIVE TOTAL GENERATION ===")

for fuel in fuels:
    if fuel not in wide.columns:
        continue

    mask = (wide[fuel] == 0) & (wide["Total Generation"] > 0)

    print(f"{fuel}: {mask.sum()} state-months")
