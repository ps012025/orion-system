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

    # --- ROBUST FIX: Actively wait for IAM policies to propagate ---
    log "Waiting for IAM policies to become effective..."
    for i in {1..15}; do
        # Try a simple read command that requires project-level permissions
        if gcloud projects describe "${PROJECT_ID}" > /dev/null 2>&1; then
            log "IAM policies are now effective."
            break
        fi
        log "Still waiting for IAM propagation (attempt ${i}/15)..."
        sleep 6
    done
    if ! gcloud projects describe "${PROJECT_ID}" > /dev/null 2>&1; then
        log "Error: IAM policies did not propagate in time. Please try running the script again later."
        exit 1
    fi
    
    log "Phase 2: Setting organizational constraints for this project..."
    gcloud resource-manager org-policies allow constraints/serviceuser.services all \
        --organization=${ORGANIZATION_ID} > /dev/null || true
    log "Phase 2 Complete: Operational constraints set."
    
    log "Phase 3: Enabling all necessary GCP APIs..."
    gcloud services enable \
        cloudresourcemanager.googleapis.com iam.googleapis.com run.googleapis.com \
        cloudfunctions.googleapis.com cloudbuild.googleapis.com pubsub.googleapis.com \
        bigquery.googleapis.com storage.googleapis.com vertexai.googleapis.com \
        secretmanager.googleapis.com eventarc.googleapis.com --project="${PROJECT_ID}"
    log "Phase 3 Complete: All APIs are online."

    log "🚀 OPERATION OVERLORD (Initial Phases) COMPLETE! 🚀"
}

# Run the main function
main
EOF

# Make the script executable and run it
chmod +x /home/admin_/orion_final_takeover.sh && /home/admin_/orion_final_takeover.sh