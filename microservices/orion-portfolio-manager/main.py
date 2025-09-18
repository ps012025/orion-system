import os
from flask import Flask, request, jsonify
from google.cloud import firestore

# Flaskアプリケーションを初期化
app = Flask(__name__)

PROJECT_ID = os.environ.get("GCP_PROJECT", "project-orion-admins") # Get from env
PORTFOLIO_COLLECTION = "orion-portfolio-positions" # Corrected collection
DOCUMENT_ID = "current_portfolio" # This is a simple approach, might need refinement

db = firestore.Client(project=PROJECT_ID)

@app.route("/", methods=['POST'])
def manage_portfolio_v2():
    """HTTP POSTリクエストでポートフォリオの銘柄リストを更新する。"""
    data = request.get_json()
    if not data or 'positions' not in data or not isinstance(data['positions'], list):
        return jsonify({"error": "Invalid request. 'positions' key with a list of objects is required."}), 400

    try:
        positions = data['positions']
        # In a real system, you'd validate each position object
        # For now, we assume the format is correct, e.g., {'symbol': 'NVDA', 'quantity': 10, ...}
        
        batch = db.batch()
        for pos in positions:
            symbol = pos.get('symbol')
            if not symbol:
                continue
            doc_ref = db.collection(PORTFOLIO_COLLECTION).document(symbol)
            batch.set(doc_ref, pos, merge=True) # Use merge=True to update fields
        
        batch.commit()
        
        print(f"Successfully updated {len(positions)} positions in the portfolio.")
        return jsonify({"status": "success", "message": f"Portfolio updated with {len(positions)} positions."}), 200
    except Exception as e:
        print(f"Error updating portfolio: {e}")
        return jsonify({"error": "An internal server error occurred."}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
