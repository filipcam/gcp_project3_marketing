resource "google_bigquery_dataset" "marketing_raw" {
  project    = var.project_id
  dataset_id = "marketing_raw"
  location   = var.region

  friendly_name = "marketing_raw"
  description   = "Raw dataset for Marketing domain in the data mesh project"

  delete_contents_on_destroy = false

  labels = {
    domain      = "marketing"
    layer       = "raw"
    environment = var.environment
    managed_by  = "terraform"
  }
}