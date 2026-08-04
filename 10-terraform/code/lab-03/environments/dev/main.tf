provider "aws" {
  region = var.region
  default_tags {
    tags = {
      Environment = "dev"
      Repo        = "the-devops-handbook"
    }
  }
}

variable "region" {
  type    = string
  default = "us-east-1"
}

module "app_data" {
  source = "../../modules/bucket"

  name        = "handbook-appdata"
  environment = "dev"

  versioning_enabled = false # dev doesn't need it
  force_destroy      = true  # ⭐ safe in dev, so cleanup is easy

  lifecycle_rules = {
    transition_to_ia_days = 7
    expiration_days       = 30 # dev data is disposable
  }

  tags = { CostCentre = "engineering" }
}

output "bucket" {
  value = module.app_data.id
}
