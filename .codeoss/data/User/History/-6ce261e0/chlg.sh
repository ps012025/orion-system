#!/bin/bash
# Orion System v8.2 - All-in-One Resilient Deployment Script
set -e
set -u
set -o pipefail

# ==============================================================================
# ACTION REQUIRED: Please edit these variables to match your environment.
# ==============================================================================
export PROJECT_ID="project-orion-admins"
export REGION="asia-northeast1"
export GITHUB_REPO_OWNER="ps012025"
export GITHUB_REPO_NAME="orion-system"
export GITHUB_TOKEN="<>"
# ==============================================================================

# Naming Conventions
export GCS_BUCKET_NAME="${PROJECT_ID}-orion-raw-storage"
export BQ_DATASET_NAME="orion_datalake"
export SERVICE_ACCOUNT_NAME="orion-service-account"
export SECRET_FINNHUB_API_KEY="finnhub-api-key"
export PUBSUB_TOPIC_INGEST="raw-urls-ingest"
export PUBSUB_TOPIC_FILTERED="filtered-urls-for-analysis"

log() {
  echo "✅ - $1"
}

enable_apis() {
    log "Enabling necessary GCP APIs..."
    gcloud services enable cloudresourcemanager.googleapis.com iam.googleapis.com run.googleapis.com cloudfunctions.googleapis.com cloudbuild.googleapis.com pubsub.googleapis.com bigquery.googleapis.com storage.googleapis.com secretmanager.googleapis.com --project="${PROJECT_ID}"
}

setup_iam() {
    log "Setting up IAM service account: ${SERVICE_ACCOUNT_NAME}..."
    export SERVICE_ACCOUNT_EMAIL="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
    if ! gcloud iam service-accounts describe "${SERVICE_ACCOUNT_EMAIL}" --project="${PROJECT_ID}" &>/dev/null; then
        gcloud iam service-accounts create "${SERVICE_ACCOUNT_NAME}" --display-name="Service Account for Orion System" --project="${PROJECT_ID}"
    fi
    log "Assigning necessary roles to service account..."
    ROLES=("roles/pubsub.publisher" "roles/run.invoker" "roles/cloudfunctions.invoker" "roles/bigquery.dataEditor" "roles/bigquery.jobUser" "roles/storage.objectAdmin" "roles/secretmanager.secretAccessor" "roles/cloudbuild.builds.builder")
    for role in "${ROLES[@]}"; do
        gcloud projects add-iam-policy-binding "${PROJECT_ID}" --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" --role="$role" --condition=None > /dev/null
    done
    log "IAM roles assigned."
}

setup_secrets() {
    log "Setting up Secret Manager for API keys..."
    if ! gcloud secrets describe ${SECRET_FINNHUB_API_KEY} --project="${PROJECT_ID}" &>/dev/null; then
        if [ ! -f "finnhub.secret" ]; then
            echo "🚨 ERROR: 'finnhub.secret' file not found."
            exit 1
        fi
        gcloud secrets create ${SECRET_FINNHUB_API_KEY} --data-file="finnhub.secret" --project="${PROJECT_ID}"
    fi
    gcloud secrets add-iam-policy-binding ${SECRET_FINNHUB_API_KEY} --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" --role="roles/secretmanager.secretAccessor" --project="${PROJECT_ID}" > /dev/null
    log "Secret '${SECRET_FINNHUB_API_KEY}' is ready."
}

setup_data_platform() {
    log "Setting up data platform components..."
    if ! gsutil ls -b "gs://${GCS_BUCKET_NAME}" &>/dev/null; then
        gsutil mb -l "${REGION}" "gs://${GCS_BUCKET_NAME}"
    fi
    if ! bq --location=${REGION} show --dataset "${PROJECT_ID}:${BQ_DATASET_NAME}" &>/dev/null; then
        bq --location=${REGION} mk --dataset --description "Orion Datalake" "${PROJECT_ID}:${BQ_DATASET_NAME}"
    fi
    if ! gcloud pubsub topics describe "${PUBSUB_TOPIC_INGEST}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
        gcloud pubsub topics create "${PUBSUB_TOPIC_INGEST}" --project="${PROJECT_ID}"
    fi
    if ! gcloud pubsub topics describe "${PUBSUB_TOPIC_FILTERED}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
        gcloud pubsub topics create "${PUBSUB_TOPIC_FILTERED}" --project="${PROJECT_ID}"
    fi
    log "Data platform (GCS, BQ, Pub/Sub) is ready."
}

main() {
    log "Starting Orion System v8.2 deployment for project: ${PROJECT_ID}"
    gcloud config set project "${PROJECT_ID}"
    enable_apis
    setup_iam
    setup_secrets
    setup_data_platform
    log "Cloning repository..."
    if [ -d "${GITHUB_REPO_NAME}" ]; then
        rm -rf "${GITHUB_REPO_NAME}"
    fi
    git clone "https://ps012025:${GITHUB_TOKEN}@github.com/ps012025/orion-system.git"
    cd "${GITHUB_REPO_NAME}"
    log "Copying new cloudbuild.yaml into the repository..."
    cp ../cloudbuild.yaml .
    log "Committing and pushing the final CI/CD pipeline..."
    git config --global user.email "gemini-cli@google.com"
    git config --global user.name "Gemini CLI"
    git add cloudbuild.yaml
    git commit -m "Feat(ci): Final version of monorepo-aware CI/CD pipeline"
    git push origin master
    log "🚀 Orion System v8.2 GitOps pipeline is now fully configured! 🚀"
    log "Future changes pushed to the 'master' branch will now be deployed automatically."
}

main
branch will now be deployed automatically."
}

main
