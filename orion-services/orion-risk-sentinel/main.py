import os
import functions_framework
import finnhub
import pandas as pd
from datetime import datetime, timedelta, timezone
from google.cloud import firestore, bigquery

# --- グローバル設定 ---
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
BQ_DATASET_ID = os.environ.get("BQ_DATASET_ID", "orion_datalake")
BQ_TABLE_ID = os.environ.get("BQ_TABLE_ID", "market_data_history")
MARKET_DATA_API_KEY = os.environ.get("MARKET_DATA_API_KEY")

# --- クライアントの初期化 ---
db = firestore.Client()
bq_client = bigquery.Client()
finnhub_client = finnhub.Client(api_key=MARKET_DATA_API_KEY) if MARKET_DATA_API_KEY else None

@functions_framework.http
def calculate_performance_v3(request):
    print("Risk Sentinel v3 (Accurate Portfolio Calculation) activated...")
    if not finnhub_client:
        error_message = "MARKET_DATA_API_KEY environment variable is not set."
        save_report_to_firestore({"status": "ERROR", "message": error_message})
        return (error_message, 500)
    try:
        positions = fetch_portfolio_positions()
        if not positions:
            raise ValueError("Portfolio is empty. No positions to process.")
        
        tickers = [pos['symbol'] for pos in positions]
        update_market_data_from_api(tickers)
        
        # --- Accurate Performance Calculation ---
        performance_report = calculate_accurate_performance(positions)
        
        print(f"Performance calculation successful.")

    except Exception as e:
        error_message = f"An error occurred during performance calculation: {e}"
        print(f"ERROR: {error_message}")
        performance_report = {"status": "ERROR", "message": error_message}
    
    save_report_to_firestore(performance_report)
    return ("OK", 200)

def calculate_accurate_performance(positions: list) -> dict:
    """Calculates weighted performance for the entire portfolio."""
    print("Calculating accurate portfolio performance...")
    tickers = [p['symbol'] for p in positions]
    hist_prices_df = get_portfolio_history_from_bq(tickers, days=2)

    report_details = []
    portfolio_total = {
        'current_value': 0, 'previous_value': 0, 'cost_basis': 0, 'unrealized_pl': 0
    }

    for pos in positions:
        symbol = pos['symbol']
        quantity = pos.get('quantity', 0)
        avg_cost = pos.get('average_cost_price', 0)

        # Get last two trading days for the symbol
        symbol_prices = hist_prices_df[hist_prices_df['symbol'] == symbol].sort_values('timestamp', ascending=False)
        if len(symbol_prices) < 2:
            print(f"Warning: Not enough historical data for {symbol}. Skipping.")
            continue
        
        current_price = symbol_prices.iloc[0]['close']
        prev_close = symbol_prices.iloc[1]['close']

        current_value = quantity * current_price
        cost_basis = quantity * avg_cost
        unrealized_pl = current_value - cost_basis
        daily_pl = quantity * (current_price - prev_close)

        report_details.append({
            'symbol': symbol, 'quantity': quantity, 'average_cost_price': avg_cost,
            'current_price': current_price, 'previous_close': prev_close, 
            'current_value': current_value, 'cost_basis': cost_basis,
            'unrealized_pl': unrealized_pl,
            'unrealized_pl_percent': (unrealized_pl / cost_basis) if cost_basis else 0,
            'daily_pl': daily_pl,
            'daily_pl_percent': (daily_pl / (quantity * prev_close)) if quantity and prev_close else 0
        })
        
        portfolio_total['current_value'] += current_value
        portfolio_total['previous_value'] += quantity * prev_close
        portfolio_total['cost_basis'] += cost_basis
        portfolio_total['unrealized_pl'] += unrealized_pl

    # Calculate total portfolio metrics
    total_daily_pl = portfolio_total['current_value'] - portfolio_total['previous_value']
    portfolio_total['daily_pl'] = total_daily_pl
    portfolio_total['daily_pl_percent'] = (total_daily_pl / portfolio_total['previous_value']) if portfolio_total['previous_value'] else 0
    portfolio_total['unrealized_pl_percent'] = (portfolio_total['unrealized_pl'] / portfolio_total['cost_basis']) if portfolio_total['cost_basis'] else 0

    return {"status": "SUCCESS", "positions": report_details, "portfolio_summary": portfolio_total}


def fetch_portfolio_positions() -> list:
    """Firestoreから現在保有するポジションのリストを取得する"""
    print("Fetching portfolio positions from Firestore...")
    positions = list(db.collection("orion-portfolio-positions").stream())
    print(f"Found {len(positions)} positions.")
    return [pos.to_dict() for pos in positions]

def update_market_data_from_api(tickers: list):
    # This function remains the same as before
    pass

def get_portfolio_history_from_bq(tickers: list, days: int) -> pd.DataFrame:
    """BigQueryデータレイクから指定日数の価格履歴を取得する"""
    print(f"Fetching last {days} days of price history for {len(tickers)} tickers...")
    table_ref_str = f"{PROJECT_ID}.{BQ_DATASET_ID}.{BQ_TABLE_ID}"
    start_date = (datetime.now(timezone.utc) - timedelta(days=days*2)).strftime('%Y-%m-%d') # Fetch more to ensure we get enough trading days
    ticker_list_str = ", ".join([f"'{t}'" for t in tickers])
    query = f"SELECT timestamp, symbol, close FROM `{table_ref_str}` WHERE symbol IN ({ticker_list_str}) AND DATE(timestamp) >= '{start_date}' ORDER BY timestamp DESC"
    df = bq_client.query(query).to_dataframe()
    if df.empty:
        raise ValueError("Could not retrieve any price history from BigQuery.")
    print(f"Retrieved {len(df)} total rows of historical data.")
    return df

def save_report_to_firestore(data):
    today_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    doc_ref = db.collection("orion-daily-performance").document(today_str)
    data["last_updated"] = firestore.SERVER_TIMESTAMP
    doc_ref.set(data)
    print(f"Report saved to Firestore for date: {today_str} with status: {data.get('status')}")