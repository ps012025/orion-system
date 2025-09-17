import os
import functions_framework
import requests
import pandas as pd
from google.cloud import bigquery, secretmanager
from datetime import datetime, timezone

# --- Configuration ---
PROJECT_ID = os.environ.get("GCP_PROJECT", "project-orion-admins")
BQ_DATASET_ID = "orion_datalake"
BQ_TABLE_ID = "macro_data_history"

# --- Clients & API Key Handling ---
bq_client = bigquery.Client()
_fred_api_key = None

def get_fred_api_key():
    """Fetches and caches the FRED API key from Secret Manager."""
    global _fred_api_key
    if _fred_api_key:
        return _fred_api_key
    try:
        client = secretmanager.SecretManagerServiceClient()
        secret_name = "fred-api-key"
        resource_name = f"projects/{PROJECT_ID}/secrets/{secret_name}/versions/latest"
        print(f"Fetching secret: {secret_name}")
        response = client.access_secret_version(name=resource_name)
        _fred_api_key = response.payload.data.decode("UTF-8")
        print("Successfully fetched FRED API key.")
        return _fred_api_key
    except Exception as e:
        print(f"FATAL: Could not fetch FRED API key: {e}")
        return None

# --- Main Logic ---
def fetch_and_store_fred_series(series_ids: dict, api_key: str):
    """Fetches multiple series from FRED and stores them in BigQuery."""
    print(f"Fetching data for {len(series_ids)} series from FRED API...")
    all_observations = []

    for series_id, series_name in series_ids.items():
        try:
            url = f"https://api.stlouisfed.org/fred/series/observations?series_id={series_id}&api_key={api_key}&file_type=json"
            response = requests.get(url, timeout=20)
            response.raise_for_status()
            data = response.json()['observations']
            
            for obs in data:
                value = obs.get('value')
                if value != '.': # FRED uses '.' for missing data
                    all_observations.append({
                        "timestamp": pd.to_datetime(obs['date']),
                        "series_id": series_id,
                        "series_name": series_name,
                        "value": float(value)
                    })
            print(f"  - Successfully fetched {len(data)} observations for {series_id}")
        except Exception as e:
            print(f"  - Failed to fetch {series_id}: {e}")

    if not all_observations:
        print("No new observations found to load.")
        return 0

    df = pd.DataFrame(all_observations)
    print(f"A total of {len(df)} valid observations collected. Loading to BigQuery...")

    table_ref_str = f"{PROJECT_ID}.{BQ_DATASET_ID}.{BQ_TABLE_ID}"
    job_config = bigquery.LoadJobConfig(
        schema=[
            bigquery.SchemaField("timestamp", "TIMESTAMP"),
            bigquery.SchemaField("series_id", "STRING"),
            bigquery.SchemaField("series_name", "STRING"),
            bigquery.SchemaField("value", "FLOAT64"),
        ],
        write_disposition="WRITE_TRUNCATE", # Overwrite table with fresh data each time
        time_partitioning=bigquery.TimePartitioning(field="timestamp"), # Partition by day
    )

    load_job = bq_client.load_table_from_dataframe(df, table_ref_str, job_config=job_config)
    load_job.result() 
    print(f"Successfully loaded {len(df)} rows into {table_ref_str}")
    return len(df)

@functions_framework.http
def fred_fetcher_http(request):
    """HTTP-triggered function to fetch key FRED data and store it in BigQuery."""
    print("Orion FRED Fetcher activated...")
    api_key = get_fred_api_key()
    if not api_key:
        return "FRED_API_KEY secret not found or accessible.", 500

    # Expanded list of key macroeconomic indicators
    fred_series_to_fetch = {
        "M2SL": "M2 Money Supply",
        "DFF": "Federal Funds Effective Rate",
        "DGS10": "10-Year Treasury Constant Maturity Rate",
        "T10Y2Y": "10-Year Treasury Constant Maturity Minus 2-Year",
        "VIXCLS": "CBOE Volatility Index (VIX)",
        "CPIAUCSL": "Consumer Price Index for All Urban Consumers",
        "PPIACO": "Producer Price Index for All Commodities",
        "UNRATE": "Civilian Unemployment Rate",
        "WTISPLC": "WTI Spot Price Crude Oil"
    }

    try:
        rows_loaded = fetch_and_store_fred_series(fred_series_to_fetch, api_key)
        return f"FRED Fetcher finished successfully. Loaded {rows_loaded} new data points.", 200
    except Exception as e:
        print(f"ERROR: An unexpected error occurred in FRED Fetcher: {e}")
        return "Internal Server Error", 500
