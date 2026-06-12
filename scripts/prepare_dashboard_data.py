import os, shutil, zipfile, tempfile
import pandas as pd
import geopandas as gpd

CLEAN_FILE   = r"C:\WORK\crime-monitor\data\gdelt_indonesia_crime_clean.parquet"
WEEKLY_FILE  = r"C:\WORK\crime-monitor\data\gdelt_weekly_province.csv"
MAP_ZIP      = r"C:\WORK\crime-monitor\map\idn_adm_bps_20200401_shp.zip"
ADM2_SHP     = "idn_admbnda_adm2_bps_20200401.shp"
OUT_DIR      = r"C:\WORK\crime-monitor\dashboard\data"

def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    # ── 1. Weekly province (copy) ─────────────────────────────────
    shutil.copy(WEEKLY_FILE, os.path.join(OUT_DIR, "weekly_province.csv"))
    print("Copied  weekly_province.csv")

    # ── 2. Load clean data ────────────────────────────────────────
    df = pd.read_parquet(CLEAN_FILE)
    df["date"]          = pd.to_datetime(df["SQLDATE"].astype(str), format="%Y%m%d")
    df["intensity"]     = df["NumMentions"] * df["GoldsteinScale"].abs()
    df["district_name"] = df["ADM2_EN"].fillna("Unknown")
    df["province_name"] = df["ADM1_EN"].fillna("Unknown")
    df["pcode"]         = df["ADM2_PCODE"].fillna("UNKNOWN")

    # ── 3. District summary (full 24-month period) ────────────────
    dist = (
        df.groupby(["pcode", "district_name", "province_name"])
        .agg(
            total_intensity = ("intensity",      "sum"),
            event_count     = ("intensity",      "count"),
            mean_goldstein  = ("GoldsteinScale", "mean"),
        )
        .reset_index()
    )
    dist["intensity_per_event"] = (dist["total_intensity"] / dist["event_count"]).round(3)
    dist["total_intensity"]     = dist["total_intensity"].round(2)
    dist["mean_goldstein"]      = dist["mean_goldstein"].round(3)
    dist.to_csv(os.path.join(OUT_DIR, "district_summary.csv"), index=False)
    print(f"Created district_summary.csv  ({len(dist)} districts)")

    # ── 4. Map comparison: current (last 30d) vs previous (30-60d) ─
    max_date   = df["date"].max()
    t1_start   = max_date - pd.Timedelta(days=30)
    t0_start   = max_date - pd.Timedelta(days=60)

    curr = (
        df[df["date"] > t1_start]
        .groupby("pcode")
        .agg(curr_intensity=("intensity","sum"), curr_events=("intensity","count"))
        .reset_index()
    )
    prev = (
        df[(df["date"] > t0_start) & (df["date"] <= t1_start)]
        .groupby("pcode")
        .agg(prev_intensity=("intensity","sum"), prev_events=("intensity","count"))
        .reset_index()
    )
    cmp = curr.merge(prev, on="pcode", how="outer").fillna(0)
    cmp["intensity_change"] = (cmp["curr_intensity"] - cmp["prev_intensity"]).round(2)
    cmp["curr_intensity"]   = cmp["curr_intensity"].round(2)
    cmp["prev_intensity"]   = cmp["prev_intensity"].round(2)
    cmp.to_csv(os.path.join(OUT_DIR, "map_comparison.csv"), index=False)
    print(f"Created map_comparison.csv    ({len(cmp)} districts)")
    print(f"  Current : {t1_start.date()} to {max_date.date()}")
    print(f"  Previous: {t0_start.date()} to {t1_start.date()}")

    # ── 5. Simplified adm2 GeoJSON for Leaflet ────────────────────
    print("Exporting GeoJSON (simplifying geometries)...")
    with tempfile.TemporaryDirectory() as tmp:
        with zipfile.ZipFile(MAP_ZIP) as z:
            z.extractall(tmp)
        adm2 = gpd.read_file(os.path.join(tmp, ADM2_SHP))

    adm2 = (
        adm2[["ADM2_PCODE", "ADM2_EN", "ADM1_EN", "geometry"]]
        .rename(columns={"ADM2_PCODE": "pcode", "ADM2_EN": "district", "ADM1_EN": "province"})
        .copy()
    )
    adm2["geometry"] = adm2["geometry"].simplify(0.01, preserve_topology=True)
    gj_path = os.path.join(OUT_DIR, "indonesia_adm2.geojson")
    adm2.to_file(gj_path, driver="GeoJSON")
    print(f"Created indonesia_adm2.geojson ({os.path.getsize(gj_path)/1e6:.1f} MB)")
    print("\nAll dashboard data files ready.")

if __name__ == "__main__":
    main()
