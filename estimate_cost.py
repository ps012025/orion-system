import databento as db

# --- 1. 初期設定 ---
API_KEY = "db-vpbCKYQfM3Kj9xwMdUgkMDBcCgpnU"
client = db.Historical(API_KEY)

# --- 2. データ取得パラメータの定義 ---
# Full Nasdaq-100 list scraped from Wikipedia
SYMBOLS = [
    'ADBE','AMD','ABNB','GOOGL','GOOG','AMZN','AEP','AMGN','ADI','AAPL','AMAT','APP','ARM','ASML','AZN','TEAM','ADSK','ADP','AXON','BKR','BIIB','BKNG','AVGO','CDNS','CDW','CHTR','CTAS','CSCO','CCEP','CTSH','CMCSA','CEG','CPRT','CSGP','COST','CRWD','CSX','DDOG','DXCM','FANG','DASH','EA','EXC','FAST','FTNT','GEHC','GILD','GFS','HON','IDXX','INTC','INTU','ISRG','KDP','KLAC','KHC','LRCX','LIN','LULU','MAR','MRVL','MELI','META','MCHP','MU','MSFT','MSTR','MDLZ','MNST','NFLX','NVDA','NXPI','ORLY','ODFL','ON','PCAR','PLTR','PANW','PAYX','PYPL','PDD','PEP','QCOM','REGN','ROP','ROST','SHOP','SBUX','SNPS','TMUS','TTWO','TSLA','TXN','TRI','TTD','VRSK','VRTX','WBD','WDAY','XEL','ZS'
]
SCHEMA = 'ohlcv-1m'
DATASET = 'XNAS.ITCH'
PERIODS = {
    "long_term_test_2018_onward": ('2018-05-01', '2023-12-31')
}

# --- 3. コスト見積もりの実行 ---
print("Nasdaq 100 (101銘柄)でのデータコストの見積もりを開始します...")
total_cost = 0
for period_name, (start_date, end_date) in PERIODS.items():
    cost = client.metadata.get_cost(
        dataset=DATASET,
        symbols=SYMBOLS,
        schema=SCHEMA,
        start=start_date,
        end=end_date
    )
    print(f"期間 '{period_name}' の推定データコスト: ${cost:.2f}")
    total_cost += cost

print(f"\nNasdaq 100での推定合計データコスト: ${total_cost:.2f}")