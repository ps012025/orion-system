import os
import json
from google.cloud import secretmanager
from google_auth_oauthlib.flow import Flow

# --- Configuration ---
CLIENT_SECRETS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'credentials.json')
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
PROJECT_ID = "thinking-orb-438805-q7"
REFRESH_TOKEN_SECRET_ID = "orion-calendar-refresh-token"
CLIENT_SECRET_SECRET_ID = "orion-calendar-client-secret"

def generate_and_store_tokens_manual():
    if not os.path.exists(CLIENT_SECRETS_FILE):
        print(f"FATAL: Client secrets file not found at '{CLIENT_SECRETS_FILE}'")
        return

    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri='urn:ietf:wg:oauth:2.0:oob'
    )

    auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')

    print("--- Manual Authorization Required for Google Calendar ---")
    print("Please open the following URL in your browser:")
    print("\n" + auth_url + "\n") # Changed from f-string to avoid syntax issues
    print("After granting permissions, you will be given an authorization code.")
    
    code = input("Please enter the authorization code here: ").strip()

    try:
        flow.fetch_token(code=code)
    except Exception as e:
        print(f"\nFATAL: Failed to fetch token. Error: {e}")
        return

    credentials = flow.credentials
    refresh_token = credentials.refresh_token

    if not refresh_token:
        print("\nFATAL: Could not obtain a refresh token.")
        return

    print("\n--- Authorization Successful ---")
    print("A refresh token for Google Calendar has been obtained.")

    print("\n--- Storing Secrets in Secret Manager ---")
    try:
        with open(CLIENT_SECRETS_FILE, 'r') as f:
            client_secrets_content = f.read()
        
        store_secret(PROJECT_ID, REFRESH_TOKEN_SECRET_ID, refresh_token)
        store_secret(PROJECT_ID, CLIENT_SECRET_SECRET_ID, client_secrets_content)

        print("\n--- Setup Complete ---")
        print("Credentials for calendar importer have been securely stored.")

    except Exception as e:
        print(f"\nFATAL: An error occurred while storing secrets: {e}")

def store_secret(project_id, secret_id, payload):
    client = secretmanager.SecretManagerServiceClient()
    parent = f"projects/{project_id}/secrets/{secret_id}"
    try:
        client.get_secret(request={"name": parent})
    except Exception:
        print(f"Secret '{secret_id}' not found. Creating it now...")
        client.create_secret(
            request={
                "parent": f"projects/{project_id}",
                "secret_id": secret_id,
                "secret": {"replication": {"automatic": {}}},
            }
        )
        print(f"Secret '{secret_id}' created.")
    response = client.add_secret_version(
        request={"parent": parent, "payload": {"data": payload.encode("UTF-8")}}
    )
    print(f"Successfully stored new version for secret '{secret_id}'.")

if __name__ == "__main__":
    print("===================================================================")
    print(" Orion Calendar Importer - One-Time Credential Setup (Manual)")
    print("===================================================================")
    generate_and_store_tokens_manual()
