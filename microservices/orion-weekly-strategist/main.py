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
import yaml

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

# --- Configuration Loading ---
def load_config():
    config_path = os.path.join(os.path.dirname(__file__), 'orion-config-final.yaml')
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

# --- Data Fetching ---
def fetch_weekly_data():
    print("Fetching all data for the last 7 days...")
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=7)

    analysis_docs = db.collection(REPORTS_COLLECTION).where("created_at", ">=", start_date).stream()
    analyses = [doc.to_dict() for doc in analysis_docs]
    
    # Compare datetime objects directly
    perf_docs = db.collection(PERFORMANCE_COLLECTION).where("last_updated", ">=", start_date).order_by("last_updated").stream()
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

    weekly_return_str = "N/A"
    if performances:
        sorted_perf = sorted(performances, key=lambda x: x.get('last_updated', datetime.min.replace(tzinfo=timezone.utc))) # Sort by actual timestamp
        start_value = sorted_perf[0].get('portfolio_summary', {}).get('current_value', 0)
        end_value = sorted_perf[-1].get('portfolio_summary', {}).get('current_value', 0)
        if start_value > 0:
            weekly_return = (end_value - start_value) / start_value
            weekly_return_str = f"{weekly_return:.2%}"

    config = load_config()
    prompt_template = config.get('weekly_strategist_config', {}).get('ai_prompt', "")
    if not prompt_template:
        raise ValueError("AI prompt template not found in config.")

    prompt = prompt_template.format(
        weekly_return_str=weekly_return_str,
        macro_summary=macro_summary,
        core_thesis=core_thesis
    )

    print("Generating final strategic review with Gemini Pro...")
    response = model.generate_content(prompt)
    return response.text

# --- Reporting ---
def send_report(report_text):
    print("Sending Weekly Strategic Review to Email and Slack...")
    if not REPORTING_AGENT_URL:
        raise ValueError("REPORTING_AGENT_URL is not set.")
    try:
        audience = REPORTING_AGENT_URL
        metadata_server_url = f'http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/identity?audience={audience}'
        token_response = requests.get(metadata_server_url, headers={'Metadata-Flavor': 'Google'})
        token = token_response.text
        
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
        subject = f"【ORION WEEKLY STRATEGIC REVIEW】{datetime.now(timezone.utc).strftime('%Y-%m-%d')}週次戦略報告"
        
        payload = {"alert_subject": subject, "alert_body": f"<pre>{report_text}</pre>"}
        
        response = requests.post(REPORTING_AGENT_URL, json=payload, headers=headers, timeout=60)
        response.raise_for_status()
        print("Successfully requested sending of weekly report.")
    except Exception as e:
        print(f"Failed to send weekly report: {e}")

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
