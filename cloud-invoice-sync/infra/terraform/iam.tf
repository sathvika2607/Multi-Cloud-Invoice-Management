resource "google_service_account" "invoice_sync_runner" {
  account_id   = "invoice-sync-runner"
  display_name = "Cloud Invoice Sync Runner"
  project      = var.project_id

  depends_on = [google_project_service.required]
}

# Allow the runner to read the two secrets it needs at runtime.
resource "google_secret_manager_secret_iam_member" "gmail_oauth_access" {
  secret_id = google_secret_manager_secret.gmail_oauth.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.invoice_sync_runner.email}"
  project   = var.project_id
}

resource "google_secret_manager_secret_iam_member" "drive_folder_id_access" {
  secret_id = google_secret_manager_secret.drive_folder_id.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.invoice_sync_runner.email}"
  project   = var.project_id
}
