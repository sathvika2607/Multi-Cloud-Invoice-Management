"""
One-time script to generate long-lived OAuth credentials for Gmail + Drive
access. Run this from a laptop -- it opens a browser window for sign-in.

Usage:
    pip install google-auth-oauthlib
    python get_oauth_token.py --client-secrets /path/to/client_secret.json

Produces gmail_oauth_creds.json in the current directory. Upload this to
Secret Manager, then delete the local copy immediately -- see the README
("One-Time OAuth Token Setup").
"""
import argparse
import json

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/drive.file",
]

OUTPUT_FILE = "gmail_oauth_creds.json"


def main():
    parser = argparse.ArgumentParser(description="Generate Gmail + Drive OAuth credentials.")
    parser.add_argument(
        "--client-secrets",
        required=True,
        help="Path to the client_secret.json downloaded from GCP Console.",
    )
    args = parser.parse_args()

    flow = InstalledAppFlow.from_client_secrets_file(args.client_secrets, SCOPES)
    credentials = flow.run_local_server(port=0)

    output = {
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "refresh_token": credentials.refresh_token,
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Saved credentials to {OUTPUT_FILE}")
    print("Upload this to Secret Manager, then delete the local file:")
    print(f"  gcloud secrets versions add cloud-invoice-sync--gmail-oauth --data-file={OUTPUT_FILE}")
    print(f"  rm {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
