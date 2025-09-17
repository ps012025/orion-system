import os
import yaml
import json
import uuid
import time
import yfinance as yf
import pandas as pd
from datetime import datetime, timezone
from google.cloud import firestore

# --- Initialization ---
db = firestore.Client(project="thinking-orb-438805-q7")
TARGET_DATE_STR = "2025-09-12"

# --- Data Fetching ---
def fetch_portfolio_positions() -> list:
    positions = []
    docs = db.collection("orion-portfolio-positions").stream()
    for doc in docs:
        positions.append(doc.to_dict())
    print(f"Found {len(positions)} positions in portfolio.")
    return positions

def download_market_data_for_date(tickers: list, target_date_str: str, retries=3, delay=5) -> pd.DataFrame:
    target_date = datetime.strptime(target_date_str, '%Y-%m-%d')
    start_date = (target_date - pd.Timedelta(days=4)).strftime('%Y-%m-%d') # 4 days to find 2 valid trading days
    end_date = (target_date + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
    
    print(f"Attempting to download market data for {tickers} from {start_date} to {end_date}")
    for i in range(retries):
        try:
            data = yf.download(tickers, start=start_date, end=end_date, progress=False)
            if not data.empty and 'Close' in data:
                # Ensure we have data for the target day and the day before
                if target_date_str in data.index.strftime('%Y-%m-%d').tolist():
                    print("Download successful.")
                    return data
        except Exception as e:
            print(f"Warning (Attempt {i+1}/{retries}): yfinance download error: {e}")
        if i < retries - 1:
            print(f"Retrying in {delay} seconds...")
            time.sleep(delay)
            
    print("Fatal: Could not download valid market data after multiple retries.")
    return pd.DataFrame()

# --- Core Calculation Logic ---
def calculate_performance_for_date(target_date_str: str):
    positions = fetch_portfolio_positions()
    if not positions:
        raise ValueError("No positions found in portfolio.")
        
    tickers = [pos['symbol'] for pos in positions]
    data = download_market_data_for_date(tickers, target_date_str)
    if data.empty:
        raise ValueError(f"Could not download market data for tickers: {tickers}")

    target_date = pd.to_datetime(target_date_str)
    # Get the actual trading day for the target date, and the one before it
    valid_days = data.loc[data.index <= target_date].index.sort_values(ascending=False)
    if len(valid_days) < 2:
        raise ValueError(f"Not enough historical data to calculate performance for {target_date_str}. Need at least 2 trading days.")
    
    current_day_index = valid_days[0]
    prev_day_index = valid_days[1]
    
    print(f"Calculating performance. Current Day: {current_day_index.date()}, Previous Day: {prev_day_index.date()}")

    report_details = []
    portfolio_total = {'current_value': 0, 'cost_basis': 0, 'daily_pl': 0}

    for pos in positions:
        symbol = pos['symbol']
        quantity = pos['quantity']
        avg_cost = pos['average_cost_price']
        
        try:
            prev_close = data.loc[prev_day_index, ('Close', symbol)]
            current_price = data.loc[current_day_index, ('Close', symbol)]
            if pd.isna(prev_close) or pd.isna(current_price):
                print(f"Skipping {symbol} due to missing price data on required dates.")
                continue
        except KeyError:
            print(f"Skipping {symbol} as it has no data for the required dates.")
            continue

        current_value = quantity * current_price
        cost_basis = quantity * avg_cost
        unrealized_pl = current_value - cost_basis
        daily_pl = quantity * (current_price - prev_close)
        
        report_details.append({
            'symbol': symbol, 'quantity': quantity, 'average_cost_price': avg_cost,
            'current_price': current_price, 'previous_close': prev_close, 'current_value': current_value,
            'cost_basis': cost_basis, 'unrealized_pl': unrealized_pl,
            'unrealized_pl_percent': (unrealized_pl / cost_basis) if cost_basis != 0 else 0,
            'daily_pl': daily_pl,
            'daily_pl_percent': (daily_pl / (quantity * prev_close)) if (quantity * prev_close) != 0 else 0
        })
        portfolio_total['current_value'] += current_value
        portfolio_total['cost_basis'] += cost_basis
        portfolio_total['daily_pl'] += daily_pl

    total_cost_basis = portfolio_total['cost_basis']
    if total_cost_basis != 0:
        portfolio_total['unrealized_pl'] = portfolio_total['current_value'] - total_cost_basis
        portfolio_total['unrealized_pl_percent'] = portfolio_total['unrealized_pl'] / total_cost_basis
    else:
        portfolio_total['unrealized_pl'] = 0
        portfolio_total['unrealized_pl_percent'] = 0
        
    prev_day_value = portfolio_total['current_value'] - portfolio_total['daily_pl']
    if prev_day_value != 0:
        portfolio_total['daily_pl_percent'] = portfolio_total['daily_pl'] / prev_day_value
    else:
        portfolio_total['daily_pl_percent'] = 0

    return {"positions": report_details, "portfolio_summary": portfolio_total}

def save_performance_report(report: dict, report_date_str: str):
    report['report_id'] = str(uuid.uuid4())
    report['report_date'] = report_date_str
    report['generated_by'] = 'fix_daily_report_script'
    report['generated_at'] = datetime.now(timezone.utc).isoformat()
    db.collection("orion-daily-performance").document(report_date_str).set(report)
    print(f"Successfully saved daily performance report for {report_date_str} to Firestore.")

if __name__ == "__main__":
    print(f"--- Starting Manual Performance Calculation for {TARGET_DATE_STR} ---")
    try:
        performance_report = calculate_performance_for_date(TARGET_DATE_STR)
        save_performance_report(performance_report, TARGET_DATE_STR)
        print(f"--- Successfully generated and saved report for {TARGET_DATE_STR} ---")
    except Exception as e:
        print(f"--- An error occurred during manual calculation: {e} ---")
