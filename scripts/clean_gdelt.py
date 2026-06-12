import zipfile
import tempfile
import os
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

RAW_FILE   = r"C:\WORK\crime-monitor\data\gdelt_indonesia_crime_raw.parquet"
MAP_ZIP    = r"C:\WORK\crime-monitor\map\idn_adm_bps_20200401_shp.zip"
ADM2_SHP   = "idn_admbnda_adm2_bps_20200401.shp"
OUT_FILE   = r"C:\WORK\crime-monitor\data\gdelt_indonesia_crime_clean.parquet"

IDN_BBOX = dict(lat_min=-11, lat_max=6, lon_min=95, lon_max=141)

def report(df, label):
    print(f"  {label:<55} {len(df):>7,} rows")

def main():
    print("Loading raw parquet ...")
    df = pd.read_parquet(RAW_FILE)
    report(df, "Raw")
    print()

    # ── Step 1: drop null coordinates ────────────────────────────────────
    print("Step 1 — Drop null coordinates")
    df = df.dropna(subset=["ActionGeo_Lat", "ActionGeo_Long"])
    report(df, "After dropping null lat/lon")
    print()

    # ── Step 2: bounding box filter ──────────────────────────────────────
    print("Step 2 — Drop rows outside Indonesia bounding box")
    mask = (
        df["ActionGeo_Lat"].between(IDN_BBOX["lat_min"], IDN_BBOX["lat_max"]) &
        df["ActionGeo_Long"].between(IDN_BBOX["lon_min"], IDN_BBOX["lon_max"])
    )
    df = df[mask]
    report(df, "After bounding box filter")
    print()

    # ── Step 3: deduplicate ───────────────────────────────────────────────
    print("Step 3 — Deduplicate (keep highest NumSources per SQLDATE/EventCode/Lat/Lon)")
    df = (
        df.sort_values("NumSources", ascending=False)
          .drop_duplicates(
              subset=["SQLDATE", "EventCode", "ActionGeo_Lat", "ActionGeo_Long"],
              keep="first"
          )
    )
    report(df, "After deduplication")
    print()

    # ── Step 4: spatial join to adm2 boundaries ──────────────────────────
    print("Step 4 — Spatial join to BPS adm2 boundaries ...")
    with tempfile.TemporaryDirectory() as tmp:
        with zipfile.ZipFile(MAP_ZIP) as z:
            z.extractall(tmp)
        adm2 = gpd.read_file(os.path.join(tmp, ADM2_SHP))[
            ["ADM2_EN", "ADM2_PCODE", "ADM1_EN", "ADM1_PCODE", "geometry"]
        ]

    gdf = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df["ActionGeo_Long"], df["ActionGeo_Lat"]),
        crs="EPSG:4326",
    )

    joined = gpd.sjoin(gdf, adm2, how="left", predicate="within")
    joined = joined.drop(columns=["index_right", "geometry"])

    before = len(joined)
    unmatched = joined["ADM2_PCODE"].isna().sum()
    report(joined, "After spatial join (all points)")
    print(f"  {'  -> matched to a district':<55} {before - unmatched:>7,} rows")
    print(f"  {'  -> outside all polygons (kept, no district)':<55} {unmatched:>7,} rows")
    print()

    # ── Step 5: save ──────────────────────────────────────────────────────
    print(f"Saving to {OUT_FILE} ...")
    joined.to_parquet(OUT_FILE, index=False)
    print("Done.")

    print("\n-- Final summary ----------------------------------------------")
    report(joined, "Clean dataset")
    print(f"  {'Columns':<55} {list(joined.columns)}")

if __name__ == "__main__":
    main()
