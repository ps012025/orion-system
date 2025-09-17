import datetime
from google.cloud import firestore

# --- 1. 初期設定 ---
# Firestoreクライアントを初期化
db = firestore.Client(project="thinking-orb-438805-q7")

# --- 2. 登録するポートフォリオのマスターデータ ---
# ご提示のスクリーンショット (Screenshot_2025-09-12-10-20-39-044) に基づくデータ
portfolio_data = [
    {"symbol": "GLDM", "quantity": 160, "average_cost_price": 56.33},
    {"symbol": "IONQ", "quantity": 2, "average_cost_price": 42.62},
    {"symbol": "NTLA", "quantity": 22, "average_cost_price": 10.95},
    {"symbol": "NVDA", "quantity": 40, "average_cost_price": 102.16},
    {"symbol": "OKLO", "quantity": 5, "average_cost_price": 68.46},
    {"symbol": "RXRX", "quantity": 12, "average_cost_price": 5.07},
    {"symbol": "TWST", "quantity": 1, "average_cost_price": 24.98},
    {"symbol": "XLU", "quantity": 15, "average_cost_price": 72.25},
]

# --- 3. Firestoreへのデータ書き込み実行 ---
def register_positions(positions):
    """
    指定されたポートフォリオデータを、Firestoreの
    orion-portfolio-positions コレクションに書き込む。
    ドキュメントIDにはティッカーシンボルを使用し、重複登録を防ぐ。
    """
    collection_ref = db.collection('orion-portfolio-positions')
    print("--- Starting Portfolio Registration ---")
    for position in positions:
        symbol = position.get("symbol")
        if not symbol:
            print(f"Skipping record with no symbol: {position}")
            continue
        
        doc_ref = collection_ref.document(symbol)
        
        # 登録日時のタイムスタンプを追加
        position['last_updated_utc'] = datetime.datetime.utcnow()
        
        doc_ref.set(position)
        print(f"SUCCESS: Registered/Updated position for {symbol}")
    print("--- Portfolio Registration Complete ---")

if __name__ == "__main__":
    register_positions(portfolio_data)
