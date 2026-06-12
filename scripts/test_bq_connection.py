import sys
from google.cloud import bigquery
from google.oauth2 import service_account

KEY_FILE = r"C:\WORK\crime-monitor\keys\indonesia-crime-monitor-67217eb8ed71.json"

def test_connection(key_path: str) -> None:
    credentials = service_account.Credentials.from_service_account_file(
        key_path,
        scopes=["https://www.googleapis.com/auth/bigquery"],
    )
    client = bigquery.Client(credentials=credentials, project=credentials.project_id)

    result = client.query("SELECT 1 AS test").result()
    row = next(iter(result))
    assert row.test == 1

    print("Connection successful")
    print(f"  Project : {client.project}")
    print(f"  Location: {client.location or 'default'}")

if __name__ == "__main__":
    key_path = sys.argv[1] if len(sys.argv) > 1 else KEY_FILE
    test_connection(key_path)
