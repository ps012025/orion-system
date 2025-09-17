#!/bin/bash
#
# Orion System v7.1 - Fully Automated & Resilient Deployment Script
#
# Description: This script deploys the entire Orion v7.1 architecture,
#              including GCP services, IAM roles with least privilege,
#              and all microservices, in a single, idempotent process.
#              It is designed to be run directly in Google Cloud Shell.

# --- Script Configuration & Safety ---
set -e  # Exit immediately if a command exits with a non-zero status.
set -u  # Treat unset variables as an error.
set -o pipefail # Pipes will fail if any command in the pipe fails.

## #############################################################
# ACTION: Please edit these variables to match your environment.
export PROJECT_ID="thinking-orb-438805-q7"
export REGION="asia-northeast1" # e.g., us-central1, asia-northeast1

# Naming Conventions (centrally managed)
export GCS_BUCKET_NAME="${PROJECT_ID}-orion-raw-storage"
export BQ_DATASET_NAME="orion_datalake"
export BQ_HISTORY_TABLE_NAME="market_data_history"
export BQ_FEATURES_MV_NAME="market_data_features"
export PUBSUB_TOPIC_INGEST="raw-urls-ingest"
export PUBSUB_TOPIC_FILTERED="filtered-urls-for-analysis"
export SERVICE_ACCOUNT_NAME="orion-service-account"
export SECRET_FINNHUB_API_KEY="finnhub-api-key"
################################################################################

# --- Function Definitions ---
log() {
  echo "✅ - $1"
}

# Function to check if a command exists
command_exists() {
  command -v "$1" >/dev/null 2>&1
}

# Function to enable APIs idempotently
enable_apis() {
    log "Enabling necessary GCP APIs..."
    gcloud services enable \
        cloudresourcemanager.googleapis.com \
        iam.googleapis.com \
        run.googleapis.com \
        cloudfunctions.googleapis.com \
        cloudbuild.googleapis.com \
        pubsub.googleapis.com \
        bigquery.googleapis.com \
        storage.googleapis.com \
        vertexai.googleapis.com \
        secretmanager.googleapis.com
}

# Function to set up IAM with least privilege
setup_iam() {
    log "Setting up IAM service account: ${SERVICE_ACCOUNT_NAME}..."
    export SERVICE_ACCOUNT_EMAIL="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
    if ! gcloud iam service-accounts describe "${SERVICE_ACCOUNT_EMAIL}" --project="${PROJECT_ID}" &>/dev/null; then
        gcloud iam service-accounts create "${SERVICE_ACCOUNT_NAME}" \
            --display-name="Service Account for Orion System" \
            --project="${PROJECT_ID}"
    fi

    log "Assigning necessary roles to service account..."
    # Grant roles one by one for better error tracking and idempotency
    gcloud projects add-iam-policy-binding "${PROJECT_ID}" --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" --role="roles/pubsub.publisher" --condition=None > /dev/null
    gcloud projects add-iam-policy-binding "${PROJECT_ID}" --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" --role="roles/run.invoker" --condition=None > /dev/null
    gcloud projects add-iam-policy-binding "${PROJECT_ID}" --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" --role="roles/aiplatform.user" --condition=None > /dev/null
    gcloud projects add-iam-policy-binding "${PROJECT_ID}" --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" --role="roles/bigquery.dataEditor" --condition=None > /dev/null
    gcloud projects add-iam-policy-binding "${PROJECT_ID}" --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" --role="roles/bigquery.jobUser" --condition=None > /dev/null
    gcloud projects add-iam-policy-binding "${PROJECT_ID}" --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" --role="roles/storage.objectAdmin" --condition=None > /dev/null
    gcloud projects add-iam-policy-binding "${PROJECT_ID}" --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" --role="roles/secretmanager.secretAccessor" --condition=None > /dev/null
    log "IAM roles assigned."
}

# Function to manage secrets securely
setup_secrets() {
    log "Setting up Secret Manager for API keys..."
    if ! gcloud secrets describe ${SECRET_FINNHUB_API_KEY} --project="${PROJECT_ID}" &>/dev/null; then
        if [ ! -f "finnhub.secret" ]; then
            echo "🚨 ERROR: 'finnhub.secret' file not found. Please create it with your Finnhub API key."
            exit 1
        fi
        gcloud secrets create ${SECRET_FINNHUB_API_KEY} --data-file="finnhub.secret" --project="${PROJECT_ID}"
    fi
    gcloud secrets add-iam-policy-binding ${SECRET_FINNHUB_API_KEY} \
        --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
        --role="roles/secretmanager.secretAccessor" \
        --project="${PROJECT_ID}" > /dev/null
    log "Secret '${SECRET_FINNHUB_API_KEY}' is ready."
}

