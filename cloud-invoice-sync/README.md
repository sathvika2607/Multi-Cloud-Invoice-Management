# Cloud Invoice Sync

Automatically collects invoice PDFs from cloud providers (GCP, AWS, Azure, OCI) out of a corporate Gmail inbox and organises them in Google Drive — no manual downloading required.

**How it works:**
1. A scheduled job runs twice daily and searches the Gmail inbox for invoice emails from cloud providers.
2. It downloads the PDF attachment from each email.
3. It reads the PDF to extract the billing period (e.g. March 2026) and invoice total.
4. It uploads the file to Google Drive under a structured folder hierarchy, using a consistent naming convention.
5. If the file is already in Drive, it is skipped — the job is safe to run repeatedly.

**Result in Google Drive:**
```
Cloud_Invoices/
  GCP/
    2026/
      2026-03_GCP_Invoice.pdf
  AWS/
    2026/
      2026-04_AWS_Invoice.pdf
  Azure/
    2026/
  OCI/
    2026/
```

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Repository Layout](#2-repository-layout)
3. [One-Time GCP Setup](#3-one-time-gcp-setup)
4. [One-Time OAuth Token Setup](#4-one-time-oauth-token-setup)
5. [Google Drive Setup](#5-google-drive-setup)
6. [Deploy with Terraform](#6-deploy-with-terraform)
7. [Build and Push the Docker Image](#7-build-and-push-the-docker-image)
8. [Populate Secrets](#8-populate-secrets)
9. [Run and Test](#9-run-and-test)
10. [Day-to-Day Operations](#10-day-to-day-operations)
11. [Adding a New Cloud Provider](#11-adding-a-new-cloud-provider)
12. [Troubleshooting](#12-troubleshooting)

---

## 1. Prerequisites

Install these tools on your laptop before starting.

| Tool | Purpose | Install |
|---|---|---|
| `gcloud` CLI | Interact with GCP | [cloud.google.com/sdk](https://cloud.google.com/sdk/docs/install) |
| `terraform` ≥ 1.5 | Deploy GCP infrastructure | [developer.hashicorp.com/terraform](https://developer.hashicorp.com/terraform/install) |
| `docker` | Build the container image | [docs.docker.com](https://docs.docker.com/get-docker/) |
| `gh` CLI | GitHub operations | [cli.github.com](https://cli.github.com) |
| Python 3.12+ | Run the OAuth setup script | [python.org](https://www.python.org/downloads/) |

Authenticate with GCP:

```bash
gcloud auth login
gcloud config set project YOUR_GCP_PROJECT_ID
```

Confirm you have the right project:

```bash
gcloud projects describe YOUR_GCP_PROJECT_ID
```

---

## 2. Repository Layout

```
cloud-invoice-sync/
├── job/                          # The Cloud Run Job (Python)
│   ├── main.py                   # Entry point — orchestrates Gmail → Drive flow
│   ├── gmail_client.py           # Gmail API: search inbox, download attachments
│   ├── drive_client.py           # Drive API: create folders, upload files
│   ├── providers.py              # Provider definitions: email patterns + PDF parsing rules
│   ├── pdf_parser.py             # PDF text extraction using pdfplumber
│   ├── requirements.txt          # Python dependencies
│   ├── Dockerfile                # Container definition
│   └── scripts/
│       └── get_oauth_token.py    # One-time script to generate Gmail + Drive credentials
└── infra/
    └── terraform/
        ├── main.tf               # Terraform provider config
        ├── variables.tf          # Input variable declarations
        ├── terraform.tfvars      # Variable values (project ID, region, schedule)
        ├── apis.tf               # GCP APIs to enable
        ├── iam.tf                # Service account and IAM roles
        ├── artifact_registry.tf  # Docker image repository
        ├── secret_manager.tf     # Secret placeholders (values set manually)
        ├── cloud_run.tf          # Cloud Run Job definition
        └── scheduler.tf          # Cloud Scheduler trigger (runs the job on a cron)
```

---

## 3. One-Time GCP Setup

This section configures the GCP project. You only need to do this once.

### 3a. Enable APIs via Terraform (done in Step 6)

The Terraform in this repo enables all required APIs automatically. If you want to enable them manually first:

```bash
gcloud services enable \
  gmail.googleapis.com \
  drive.googleapis.com \
  run.googleapis.com \
  cloudscheduler.googleapis.com \
  secretmanager.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  --project=YOUR_GCP_PROJECT_ID
```

### 3b. Create the OAuth consent screen

The OAuth consent screen defines what your application is allowed to request access to.

1. Go to **GCP Console → APIs & Services → OAuth consent screen**
   - URL: `https://console.cloud.google.com/apis/credentials/consent?project=YOUR_GCP_PROJECT_ID`
2. User type: **Internal** (this restricts login to your organization's Google Workspace accounts only — no external review needed)
3. Fill in:
   - App name: `Cloud Invoice Sync`
   - User support email: your email
   - Developer contact email: your email
4. Click **Add or Remove Scopes** and add both of these:
   - `https://www.googleapis.com/auth/gmail.readonly`
   - `https://www.googleapis.com/auth/drive.file`
5. Save and continue.

### 3c. Create an OAuth 2.0 Client ID

This is the identity your application uses when requesting access.

1. Go to **GCP Console → APIs & Services → Credentials**
   - URL: `https://console.cloud.google.com/apis/credentials?project=YOUR_GCP_PROJECT_ID`
2. Click **Create Credentials → OAuth 2.0 Client ID**
3. Application type: **Desktop app**
4. Name: `Cloud Invoice Sync Desktop`
5. Click **Create**, then **Download JSON**
6. Save the downloaded file as `client_secret.json` somewhere safe on your laptop (not in this repo).

---

## 4. One-Time OAuth Token Setup

This step signs in to the Gmail account that receives cloud billing invoices and generates a long-lived credential. **You need to do this from a laptop — it opens a browser window.**

> **MFA note:** If the Gmail account has hardware-key or app-based MFA, you will need to complete it during the browser sign-in below. This is the **only time** MFA is required. After this, the Cloud Run job refreshes its access token automatically — no MFA, no browser, no manual steps.

### 4a. Install the setup dependency

```bash
pip install google-auth-oauthlib
```

### 4b. Run the token script

```bash
python job/scripts/get_oauth_token.py --client-secrets /path/to/client_secret.json
```

A browser window opens. Sign in as the **Gmail account that receives the cloud billing invoices** (not your personal account). Approve the permissions when prompted.

The script saves a file called `gmail_oauth_creds.json` in your current directory. It looks like this (never share this file):

```json
{
  "client_id": "YOUR_CLIENT_ID",
  "client_secret": "YOUR_CLIENT_SECRET",
  "refresh_token": "YOUR_REFRESH_TOKEN"
}
```

### 4c. Upload to Secret Manager

```bash
gcloud secrets versions add cloud-invoice-sync--gmail-oauth \
  --data-file=gmail_oauth_creds.json \
  --project=YOUR_GCP_PROJECT_ID
```

Delete the local file immediately after uploading:

```bash
rm gmail_oauth_creds.json
```

> **Token lifetime:** The refresh token does not expire as long as it is used at least once every 6 months. The Cloud Scheduler runs the job twice daily, so it will never go stale. If the token is ever revoked, re-run steps 4b and 4c.

---

## 5. Google Drive Setup

### 5a. Create the root folder

1. Open **Google Drive** as the same account you used in Step 4.
2. Create a folder named `Cloud_Invoices` (or any name you prefer).
3. Open the folder and copy its ID from the URL:
   ```
   https://drive.google.com/drive/folders/EXAMPLE_FOLDER_ID
                                           ^^^^^^^^^^^^^^^^^^
                                           This is the folder ID
   ```

The job creates all provider and year subfolders automatically — you only need to create the root.

### 5b. Upload the folder ID to Secret Manager

> **Note:** Complete Step 6 (Terraform apply) first so the secret resource exists before adding a version.

```bash
echo -n "YOUR_FOLDER_ID_HERE" | gcloud secrets versions add cloud-invoice-sync--drive-folder-id \
  --data-file=- \
  --project=YOUR_GCP_PROJECT_ID
```

Replace `YOUR_FOLDER_ID_HERE` with the ID you copied from the Drive URL.

---

## 6. Deploy with Terraform

Terraform creates all GCP infrastructure: APIs, service account, Artifact Registry, Secret Manager secrets, Cloud Run Job, and Cloud Scheduler.

```bash
cd infra/terraform

# Authenticate Terraform with GCP
export GOOGLE_OAUTH_ACCESS_TOKEN=$(gcloud auth print-access-token)

# Download providers and initialise state
terraform init

# Preview what will be created (no changes yet)
terraform plan

# Apply — type "yes" when prompted
terraform apply
```

After `apply`, the infrastructure exists but the job **will not run yet** because:
- The Docker image has not been pushed (Step 7)
- The Drive folder ID secret has not been populated (Step 5b)

**Do not skip Step 8 before triggering the job.**

---

## 7. Build and Push the Docker Image

The Cloud Run Job runs from a Docker image stored in Artifact Registry.

```bash
# Configure Docker to push to GCP
gcloud auth configure-docker us-central1-docker.pkg.dev

# Set the image path (matches what Terraform expects)
IMAGE="us-central1-docker.pkg.dev/YOUR_GCP_PROJECT_ID/cloud-invoice-sync/invoice-sync-job:latest"

# Build from the job/ directory
docker build -t "$IMAGE" job/

# Push to Artifact Registry
docker push "$IMAGE"
```

Every time you change the Python code, rebuild and push the image, then the next scheduled run picks up the new version automatically.

---

## 8. Populate Secrets

After Terraform creates the secret resources (Step 6), populate their values.

You should have already done the Gmail OAuth secret in Step 4c. Check it exists:

```bash
gcloud secrets versions list cloud-invoice-sync--gmail-oauth --project=YOUR_GCP_PROJECT_ID
```

Populate the Drive folder ID (Step 5b):

```bash
echo -n "YOUR_FOLDER_ID_HERE" | gcloud secrets versions add cloud-invoice-sync--drive-folder-id \
  --data-file=- --project=YOUR_GCP_PROJECT_ID
```

Verify both secrets have an active version:

```bash
gcloud secrets list --project=YOUR_GCP_PROJECT_ID
```

---

## 9. Run and Test

### Run the job manually (recommended for first test)

```bash
gcloud run jobs execute cloud-invoice-sync \
  --region=us-central1 \
  --project=YOUR_GCP_PROJECT_ID \
  --wait
```

The `--wait` flag streams the exit status. A successful run exits with code 0.

### View logs

```bash
gcloud logging read \
  'resource.type="cloud_run_job" AND resource.labels.job_name="cloud-invoice-sync"' \
  --project=YOUR_GCP_PROJECT_ID \
  --limit=50 \
  --format="table(timestamp, textPayload)"
```

Or view in GCP Console: **Cloud Run → Jobs → cloud-invoice-sync → Logs**

### What to check after the first run

1. **Google Drive**: Open `Cloud_Invoices/` — you should see provider subfolders and PDF files.
2. **Logs**: Look for lines like `Uploaded 2026-03_GCP_Invoice.pdf` and `Sync complete — processed=N`.
3. **Skipped emails**: If you see `No provider match` for a legitimate invoice, you may need to update `providers.py` with the correct sender address (see Section 11).

### Run locally for development

To test without deploying, set the environment variables from the secrets and run directly:

```bash
cd job

pip install -r requirements.txt

export GMAIL_OAUTH_JSON=$(gcloud secrets versions access latest \
  --secret=cloud-invoice-sync--gmail-oauth --project=YOUR_GCP_PROJECT_ID)

export DRIVE_ROOT_FOLDER_ID=$(gcloud secrets versions access latest \
  --secret=cloud-invoice-sync--drive-folder-id --project=YOUR_GCP_PROJECT_ID)

python main.py
```

---

## 10. Day-to-Day Operations

### Schedule

The job runs automatically at **8:00 AM and 8:00 PM Pacific Time** every day, triggered by Cloud Scheduler. You can view or manually trigger it in:
- **GCP Console → Cloud Scheduler → cloud-invoice-sync-trigger**

### Changing the schedule

Edit `infra/terraform/terraform.tfvars`:

```hcl
scheduler_cron     = "0 8,20 * * *"   # change this
scheduler_timezone = "America/Los_Angeles"
```

Then re-run `terraform apply`.

### Rotating the OAuth token

If the refresh token is revoked or expires, re-run Steps 4b and 4c:

```bash
python job/scripts/get_oauth_token.py --client-secrets /path/to/client_secret.json

gcloud secrets versions add cloud-invoice-sync--gmail-oauth \
  --data-file=gmail_oauth_creds.json --project=YOUR_GCP_PROJECT_ID

rm gmail_oauth_creds.json
```

### Deploying code changes

```bash
IMAGE="us-central1-docker.pkg.dev/YOUR_GCP_PROJECT_ID/cloud-invoice-sync/invoice-sync-job:latest"
docker build -t "$IMAGE" job/
docker push "$IMAGE"
```

The next scheduled run uses the new image. To test immediately:

```bash
gcloud run jobs execute cloud-invoice-sync --region=us-central1 --project=YOUR_GCP_PROJECT_ID --wait
```

---

## 11. Adding a New Cloud Provider

All provider logic lives in `job/providers.py`. Adding a new provider requires changes **only in that file**.

### Step 1: Find the sender email address

In Gmail, open one of the invoice emails from the new provider and check the **From** field. Example: `billing@example-provider.com`.

### Step 2: Add a Provider entry

Open `job/providers.py` and add a new entry to the `PROVIDERS` list:

```python
Provider(
    name="NewCloud",                        # Drive folder name — keep it short
    sender_domains=["example-provider.com"], # Substring matched against From address
    subject_keywords=["invoice", "bill"],   # At least one must appear in subject
    period_patterns=[
        # Add a regex that matches the billing period in the PDF.
        # Test by extracting PDF text and running the regex manually.
        r"billing period[:\s]+(\w+ \d{1,2}),?\s+(\d{4})",
        r"(january|february|march|...)\s+(\d{4})",   # fallback month-name pattern
    ],
    amount_patterns=[
        r"(?:total due|amount due)[:\s]+\$?([\d,]+\.\d{2})",
    ],
),
```

### Step 3: Test the regex against a real PDF

```python
import pdfplumber, io, re

pdf_bytes = open("sample_invoice.pdf", "rb").read()
with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
    text = "\n".join(page.extract_text() or "" for page in pdf.pages)

# Test your pattern
m = re.search(r"billing period[:\s]+(\w+ \d{1,2}),?\s+(\d{4})", text, re.IGNORECASE)
print(m.groups() if m else "no match")
```

### Step 4: Rebuild and push

```bash
IMAGE="us-central1-docker.pkg.dev/YOUR_GCP_PROJECT_ID/cloud-invoice-sync/invoice-sync-job:latest"
docker build -t "$IMAGE" job/ && docker push "$IMAGE"
```

---

## 12. Troubleshooting

### "No provider match" in logs

The email sender or subject does not match any entry in `providers.py`.

1. Find the email in Gmail and note the exact **From** address and **Subject**.
2. Open `job/providers.py` and check `sender_domains` and `subject_keywords` for the expected provider.
3. Update them to match the actual email, rebuild, and push.

### "No GCP billing invoice email found" error

The OAuth token may have expired or been revoked. Re-run Steps 4b and 4c to generate and upload a fresh token.

### PDF period parsed as 0-0 (unknown)

The billing period regex did not match the PDF content.

1. Extract the PDF text locally:
   ```python
   import pdfplumber, io
   pdf_bytes = open("invoice.pdf", "rb").read()
   with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
       print("\n".join(p.extract_text() or "" for p in pdf.pages))
   ```
2. Find where the billing period appears in the text.
3. Update the matching `period_patterns` regex in `providers.py`.

The file is still uploaded to Drive even when the period cannot be parsed — the filename defaults to the previous month as a fallback so no invoice is lost.

### Terraform apply fails with "Permission denied"

Re-export your access token (it expires after 1 hour):

```bash
export GOOGLE_OAUTH_ACCESS_TOKEN=$(gcloud auth print-access-token)
terraform apply
```

### Drive upload fails with "File not found" on the root folder

The folder ID stored in Secret Manager is incorrect or the Drive account does not have access to the folder. Verify:
1. The folder ID matches the one in the Drive URL.
2. You are signed in to Drive as the same account used to generate the OAuth token.

---

## Security Notes

- **Never commit `gmail_oauth_creds.json` or `client_secret.json`** — both are in `.gitignore`.
- The OAuth token has `gmail.readonly` scope (read-only inbox) and `drive.file` scope (only files created by this app). No broader access is granted.
- The Cloud Run Job runs as a dedicated service account (`invoice-sync-runner`) with the minimum IAM roles required.
- All secrets are stored in Google Secret Manager and injected at runtime — nothing sensitive is baked into the Docker image.

---

## Contact

For questions about this project, contact your organization's IT Systems team or open an issue in this repository.
