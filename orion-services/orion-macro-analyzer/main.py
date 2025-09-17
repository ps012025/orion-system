import os
import pandas as pd
import pandas_datareader.data as web
from datetime import datetime, timedelta
from google.cloud import firestore
import vertexai
from vertexai.generative_models import GenerativeModel
from flask import Flask, jsonify

# --- Initialization ---
app = Flask(__name__)

# --- Configuration ---
PROJECT_ID = os.environ.get("GCP_PROJECT", "thinking-orb-438805-q7")
LOCATION = "asia-northeast1"
REPORTS_COLLECTION = "orion-analysis-reports"
FRED_SERIES = {
    "M2SL": "M2 Money Supply",
    "DFF": "Federal Funds Effective Rate",
    "DGS10": "10-Year Treasury Constant Maturity Rate"
}
MARKET_SYMBOLS = {
    "GC=F": "Gold Futures",
    "^IXIC": "NASDAQ Composite"
}

# --- Clients ---
vertexai.init(project=PROJECT_ID, location=LOCATION)
db = firestore.Client(project=PROJECT_ID)
model = GenerativeModel("gemini-1.5-flash-001")

@app.route("/", methods=["POST"])
def analyze_macro_environment():
    try:
        print("Macro analyzer activated. Fetching data...")
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365 * 2)

        fred_data = web.DataReader(list(FRED_SERIES.keys()), 'fred', start_date, end_date)
        print("Successfully fetched FRED data.")

        market_data = web.DataReader(list(MARKET_SYMBOLS.keys()), 'yahoo', start_date, end_date)['Adj Close']
        market_data.rename(columns=MARKET_SYMBOLS, inplace=True)
        print("Successfully fetched market data.")

        combined_data = pd.concat([fred_data, market_data], axis=1).ffill().dropna()
        daily_returns = combined_data.pct_change().dropna()
        
        correlation_matrix = daily_returns.corr()
        print("Correlation Matrix:\n", correlation_matrix)

        prompt = f"""
        あなたはシニアマクロ経済アナリストです。以下の最新マクロ経済指標と市場データの相関行列を分析してください。
        
        データ概要:
        - M2 Money Supply (M2SL): 通貨供給量
        - Federal Funds Effective Rate (DFF): 政策金利
        - 10-Year Treasury Constant Maturity Rate (DGS10): 10年債利回り
        - Gold Futures (GC=F): ゴールド価格
        - NASDAQ Composite (^IXIC): 市場ベンチマーク

        相関行列:
        {correlation_matrix.to_string()}

        この分析に基づき、以下の項目について、プロフェッショナルな視点から簡潔なインサイトを生成してください。
        1.  **現在の市場センチメント:** 金利、通貨供給量、ゴールドの動きから、市場がリスクオンかリスクオフか。
        2.  **注目すべき相関の変化:** 過去と比較して、特筆すべき相関関係の変化や異常値はあるか。
        3.  **ポートフォリオへの戦略的示唆:** このマクロ環境が、テクノロジー株中心のポートフォリオに与える短期的な影響（追い風か、逆風か）。
        """

        analysis_response = model.generate_content(prompt)
        print("AI analysis generated.")

        report_data = {
            "type": "macro_analysis",
            "created_at": firestore.SERVER_TIMESTAMP,
            "correlation_matrix": correlation_matrix.to_json(),
            "analysis_summary": analysis_response.text
        }
        db.collection(REPORTS_COLLECTION).add(report_data)
        
        print("Successfully stored macro analysis report in Firestore.")
        return jsonify({"status": "success"}), 200

    except Exception as e:
        print(f"An error occurred in macro analyzer: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))