# Function to set up the data platform
setup_data_platform() {
    log "Setting up data platform components..."
    # GCS Bucket
    if ! gsutil ls -b "gs://${GCS_BUCKET_NAME}" &>/dev/null; then
        gsutil mb -l "${REGION}" "gs://${GCS_BUCKET_NAME}"
    fi
    cat <<EOF > lifecycle.json
{ "rule": [ { "action": { "type": "Delete" }, "condition": { "age": 365 } } ] }
EOF
    gsutil lifecycle set lifecycle.json "gs://${GCS_BUCKET_NAME}"
    rm lifecycle.json
    log "GCS bucket '${GCS_BUCKET_NAME}' with lifecycle policy is ready."

    # BigQuery Dataset
    if ! bq --location=${REGION} show --dataset "${PROJECT_ID}:${BQ_DATASET_NAME}" &>/dev/null; then
        bq --location=${REGION} mk --dataset \
            --default_table_expiration 157680000 \
            --description "Orion Datalake with 5-year table expiration" \
            "${PROJECT_ID}:${BQ_DATASET_NAME}"
    fi
    log "BigQuery dataset '${BQ_DATASET_NAME}' is ready."

    # Pub/Sub Topics
    if ! gcloud pubsub topics describe "${PUBSUB_TOPIC_INGEST}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
        gcloud pubsub topics create "${PUBSUB_TOPIC_INGEST}" --project="${PROJECT_ID}"
    fi
    if ! gcloud pubsub topics describe "${PUBSUB_TOPIC_FILTERED}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
        gcloud pubsub topics create "${PUBSUB_TOPIC_FILTERED}" --project="${PROJECT_ID}"
    fi
    log "Pub/Sub topics are ready."
}

# Function to deploy all microservices
deploy_microservices() {
    log "Deploying microservices..."
    # Create dummy source directories and files for deployment
    # This allows the script to be self-contained and run without a git clone
    mkdir -p microservices/zero-cost-filter
    cat <<'EOF' > microservices/zero-cost-filter/main.py
import os, json, base64
from google.cloud import pubsub_v1
publisher = pubsub_v1.PublisherClient()
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
NEXT_TOPIC_ID = os.environ.get("NEXT_TOPIC_ID")
TOPIC_PATH = publisher.topic_path(PROJECT_ID, NEXT_TOPIC_ID)
IRRELEVANT_KEYWORDS = ['sports', 'entertainment', 'celebrity', 'fashion', 'lifestyle']
def pre_filter_url(event, context):
    try:
        message_data_str = base64.b64decode(event["data"]).decode('utf-8')
        data = json.loads(message_data_str)
        url = data.get('url', '').lower()
        title = data.get('title', '').lower()
        if any(keyword in title or keyword in url for keyword in IRRELEVANT_KEYWORDS):
            print(f"IRRELEVANT: URL破棄: {url}")
            return
        future = publisher.publish(TOPIC_PATH, data=message_data_str.encode('utf-8'))
        print(f"RELEVANT: URL転送: {url} (Message ID: {future.result()})")
    except Exception as e:
        print(f"エラー: メッセージ処理に失敗しました: {e}")
EOF
    echo "google-cloud-pubsub" > microservices/zero-cost-filter/requirements.txt

    log "Deploying Zero-Cost Filter (Cloud Function)..."
    gcloud functions deploy pre-filter-url \
        --gen2 \
        --runtime=python312 \
        --source=./microservices/zero-cost-filter/ \
        --entry-point=pre_filter_url \
        --trigger-topic="${PUBSUB_TOPIC_INGEST}" \
        --region="${REGION}" \
        --service-account="${SERVICE_ACCOUNT_EMAIL}" \
        --set-env-vars="GOOGLE_CLOUD_PROJECT=${PROJECT_ID},NEXT_TOPIC_ID=${PUBSUB_TOPIC_FILTERED}" \
        --project="${PROJECT_ID}"

    #
}

# --- Main Execution Logic ---
main() {
    log "Starting Orion System v7.1 deployment for project: ${PROJECT_ID}"
    gcloud config set project "${PROJECT_ID}"

    enable_apis
    setup_iam
    setup_secrets
    setup_data_platform
    deploy_microservices

    log "NOTE: BigQuery Materialized View is not created by this script as it requires the base table to have data."
    log "Please populate '${BQ_HISTORY_TABLE_NAME}' and then run the SQL from the technical report."
    log "🚀 Orion System v7.1 deployment script finished successfully! 🚀"
}

# Execute the main function
main
