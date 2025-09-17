import databento as db

# APIキーを設定
API_KEY = "db-vpbCKYQfM3Kj9xwMdUgkMDBcCgpnU"
client = db.Historical(API_KEY)

# 見積もりパラメータを定義
SYMBOLS = [
    'ADBE','AMD','ABNB','GOOGL','GOOG','AMZN','AEP','AMGN','ADI','AAPL','AMAT','APP','ARM','ASML','AZN','TEAM','ADSK','ADP','AXON','BKR','BIIB','BKNG','AVGO','CDNS','CDW','CHTR','CTAS','CSCO','CCEP','CTSH','CMCSA','CEG','CPRT','CSGP','COST','CRWD','CSX','DDOG','DXCM','FANG','DASH','EA','EXC','FAST','FTNT','GEHC','GILD','GFS','HON','IDXX','INTC','INTU','ISRG','KDP','KLAC','KHC','LRCX','LIN','LULU','MAR','MRVL','MELI','META','MCHP','MU','MSFT','MSTR','MDLZ','MNST','NFLX','NVDA','NXPI','ORLY','ODFL','ON','PCAR','PLTR','PANW','PAYX','PYPL','PDD','PEP','QCOM','REGN','ROP','ROST','SHOP','SBUX','SNPS','TMUS','TTWO','TSLA','TXN','TRI','TTD','VRSK','VRTX','WBD','WDAY','XEL','ZS'
]
SCHEMA = 'ohlcv-1m'
DATASET = 'XNAS.ITCH'
START_DATE = '2024-01-01'
END_DATE = '2024-12-31'

print("2024年のデータコストを見積もります...")

try:
    cost = client.metadata.get_cost(
        dataset=DATASET,
        symbols=SYMBOLS,
        schema=SCHEMA,
        start=START_DATE,
        end=END_DATE
    )
    print(f"\n--- 2024年 見積もり結果 ---")
    print(f"推定データコスト: ${cost:.2f} USD")

except Exception as e:
    print(f"コストの見積もり中にエラーが発生しました: {e}")
