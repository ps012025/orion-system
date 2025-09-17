import yfinance as yf
from flask import Flask, jsonify, request
import pandas as pd
from vertexai.preview.generative_models import GenerativeModel
import requests
import os



app = Flask(__name__)

# --- エコシステムの定義 ---
ECOSYSTEM_MAP = {
    "OKLO": {"unit": "Power", "role": "Next-gen energy supply"},
    "NVDA": {"unit": "Intelligence", "role": "Core computational power"},
    "IONQ": {"unit": "Intelligence", "role": "Quantum acceleration"},
    "RXRX": {"unit": "Intelligence", "role": "AI-driven drug discovery"},
    "TWST": {"unit": "Intelligence", "role": "DNA synthesis (Information physicalization)"},
    "NTLA": {"unit": "Implementation", "role": "Implementation to life (Gene editing)"},
    "ASTS": {"unit": "Implementation", "role": "Implementation to information (Space communication)"},
    "SYM": {"unit": "Implementation", "role": "Implementation to physical world (Logistics automation)"},
    "AAPL": {"unit": "Implementation", "role": "Consumer hardware ecosystem"},
    "MSFT": {"unit": "Intelligence", "role": "Cloud and software platform"},
}

def calculate_cagr(start_value, end_value, num_years):
    if start_value is None or end_value is None or start_value <= 0 or num_years <= 0:
        return 0
    return ((end_value / start_value) ** (1 / num_years)) - 1

def get_gemini_qualitative_analysis(ticker_info):
    model = GenerativeModel("gemini-pro-flash")
    prompt = f"""
    あなたは、投資戦略OS「GEM」の一部として機能する、高度な金融アナリストです。
    以下の企業情報について、私たちの投資哲学に基づき、三つの質問に答えてください。
    # 企業情報
    - ティッカー: {ticker_info['ticker']}
    - ユニット分類: {ticker_info['unit']}
    - 役割: {ticker_info['role']}
    - 2年間の売上CAGR: {ticker_info['revenue_cagr']}
    - P/S比率: {ticker_info['ps_ratio']}
    # 質問
    1. エコシステムにおける役割: この企業が、私たちのエコシステム「原動力 → 知性 → 実装」の中で、どのような具体的な役割を担っていますか？
    2. 競争優位性: この企業が持つ、10倍以上の非連続的な成長の源泉（技術、ブランド、ネットワーク効果など）は何ですか？
    3. 市場の歪み: 市場がまだ気づいていない、この企業の長期的な価値は何だと思いますか？
    回答は簡潔に、各質問に対して2-3行でまとめてください。
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Gemini analysis failed: {e}")
        return "定性分析に失敗しました。"

@app.route('/screener', methods=['POST'])
def run_screener():
    try:
        macro_insight = request.json.get('macro_insight', {})
        candidate_tickers = list(ECOSYSTEM_MAP.keys())
        potential_targets = []
        for ticker_symbol in candidate_tickers:
            try:
                ticker = yf.Ticker(ticker_symbol)
                info = ticker.info
                financials = ticker.financials
                cash_flow = ticker.cashflow
                balance_sheet = ticker.balance_sheet

                revenue_history = financials.loc['Total Revenue']
                fcf_history = cash_flow.loc['Free Cash Flow']
                ps_ratio = info.get('priceToSalesTrailing12Months')
                
                if len(revenue_history) < 3: continue
                
                unit = ECOSYSTEM_MAP[ticker_symbol]["unit"]
                passes_screener = False
                revenue_cagr = calculate_cagr(revenue_history.iloc[-1], revenue_history.iloc[0], 2)

                if unit == "Power" or unit == "Intelligence":
                    if revenue_cagr > 0.25: passes_screener = True
                elif unit == "Implementation":
                    if revenue_cagr > 0.15 and fcf_history.iloc[0] > 0: passes_screener = True

                if passes_screener:
                    if ps_ratio and ps_ratio > 30: continue
                    if macro_insight.get("sentiment_score", 0) > 5:
                        total_debt = balance_sheet.loc['Total Debt'].iloc[0]
                        total_equity = balance_sheet.loc['Total Equity Gross Minority Interest'].iloc[0]
                        debt_to_equity = total_debt / total_equity if total_equity != 0 else float('inf')
                        if debt_to_equity > 1.5: continue
                    
                    quantitative_data = {
                        "ticker": ticker_symbol,
                        "unit": unit,
                        "role": ECOSYSTEM_MAP[ticker_symbol]["role"],
                        "revenue_cagr": f"{revenue_cagr:.2%}",
                        "ps_ratio": f"{ps_ratio:.2f}"
                    }
                    
                    qualitative_analysis = get_gemini_qualitative_analysis(quantitative_data)
                    
                    quantitative_data["qualitative_analysis"] = qualitative_analysis
                    potential_targets.append(quantitative_data)

            except Exception as e:
                print(f"Error processing {ticker_symbol}: {e}")
                continue

        return jsonify({"potential_targets": potential_targets})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)