import databento as db
import pandas as pd
from google.cloud import storage
import io

# --- 設定 ---
# !!! 重要 !!!: 以下のAPIキーを、あなたの実際のDatabento APIキーに置き換えてください。
API_KEY = "db-vpbCKYQfM3Kj9xwMdUgkMDBcCgpnU"

PROJECT_ID = "thinking-orb-438805-q7"
DATA_LAKE_BUCKET = "orion-market-data-lake"
SYMBOLS = [
    'ADBE','AMD','ABNB','GOOGL','GOOG','AMZN','AEP','AMGN','ADI','AAPL','AMAT','APP','ARM','ASML','AZN','TEAM','ADSK','ADP','AXON','BKR','BIIB','BKNG','AVGO','CDNS','CDW','CHTR','CTAS','CSCO','CEG','CTSH','CMCSA','CEG','CPRT','CSGP','COST','CRWD','CSX','DDOG','DXCM','FANG','DASH','EA','EXC','FAST','FTNT','GEHC','GILD','GFS','HON','IDXX','INTC','INTU','ISRG','KDP','KLAC','KHC','LRCX','LIN','LULU','MAR','MRVL','MELI','META','MCHP','MU','MSFT','MSTR','MDLZ','MNST','NFLX','NVDA','NXPI','ORLY','ODFL','ON','PCAR','PLTR','PANW','PAYX','PYPL','PDD','PEP','QCOM','REGN','ROP','ROST','SHOP','SBUX','SNPS','TMUS','TTWO','TSLA','TXN','TRI','TTD','VRSK','VRTX','WBD','WDAY','XEL','ZS'
]
SCHEMA = 'ohlcv-1m'
DATASET = 'XNAS.ITCH'
YEAR_TO_DOWNLOAD = 2018
MONTH_TO_DOWNLOAD = 5

def download_single_month():
    """指定された一ヶ月分のデータをDatabentoから取得し、Cloud Storageにアップロードする。"""
    if API_KEY == "YOUR_DATABENTO_API_KEY":
        print("FATAL: Please replace 'YOUR_DATABENTO_API_KEY' in the script with your actual Databento API key.")
        return

    db_client = db.Historical(API_KEY)
    storage_client = storage.Client(project=PROJECT_ID)
    bucket = storage_client.bucket(DATA_LAKE_BUCKET)

    try:
        start_date = f"{YEAR_TO_DOWNLOAD}-{MONTH_TO_DOWNLOAD:02d}-01"
        # Calculate the end date for the month
        import calendar
        _, num_days = calendar.monthrange(YEAR_TO_DOWNLOAD, MONTH_TO_DOWNLOAD)
        end_date = f"{YEAR_TO_DOWNLOAD}-{MONTH_TO_DOWNLOAD:02d}-{num_days:02d}"

        print(f"\nFetching data for period: {start_date} to {end_date}...")
        
        data = db_client.timeseries.get_range(
            dataset=DATASET,
            symbols=SYMBOLS,
            schema=SCHEMA,
            start=start_date,
            end=end_date
        )
        
        df = data.to_df()
        
        if df.empty:
            print(f"No data returned for the period. Skipping.")
            return

        output_filename = f"nasdaq100_ohlcv_1m_{YEAR_TO_DOWNLOAD}_{MONTH_TO_DOWNLOAD:02d}.csv"
        
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        
        blob = bucket.blob(output_filename)
        blob.upload_from_string(csv_buffer.getvalue(), 'text/csv')
        
        print(f"Successfully uploaded '{output_filename}' to gs://{DATA_LAKE_BUCKET}")

    except Exception as e:
        print(f"An error occurred while processing: {e}")

if __name__ == "__main__":
    print("--- Starting Single Month Data Download Process ---")
    download_single_month()
    print("\n--- Single Month Data Download Process Finished ---")
