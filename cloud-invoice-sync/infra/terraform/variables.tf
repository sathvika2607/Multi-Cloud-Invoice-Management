variable "project_id" {
  description = "GCP project ID to deploy into."
  type        = string
}

variable "region" {
  description = "GCP region for Cloud Run, Artifact Registry, and Scheduler."
  type        = string
  default     = "us-central1"
}

variable "scheduler_cron" {
  description = "Cron schedule for the invoice sync job."
  type        = string
  default     = "0 8,20 * * *"
}

variable "scheduler_timezone" {
  description = "Timezone for the Cloud Scheduler cron expression."
  type        = string
  default     = "America/Los_Angeles"
}

variable "image_tag" {
  description = "Docker image tag to deploy."
  type        = string
  default     = "latest"
}
