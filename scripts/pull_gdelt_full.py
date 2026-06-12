from google.cloud import bigquery
from google.oauth2 import service_account
import pandas as pd

KEY_FILE  = r"C:\WORK\crime-monitor\keys\indonesia-crime-monitor-67217eb8ed71.json"
OUT_FILE  = r"C:\WORK\crime-monitor\data\gdelt_indonesia_crime_raw.parquet"

QUERY = """
SELECT
    SQLDATE,
    EventCode,
    ActionGeo_FullName,
    ActionGeo_Lat,
    ActionGeo_Long,
    GoldsteinScale,
    NumMentions,
    NumSources
FROM `gdelt-bq.gdeltv2.events`
WHERE
    ActionGeo_CountryCode = 'ID'
    AND LEFT(EventCode, 2) IN ('14', '18', '19')
    AND SQLDATE >= CAST(
        FORMAT_DATE('%Y%m%d', DATE_SUB(CURRENT_DATE(), INTERVAL 24 MONTH))
        AS INT64
    )
"""

def main():
    credentials = service_account.Credentials.from_service_account_file(
        KEY_FILE,
        scopes=["https://www.googleapis.com/auth/bigquery"],
    )
    client = bigquery.Client(credentials=credentials, project=credentials.project_id)

    print("Estimating query size ...")
    job_config = bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)
    dry = client.query(QUERY, job_config=job_config)
    mb = dry.total_bytes_processed / 1_048_576
    print(f"  Bytes to scan: {dry.total_bytes_processed:,}  ({mb:.1f} MB)")

    print("\nRunning full pull (24 months, Indonesia, EventCode 14x/18x/19x) ...")
    df = client.query(QUERY).to_dataframe()

    # normalise SQLDATE to a proper date column for inspection
    df["date"] = pd.to_datetime(df["SQLDATE"].astype(str), format="%Y%m%d")

    print(f"\nSaving to {OUT_FILE} ...")
    df.to_parquet(OUT_FILE, index=False)
    print("Saved.")

    print("\n--- Final shape ---")
    print(df.shape)

    print("\n--- Date range ---")
    print(f"  Earliest : {df['date'].min().date()}")
    print(f"  Latest   : {df['date'].max().date()}")
    print(f"  Span     : {(df['date'].max() - df['date'].min()).days} days")

if __name__ == "__main__":
    main()
