#!/bin/bash
set -e
set -u
set -o pipefail

log() {
    echo "✅ [$(date +'%Y-%m-%dT%H:%M:%S%z')] - $1"
}

# --- Configuration ---
export PROJECT_ID="project-orion-admins"
export REGION="asia-northeast1"
export SERVICE_ACCOUNT_NAME="orion-service-account"
export GITHUB_REPO_OWNER="ps012025"
export GITHUB_REPO_NAME="orion-system"
export TRIGGER_NAME="orion-main-branch-trigger-v4"
export SECRET_GITHUB_TOKEN="github-pat"
export ORGANIZATION_ID="132668944065"

# --- Utility Functions ---
enable_apis() {
    log "Enabling all necessary GCP APIs for project: ${PROJECT_ID}..."
    gcloud services enable \
        cloudresourcemanager.googleapis.com iam.googleapis.com run.googleapis.com \
        cloudfunctions.googleapis.com cloudbuild.googleapis.com pubsub.googleapis.com \
        bigquery.googleapis.com storage.googleapis.com vertexai.googleapis.com \
        secretmanager.googleapis.com eventarc.googleapis.com --project="${PROJECT_ID}"
}

setup_iam() {
    log "Setting up IAM service account and roles..."
    export SERVICE_ACCOUNT_EMAIL="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
    if ! gcloud iam service-accounts describe "${SERVICE_ACCOUNT_EMAIL}" --project="${PROJECT_ID}" &>/dev/null; then
        gcloud iam service-accounts create "${SERVICE_ACCOUNT_NAME}" --display-name="Service Account for Orion System" --project="${PROJECT_ID}"
    fi
    ROLES=(
        "roles/pubsub.publisher" "roles/run.invoker" "roles/cloudfunctions.invoker"
        "roles/bigquery.dataEditor" "roles/bigquery.jobUser" "roles/storage.objectAdmin"
        "roles/secretmanager.secretAccessor" "roles/cloudbuild.builds.builder"
        "roles/eventarc.eventReceiver" "roles/logging.logWriter" "roles/iam.serviceAccountUser"
    )
    for role in "${ROLES[@]}"; do
        gcloud projects add-iam-policy-binding "${PROJECT_ID}" --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" --role="$role" --condition=None > /dev/null
    done
    
    # Correctly get the GCS service agent and grant permissions
    log "Granting Pub/Sub publish permission to the GCS service agent..."
    export GCS_SERVICE_AGENT=$(gcloud storage service-agent --project="${PROJECT_ID}")
    gcloud projects add-iam-policy-binding "${PROJECT_ID}" --member="serviceAgent:${GCS_SERVICE_AGENT}" --role="roles/pubsub.publisher" > /dev/null || log "GCS service agent pub/sub permission may already exist."
    
    log "All IAM roles assigned."
}

setup_secrets() {
    log "Setting up Secret Manager for GitHub token..."
    if ! gcloud secrets describe ${SECRET_GITHUB_TOKEN} --project="${PROJECT_ID}" &>/dev/null; then
        echo "Please enter your GitHub Personal Access Token (PAT) with repo scope:"
        read -s GITHUB_TOKEN
        echo -n "${GITHUB_TOKEN}" | gcloud secrets create ${SECRET_GITHUB_TOKEN} --data-file=- --project="${PROJECT_ID}"
    fi
    log "GitHub token secret is configured."
}

create_trigger() {
    log "Creating new Cloud Build trigger..."
    # Delete trigger if it exists to ensure a clean state
    gcloud beta builds triggers delete "${TRIGGER_NAME}" --region="${REGION}" --quiet || true
    
    gcloud beta builds triggers create github \
        --name="${TRIGGER_NAME}" \
        --repo-owner="${GITHUB_REPO_OWNER}" \
        --repo-name="${GITHUB_REPO_NAME}" \
        --branch-pattern="^master$" \
        --build-config="cloudbuild.yaml" \
        --region="${REGION}" \
        --service-account="projects/${PROJECT_ID}/serviceAccounts/${SERVICE_ACCOUNT_EMAIL}"
}

