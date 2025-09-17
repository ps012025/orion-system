import os
import requests
import pandas as pd
import finnhub
from io import StringIO
from datetime import datetime
from flask import Flask, jsonify
from google.cloud import firestore
import vertexai
from vertexai.generative_models import GenerativeModel

# --- Initialization ---
app = Flask(__name__)

# --- Configuration ---
PROJECT_ID = os.environ.get("GCP_PROJECT", "project-orion-admins")
LOCATION = "asia-northeast1"
REPORTS_COLLECTION = "orion-analysis-reports"
PORTFOLIO_COLLECTION = "orion-portfolio-positions"
CBOE_PC_RATIO_URL = 'https://cdn.cboe.com/api/global/us_indices/daily_market_statistics/P-C_Ratio_SPX_30_Day_Moving_Average.csv'
MARKET_DATA_API_KEY = os.environ.get("MARKET_DATA_API_KEY")

# --- Clients ---
vertexai.init(project=PROJECT_ID, location=LOCATION)
db = firestore.Client(project=PROJECT_ID)
model = GenerativeModel("gemini-1.5-flash-001")
finnhub_client = finnhub.Client(api_key=MARKET_DATA_API_KEY) if MARKET_DATA_API_KEY else None

# --- Data Fetching ---
def get_cboe_pc_ratio():
    print("Fetching CBOE Total Put/Call Ratio...")
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(CBOE_PC_RATIO_URL, headers=headers)
    response.raise_for_status()
    lines = response.text.splitlines()
    csv_start_line = 0
    for i, line in enumerate(lines):
        if line.startswith('Date,P-C Ratio'):
            csv_start_line = i
            break
    csv_data = "\n".join(lines[csv_start_start_line:])
    df = pd.read_csv(StringIO(csv_data))
    latest_ratio = df.iloc[-1]
    print(f"Latest CBOE P/C Ratio from {latest_ratio['Date']}: {latest_ratio['P-C Ratio']}")
    return latest_ratio.to_dict()

def get_portfolio_news_sentiments():
    """Fetches news sentiment for portfolio tickers from Finnhub."""
    print("Fetching portfolio holdings...")
    docs = db.collection(PORTFOLIO_COLLECTION).stream()
    symbols = [doc.to_dict().get('symbol') for doc in docs if doc.to_dict().get('symbol')]
    if not symbols:
        return {}
    
    print(f"Fetching News Sentiment for symbols: {symbols} from Finnhub...")
    sentiments = {}
    for symbol in symbols:
        try:
            sentiment_data = finnhub_client.news_sentiment(symbol)
            score = sentiment_data['companyNewsScore']
            sentiments[symbol] = score
            print(f"  - {symbol} News Sentiment Score: {score:.4f}")
        except Exception as e:
            print(f"  - Could not fetch news sentiment for {symbol}: {e}")
            continue
    return sentiments

# --- Main Logic ---
@app.route("/", methods=["POST"])
def analyze_sentiment():
    if not finnhub_client:
        return jsonify({"error": "MARKET_DATA_API_KEY is not configured.")}), 500

    try:
        print("Sentiment analyzer v2 (Finnhub) activated...")
        cboe_data = get_cboe_pc_ratio()
        portfolio_sentiments = get_portfolio_news_sentiments()

        prompt = f"""..."""

        print("Generating AI analysis of market sentiment...")
        analysis_response = model.generate_content(prompt)
        print("AI analysis generated.")

        report_data = {
            "type": "market_sentiment_analysis",
            "created_at": firestore.SERVER_TIMESTAMP,
            "cboe_pc_ratio": cboe_data,
            "portfolio_news_sentiment": portfolio_sentiments,
            "analysis_summary": analysis_response.text
        }
        db.collection(REPORTS_COLLECTION).add(report_data)
        
        print("Successfully stored market sentiment analysis report in Firestore.")
        return jsonify({"status": "success"}), 200

    except Exception as e:
        print(f"An error occurred in sentiment analyzer: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
