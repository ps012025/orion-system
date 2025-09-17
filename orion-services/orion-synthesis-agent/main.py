import os
import numpy as np
from flask import Flask, jsonify
from google.cloud import firestore
from google.cloud.firestore_v1.vector import Vector
from google.cloud import pubsub_v1
import vertexai
from vertexai.generative_models import GenerativeModel

# --- Initialization ---
app = Flask(__name__)

# --- Configuration ---
PROJECT_ID = "thinking-orb-438805-q7"
LOCATION = "asia-northeast1"
INSIGHTS_COLLECTION = "orion-analysis-reports"
SYNTHESIS_TOPIC_ID = "orion-synthesis-to-report-topic"
NUM_NEIGHBORS = 5

# --- Clients ---
vertexai.init(project=PROJECT_ID, location=LOCATION)
db = firestore.Client(project=PROJECT_ID)
model = GenerativeModel("gemini-1.5-pro-001")
publisher = pubsub_v1.PublisherClient()
synthesis_topic_path = publisher.topic_path(PROJECT_ID, SYNTHESIS_TOPIC_ID)

def find_similar_insights(seed_embedding):
    """Firestoreのベクトル検索を使い、類似するインサイトを見つける。"""
    query = db.collection(INSIGHTS_COLLECTION).find_nearest(
        vector_field="analysis_result_embedding",
        query_vector=Vector(seed_embedding),
        distance_measure="COSINE",
        limit=NUM_NEIGHBORS
    )
    return [doc.to_dict() for doc in query]

def generate_strategic_briefing():
    """ベクトル検索を使ってインサイトをクラスタリングし、戦略的ブリーフィングを生成する。"""
    print("Synthesizer activated. Generating weekly strategic briefing...")
    print("Fetching seed insight (latest macro analysis)...")
    try:
        seed_query = db.collection(INSIGHTS_COLLECTION).where("type", "==", "macro_analysis").order_by("created_at", direction=firestore.Query.DESCENDING).limit(1)
        seed_docs = list(seed_query.stream())
        if not seed_docs:
            return "今週、分析の起点となる主要なマクロ経済レポートが見つかりませんでした。"
        seed_insight = seed_docs[0].to_dict()
        seed_embedding = seed_insight.get("analysis_result_embedding")
        if not seed_embedding:
            return "主要なマクロ経済レポートに、分析の起点となるベクトル埋め込みが見つかりませんでした。"
    except Exception as e:
        print(f"Error fetching seed insight: {e}")
        return "分析の起点となるシードインサイトの取得中にエラーが発生しました。"

    print("Finding similar insights using vector search...")
    try:
        similar_insights = find_similar_insights(seed_embedding)
        if not similar_insights:
            return "類似するインサイトが見つかりませんでした。"
    except Exception as e:
        print(f"Error during vector search: {e}")
        return "ベクトル検索中にエラーが発生しました。"

    print(f"Generating briefing from {len(similar_insights)} related insights...")
    cluster_texts = "\n---\n".join([d.get('analysis_result', '') for d in similar_insights])
    final_summary_prompt = f"""
    あなたは、オリオンシステムの最高分析責任者です。
    今週の主要なマクロ経済レポートを起点として、それに「意味が近い」とAIが判断した、以下のインサイト群が発見されました。
    この全ての情報を統合し、机長（CEO）に向けて、今週の市場で起きた最も重要な変化と、我々が取るべき戦略的アクションを、簡潔にブリーフィングしてください。

    関連インサイト群：
    ---
    {cluster_texts}
    ---

    週次戦略ブリーフィング：
    """
    try:
        final_response = model.generate_content(final_summary_prompt)
        return final_response.text
    except Exception as e:
        print(f"Error generating final briefing: {e}")
        return "最終ブリーフィングの生成に失敗しました。"

@app.route("/", methods=["POST"])
def handle_request():
    """Main entry point. Triggers synthesis and publishes the result."""
    print("Received request to synthesize insights and generate strategic briefing.")
    try:
        briefing = generate_strategic_briefing()
        print("---", "Weekly Strategic Briefing Generated", "---")
        print(briefing)
        print("-----------------------------------------")
        
        print(f"Publishing weekly briefing to topic: {synthesis_topic_path}")
        message_data = briefing.encode("utf-8")
        future = publisher.publish(synthesis_topic_path, data=message_data)
        future.result()
        print("Successfully published weekly briefing for reporting.")
        
        return jsonify({"status": "success", "briefing_published": True}), 200
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({"error": "An internal server error occurred.", "details": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
