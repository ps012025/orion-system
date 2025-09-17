import databento as db
import pandas as pd
from datetime import datetime

# --- 1. 初期設定 ---
API_KEY = "db-vpbCKYQfM3Kj9xwMdUgkMDBcCgpnU"
client = db.Historical(API_KEY)

# --- 2. データ取得パラメータの定義 ---
SYMBOLS = [
    'ADBE','AMD','ABNB','GOOGL','GOOG','AMZN','AEP','AMGN','ADI','AAPL','AMAT','APP','ARM','ASML','AZN','TEAM','ADSK','ADP','AXON','BKR','BIIB','BKNG','AVGO','CDNS','CDW','CHTR','CTAS','CSCO','CCEP','CTSH','CMCSA','CEG','CPRT','CSGP','COST','CRWD','CSX','DDOG','DXCM','FANG','DASH','EA','EXC','FAST','FTNT','GEHC','GILD','GFS','HON','IDXX','INTC','INTU','ISRG','KDP','KLAC','KHC','LRCX','LIN','LULU','MAR','MRVL','MELI','META','MCHP','MU','MSFT','MSTR','MDLZ','MNST','NFLX','NVDA','NXPI','ORLY','ODFL','ON','PCAR','PLTR','PANW','PAYX','PYPL','PDD','PEP','QCOM','REGN','ROP','ROST','SHOP','SBUX','SNPS','TMUS','TTWO','TSLA','TXN','TRI','TTD','VRSK','VRTX','WBD','WDAY','XEL','ZS'
]
SCHEMA = 'ohlcv-1m'
DATASET = 'XNAS.ITCH'

# Define years to download
YEARS = range(2018, 2026) # 2018 through 2025

# --- 3. データ取得の実行 ---
print("Nasdaq 100の1分足OHLCVデータの取得を開始します...")

for year in YEARS:
    if year == 2018:
        start_date = "2018-05-01"
    else:
        start_date = f"{year}-01-01"
    
    end_date = f"{year}-12-31"
    print(f"\n期間: {start_date} to {end_date} のデータを取得中...")
    
    try:
        data = client.timeseries.get_range(
            dataset=DATASET,
            symbols=SYMBOLS,
            schema=SCHEMA,
            start=start_date,
            end=end_date
        )
        
        df = data.to_df()
        output_filename = f"nasdaq100_ohlcv_1m_{year}.csv"
        df.to_csv(output_filename)
        print(f"期間 '{year}' のデータを '{output_filename}' として保存しました。")
        
    except Exception as e:
        print(f"期間 '{year}' のデータ取得中にエラーが発生しました: {e}")

print("\n全てのデータ取得が完了しました。")