from google.cloud import bigquery
from google.oauth2 import service_account
import pandas as pd

KEY_FILE = r"C:\WORK\crime-monitor\keys\indonesia-crime-monitor-67217eb8ed71.json"

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
        FORMAT_DATE('%Y%m%d', DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY))
        AS INT64
    )
LIMIT 500
"""

def main():
    credentials = service_account.Credentials.from_service_account_file(
        KEY_FILE,
        scopes=["https://www.googleapis.com/auth/bigquery"],
    )
    client = bigquery.Client(credentials=credentials, project=credentials.project_id)

    print("Running sample query against gdelt-bq.gdeltv2.events ...")
    df = client.query(QUERY).to_dataframe()

    print(f"\n--- (1) Shape ---")
    print(df.shape)

    print(f"\n--- (2) First 5 rows ---")
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 120)
    print(df.head())

    print(f"\n--- (3) Null counts per column ---")
    print(df.isnull().sum())

    print(f"\n--- (4) Unique EventCodes ---")
    print(sorted(df["EventCode"].dropna().unique()))

if __name__ == "__main__":
    main()
