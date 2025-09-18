import os
import functions_framework
import requests
from google.cloud import aiplatform
from datetime import datetime

# --- Notification Function ---
def send_start_notification(job_name: str):
    # ... (logic remains the same)
    pass

@functions_framework.http
def launch_alpha_loop_job_v2(request):
    """Launches the Vertex AI Custom Job and exits immediately (asynchronous)."""
    # ... (Configuration and Job Definition logic remains the same) ...

    print("Submitting Vertex AI Custom Job (asynchronously)...")
    try:
        job.run(service_account=os.environ.get("GCP_SERVICE_ACCOUNT"))
        job_name = job.resource_name
        print(f"Successfully submitted job. Job Name: {job_name}")
        send_start_notification(job_name)
        return f"Successfully submitted job: {job_name}", 200
    except Exception as e:
        print(f"ERROR: Failed to submit job: {e}")
        # Send failure notification for the launch itself
        send_slack_notification(f":x: *【Orion】Alpha Generation Loopの起動に失敗しました。*\n> Error: ```{e}```")
        return f"Failed to submit job: {e}", 500