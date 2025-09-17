import os
import pandas as pd
import numpy as np
from flask import Flask, jsonify, request
from google.cloud import firestore
from datetime import datetime, timedelta, timezone
import vertexai
from vertexai.generative_models import GenerativeModel
import requests
import json

# --- Initialization ---
app = Flask(__name__)

# --- Configuration ---
PROJECT_ID = os.environ.get("GCP_PROJECT", "project-orion-admins")
LOCATION = "asia-northeast1"
REPORTS_COLLECTION = "orion-analysis-reports"
PERFORMANCE_COLLECTION = "orion-daily-performance"
CONFIG_COLLECTION = "orion_system_config"
CORE_THESIS_DOC_ID = "dynamic_core_thesis"
REPORTING_AGENT_URL = os.environ.get("REPORTING_AGENT_URL")

# --- Clients ---
vertexai.init(project=PROJECT_ID, location=LOCATION)
db = firestore.Client(project=PROJECT_ID)
model = GenerativeModel("gemini-1.5-pro-001")

# --- Data Fetching ---
def fetch_weekly_data():
    print("Fetching all data for the last 7 days...")
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=7)

    analysis_docs = db.collection(REPORTS_COLLECTION).where("created_at", ">=", start_date).stream()
    analyses = [doc.to_dict() for doc in analysis_docs]
    
    perf_docs = db.collection(PERFORMANCE_COLLECTION).where("report_date", ">=", start_date.strftime('%Y-%m-%d')).order_by("report_date").stream()
    performances = [doc.to_dict() for doc in perf_docs]

    core_thesis_doc = db.collection(CONFIG_COLLECTION).document(CORE_THESIS_DOC_ID).get()
    core_thesis = core_thesis_doc.to_dict().get('thesis_text', 'N/A') if core_thesis_doc.exists else 'N/A'

    print(f"Found {len(analyses)} analysis reports and {len(performances)} performance reports.")
    return analyses, performances, core_thesis

# --- Analysis & Synthesis ---
def synthesize_weekly_review(analyses, performances, core_thesis):
    print("Synthesizing Weekly Strategic Review...")
    
    macro_reports = [r['analysis_summary'] for r in analyses if r.get('type', '').startswith('macro_analysis')]
    macro_summary = "\n".join(macro_reports) if macro_reports else "今週のマクロ経済分析レポートはありませんでした。"

    # --- Accurate Weekly Performance Calculation ---
    weekly_return_str = "N/A"
    if performances:
        # Ensure reports are sorted by date
        sorted_perf = sorted(performances, key=lambda x: x['report_date'])
        start_value = sorted_perf[0].get('portfolio_summary', {}).get('current_value', 0)
        end_value = sorted_perf[-1].get('portfolio_summary', {}).get('current_value', 0)
        if start_value > 0:
            weekly_return = (end_value - start_value) / start_value
            weekly_return_str = f"{weekly_return:.2%}"

    prompt = f"""... (prompt now includes weekly_return_str and core_thesis) ..."""

    print("Generating final strategic review with Gemini Pro...")
    response = model.generate_content(prompt)
    return response.text

# --- Reporting ---
def send_report(report_text):
    # This function remains the same
    pass

# --- Flask Web Server ---
@app.route("/", methods=["POST"])
def handle_request():
    print("Received request to generate Weekly Strategic Review.")
    try:
        analyses, performances, core_thesis = fetch_weekly_data()
        if not analyses and not performances:
            return jsonify({"status": "success", "message": "No data available for weekly review."} ), 200

        review_text = synthesize_weekly_review(analyses, performances, core_thesis)
        send_report(review_text)
        
        return jsonify({"status": "success"}), 200
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({"error": "An internal server error occurred.", "details": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))