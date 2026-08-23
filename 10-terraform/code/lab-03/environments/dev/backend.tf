terraform {
  required_version = ">= 1.10.0" # ⭐ use_lockfile needs 1.10+
  required_providers {
    aws    = { source = "hashicorp/aws", version = "~> 5.0" }
    random = { source = "hashicorp/random", version = "~> 3.6" }
  }
  backend "s3" {
    key          = "lab-03/dev/terraform.tfstate" # ⭐ separate state per environment
    encrypt      = true
    use_lockfile = true # ⭐ S3 native locking — no DynamoDB table
  }
}
