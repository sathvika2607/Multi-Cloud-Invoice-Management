# ☁️ Cloud Invoice Sync

Automatically collects invoice PDFs from **GCP, AWS, Azure, and OCI** from a corporate Gmail inbox and organizes them in Google Drive — eliminating manual invoice downloading and organization.

## 🚀 Overview

Cloud Invoice Sync is a serverless Python automation system that periodically searches a Gmail inbox for cloud-provider billing invoices, downloads the PDF attachments, extracts billing information, and stores the invoices in a structured Google Drive hierarchy.

The system is designed to be **reliable, repeatable, and secure**, with duplicate detection, centralized secret management, Infrastructure as Code, and automated scheduling.

## ✨ Key Features

* 📧 Automatically searches Gmail for cloud-provider invoice emails
* 📄 Downloads invoice PDF attachments
* 🔍 Extracts billing period and invoice amount using PDF parsing
* ☁️ Supports **GCP, AWS, Azure, and OCI**
* 📁 Automatically organizes invoices in Google Drive by provider and year
* ♻️ Skips invoices that have already been processed
* ⏰ Runs automatically twice daily using Google Cloud Scheduler
* 🐳 Uses Docker for containerized execution
* ☁️ Runs as a **Google Cloud Run Job**
* 🏗️ Uses **Terraform** for Infrastructure as Code
* 🔐 Stores credentials and secrets securely in **Google Secret Manager**
* 📊 Provides Cloud Run and Cloud Logging integration for monitoring

## 🏗️ Architecture

```text
Cloud Provider Invoice Emails
        │
        ▼
     Gmail API
        │
        ▼
 Google Cloud Scheduler
        │
        ▼
  Google Cloud Run Job
        │
        ├── Search Gmail
        ├── Download PDF
        ├── Extract invoice data
        ├── Validate provider
        └── Check duplicates
        │
        ▼
    Google Drive API
        │
        ▼
   Cloud_Invoices/
   ├── GCP/
   │   └── 2026/
   ├── AWS/
   │   └── 2026/
   ├── Azure/
   │   └── 2026/
   └── OCI/
       └── 2026/

        +
        │
        ▼
 Google Secret Manager
        │
        ▼
   Secure Credentials
```

## 🛠️ Technology Stack

* **Python 3.12+**
* **Gmail API**
* **Google Drive API**
* **Google Cloud Run Jobs**
* **Google Cloud Scheduler**
* **Google Secret Manager**
* **Google Artifact Registry**
* **Docker**
* **Terraform**
* **pdfplumber**
* **Google Cloud Logging**
* **Git/GitHub**

## 🔄 How It Works

1. Cloud Scheduler triggers the Cloud Run Job twice daily.
2. The Python application searches Gmail for invoice emails from supported cloud providers.
3. Invoice PDF attachments are downloaded.
4. `pdfplumber` extracts relevant information such as the billing period and invoice total.
5. Provider-specific rules determine how the invoice should be processed.
6. The system checks whether the invoice already exists in Google Drive.
7. New invoices are uploaded using a consistent naming convention.
8. Existing invoices are skipped, making the process safe to run repeatedly.
9. Cloud Run and Cloud Logging provide execution monitoring.

## 🔐 Security

* OAuth credentials are stored in **Google Secret Manager**.
* Gmail access uses the `gmail.readonly` scope.
* Google Drive access uses the restricted `drive.file` scope.
* Cloud Run uses a dedicated service account with required IAM permissions.
* Sensitive credentials are never baked into the Docker image.
* OAuth and client-secret files are excluded from Git using `.gitignore`.

## 📂 Repository Structure

```text
cloud-invoice-sync/
│
├── job/
│   ├── main.py
│   ├── gmail_client.py
│   ├── drive_client.py
│   ├── providers.py
│   ├── pdf_parser.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── scripts/
│       └── get_oauth_token.py
│
└── infra/
    └── terraform/
        ├── main.tf
        ├── variables.tf
        ├── terraform.tfvars
        ├── apis.tf
        ├── iam.tf
        ├── artifact_registry.tf
        ├── secret_manager.tf
        ├── cloud_run.tf
        └── scheduler.tf
```

## 💡 Why This Project?

Managing invoices across multiple cloud providers can require repetitive manual work. This project demonstrates how **Python automation, APIs, serverless computing, Docker, Terraform, and secure cloud infrastructure** can be combined to create a reliable end-to-end workflow.

## 🔮 Future Enhancements

* AI-powered invoice classification
* OCR support for scanned invoices
* Invoice anomaly detection
* Cloud spending analytics dashboard
* Automated invoice reconciliation
* Email notifications for processing failures
* Additional cloud-provider integrations

## 👩‍💻 Author

**Sathvika Mahamkali**

B.Tech – Computer Science and Engineering
R.V.R & J.C College of Engineering
