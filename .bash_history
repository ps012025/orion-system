gcloud run deploy orion-insight-wrangler   --source .   --region=asia-northeast1   --allow-unauthenticated   --project=thinking-orb-438805-q7
gcloud pubsub topics publish orion-input-topic --message='{"url": "https://www.bloomberg.co.jp/news/articles/2025-09-08/T1ZIYQGOYMTH00"}'
nano Dockerfile
gcloud run deploy orion-insight-wrangler   --source .   --region=asia-northeast1   --allow-unauthenticated   --project=thinking-orb-438805-q7
#!/bin/bash
# Orion System - Genesis Script v3.0 - Final Corrected Version
# This script creates the complete, correct source code and deploys the core agent.
set -e
echo "INFO: オペレーション『ジェネシス・リバース』を開始します。"
echo "INFO: 古い設計図を完全に破棄し、最終確定版をゼロから建造します..."
# --- ステップ0：環境の完全な初期化 ---
cd ~
rm -rf orion-services
mkdir -p orion-services
cd orion-services/
mkdir -p orion-insight-wrangler
cd orion-insight-wrangler
# --- ステップ1：orion-insight-wrangler の最終確定版ファイルを生成 ---
echo "INFO: 旗艦『orion-insight-wrangler』の最終版コードを生成中..."
# main.py (Final Version)
cat << 'EOF' > main.py
import os, base64, json, requests, datetime
from flask import Flask, request
from google.cloud import aiplatform, firestore
from bs4 import BeautifulSoup

app = Flask(__name__)

GCP_PROJECT = os.environ.get('GCP_PROJECT')
LOCATION = 'asia-northeast1'

try:
    aiplatform.init(project=GCP_PROJECT, location=LOCATION)
    DB_CLIENT = firestore.Client()
except Exception as e:
    print(f"FATAL: Failed to initialize Google Cloud clients: {e}")

@app.route('/', methods=['POST'])
def process_article():
    article_url = None
    try:
        envelope = request.get_json()
        if not envelope or 'message' not in envelope or 'data' not in envelope['message']:
            print(f"Invalid message format: {envelope}")
            return "Invalid message format", 400
        
        data = json.loads(base64.b64decode(envelope['message']['data']).decode('utf-8'))
        article_url = data.get('url')
        if not article_url:
            print("URL not found in message")
            return "URL not found", 400

        headers = {'User-Agent': 'OrionScout/1.0'}
        response = requests.get(article_url, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        article_text = " ".join(soup.get_text().split())
        
        model_endpoint = f"projects/{GCP_PROJECT}/locations/{LOCATION}/publishers/google/models/gemini-1.5-flash-001"
        prompt = f"""以下の記事から投資判断に関連する核心情報をJSON形式で抽出してください: - summary (string): 記事の核心的な主張を1文で要約。 - entities (list of strings): 関連する企業名や組織名。 - sentiment (string): "Positive", "Negative", "Neutral"。 - risk_level (integer): 1から5のリスクレベル。 記事：{article_text[:15000]}"""
        
        instances = [{"prompt": prompt}]
        client_options = {"api_endpoint": f"{LOCATION}-aiplatform.googleapis.com"}
        prediction_client = aiplatform.gapic.PredictionServiceClient(client_options=client_options)
        response = prediction_client.predict(endpoint=model_endpoint, instances=instances)
        
        if isinstance(response.predictions[0], str):
             insight_data = json.loads(response.predictions[0])
        else:
             insight_data = dict(response.predictions[0])

        insight_data['timestamp'] = datetime.datetime.utcnow()
        insight_data['source_url'] = article_url
        DB_CLIENT.collection('orion-insights').add(insight_data)
        
        print(f"SUCCESS: Insight saved to Firestore for {article_url}")
        return "OK", 204
    except Exception as e:
        error_message = f"ERROR: Processing URL '{article_url}' failed. Reason: {e}"
        print(error_message)
        return error_message, 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
EOF

# requirements.txt (Final Version)
cat << 'EOF' > requirements.txt
Flask
gunicorn
google-cloud-aiplatform
google-cloud-firestore
requests
beautifulsoup4
EOF

# Dockerfile (Final, Corrected Version)
cat << 'EOF' > Dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# --- これが本来あるべき、正しい本番用サーバーの起動命令 ---
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "main:app"]
EOF

