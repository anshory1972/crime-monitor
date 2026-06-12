import pandas as pd

CLEAN_FILE = r"C:\WORK\crime-monitor\data\gdelt_indonesia_crime_clean.parquet"
OUT_FILE   = r"C:\WORK\crime-monitor\data\gdelt_weekly_province.csv"

def main():
    df = pd.read_parquet(CLEAN_FILE)

    # ── Step 1: week column (Monday-anchored) ─────────────────────────────
    df["date"] = pd.to_datetime(df["SQLDATE"].astype(str), format="%Y%m%d")
    df["week"] = df["date"].dt.to_period("W-SUN").dt.start_time  # Monday start

    # ── Step 2: per-event intensity ───────────────────────────────────────
    df["intensity"] = df["NumMentions"] * df["GoldsteinScale"].abs()

    # ── Step 3: aggregate by week × province ─────────────────────────────
    # Rows unmatched by spatial join have null ADM1_EN; label them explicitly
    df["province_name"] = df["ADM1_EN"].fillna("Unknown")

    weekly = (
        df.groupby(["week", "province_name"], sort=True)
        .agg(
            total_intensity  = ("intensity",      "sum"),
            event_count      = ("intensity",      "count"),
            mean_goldstein   = ("GoldsteinScale", "mean"),
        )
        .reset_index()
    )

    # ── Step 4: intensity per event ───────────────────────────────────────
    weekly["intensity_per_event"] = weekly["total_intensity"] / weekly["event_count"]

    # Round for readability
    weekly["mean_goldstein"]      = weekly["mean_goldstein"].round(3)
    weekly["total_intensity"]     = weekly["total_intensity"].round(2)
    weekly["intensity_per_event"] = weekly["intensity_per_event"].round(3)

    # ── Step 5: save and report ───────────────────────────────────────────
    weekly.to_csv(OUT_FILE, index=False)

    print(f"Saved: {OUT_FILE}")
    print(f"Shape: {weekly.shape}  ({weekly['week'].nunique()} weeks x {weekly['province_name'].nunique()} provinces)\n")

    print("-- First 10 rows -----------------------------------------------")
    print(weekly.head(10).to_string(index=False))

    print("\n-- Summary statistics ------------------------------------------")
    print(weekly[["total_intensity", "event_count", "mean_goldstein", "intensity_per_event"]].describe().round(3).to_string())

if __name__ == "__main__":
    main()
