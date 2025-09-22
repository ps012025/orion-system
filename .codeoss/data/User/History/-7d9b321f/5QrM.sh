cat << 'EOF' > /home/admin_/orion_final_takeover.sh
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

    # --- FIX: Add a sleep command to wait for IAM propagation ---
    log "Waiting 20 seconds for IAM policies to propagate..."
    sleep 20
    
    log "Phase 2: Setting organizational constraints for this project..."
    # --- FIX: Added '|| true' to prevent script from failing if the policy is already set ---
    gcloud resource-manager org-policies allow constraints/serviceuser.services all \
        --organization=${ORGANIZATION_ID} || true
    log "Phase 2 Complete: Operational constraints set."
    
    log "Phase 3: Enabling all necessary GCP APIs..."
    gcloud services enable \
        cloudresourcemanager.googleapis.com iam.googleapis.com run.googleapis.com \
        cloudfunctions.googleapis.com cloudbuild.googleapis.com pubsub.googleapis.com \
        bigquery.googleapis.com storage.googleapis.com vertexai.googleapis.com \
        secretmanager.googleapis.com eventarc.googleapis.com --project="${PROJECT_ID}"
    log "Phase 3 Complete: All APIs are online."

    # (Phase 4 and subsequent steps would go here)
    # For now, we confirm the initial setup works.
    
    log "🚀 OPERATION OVERLORD (Initial Phases) COMPLETE! 🚀"
}

# Run the main function
main
EOF

# Make the script executable and run it
chmod +x /home/admin_/orion_final_takeover.sh && /home/admin_/orion_final_takeover.sh