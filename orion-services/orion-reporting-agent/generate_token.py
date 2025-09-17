import os
import json
from google.cloud import secretmanager
from google_auth_oauthlib.flow import Flow

# --- Configuration ---
CLIENT_SECRETS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'credentials.json')
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
PROJECT_ID = "thinking-orb-438805-q7"
REFRESH_TOKEN_SECRET_ID = "orion-reporting-refresh-token"
CLIENT_SECRET_SECRET_ID = "orion-reporting-client-secret"
# ------------------------------------

def generate_and_store_tokens_manual():
    """
    Performs a manual OAuth 2.0 flow and stores the resulting refresh token.
    This avoids using helpers that may fail in some environments.
    """
    if not os.path.exists(CLIENT_SECRETS_FILE):
        print(f"FATAL: Client secrets file not found at '{CLIENT_SECRETS_FILE}'")
        return

    # Create a Flow instance from the client secrets file
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri='urn:ietf:wg:oauth:2.0:oob' # Out-of-band redirect URI for console apps
    )

    # Generate the authorization URL
    auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')

    print("--- Manual Authorization Required ---")
    print("Please open the following URL in your browser:")
    print(f"\n{auth_url}\n")
    print("After granting permissions, you will be given an authorization code.")
    
    # Prompt the user to enter the authorization code
    code = input("Please enter the authorization code here: ").strip()

    # Exchange the code for credentials
    try:
        flow.fetch_token(code=code)
    except Exception as e:
        print(f"\nFATAL: Failed to fetch token. Error: {e}")
        print("Please ensure you copied the code correctly.")
        return

    credentials = flow.credentials
    refresh_token = credentials.refresh_token

    if not refresh_token:
        print("\nFATAL: Could not obtain a refresh token.")
        return

    print("\n--- Authorization Successful ---")
    print("A refresh token has been obtained.")

    # Store secrets in Secret Manager
    print("\n--- Storing Secrets in Secret Manager ---")
    try:
        with open(CLIENT_SECRETS_FILE, 'r') as f:
            client_secrets_content = f.read()
        
        store_secret(PROJECT_ID, REFRESH_TOKEN_SECRET_ID, refresh_token)
        store_secret(PROJECT_ID, CLIENT_SECRET_SECRET_ID, client_secrets_content)

        print("\n--- Setup Complete ---")
        print("Credentials have been securely stored in Secret Manager.")

    except Exception as e:
        print(f"\nFATAL: An error occurred while storing secrets: {e}")

def store_secret(project_id, secret_id, payload):
    """Stores a payload as a new version in the specified secret."""
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
    print(f"Successfully stored new version for secret '{secret_id}' (version: {response.name.split('/')[-1]}).")

if __name__ == "__main__":
    print("===================================================================")
    print(" Orion Reporting Agent - One-Time Credential Setup Utility (Manual)")
    print("===================================================================")
    generate_and_store_tokens_manual()