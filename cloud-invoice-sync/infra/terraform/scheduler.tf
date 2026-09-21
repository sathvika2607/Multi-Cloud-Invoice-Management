resource "google_service_account" "scheduler_invoker" {
  account_id   = "invoice-sync-scheduler"
  display_name = "Cloud Invoice Sync Scheduler Invoker"
  project      = var.project_id

  depends_on = [google_project_service.required]
}

resource "google_cloud_run_v2_job_iam_member" "scheduler_can_invoke" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_job.invoice_sync.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.scheduler_invoker.email}"
}

resource "google_cloud_scheduler_job" "invoice_sync_trigger" {
  name      = "cloud-invoice-sync-trigger"
  project   = var.project_id
  region    = var.region
  schedule  = var.scheduler_cron
  time_zone = var.scheduler_timezone

  http_target {
    http_method = "POST"
    uri         = "https://${var.region}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${var.project_id}/jobs/${google_cloud_run_v2_job.invoice_sync.name}:run"

    oauth_token {
      service_account_email = google_service_account.scheduler_invoker.email
    }
  }

  depends_on = [google_project_service.required]
}
