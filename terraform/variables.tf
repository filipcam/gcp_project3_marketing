variable "project_id" {
  description = "ID Twojego projektu w GCP"
  type        = string
}

variable "region" {
  description = "Region dla zasobów"
  type        = string
  default     = "europe-central2" # Warszawa
}

variable "zone" {
  description = "Strefa dla VM"
  type        = string
  default     = "europe-central2-a"
}

variable "instance_type" {
  description = "Typ maszyny wirtualnej"
  type        = string
  default     = "e2-standard-2" # e2-small (2GB RAM) okazał się niewystarczający
}

variable "vscode_password" {
  description = "Visual Studio Code admin password"
  type        = string
  default     = "dbtlab"
}


variable "data_bucket_name" {
  description = "Main landing bucket for project data"
  type        = string
}

variable "data_bucket_location" {
  description = "Location for the main data bucket"
  type        = string
  default     = "EUROPE-CENTRAL2"
}
