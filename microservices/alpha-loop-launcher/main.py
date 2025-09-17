import os
import functions_framework
import requests
import time
from google.cloud import aiplatform
from datetime import datetime

# --- Notification Function ---
def send_slack_notification(text: str):
    """Calls the reporting agent to send a notification to Slack."""
    print(f"Requesting to send Slack notification...")
    try:
        reporting_agent_url = os.environ.get("REPORTING_AGENT_URL")
        if not reporting_agent_url:
            raise ValueError("REPORTING_AGENT_URL environment variable is not set.")

        metadata_server_url = f'http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/identity?audience={reporting_agent_url}'
        token_response = requests.get(metadata_server_url, headers={'Metadata-Flavor': 'Google'})
        token = token_response.text
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
        
        payload = {"slack_message": text}
        
        response = requests.post(reporting_agent_url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        print("Successfully requested Slack notification.")
    except Exception as e:
        print(f"ERROR: Failed to request Slack notification: {e}")

@functions_framework.http
def launch_and_wait_alpha_loop(request):
    """
    Launches the Vertex AI Custom Job, waits for it to complete, 
    and sends start/completion notifications.
    """
    # --- Configuration from Environment Variables ---
    PROJECT_ID = os.environ.get("GCP_PROJECT")
    REGION = os.environ.get("GCP_REGION")
    SERVICE_ACCOUNT = os.environ.get("GCP_SERVICE_ACCOUNT")
    CONTAINER_URI = os.environ.get("CONTAINER_IMAGE_URI")

    if not all([PROJECT_ID, REGION, SERVICE_ACCOUNT, CONTAINER_URI]):
        error_msg = "Missing one or more required environment variables."
        print(f"ERROR: {error_msg}")
        return error_msg, 500

    print("Launcher function triggered. Initializing Vertex AI client...")
    aiplatform.init(project=PROJECT_ID, location=REGION)

    display_name = f'alpha-loop-scheduled-run-{datetime.now().strftime("%Y%m%d-%H%M%S")}'
    job = aiplatform.CustomJob(
        display_name=display_name,
        worker_pool_specs=[{
            "machine_spec": {"machine_type": "n1-standard-4"},
            "replica_count": 1,
            "container_spec": {"image_uri": CONTAINER_URI}
        }],
    )

    print(f"Submitting Vertex AI Custom Job: {display_name}")
    try:
        # --- Submit the Job and Send Start Notification ---
        job.run(service_account=SERVICE_ACCOUNT)
        job_name = job.resource_name
        print(f"Successfully submitted job. Job Name: {job_name}")
        send_slack_notification(f"✅ *【Orion】Alpha Generation Loopを開始しました。*\n> Job Name: `{job_name}`")

        # --- Wait for Job Completion ---
        print("Waiting for job to complete...")
        job.wait() # This blocks until the job is finished

        # --- Send Completion Notification ---
        final_state = job.state.name
        print(f"Job finished with state: {final_state}")

        if final_state == "JOB_STATE_SUCCEEDED":
            slack_message = f"✅ *【Orion】Alpha Generation Loopが正常に完了しました。*\n> Job Name: `{job_name}`"
        elif final_state == "JOB_STATE_FAILED":
            error_message = job.error.message if job.error else "No error details."
            slack_message = f":x: *【Orion】Alpha Generation Loopが失敗しました。*\n> Job Name: `{job_name}`\n> Error: ```{error_message}```"
        else:
            slack_message = f":warning: *【Orion】Alpha Generation Loopが予期せぬ状態で終了しました: {final_state}*\n> Job Name: `{job_name}`"

        send_slack_notification(slack_message)
        return f"Job completed with state: {final_state}", 200

    except Exception as e:
        print(f"ERROR: An error occurred during job execution or notification: {e}")
        send_slack_notification(f":x: *【Orion】Alpha Generation Loopの起動または待機中にエラーが発生しました。*\n> Error: ```{e}```")
        return f"An error occurred: {e}", 500
