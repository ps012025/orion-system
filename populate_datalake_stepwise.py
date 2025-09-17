import databento as db
import pandas as pd
import traceback
import os

# --- 1. 初期設定 ---
API_KEY = "db-vpbCKYQfM3Kj9xwMdUgkMDBcCgpnU"
client = db.Historical(API_KEY)
BUCKET_NAME = "orion-market-data-lake"

# --- 2. データ取得パラメータの定義 ---
SYMBOLS = [
    'ADBE','AMD','ABNB','GOOGL','GOOG','AMZN','AEP','AMGN','ADI','AAPL','AMAT','APP','ARM','ASML','AZN','TEAM','ADSK','ADP','AXON','BKR','BIIB','BKNG','AVGO','CDNS','CDW','CHTR','CTAS','CSCO','CEG','CTSH','CMCSA','CEG','CPRT','CSGP','COST','CRWD','CSX','DDOG','DXCM','FANG','DASH','EA','EXC','FAST','FTNT','GEHC','GILD','GFS','HON','IDXX','INTC','INTU','ISRG','KDP','KLAC','KHC','LRCX','LIN','LULU','MAR','MRVL','MELI','META','MCHP','MU','MSFT','MSTR','MDLZ','MNST','NFLX','NVDA','NXPI','ORLY','ODFL','ON','PCAR','PLTR','PANW','PAYX','PYPL','PDD','PEP','QCOM','REGN','ROP','ROST','SHOP','SBUX','SNPS','TMUS','TTWO','TSLA','TXN','TRI','TTD','VRSK','VRTX','WBD','WDAY','XEL','ZS'
]
SCHEMA = 'ohlcv-1m'
DATASET = 'XNAS.ITCH'
YEARS = range(2018, 2025) # 2018 through 2024

# --- 3. データ取得、GCSへのアップロード、ローカルファイル削除のステップワイズ実行 ---
print("データレイクの段階的な構築を開始します...")

for year in YEARS:
    if year == 2018:
        start_date = "2018-05-01"
    else:
        start_date = f"{year}-01-01"
    
    end_date = f"{year}-12-31"
    local_path = f"nasdaq100_ohlcv_1m_{year}.csv"
    gcs_path = f"gs://{BUCKET_NAME}/{local_path}"
    
    print(f"\n--- 年: {year} の処理を開始 ---")
    
    try:
        # 1. データ取得
        print(f"期間: {start_date} to {end_date} のデータを取得中...")
        data = client.timeseries.get_range(
            dataset=DATASET,
            symbols=SYMBOLS,
            schema=SCHEMA,
            start=start_date,
            end=end_date
        )
        df = data.to_df()
        
        # 2. ローカルに保存
        print(f"データをローカルファイル: {local_path} に保存中...")
        df.to_csv(local_path, index=False)
        
        # 3. GCSにアップロード
        print(f"GCSパス: {gcs_path} にアップロード中...")
        os.system(f"gsutil cp {local_path} {gcs_path}")
        
        # 4. ローカルファイルを削除
        print(f"ローカルファイル: {local_path} を削除します。\n")
        os.remove(local_path)
        
        print(f"--- 年: {year} の処理が正常に完了しました ---")
        
    except Exception as e:
        print(f"期間 '{year}' の処理中にエラーが発生しました:")
        traceback.print_exc()
        # エラーが発生した場合でも、次の年の処理に進む
        continue

print("\n全てのデータ処理が完了し、データレイクが構築されました。")
