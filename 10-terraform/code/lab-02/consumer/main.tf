terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
  backend "s3" {
    key     = "lab-02/consumer/terraform.tfstate"
    encrypt = true
  }
}

provider "aws" {
  region = var.region
}

# ⭐ Read the OTHER stack's outputs — read-only, no ability to modify it
data "terraform_remote_state" "app" {
  backend = "s3"
  config = {
    bucket = var.state_bucket
    key    = "lab-02/app/terraform.tfstate"
    region = var.region
  }
}

# Use a value produced by the other stack
resource "aws_s3_object" "marker" {
  bucket  = data.terraform_remote_state.app.outputs.bucket_name
  key     = "consumer/marker.txt"
  content = "written by the consumer stack at ${timestamp()}\n"

  lifecycle {
    ignore_changes = [content] # timestamp() changes every plan
  }
}

output "referenced_bucket" {
  value = data.terraform_remote_state.app.outputs.bucket_name
}