# --- Main Execution ---
main() {
    log "STARTING OPERATION OVERLORD: Taking full control of project ${PROJECT_ID}..."
    gcloud config set project "${PROJECT_ID}"

    log "Phase 1: Granting Omnipotence to admin@project-orion-hq.dev..."
    gcloud organizations add-iam-policy-binding "${ORGANIZATION_ID}" \
        --member="user:admin@project-orion-hq.dev" \
        --role="roles/resourcemanager.organizationAdmin" --condition=None > /dev/null || log "Organization Admin role already exists."
    gcloud organizations add-iam-policy-binding "${ORGANIZATION_ID}" \
        --member="user:admin@project-orion-hq.dev" \
        --role="roles/orgpolicy.policyAdmin" --condition=None > /dev/null || log "Org Policy Admin role already exists."
    gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
        --member="user:admin@project-orion-hq.dev" \
        --role="roles/owner" --condition=None > /dev/null || log "Project Owner role already exists."
    log "Phase 1 Complete: Full administrative power asserted."
    
    log "Phase 2: Setting organizational constraints for this project..."
    # Added '|| true' to prevent script from failing if the policy is already set
    gcloud resource-manager org-policies allow constraints/serviceuser.services all \
        --organization=${ORGANIZATION_ID} || true
    log "Phase 2 Complete: Operational constraints set."
    
    log "Phase 3 & 4: Setting up core infrastructure and CI/CD pipeline..."
    
    # Call utility functions to perform setup
    enable_apis
    setup_iam
    setup_secrets
    create_trigger

    log "Cloning repository and pushing initial config..."
    cd ~
    rm -rf "${GITHUB_REPO_NAME}"
    export GITHUB_TOKEN_VALUE=$(gcloud secrets versions access latest --secret="${SECRET_GITHUB_TOKEN}" --project="${PROJECT_ID}")
    git clone "https://ps012025:${GITHUB_TOKEN_VALUE}@github.com/${GITHUB_REPO_OWNER}/${GITHUB_REPO_NAME}.git"
    cd "${GITHUB_REPO_NAME}"

    # Create the essential cloudbuild.yaml file before trying to add it
    log "Creating the final cloudbuild.yaml in the repository..."
    cat << 'EOCB' > cloudbuild.yaml
steps:
- name: 'gcr.io/cloud-builders/git'
  id: 'detect-changes'
  entrypoint: 'bash'
  args:
  - '-c'
  - |
    git fetch origin master
    # Get a list of changed directories within microservices/
    git diff --name-only origin/master~1 HEAD | grep 'microservices/' | cut -d/ -f1-2 | sort -u > /workspace/changed_services.txt
    if [ -s /workspace/changed_services.txt ]; then
      echo "Detected changes in the following services:"
      cat /workspace/changed_services.txt
    else
      echo "No changes detected in any microservice."
    fi

- name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
  id: 'deploy-services'
  entrypoint: 'bash'
  args:
  - '-c'
  - |
    if [ ! -s /workspace/changed_services.txt ]; then
      echo "No changes to deploy."
      exit 0
    fi
    while read -r SERVICE_DIR; do
      SERVICE_NAME=$(basename "$SERVICE_DIR")
      echo "--- Deploying $SERVICE_NAME ---"
      # For now, we assume all are Cloud Run services for simplicity.
      # A full implementation would have dynamic command construction based on service type.
      gcloud run deploy "$SERVICE_NAME" --source="$SERVICE_DIR" --region="asia-northeast1" \
        --service-account="${SERVICE_ACCOUNT_EMAIL}" --no-allow-unauthenticated \
        --set-env-vars=GCP_PROJECT=${PROJECT_ID} &
    done < /workspace/changed_services.txt
    wait
options:
  logging: CLOUD_LOGGING_ONLY
EOCB

    log "Committing and pushing the final CI/CD pipeline..."
    git config --global user.email "ci-bot@orion-system.dev"
    git config --global user.name "Orion CI Bot"
    git add cloudbuild.yaml
    git commit -m "Feat(ci): Final self-healing CI/CD pipeline v8.3.3"
    git push origin master
    
    log "🚀 OPERATION OVERLORD COMPLETE: System is fully operational. 🚀"
}

# Run the main function
main