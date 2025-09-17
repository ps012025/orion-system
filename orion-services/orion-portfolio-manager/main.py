# /orion-services/orion-portfolio-manager/main.py

import os
from flask import Flask, request, jsonify
from google.cloud import firestore

# Flaskアプリケーションを初期化
app = Flask(__name__)

PROJECT_ID = os.environ.get("GCP_PROJECT", "thinking-orb-438805-q7")
PORTFOLIO_COLLECTION = "orion-portfolio-holdings"
DOCUMENT_ID = "current_portfolio"

db = firestore.Client(project=PROJECT_ID)

@app.route("/", methods=['POST'])
def manage_portfolio():
    """HTTP POSTリクエストでポートフォリオの銘柄リストを更新する。"""
    data = request.get_json()
    if not data or 'symbols' not in data or not isinstance(data['symbols'], list):
        return jsonify({"error": "Invalid request. 'symbols' key with a list of strings is required."}), 400

    try:
        symbols = data['symbols']
        doc_ref = db.collection(PORTFOLIO_COLLECTION).document(DOCUMENT_ID)
        doc_ref.set({"symbols": symbols, "updated_at": firestore.SERVER_TIMESTAMP})
        
        print(f"Successfully updated portfolio with {len(symbols)} symbols.")
        return jsonify({"status": "success", "message": f"Portfolio updated with {len(symbols)} symbols."}), 200
    except Exception as e:
        print(f"Error updating portfolio: {e}")
        return jsonify({"error": "An internal server error occurred."}), 500

if __name__ == "__main__":
    # PORT環境変数をリッスン
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))