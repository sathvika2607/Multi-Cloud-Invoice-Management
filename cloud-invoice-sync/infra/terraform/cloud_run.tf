resource "google_cloud_run_v2_job" "invoice_sync" {
  name     = "cloud-invoice-sync"
  location = var.region
  project  = var.project_id

  template {
    template {
      service_account = google_service_account.invoice_sync_runner.email

      containers {
        image = "${var.region}-docker.pkg.dev/${var.project_id}/cloud-invoice-sync/invoice-sync-job:${var.image_tag}"

        env {
          name = "GMAIL_OAUTH_JSON"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.gmail_oauth.secret_id
              version = "latest"
            }
          }
        }

        env {
          name = "DRIVE_ROOT_FOLDER_ID"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.drive_folder_id.secret_id
              version = "latest"
            }
          }
        }

        resources {
          limits = {
            cpu    = "1"
            memory = "512Mi"
          }
        }
      }

      max_retries = 1
      timeout     = "600s"
    }
  }

  depends_on = [
    google_project_service.required,
    google_artifact_registry_repository.invoice_sync,
  ]
}
