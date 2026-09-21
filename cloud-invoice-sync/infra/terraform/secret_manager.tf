# Terraform only creates the secret *resources* here. The actual secret
# *values* (OAuth credentials, Drive folder ID) are populated manually --
# see the README ("Populate Secrets"). Keeping values out of Terraform
# state avoids storing credentials in plaintext state files.

resource "google_secret_manager_secret" "gmail_oauth" {
  project   = var.project_id
  secret_id = "cloud-invoice-sync--gmail-oauth"

  replication {
    auto {}
  }

  depends_on = [google_project_service.required]
}

resource "google_secret_manager_secret" "drive_folder_id" {
  project   = var.project_id
  secret_id = "cloud-invoice-sync--drive-folder-id"

  replication {
    auto {}
  }

  depends_on = [google_project_service.required]
}
