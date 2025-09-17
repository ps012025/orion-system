import os
import requests
import pandas as pd
import finnhub
from io import StringIO
from datetime import datetime
import functions_framework
from google.cloud import firestore
import vertexai
from vertexai.generative_models import GenerativeModel

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
    # ... (logic remains the same)
    pass

def get_portfolio_news_sentiments():
    # ... (logic remains the same)
    pass

# --- Main Logic ---
@functions_framework.http
def analyze_sentiment_http(request):
    if not finnhub_client:
        return "MARKET_DATA_API_KEY is not configured.", 500

    try:
        print("Sentiment analyzer v3 (Function) activated...")
        cboe_data = get_cboe_pc_ratio()
        portfolio_sentiments = get_portfolio_news_sentiments()

        prompt = f"""...""" # Prompt remains the same

        analysis_response = model.generate_content(prompt)

        report_data = {
            "type": "market_sentiment_analysis",
            "created_at": firestore.SERVER_TIMESTAMP,
            "cboe_pc_ratio": cboe_data,
            "portfolio_news_sentiment": portfolio_sentiments,
            "analysis_summary": analysis_response.text
        }
        db.collection(REPORTS_COLLECTION).add(report_data)
        
        return "Successfully stored market sentiment analysis report.", 200

    except Exception as e:
        print(f"An error occurred in sentiment analyzer: {e}")
        return f"An error occurred: {e}", 500