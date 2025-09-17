import databento as db
from datetime import datetime, timedelta, timezone

# --- 1. 初期設定 ---
API_KEY = "db-vpbCKYQfM3Kj9xwMdUgkMDBcCgpnU"
client = db.Historical(API_KEY)

# --- 2. データ取得パラメータの定義 ---
SYMBOLS = ['ES.c.0']  # E-mini S&P 500 continuous front-month future
SCHEMA = 'mbo'          # Market-by-order (L3 tick data)
DATASET = 'GLBX.MDP3'

# Calculate the date range for the last 3 months, with a 15-minute buffer
end_date = datetime.now(timezone.utc) - timedelta(minutes=15)
start_date = end_date - timedelta(days=90)

# --- 3. コスト見積もりの実行 ---
print(f"データコストの見積もりを開始します...")
print(f"対象銘柄: {SYMBOLS}")
print(f"データタイプ: {SCHEMA}")
print(f"期間: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")

cost = client.metadata.get_cost(
    dataset=DATASET,
    symbols=SYMBOLS,
    schema=SCHEMA,
    start=start_date,
    end=end_date
)

print(f"\n推定合計データコスト: ${cost:.2f}")
