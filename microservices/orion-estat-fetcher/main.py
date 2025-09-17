import os
import functions_framework
import requests
import pandas as pd
from google.cloud import bigquery, secretmanager
from datetime import datetime, timezone
import json

# --- Configuration ---
PROJECT_ID = os.environ.get("GCP_PROJECT", "project-orion-admins")
BQ_DATASET_ID = "orion_datalake"
BQ_TABLE_ID = "jp_macro_data_history"

# --- Clients & API Key Handling ---
bq_client = bigquery.Client()
_estat_api_key = None

def get_estat_api_key():
    """Fetches and caches the e-Stat API key from Secret Manager."""
    global _estat_api_key
    if _estat_api_key:
        return _estat_api_key
    try:
        client = secretmanager.SecretManagerServiceClient()
        secret_name = "estat-api-key"
        resource_name = f"projects/{PROJECT_ID}/secrets/{secret_name}/versions/latest"
        response = client.access_secret_version(name=resource_name)
        _estat_api_key = response.payload.data.decode("UTF-8")
        return _estat_api_key
    except Exception as e:
        print(f"FATAL: Could not fetch e-Stat API key: {e}")
        return None

# --- Main Logic ---
def fetch_and_store_estat_series(series_to_fetch: dict, api_key: str):
    print(f"Fetching data for {len(series_to_fetch)} series from e-Stat API...")
    all_observations = []

    for series_name, series_id in series_to_fetch.items():
        try:
            # Fetch only the last 5 years of data to be efficient
            url = f"https://api.e-stat.go.jp/rest/3.0/app/json/getStatsData?appId={api_key}&statsDataId={series_id}&cdTimeFrom={(datetime.now().year - 5) * 10000 + 101}"
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()['GET_STATS_DATA']['STATISTICAL_DATA']['DATA_INF']['VALUE']

            for obs in data:
                time_code = obs.get('@time')
                value = obs.get('$')
                unit = obs.get('@unit')
                
                if time_code and value and len(time_code) >= 6:
                    # Handle YYYYMM and YYYY formats
                    if len(time_code) == 6: # YYYYMM
                        timestamp = pd.to_datetime(time_code, format='%Y%m') + pd.offsets.MonthEnd(0)
                    elif len(time_code) == 4: # YYYY
                        timestamp = pd.to_datetime(time_code, format='%Y') + pd.offsets.YearEnd(0)
                    else: continue

                    all_observations.append({
                        "timestamp": timestamp,
                        "series_id": series_id,
                        "series_name": series_name,
                        "value": float(value),
                        "unit": unit
                    })
            print(f"  - Successfully fetched {len(data)} observations for {series_name}")
        except Exception as e:
            print(f"  - Failed to fetch {series_name}: {e}")

    if not all_observations:
        print("No new observations found to load.")
        return 0

    df = pd.DataFrame(all_observations).drop_duplicates(subset=['timestamp', 'series_id'], keep='last')
    print(f"A total of {len(df)} unique observations collected. Loading to BigQuery...")

    table_ref_str = f"{PROJECT_ID}.{BQ_DATASET_ID}.{BQ_TABLE_ID}"
    job_config = bigquery.LoadJobConfig(
        schema=[
            bigquery.SchemaField("timestamp", "TIMESTAMP"),
            bigquery.SchemaField("series_id", "STRING"),
            bigquery.SchemaField("series_name", "STRING"),
            bigquery.SchemaField("value", "FLOAT64"),
            bigquery.SchemaField("unit", "STRING"),
        ],
        write_disposition="WRITE_TRUNCATE", # e-Stat data is often revised, so overwriting is safer
        time_partitioning=bigquery.TimePartitioning(field="timestamp"),
    )

    load_job = bq_client.load_table_from_dataframe(df, table_ref_str, job_config=job_config)
    load_job.result()
    print(f"Successfully loaded {len(df)} rows into {table_ref_str}")
    return len(df)

@functions_framework.http
def estat_fetcher_http(request):
    print("Orion e-Stat Fetcher v2 activated...")
    api_key = get_estat_api_key()
    if not api_key:
        return "e-Stat API key secret not found or accessible.", 500

    estat_series_to_fetch = {
        "JP_CPI_ALL_ITEMS": "0003410301",          # 消費者物価指数（総合）
        "JP_IND_PROD": "0003440321",             # 鉱工業生産指数
        "JP_UNEMP_RATE": "0000010206",           # 完全失業率
        "JP_BUSINESS_CONDITIONS_CI": "00100406", # 景気動向指数（CI一致指数）
        "JP_GOVT_BOND_YIELD": "0003436085"      # 国債金利情報
    }

    try:
        rows_loaded = fetch_and_store_estat_series(estat_series_to_fetch, api_key)
        return f"e-Stat Fetcher finished successfully. Loaded {rows_loaded} new data points.", 200
    except Exception as e:
        print(f"ERROR: An unexpected error occurred in e-Stat Fetcher: {e}")
        return "Internal Server Error", 500