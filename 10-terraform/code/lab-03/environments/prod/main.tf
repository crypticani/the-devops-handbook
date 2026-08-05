provider "aws" {
  region = var.region
  default_tags {
    tags = {
      Environment = "prod"
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
  environment = "prod"

  versioning_enabled = true  # ⭐ prod keeps history
  force_destroy      = false # ⭐ terraform destroy CANNOT wipe it

  lifecycle_rules = {
    transition_to_ia_days      = 90
    transition_to_glacier_days = 365
    expiration_days            = 0 # never expire prod data
  }

  tags = { CostCentre = "platform", Compliance = "sox" }
}

output "bucket" {
  value = module.app_data.id
}
