import os
import pandas as pd
import numpy as np
from flask import Flask, jsonify, request
from google.cloud import firestore
from datetime import datetime, timedelta
import vertexai
from vertexai.generative_models import GenerativeModel
import requests

# --- Initialization ---
app = Flask(__name__)

# --- Configuration ---
PROJECT_ID = os.environ.get("GCP_PROJECT", "thinking-orb-438805-q7")
LOCATION = "asia-northeast1"
REPORTS_COLLECTION = "orion-analysis-reports"
PERFORMANCE_COLLECTION = "orion-daily-performance"
PORTFOLIO_COLLECTION = "orion-portfolio-holdings"
REPORTING_AGENT_URL = "https://orion-reporting-agent-100139368807.asia-northeast1.run.app"

# --- Clients ---
vertexai.init(project=PROJECT_ID, location=LOCATION)
db = firestore.Client(project=PROJECT_ID)
model = GenerativeModel("gemini-1.5-pro-001")

# --- Data Fetching ---
def fetch_monthly_data():
    print("Fetching all data for the last month...")
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)

    # Fetch all analysis reports for the month
    analysis_docs = db.collection(REPORTS_COLLECTION).where("created_at", ">=", start_date).stream()
    analyses = [doc.to_dict() for doc in analysis_docs]
    
    # Fetch all performance reports for the month
    perf_docs = db.collection(PERFORMANCE_COLLECTION).where("generated_at", ">=", start_date.isoformat()).stream()
    performances = [doc.to_dict() for doc in perf_docs]

    return analyses, performances

# --- Analysis & Synthesis ---
def synthesize_monthly_review(analyses, performances):
    print("Synthesizing Monthly Strategic Review...")
    
    # This is a simplified synthesis logic. A real implementation would be more complex.
    # 1. Summarize Macro Environment
    macro_reports = [r['analysis_summary'] for r in analyses if r.get('type') == 'macro_analysis']
    macro_summary = "\n".join(macro_reports)

    # 2. Calculate Monthly Performance
    # This is a placeholder. A real implementation would calculate returns from the performance data.
    monthly_return_fortress = "-0.5%"
    monthly_return_recon = "-5.8%"

    # 3. Generate Final Recommendations with Gemini
    prompt = f"""
    あなたはオリオンシステムの最高戦略責任者、GEMです。
    以下の月間データを統合し、机長（CEO）に向けた「月次戦略レビュー」を生成してください。

    **1. 月間パフォーマンス:**
    - 要塞ファンド: {monthly_return_fortress}
    - 偵察衛星ファンド: {monthly_return_recon}

    **2. 月間マクロ環境分析サマリー:**
    {macro_summary}

    **3. その他、今月観測された重要インサイト:**
    (ここに、ミクロ、クオンツ、オプション分析のサマリーが入ります)

    **指示:**
    上記の全ての情報を基に、あなたが以前提示したフォーマットに従い、以下の項目を含む、完全な「月次戦略レビュー」を生成してください。
    - 総括 (Executive Summary)
    - パフォーマンス・レビュー
    - オリオンシステム分析サマリー
    - 『共進化的ロケット』個別銘柄レビュー
    - 最終勧告と次月の戦略
    """

    print("Generating final strategic review with Gemini Pro...")
    response = model.generate_content(prompt)
    return response.text

# --- Reporting ---
def send_report(report_text):
    print("Sending Monthly Strategic Review...")
    try:
        audience = REPORTING_AGENT_URL
        metadata_server_url = f'http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/identity?audience={audience}'
        token_response = requests.get(metadata_server_url, headers={'Metadata-Flavor': 'Google'})
        token = token_response.text
        
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
        subject = f"【ORION MONTHLY STRATEGIC REVIEW】{datetime.now().strftime('%Y-%m')}月度 戦略報告"
        
        # Use the alert mechanism of the reporting agent to send this special report
        payload = {"alert_subject": subject, "alert_body": f"<pre>{report_text}</pre>"}
        
        response = requests.post(REPORTING_AGENT_URL, json=payload, headers=headers, timeout=60)
        response.raise_for_status()
        print("Successfully requested sending of monthly report.")
    except Exception as e:
        print(f"Failed to send monthly report: {e}")

# --- Flask Web Server ---
@app.route("/", methods=["POST"])
def handle_request():
    print("Received request to generate Monthly Strategic Review.")
    try:
        analyses, performances = fetch_monthly_data()
        if not analyses and not performances:
            return jsonify({"status": "success", "message": "No data available for monthly review."} ), 200

        review_text = synthesize_monthly_review(analyses, performances)
        send_report(review_text)
        
        return jsonify({"status": "success"}), 200
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({"error": "An internal server error occurred.", "details": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
