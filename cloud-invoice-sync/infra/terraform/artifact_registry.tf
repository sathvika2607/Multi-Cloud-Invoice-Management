resource "google_artifact_registry_repository" "invoice_sync" {
  project       = var.project_id
  location      = var.region
  repository_id = "cloud-invoice-sync"
  description   = "Docker images for the Cloud Invoice Sync job"
  format        = "DOCKER"

  depends_on = [google_project_service.required]
}