# --- ステップ2：最終確認とデプロイの実行 ---
echo "INFO: 全ファイルの最終版の生成を確認..."
ls -l
echo "INFO: 旗艦『orion-insight-wrangler』の最終配備を開始します..."
gcloud run deploy orion-insight-wrangler   --source .   --region=asia-northeast1   --allow-unauthenticated   --set-env-vars="GCP_PROJECT=thinking-orb-438805-q7"   --project=thinking-orb-438805-q7
gcloud pubsub topics create orion-input-topic
gcloud pubsub topics publish orion-input-topic --message='{"url": "https://www.bloomberg.co.jp/news/articles/2025-09-08/T1ZIYQGOYMTH00"}'
gcloud ai models list --region=asia-northeast1
python /home/ps012025/orion-services/orion-reporting-agent/main.py
cd /home/ps012025/orion-services/orion-reporting-agent
python main.py
cd /home/ps012025/orion-services/orion-reporting-agent
python main.py
cd /home/ps012025/orion-services/orion-reporting-agent
main.py
d /home/ps012025/orion-services/orion-reporting-agent
/home/ps012025/orion-services/orion-reporting-agent
cd /home/ps012025/orion-services/orion-reporting-agent
python main.py
http://localhost:38035/
python main.py
http://localhost:38035/?state=fBjtCTliZePYP7v63OVB6k0Dd4rKpC&code=4/0AVMBsJhev8Q-ifw84y-nH-mdgYfNYQRNETasAGyVQq96aK5mxxxk6rFpzDaEm5PgS-Gkdw&scope=https://www.googleapis.com/auth/gmail.send
http://localhost:38035/?state=fBjtCTliZePYP7v63OVB6k0Dd4rKpC&code=4/0AVMBsJjd2dfOv7UiPelhMyZIlNq262h-wTn4DQ1go4r8olH0k1UvXHWQrtN9gPumMNB81A&scope=https://www.googleapis.com/auth/gmail.send
python main.py
http://localhost:38035/?state=fBjtCTliZePYP7v63OVB6k0Dd4rKpC&code=4/0AVMBsJg8tVzA1RLgrwDAwjb9NcLSdUrRHYuPxxttAq9elDFe4ug5jbZeEqwc618IZbbUvw&scope=https://www.googleapis.com/auth/gmail.send
http://localhost:38035/?state=fBjtCTliZePYP7v63OVB6k0Dd4rKpC&code=4/0AVMBsJgrzwEkxuGGEFkxS4Ct_HCwyYaDGYnrEtWjYtHov_3ffRj33VXYCnFQtfwELr7QOA&scope=https://www.googleapis.com/auth/gmail.send
cd /home/ps012025/orion-services/orion-reporting-agent
python main.py
http://localhost:34021/?state=05mSLB0HhuX3AYXEaCXIuRNjSzBCRM&code=4/0AVMBsJich0qpNhFYPm-qNia6PK3BGnUdcfpKWKYYHivW_TvtnZwCJplyTu1ig087GZCUtA&scope=https://www.googleapis.com/auth/gmail.send
http://localhost:34021/?state=05mSLB0HhuX3AYXEaCXIuRNjSzBCRM&code=4/0AVMBsJgTOuxvfwu-u899UfTka6skl4iEVOOvMrp-u1Gec-G0_fuQkBmrS8TiS0D3cm7CXQ&scope=https://www.googleapis.com/auth/gmail.send
cd /home/ps012025/orion-services/orion-reporting-agent
python main.py
cd /home/ps012025/orion-services/orion-reporting-agent
gunicorn --bind :8083 main:app
curl -X POST http://localhost:8083/
gunicorn --bind :8083 main:app
gunicorn --bind :8090 main:app
cd /home/ps012025/orion-services/orion-reporting-agent
curl -X POST http://localhost:8090/
gunicorn --bind :8090 main:app
cd /home/ps012025/orion-services/orion-synergy-analyzer
gunicorn --bind :8085 main:app
cd /home/ps012025/orion-services/orion-insight-wrangler
gunicorn --bind :8080 main:app
curl -X POST -H "Content-Type: application/json" -d
gunicorn --bind :8080 main:app
curl -X POST -H "Content-Type: application/json" -d                                                                  │·························
curl -X POST -H "Content-Type: application/json" -d'{"message":{"data":"eyJ1cmwiOiAiaHR0cHM6Ly93d3cuYmxvb21iZXJnLmNvLmpwL25ld3MvYXJ0aWNsZXMvMjAyNS0wOS0wOC9UMjNLTlVHT1QwSlAwMCJ9"}}' http://localhost:8080/
curl -X POST -H "Content-Type: application/json" -d'{"message":{"data":"eyJ1cmwiOiAiaHR0cHM6Ly93d3cuYmxvb21iZXJnLmNvLmpwL25ld3MvYXJ0aWNsZXMvMjAyNS0wOS0wOC9UMjNLTlVHT1QwSlAwMCJ9"}}' http://localhost:8080/
gunicorn --bind :8080 --chdir /home/ps012025/orion-services/orion-insight-wrangler main:app
cd /home/ps012025/orion-services/orion-econ-analyzer
gunicorn --bind :8082 main:app
cd /home/ps012025/orion-services/orion-insight-wrangler
gcloud run deploy orion-insight-wrangler --source . --region asia-northeast1
cd ../orion-econ-analyzer
gcloud run deploy orion-econ-analyzer --source . --region asia-northeast1
cd ../orion-synergy-analyzer
gcloud run deploy orion-synergy-analyzer --source . --region asia-northeast1
cd ../orion-risk-sentinel
gcloud run deploy orion-risk-sentinel --source . --region asia-northeast1
cd ../orion-reporting-agent
gcloud run deploy orion-reporting-agent --source . --region asia-northeast1
cd ../orion-daily-heartbeat
gcloud run deploy orion-daily-heartbeat --source . --region asia-northeast1
gemini; exit
python3 /home/ps012025/orion-services/orion-calendar-importer/main.py
curl -X POST http://127.0.0.1:8080/
cd /home/ps012025/orion-services/orion-calendar-importer/
python3 main.py
cd /home/ps012025/orion-services/orion-calendar-importer/
python3 main.py
curl -X POST http://127.0.0.1:8080/
python3 main.py
python3 /home/ps012025/orion-services/orion-calendar-importer/main.py
curl -X POST http://127.0.0.1:8080/
gcloud auth login
[200~gcloud run deploy orion-insight-wrangler --source /home/ps012025/orion-insight-wrangler --region asia-northeast1 --allow-unauthenticated--project thinking-orb-438805-q7 --memory=1Gi
gcloud run deploy orion-insight-wrangler --source /home/ps012025/orion-insight-wrangler --region asia-northeast1 --allow-unauthenticated--project thinking-orb-438805-q7 --memory=1Gi
gcloud run deploy orion-econ-analyzer --source /home/ps012025/orion-services/orion-econ-analyzer --region asia-northeast1--allow-unauthenticated --project thinking-orb-438805-q7 --memory=1Gi
gcloud run deploy orion-synergy-analyzer --source /home/ps012025/orion-services/orion-synergy-analyzer --region asia-northeast1--allow-unauthenticated --project thinking-orb-438805-q7 --memory=1Gi
gcloud run deploy orion-insight-wrangler --source /home/ps012025/orion-insight-wrangler --region asia-northeast1 --allow-unauthenticated--project thinking-orb-438805-q7 --memory=1Gi
gcloud run deploy orion-econ-analyzer --source /home/ps012025/orion-services/orion-econ-analyzer --region asia-northeast1 --allow-unauthenticated --project thinking-orb-438805-q7 --memory=1Gi
gcloud run deploy orion-synergy-analyzer --source /home/ps012025/orion-services/orion-synergy-analyzer --region asia-northeast1 --allow-unauthenticated --project thinking-orb-438805-q7 --memory=1Gi
python3 /home/ps012025/orion-services/orion-reporting-agent/generate_token.py
gcloud auth login
gcloud run deploy orion-reporting-agent --source /home/ps012025/orion-services/orion-reporting-agent --region asia-northeast1 --allow-unauthenticated --project thinking-orb-438805-q7 --memory=1Gi
pip install httplib2
gemini; exit
1
$ vim ./fileA
[1]+  停止                  vim ./fileA
$ fg 1
$ jobs
[1]+ Stopped                 vim .bash
$ jobs -l
[1]+ 10540 Stopped                 vim .bashrc
$ fg %1
ps -ef
ps -ef | grep 1
UID    PID   PPID   C      STIME       TTY  TIME  COMMAND
root   1234  13682  0      00:59:53    -    0:01  vi test
root  14277  13682  1      01:00:34    -    0:00  grep 1
ls
gl
/quit
fg
/quit
exit
jobs
kill %1
jobs
kill %1
tmux kill-session -t geminicli
cd /home/ps012025/orion-services/orion-reporting-agent/
gcloud auth application-default login
python3 generate_token.py
pip install -r requirements.txt
python3 generate_token.py
cd /home/ps012025/orion-services/orion-reporting-agent/
python3 generate_token.py
pip install -r requirements.txt
python3 generate_token.py
gcloud auth application-default login
python3 generate_token.py
gcloud auth login
gcloud auth login
gcloud run deploy orion-reporting-agent --source . --region asia-northeast1
gcloud run deploy orion-reporting-agent --source . --region asia-northeast1 --clear-base-image
curl -X POST -H "Content-Type: application/json" -d '{}' https://orion-reporting-agent-100139368807.asia-northeast1.run.app/
cd /home/ps012025/orion-services/orion-calendar-importer/
pip install -r requirements.txt
gcloud auth application-default login
python3 generate_token.py
python3 /home/ps012025/orion-services/orion-calendar-importer/generate_token.py
gcloud run deploy orion-calendar-importer --source . --region asia-northeast1 --allow-unauthenticated --set-secrets=ORION_CALENDAR_REFRESH_TOKEN=orion-calendar-refresh-token:latest,ORION_CALENDAR_CLIENT_SECRET=orion-calendar-client-secret:latest
ps012025@cloudshell:~/orion-services/orion-calendar-importer (thinking-orb-438805-q7)$ gcloud run deploy orion-calendar-importer --source . --region asia-northeast1 --allow-unauthenticated --set-secrets=ORION_CALENDAR_REFRESH_TOKEN=orion-calendar-refresh-token:latest,ORION_CALENDAR_CLIENT_SECRET=orion-calendar-client-secret:latest
ERROR: (gcloud.run.deploy) Missing required argument [--clear-base-image]: Base image is not supported for services built from Dockerfile. To continue the deployment, please use --clear-base-image to clear the base image.
gcloud run deploy orion-calendar-importer --source . --region asia-northeast1 --allow-unauthenticated --set-secrets=ORION_CALENDAR_REFRESH_TOKEN=orion-calendar-refresh-token:latest,ORION_CALENDAR_CLIENT_SECRET=orion-calendar-client-secret:latest
gcloud run deploy orion-calendar-importer --source . --region asia-northeast1 --allow-unauthenticated --set-secrets=ORION_CALENDAR_REFRESH_TOKEN=orion-calendar-refresh-token:latest,ORION_CALENDAR_CLIENT_SECRET=orion-calendar-client-secret:latest --clear-base-image
gcloud auth login
cd /home/ps012025/orion-services/orion-econ-analyzer && gcloud run deploy orion-econ-analyzer --source . --region asia-northeast1 --clear-base-image
cd /home/ps012025/orion-services/orion-synergy-analyzer && gcloud run deploy orion-synergy-analyzer --source . --region asia-northeast1 --clear-base-image
cd /home/ps012025/orion-services/orion-insight-wrangler && gcloud run deploy orion-insight-wrangler --source . --region asia-northeast1 --clear-base-image
cd /home/ps012025/orion-services/orion-risk-sentinel && gcloud run deploy orion-risk-sentinel --source . --region asia-northeast1 --clear-base-image
cd /home/ps012025/orion-services/orion-insight-wrangler && gcloud run deploy orion-insight-wrangler --source . --region asia-northeast1 --clear-base-image
cd /home/ps012025/orion-services/orion-econ-analyzer && gcloud run deploy orion-econ-analyzer --source . --region asia-northeast1 --clear-base-image
cd /home/ps012025/orion-services/orion-synergy-analyzer && gcloud run deploy orion-synergy-analyzer --source . --region asia-northeast1 --clear-base-image
cd /home/ps012025/orion-services/orion-reporting-agent && gcloud run deploy orion-reporting-agent --source . --region asia-northeast1 --clear-base-image
gcloud artifacts repositories create orion-container-repo --repository-format=docker --location=asia-northeast1 --description="Repository for Orion System container images."
rm /home/ps012025/nasdaq100_ohlcv_1m_*.csv
gcloud artifacts repositories create orion-container-repo --repository-format=docker --location=asia-northeast1 --description="Repository for Orion System container images."
gsutil mb -p thinking-orb-438805-q7 gs://orion-market-data-lake
pip install gcsfs google-cloud-storage
python3 /home/ps012025/populate_datalake.py
gsutil ls gs://orion-market-data-lake/
populate_datalake.py
/home/ps012025/download_data.py:32
/home/ps012025/download_data
gcloud auth login
gcloud auth application-default login
export GOOGLE_APPLICATION_CREDENTIALS=/tmp/tmp.oO3kIVUZoj/application_default_credentials.json
gcloud auth application-default set-quota-project thinking-orb-438805-q7
gsutil mb -p thinking-orb-438805-q7 gs://orion-market-data-lake
python populate_datalake_stepwise.py
python estimate_cost_2023.py
python download_2023_data.py
gsutil ls gs://orion-market-data-lake/
gcloud builds submit --tagasia-northeast1-docker.pkg.dev/thinking-orb-438805-q7/orion-container-repo/orion-backte ster:v1 .
gcloud builds submit --tag asia-northeast1-docker.pkg.dev/thinking-orb-438805-q7/orion-container-repo/orion-backtester:v1 .
gcloud builds submit --tag
gcloud builds submit --tag asia-northeast1-docker.pkg.dev/thinking-orb-438805-q7/orion-container-repo/orion-backte ster:v1 .
/home/ps012025/orion-services/orion-backtester
gcloud builds submit --tag
/home/ps012025/orion-services/orion-backtester
gcloud builds submit --tag
/home/ps012025/orion-services/orion-backtester
gcloud builds submit --tag asia-northeast1-docker.pkg.dev/thinking-orb-438805-q7/orion-container-repo/orion-backte ster:v1 .
cd /home/ps012025/orion-services/orion-backtester
gcloud builds submit --tag asia-northeast1-docker.pkg.dev/thinking-orb-438805-q7/orion-container-repo/orion-backtester: v1 
gcloud builds submit --project thinking-orb-438805-q7 --tag
gcloud builds submit --project thinking-orb-438805-q7 --tag asia-northeast1-docker.pkg.dev/thinking-orb-438805-q7/orion-container-repo/orion-backtester: v1 .
gcloud builds submit --project thinking-orb-438805-q7 --ta asia-northeast1-docker.pkg.dev/thinking-orb-438805-q7/orion-container-repo/orion-backtester: v1 .
gcloud builds submit --project thinking-orb-438805-q7 --tag asia-northeast1-docker.pkg.dev/thinking-orb-438805-q7/orion-container-repo/orion-backtester:v1 .
The command gcloud run deploy orion-backtester --project thinking-orb-438805-q7 --image asia-northeast1-docker.pkg.dev/thinking-orb-438805-q7/orion-container-repo/orion-backtester:v1 --region asia-northeast1 --memory=4Gi --timeout=3600 --allow-unauthenticated
gcloud run deploy orion-backtester --project thinking-orb-438805-q7 --image asia-northeast1-docker.pkg.dev/thinking-orb-438805-q7/orion-container-repo/orion-backtester:v1 --region asia-northeast1 --memory=4Gi --timeout=3600 --allow-unauthenticated　
gcloud run deploy orion-backtester --project thinking-orb-438805-q7 --image asia-northeast1-docker.pkg.dev/thinking-orb-438805-q7/orion-container-repo/orion-backtester:v1 --region asia-northeast1 --memory=4Gi --timeout=3600 --allow-unauthenticated
cd /home/ps012025/orion-services/orion-reporting-agent
python generate_token.py
/home/ps012025/orion-services/orion-reporting-agent
gcloud builds submit --project thinking-orb-438805-q7 --tag asia-northeast1-docker.pkg.dev/thinking-orb-438805-q7/orion-container-repo/orion-reporting-agent:v1 .
gcloud run deploy orion-reporting-agent --project thinking-orb-438805-q7 --image asia-northeast1-docker.pkg.dev/thinking-orb-438805-q7/orion-container-repo/orion-reporting-agent:v1 --region asia-northeast1 --memory=2Gi --timeout=300 --allow-unauthenticated --set-secrets=GOOGLE_CLIENT_SECRET=orion-reporting-client-secret:latest,GOOGLE_REFRESH_TOKEN=orion-reporting-refresh-token:latest
/home/ps012025/orion-services/orion-daily-heartbeat
gcloud builds submit --project thinking-orb-438805-q7 --tag asia-northeast1-docker.pkg.dev/thinking-orb-438805-q7/orion-container-epo/orion-daily-heartbeat:v1 .
/home/ps012025/orion-services/orion-daily-heartbeat
gcloud builds submit --project thinking-orb-438805-q7 --tag asia-northeast1-docker.pkg.dev/thinking-orb-438805-q7/orion-container-repo/orion-daily-heartbeat:v1 .
gcloud run deploy orion-daily-heartbeat --project thinking-orb-438805-q7 --image asia-northeast1-docker.pkg.dev/thinking-orb-438805-q7/orion-container-repo/orion-daily-heartbeat:v1 --region asia-northeast1 --memory=1Gi --timeout=60 --allow-unauthenticated
/home/ps012025/orion-services/orion-insight-wrangler
gcloud builds submit --project thinking-orb-438805-q7 --tag asia-northeast1-docker.pkg.dev/thinking-orb-438805-q7/orion-container-repo/orion-insight-wrangler:v1 .
gcloud builds submit --project thinking-orb-438805-q7 --tag asia-northeast1-docker.pkg.dev/thinking-orb-438805-q7/orion-container-repo/orion-insight-wrangler:v1.
cd /home/ps012025/orion-services/orion-insight-wrangler
gcloud builds submit --project thinking-orb-438805-q7 --tag asia-northeast1-docker.pkg.dev/thinking-orb-438805-q7/orion-container-repo/orion-insight-wrangler:v1 .
gcloud run deploy orion-insight-wrangler --project thinking-orb-438805-q7 --image asia-northeast1-docker.pkg.dev/thinking-orb-438805-q7/orion-container-repo/orion-insight-wrangler:v1 --region asia-northeast1 --memory=2Gi --timeout=300 --allow-unauthenticated
/home/ps012025/orion-services/orion-job-sentiment-analyzer
gcloud builds submit --project thinking-orb-438805-q7 --tag asia-northeast1-docker.pkg.dev/thinking-orb-438805-q7/orion-container-repo/orion-job-sentiment-analyzer:v1 .
gcloud run deploy orion-job-sentiment-analyzer --project thinking-orb-438805-q7 --image asia-northeast1-docker.pkg.dev/thinking-orb-438805-q7/orion-container-repo/orion-job-sentiment-analyzer:v1 --region asia-northeast1 --memory=2Gi --timeout=300 --allow-unauthenticated
/home/ps012025/orion-services/orion-econ-analyzer
gcloud builds submit --project thinking-orb-438805-q7 --tag asia-northeast1-docker.pkg.dev/thinking-orb-438805-q7/orion-container-repo/orion-econ-analyzer:v1 .
gcloud run deploy orion-econ-analyzer --project thinking-orb-438805-q7 --image asia-northeast1-docker.pkg.dev/thinking-orb-438805-q7/orion-container-repo/orion-econ-analyzer:v1 --region asia-northeast1 --memory=2Gi --timeout=300 --allow-unauthenticated
/home/ps012025/orion-services/orion-synergy-analyzer
gcloud builds submit --project thinking-orb-438805-q7 --tag asia-northeast1-docker.pkg.dev/thinking-orb-438805-q7/orion-container-repo/orion-synergy -analyzer:v1 .
gcloud builds submit --project thinking-orb-438805-q7 --tag asia-northeast1-docker.pkg.dev/thinking-orb-438805-q7/orion-container-repo/orion-synergy-analyzer:v1 .
gcloud run deploy orion-synergy-analyzer --project thinking-orb-438805-q7 --image asia-northeast1-docker.pkg.dev/thinking-orb-438805-q7/orion-container-repo/orion-synergy-analyzer:v1 --region asia-northeast1 --memory=2Gi --timeout=300 --allow-unauthenticated
/home/ps012025/orion-services/orion-risk-sentinel
gcloud builds submit --project thinking-orb-438805-q7 --tag asia-northeast1-docker.pkg.dev/thinking-orb-438805-q7/orion-container-repo/orion-risk-sentinel:v1 .
gcloud run deploy orion-risk-sentinel --project thinking-orb-438805-q7 --image asia-northeast1-docker.pkg.dev/thinking-orb-438805-q7/orion-container-repo/orion-risk-sentinel:v1 --region asia-northeast1 --memory=1Gi --timeout=180 --allow-unauthenticated
cd /home/ps012025/orion-services/orion-calendar-importer
python generate_token.py
/home/ps012025/orion-services/orion-calendar-importer
gcloud builds submit --project thinking-orb-438805-q7 --tag asia-northeast1-docker.pkg.dev/thinking-orb-438805-q7/orion-container-repo/orion-calendar-importer:v1 .
gcloud run deploy orion-calendar-importer --project thinking-orb-438805-q7 --image asia-northeast1-docker.pkg.dev/thinking-orb-438805-q7/orion-container-repo/orion-calendar-importer:v1 --region asia-northeast1 --memory=1Gi --timeout=60 --allow-unauthenticated --set-secrets=ORION_CALENDAR_CLIENT_SECRET=orion-calendar-client-secret:latest,ORION_CALENDAR_REFRESH_TOKEN=orion-calendar-refresh-token:latest
gcloud scheduler jobs create http orion-calendar-importer-trigger --project thinking-orb-438805-q7 --schedule "0 0 * * *" --uri "https://orion-calendar-importer-100139368807.asia-northeast1.run.app" --http-method POST --location asia-northeast1 --time-zone "Etc/UTC"
gcloud scheduler jobs create http orion-risk-sentinel-trigger --project thinking-orb-438805-q7 --schedule "30 0 * * *" --uri "https://orion-risk-sentinel-100139368807.asia-northeast1.run.app" --http-method POST --location asia-northeast1 --time-zone "Etc/UTC"
gcloud scheduler jobs create http orion-daily-report-trigger --project thinking-orb-438805-q7 --schedule "0 1 * * *" --uri "https://orion-reporting-agent-100139368807.asia-northeast1.run.app" --http-method POST --location asia-northeast1 --time-zone "Etc/UTC"
gcloud scheduler jobs create http orion-hourly-heartbeat-trigger --project thinking-orb-438805-q7 --schedule "0 * * * *" --uri "https://orion-daily-heartbeat-100139368807.asia-northeast1.run.app" --http-method POST --location asia-northeast1 --time-zone "Etc/UTC"
gcloud scheduler jobs list --project thinking-orb-438805-q7 --location asia-northeast1
gcloud scheduler jobs update http orion-calendar-importer-trigger --project thinking-orb-438805-q7 --schedule "0 15 * * *" --time-zone "Etc/UTC"
gcloud scheduler jobs update http orion-calendar-importer-trigger --project  thinking-orb-438805-q7 --schedule "0 15 * * *" --time-zone "Etc/UTC"
gcloud scheduler jobs update http orion-calendar-importer-trigger --project thinking-orb-438805-q7 --schedule "0 15 * * *" --time-zone "Etc/UTC" --location asia-northeast1
gcloud scheduler jobs update http orion-risk-sentinel-trigger --project thinking-orb-438805-q7 --schedule "30 20 * * *" --time-zone "Etc/UTC" --location asia-northeast1
gcloud scheduler jobs update http orion-daily-report-trigger --project thinking-orb-438805-q7 --schedule "0 21 * * *" --time-zone "Etc/UTC" --location asia-northeast1
gcloud scheduler jobs list --project thinking-orb-438805-q7 --location asia-northeast1
gcloud pubsub topics create orion-url-to-process-topic --project thinking-orb-438805-q7
gcloud pubsub topics create orion-scouting-agent-trigger-topic --project thinking-orb-438805-q7
/home/ps012025/orion-services/orion-scouting-agent
gcloud functions deploy orion-scouting-agent --gen2 --project=thinking-orb-438805-q7 --region=asia-northeast1 --runtime=python312 --source=. --entry-point=scout_and_publish_urls --trigger-topic=orion-scouting-agent-trigger-topic
/home/ps012025/orion-services/orion-scouting-agent
gcloud functions deploy orion-scouting-agent --gen2 --project=thinking-orb-438805-q7 --region=asia-northeast1 --runtime=python312 --source=. --entry-point=scout_and_publish_urls --trigger-topic=orion-scouting-agent-trigger-topic
/home/ps012025/orion-services/orion-scouting-agent
gcloud functions deploy orion-scouting-agent-http --gen2 --project=thinking-orb-438805-q7 --region=asia-northeast1 --runtime=python312 --source=. --entry-point=hello_http --trigger-http --allow-unauthenticated
/home/ps012025/orion-services/orion-scouting-agent
gcloud functions deploy orion-scouting-agent \ --gen2 \ --project=thinking-orb-438805-q7 \ --region=asia-northeast1 \ --runtime=python312 \ --source=. \ --entry-point=scout_and_publish_urls \ --trigger-topic=orion-scouting-agent-trigger-topic
/home/ps012025/orion-services/orion-scouting-agent
gcloud functions deploy orion-scouting-agent --gen2 -- roject=thinking-orb-438805-q7 --region=asia-northeast1 --runtime=python312 --source=. --entry-point=scout_and_publish_urls --trigger-topic=orion-scouting-agent-trigger-topic
cd /home/ps012025/orion-services/orion-scouting-agent
gcloud functions deploy orion-scouting-agent --gen2 --project=thinking-orb-438805-q7--region=asia-northeast1 --runtime=python312 --source=.--region=asia-northeast1 --runtime=python312 --source=.
cd /home/ps012025/orion-services/orion-scouting-agent
gcloud functions deploy orion-scouting-agent --gen2 --project=thinking-orb-438805-q7
/home/ps012025/orion-services/orion-insight-wrangler
gcloud functions deploy orion-insight-wrangler \ --gen2 \ --project=thinking-orb-438805-q7 \ --region=asia-northeast1 \ --runtime=python312 \ --source=. \ --entry-point=process_url \ --trigger-topic=orion-url-to-process-topic \ --timeout=300s \ --memory=512Mi
gcloud functions deploy orion-insight-wrangler --gen2 --project=thinking-orb-438805-q7--region=asia-northeast1 --runtime=python312 --source=. --entry-point=process_url--trigger-topic=orion-url-to-process-topic --timeout=300s --memory=512Mi
/home/ps012025/orion-services/orion-insight-wrangler
gcloud functions deploy orion-insight-wrangler --gen2 --project=thinking-orb-438805-q7 --region=asia-northeast1 --runtime=python312 --source=. --entry-point=process_url --trigger-topic=orion-url-to-process-topic --timeout=300s --memory=512Mi
gcloud functions deploy orion-insight-wrangler --gen2 --project=thinking-orb-438805-q7 --region=asia-northeast1 --runtime=python312 --source=. --entry-point=process_url --trigger-topic=orion-url-to-process-topic --timeout=300s --memory=512Mi
gcloud functions deploy orion-insight-wrangler --gen2 --project=thinking-orb-438805-q7 --region=asia-northeast1 --runtime=python312 --source=. --entry-point=process_url --trigger-topic=orion-url-to-process-topic --timeout=300s --memory=512Mi
/home/ps012025/orion-services/orion-insight-wrangler
gcloud functions deploy orion-insight-wrangler --gen2 --project=thinking-orb-438805-q7 --region=asia-northeast1 --runtime=python312 --source=. --entry-point=process_url --trigger-topic=orion-url-to-process-topic --timeout=300s --memory=512Mi
cd /home/ps012025/orion-services/orion-insight-wrangler
gcloud functions deploy orion-insight-wrangler --gen2 --project=thinking-orb-438805-q7 --region=asia-northeast1 --runtime=python312 --source=. --entry-point=process_url --trigger-topic=orion-url-to-process-topic --timeout=300s --memory=512Mi
gcloud run services delete orion-insight-wrangler --project thinking-orb-438805-q7 --region asia-northeast1
gcloud auth login
gcloud run services delete orion-insight-wrangler --project thinking-orb-438805-q7 --region asia-northeast1
gcloud functions deploy orion-insight-wrangler --gen2 --project=thinking-orb-438805-q7 --region=asia-northeast1 --runtime=python312 --source=. --entry-point=process_url --trigger-topic=orion-url-to-process-topic --timeout=300s --memory=512Mi
/home/ps012025/orion-services/orion-scouting-agent
gcloud functions deploy orion-scouting-agent --gen2 --project=thinking-orb-438805-q7 --region=asia-northeast1 --runtime=python312 --source=. --entry-point=scout_and_publish_urls --trigger-topic=orion-scouting-agent-trigger-topic
gcloud functions delete orion-scouting-agent --project thinking-orb-438805-q7 --region asia-northeast1
gcloud functions deploy orion-scouting-agent --gen2 --project=thinking-orb-438805-q7 --region=asia-northeast1 --runtime=python312 --source=. --entry-point=scout_and_publish_urls --trigger-topic=orion-scouting-agent-trigger-topic
/home/ps012025/orion-services/orion-scouting-agent
gcloud builds submit --project thinking-orb-438805-q7 --tag asia-northeast1-docker.pkg.dev/thinking-orb-438805-q7/orion-container-repo/orion-scouting-agent:v1 .
cd /home/ps0s12025/orion-services/orion-scouting-agent
gcloud builds submit --project thinking-orb-438805-q7 --tag asia-northeast1-docker.pkg.dev/thinking-orb-438805-q7/orion-container-repo/orion-scouting-agent:v1 .
cd /home/ps012025/orion-services/orion-scouting-agent
gcloud builds submit --project thinking-orb-438805-q7 --tag asia-northeast1-docker.pkg.dev/thinking-orb-438805-q7/orion-container-repo/orion-scouting-agent:v1 .
gcloud run deploy orion-scouting-agent --project thinking-orb-438805-q7 --image asia-northeast1-docker.pkg.dev/thinking-orb-438805-q7/orion-container-repo/orion-scouting-agent:v1 --region asia-northeast1 --memory=1Gi --timeout=180 --allow-unauthenticated
/home/ps012025/orion-services/orion-insight-wrangler
gcloud builds submit --project thinking-orb-438805-q7 --tag asia-northeast1-docker.pkg.dev/thinking-orb-438805-q7/orion-container-repo/orion-insight-wrangler:v1 .
gcloud run deploy orion-insight-wrangler --project thinking-orb-438805-q7 --image asia-northeast1-docker.pkg.dev/thinking-orb-438805-q7/orion-container-repo/orion-insight-wrangler:v1 --region asia-northeast1 --memory=2Gi --timeout=300s --no-allow-unauthenticated
gcloud iam service-accounts create orion-pubsub-invoker --project=thinking-orb-438805-q7 --display-name="Orion Pub/Sub Invoker"
gcloud run services add-iam-policy-binding orion-insight-wrangler --project=thinking-orb-438805-q7 --region=asia-northeast1 --member="serviceAccount:orion-pubsub-invoker@thinking-orb-438805-q7.iam.gserviceaccount.com" --role="roles/run.invoker"
gcloud pubsub subscriptions create orion-insight-wrangler-sub --project=thinking-orb-438805-q7 --topic=orion-url-to-process-topic --push-endpoint="https://orion-insight-wrangler-100139368807.asia-northeast1.run.app" --push-auth-service-account="orion-pubsub-invoker@thinking-orb-438805-q7.iam.gserviceaccount.com"
gcloud scheduler jobs create pubsub orion-daily-scouting-job --project=thinking-orb-438805-q7 --schedule="0 8 * * *" --topic=orion-scouting-agent-trigger-topic --message-body="Start scouting" --time-zone="Asia/Tokyo"
gcloud scheduler jobs create pubsub orion-daily-scouting-job --project=thinking-orb-438805-q7 --schedule="0 8 * * *" --topic=orion-scouting-agent-trigger-topic --message-body="Start scouting" --time-zone="Asia/Tokyo" --location=asia-northeast1
/home/ps012025/orion-services/orion-insight-wrangler
gcloud builds submit --project thinking-orb-438805-q7 --tag asia-northeast1-docker.pkg.dev/thinking-orb-438805-q7/orion-container-repo/orion-insight-wrangler:v2 .
gcloud run deploy orion-insight-wrangler --project=thinking-orb-438805-q7 --image asia-northeast1-docker.pkg.dev/thinking-orb-438805-q7/orion-container-repo/orion-insight-wrangler:v2 --region asia-northeast1 --memory=2Gi --timeout=300s --no-allow-unauthenticated
/home/ps012025/orion-services/orion-synthesis-agent
gcloud builds submit --project thinking-orb-438805-q7 --tag asia-northeast1-docker.pkg.dev/thinking-orb-438805-q7/orion-container-repo/orion-synthesis-agent:v1 .
gcloud run deploy orion-synthesis-agent --project thinking-orb-438805-q7 --image asia-northeast1-docker.pkg.dev/thinking-orb-438805-q7/orion-container-repo/orion-synthesis-agent:v1 --region asia-northeast1 --memory=2Gi --timeout=600 --allow-unauthenticated
gcloud scheduler jobs create http orion-weekly-synthesis-trigger --project thinking-orb-438805-q7 --schedule "0 2 * * 1" --uri "https://orion-synthesis-agent-100139368807.asia-northeast1.run.app" --http-method POST --location asia-northeast1 --time-zone "Etc/UTC"
gcloud scheduler jobs update http orion-daily-report-trigger --project thinking-orb-438805-q7 --schedule "0 21 * * *" --time-zone "Etc/UTC" --location asia-northeast1
gcloud scheduler jobs update http orion-weekly-synthesis-trigger --project thinking-orb-438805-q7 --schedule "0 23 * * 5" --time-zone "Etc/UTC" --location asia-northeast1
/home/ps012025/orion-services/orion-reporting-agent
gcloud builds submit --project thinking-orb-438805-q7 --tag asia-northeast1-docker.pkg.dev/thinking-orb-438805-q7/orion-container-repo/orion-reporting-agent:v2 .
gcloud run deploy orion-reporting-agent --project=thinking-orb-438805-q7 --image asia-northeast1-docker.pkg.dev/thinking-orb-438805-q7/orion-container-repo/orion-reporting-agent:v2 --region asia-northeast1 --memory=2Gi --timeout=300 --allow-unauthenticated --set-secrets=GOOGLE_CLIENT_SECRET=orion-reporting-client-secret:latest,GOOGLE_REFRESH_TOKEN=orion-reporting-refresh-token:latest
/home/ps012025/orion-services/orion-risk-sentinel
gcloud builds submit --project thinking-orb-438805-q7 --tag asia-northeast1-docker.pkg.dev/thinking-orb-438805-q7/orion-container-repo/orion-risk-sentinel:v2 .
cd /home/ps012025/orion-services/orion-risk-sentinel
gcloud builds submit --project thinking-orb-438805-q7 --tag asia-northeast1-docker.pkg.dev/thinking-orb-438805-q7/orion-container-repo/orion-risk-sentinel:v2 .
cd /home/ps012025/orion-services/orion-risk-sentinel
gcloud builds submit --project thinking-orb-438805-q7 --tag asia-northeast1-docker.pkg.dev/thinking-orb-438805-q7/orion-container-repo/orion-risk-sentinel:v2 .
gcloud run deploy orion-risk-sentinel --project=thinking-orb-438805-q7 --image asia-northeast1-docker.pkg.dev/thinking-orb-438805-q7/orion-container-repo/orion-risk-sentinel:v2 --region asia-northeast1 --memory=1Gi --timeout=180 --allow-unauthenticated
gcloud run services add-iam-policy-binding orion-reporting-agent --project=thinking-orb-438805-q7 --region=asia-northeast1 --member="serviceAccount:100139368807-compute@developer.gserviceaccount.com" --role="roles/run.invoker"
/home/ps012025/orion-services/orion-risk-sentinel
gcloud builds submit --project thinking-orb-438805-q7 --tag asia-northeast1-docker.pkg.dev/thinking-orb-438805-q7/orion-container-repo/orion-risk-sentinel:v3 .
gcloud run deploy orion-risk-sentinel --project=thinking-orb-438805-q7 --image asia-northeast1-docker.pkg.dev/thinking-orb-438805-q7/orion-container-repo/orion-risk-sentinel:v3 --region asia-northeast1 --memory=1Gi --timeout=180 --allow-unauthenticated
/home/ps012025/orion-services/orion-reporting-agent
gcloud builds submit --project thinking-orb-438805-q7 --tag asia-northeast1-docker.pkg.dev/thinking-orb-438805-q7/orion-container-repo/orion-reporting-agent:v3 .
gcloud run deploy orion-reporting-agent --project=thinking-orb-438805-q7 --image asia-northeast1-docker.pkg.dev/thinking-orb-438805-q7/orion-container-repo/orion-reporting-agent:v3 --region asia-northeast1 --memory=2Gi --timeout=300 --allow-unauthenticated --set-secrets=GOOGLE_CLIENT_SECRET=orion-reporting-client-secret:latest,GOOGLE_REFRESH_TOKEN=orion-reporting-refresh-token:latest
/home/ps012025/orion-services/orion-macro-analyzer
gcloud functions deploy orion-macro-analyzer --gen2 --project=thinking-orb-438805-q7 --region=asia-northeast1 --runtime=python312 --source=. --entry-point=analyze_macro_environment --trigger-http --allow-unauthenticated
/home/ps012025/orion-services/orion-options-analyzer
gcloud builds submit --project thinking-orb-438805-q7 --tag asia-northeast1-docker.pkg.dev/thinking-orb-438805-q7/orion-container-repo/orion-options-analyzer:v1 .
gcloud run deploy orion-options-analyzer --project=thinking-orb-438805-q7 --image asia-northeast1-docker.pkg.dev/thinking-orb-438805-q7/orion-container-repo/orion-options-analyzer:v1 --region asia-northeast1 --memory=2Gi --timeout=300 --allow-unauthenticated
/home/ps012025/orion-services/orion-quant-analyzer
gcloud builds submit --project thinking-orb-438805-q7 --tag asia-northeast1-docker.pkg.dev/thinking-orb-438805-q7/orion-container-repo/orion-quant-analyzer:v1 .
gcloud run deploy orion-quant-analyzer --project=thinking-orb-438805-q7 --image asia-northeast1-docker.pkg.dev/thinking-orb-438805-q7/orion-container-repo/orion-quant-analyzer:v1 --region asia-northeast1 --memory=2Gi --timeout=600 --allow-unauthenticated
gcloud scheduler jobs create http orion-macro-analyzer-trigger --project thinking-orb-438805-q7 --schedule "0 15 * * *" --uri "https://orion-macro-analyzer-100139368807.asia-northeast1.run.app" --http-method POST --location asia-northeast1 --time-zone "Etc/UTC"
gcloud scheduler jobs create http orion-quant-analyzer-trigger --project thinking-orb-438805-q7 --schedule "15 15 * * *" --uri "https://orion-quant-analyzer-100139368807.asia-northeast1.run.app" --http-method POST --location asia-northeast1 --time-zone "Etc/UTC"
gcloud scheduler jobs create http orion-options-analyzer-trigger --project thinking-orb-438805-q7 --schedule "45 20 * * *" --uri "https://orion-options-analyzer-100139368807.asia-northeast1.run.app" --http-method POST --location asia-northeast1 --time-zone "Etc/UTC"
gcloud scheduler jobs list --project thinking-orb-438805-q7 --location asia-northeast1
/home/ps012025/orion-services/orion-macro-analyzer
gcloud builds submit --project thinking-orb-438805-q7 --tag asia-northeast1-docker.pkg.dev/thinking-orb-438805-q7/orion-container-repo/orion-macro-analyzer:v1 .
/home/ps012025/orion-services/orion-macro-analyzer
gcloud builds submit --project thinking-orb-438805-q7 --tag asia-northeast1-docker.pkg.dev/thinking-orb-438805-q7/orion-container-repo/orion-macro-analyzer:v1 .
gcloud run deploy orion-macro-analyzer --project=thinking-orb-438805-q7 --image asia-northeast1-docker.pkg.dev/thinking-orb-438805-q7/orion-container-repo/orion-macro-analyzer:v1 --region asia-northeast1 --memory=2Gi --timeout=600 --allow-unauthenticated
/home/ps012025/orion-services/orion-quant-analyzer
gcloud builds submit --project thinking-orb-438805-q7 --tag asia-northeast1-docker.pkg.dev/thinking-orb-438805-q7/orion-container-repo/orion-quant-analyzer:v1 .
gcloud run deploy orion-quant-analyzer --project=thinking-orb-438805-q7 --image asia-northeast1-docker.pkg.dev/thinking-orb-438805-q7/orion-container-repo/orion-quant-analyzer:v1 --region asia-northeast1 --memory=2Gi --timeout=600 --allow-unauthenticated
gcloud scheduler jobs create http orion-macro-analyzer-trigger --project thinking-orb-438805-q7 --schedule "0 15 * * *" --uri "https://orion-macro-analyzer-100139368807.asia-northeast1.run.app" --http-method POST --location asia-northeast1 --time-zone "Etc/UTC"
gcloud scheduler jobs create http orion-quant-analyzer-trigger --project thinking-orb-438805-q7 --schedule "15 15 * * *" --uri "https://orion-quant-analyzer-100139368807.asia-northeast1.run.app" --http-method POST --location asia-northeast1 --time-zone "Etc/UTC"
gcloud scheduler jobs create http orion-options-analyzer-trigger --project thinking-orb-438805-q7 --schedule "45 20 * * *" --uri "https://orion-options-analyzer-100139368807.asia-northeast1.run.app" --http-method POST --location asia-northeast1 --time-zone "Etc/UTC"
/home/ps012025/orion-services/orion-portfolio-manager
cd//home/ps012025/orion-services/orion-portfolio-manager
cd /home/ps012025/orion-services/orion-portfolio-manager
gcloud functions deploy orion-portfolio-manager --gen2 --project=thinking-orb-438805-q7 --region=asia-northeast1 --runtime=python312 --source=. --entry-point=manage_portfolio --trigger-http --allow-unauthenticated
gcloud functions deploy orion-portfolio-manager --gen2 --project=thinking-orb-438805-q7 --region=asia-northeast1 --runtime=python312 --source=. --entry-point=manage_portfolio --trigger-http --allow-unauthenticated
cd /home/ps012025/orion-services/orion-portfolio-manager
exit
gcloud functions deploy orion-portfolio-manager --gen2 --project=thinking-orb-438805-q7 --region=asia-northeast1 --runtime=python312 --source=. --entry-point=manage_portfolio --trigger-http --allow-unauthenticated
gcloud artifacts repositories create orion-container-repo --project=thinking-orb-438805-q7 --repository-format=docker --location=asia-northeast1 --description="Container repository for Orion Intelligence Engine services"
gcloud builds submit --tag asia-northeast1-docker.pkg.dev/thinking-orb-438805-q7/orion-container-repo/orion-portfolio-manager:v1 .
gcloud run deploy orion-portfolio-manager --image asia-northeast1-docker.pkg.dev/thinking-orb-438805-q7/orion-container-repo/orion-portfolio-manager:v1 --project=thinking-orb-438805-q7 --region=asia-northeast1 --allow-unauthenticated --memory=256Mi
gcloud firestore indexes composite create --collection-group=orion-analysis-reports --query-scope=COLLECTION --field-config=field-path=analysis_result_embedding,vector-config='{"dimension":768,"flat":{}}'
/home/ps012025/orion-services/orion-synthesis-agent
gcloud builds submit --project thinking-orb-438805-q7 --tag asia-northeast1-docker.pkg.dev/thinking-orb-438805-q7/orion-container-repo/orion-synthesis-agent:v2 .
gcloud run deploy orion-synthesis-agent --project=thinking-orb-438805-q7 --image asia-northeast1-docker.pkg.dev/thinking-orb-438805-q7/orion-container-repo/orion-synthesis-agent:v2 --region asia-northeast1 --memory=2Gi --timeout=600 --allow-unauthenticated
gcloud pubsub topics create orion-synthesis-to-report-topic --project thinking-orb-438805-q7
gcloud builds submit --project thinking-orb-438805-q7 --tag asia-northeast1-docker.pkg.dev/thinking-orb-438805-q7/orion-container-repo/orion-synthesis-agent:v3 .
gcloud run deploy orion-synthesis-agent --project=thinking-orb-438805-q7 --image asia-northeast1-docker.pkg.dev/thinking-orb-438805-q7/orion-container-repo/orion-synthesis-agent:v3 --region asia-northeast1 --memory=2Gi --timeout=600 --allow-unauthenticated
/home/ps012025/orion-services/orion-reporting-agent
gcloud builds submit --project thinking-orb-438805-q7 --tag asia-northeast1-docker.pkg.dev/thinking-orb-438805-q7/orion-container-repo/orion-reporting-agent:v4 .
gcloud run deploy orion-reporting-agent --project=thinking-orb-438805-q7 --image asia-northeast1-docker.pkg.dev/thinking-orb-438805-q7/orion-container-repo/orion-reporting-agent:v4 --region asia-northeast1 --memory=2Gi --timeout=300 --allow-unauthenticated --set-secrets=GOOGLE_CLIENT_SECRET=orion-reporting-client-secret:latest,GOOGLE_REFRESH_TOKEN=orion-reporting-refresh-token:latest
gcloud pubsub subscriptions create orion-weekly-briefing-sub --project=thinking-orb-438805-q7 --topic=orion-synthesis-to-report-topic --push-endpoint="https://orion-reporting-agent-100139368807.asia-northeast1.run.app/handle-weekly-briefing" --push-auth-service-account="orion-pubsub-invoker@thinking-orb-438805-q7.iam.gserviceaccount.com"
/home/ps012025/orion-services/orion-monthly-strategist
gcloud builds submit --project thinking-orb-438805-q7 --tag asia-northeast1-docker.pkg.dev/thinking-orb-438805-q7/orion-container-repo/orion-monthly-strategist:v1 .
gcloud run deploy orion-monthly-strategist --project=thinking-orb-438805-q7 --image asia-northeast1-docker.pkg.dev/thinking-orb-438805-q7/orion-container-repo/orion-monthly-strategist:v1 --region asia-northeast1 --memory=2Gi --timeout=900 --allow-unauthenticated
gcloud scheduler jobs create http orion-monthly-strategist-trigger --project=thinking-orb-438805-q7 --schedule "0 2 1 * *" --uri "https://orion-monthly-strategist-100139368807.asia-northeast1.run.app" --http-method POST --location asia-northeast1 --time-zone "Etc/UTC"
python download_2018_05_data.py
python download_2018_05_01_data.py
gsutil mb -p thinking-orb-438805-q7 gs://orion-hr-text-bucket
/home/ps012025/orion-services/orion-scouting-agent
gcloud builds submit --project thinking-orb-438805-q7 --tag asia-northeast1-docker.pkg.dev/thinking-orb-438805-q7/orion-container-repo/orion-scouting-agent:v2 .
/home/ps012025/orion-services/orion-scouting-agent
cd /home/ps012025/orion-services/orion-scouting-agent
gcloud builds submit --project thinking-orb-438805-q7 --tag asia-northeast1-docker.pkg.dev/thinking-orb-438805-q7/orion-container-repo/orion-scouting-agent:v2 .
gcloud run deploy orion-scouting-agent --project=thinking-orb-438805-q7 --image asia-northeast1-docker.pkg.dev/thinking-orb-438805-q7/orion-container-repo/orion-scouting-agent:v2 --region asia-northeast1 --memory=1Gi --timeout=180 --allow-unauthenticated
/home/ps012025/orion-services/orion-job-sentiment-analyzer
gcloud functions deploy orion-job-sentiment-analyzer --gen2 --project=thinking-orb-438805-q7 --region=asia-northeast1 --runtime=python312 --source=. --entry-point=analyze_job_sentiment --trigger-bucket=orion-hr-text-bucket
gsutil rm -r gs://orion-hr-text-bucket
gsutil mb -p thinking-orb-438805-q7 -l asia-northeast1 gs://orion-hr-text-bucket
/home/ps012025/orion-services/orion-job-sentiment-analyzer
gcloud functions deploy orion-job-sentiment-analyzer --gen2 --project=thinking-orb-438805-q7 --region=asia-northeast1 --runtime=python312 --source=. --entry-point=analyze_job_sentiment --trigger-bucket=orion-hr-text-bucket
ステップ1：古いCloud Runサービスの削除
gcloud run services delete orion-job-sentiment-analyzer --project thinking-orb-438805-q7 --region asia-northeast1
gcloud functions deploy orion-job-sentiment-analyzer --gen2 --project=thinking-orb-438805-q7 --region=asia-northeast1 --runtime=python312 --source=. --entry-point=analyze_job_sentiment --trigger-bucket=orion-hr-text-bucket
/home/ps012025/orion-services/orion-scouting-agent
gcloud functions deploy orion-scouting-agent --gen2 --project=thinking-orb-438805-q7 --region=asia-northeast1 --runtime=python312 --source=. --entry-point=scout_and_publish_urls --trigger-topic=orion-scouting-agent-trigger-topic
npm upgrade -g @google/gemini-cli
gcloud auth login
gcloud services enable vertexai.googleapis.com --project=thinking-orb-438805-q7
exit
gsutil mb -p thinking-orb-438805-q7 -l asia-northeast1 gs://orion-hr-text-bucket
gs://gcf-v2-uploads-328258682114.asia-northeast1.cloudfunctions.appspot.com/
gs://gcf-v2-sources-328258682114-asia-northeast1/
gs://gcf-v2-uploads-328258682114.asia-northeast1.cloudfunctions.appspot.com/
gs://orion-market-data-lake-v1/
gs://project-orion-admins-orion-raw-storage/
gs://project-orion-admins_cloudbuild/
gs://run-sources-project-orion-admins-asia-northeast1/
gs://gcf-v2-uploads-328258682114.asia-northeast1.cloudfunctions.appspot.com/
gs://orion-market-data-lake-v1/
gs://project-orion-admins-orion-raw-storage/
gs://project-orion-admins_cloudbuild/
gs://run-sources-project-orion-admins-asia-northeast1/
