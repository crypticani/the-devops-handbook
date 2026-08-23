terraform {
  required_version = ">= 1.10.0"
  required_providers {
    aws    = { source = "hashicorp/aws", version = "~> 5.0" }
    random = { source = "hashicorp/random", version = "~> 3.6" }
  }
}

provider "aws" {
  region = var.region
  default_tags {
    tags = {
      ManagedBy = "terraform"
      Lab       = "10-terraform-lab-02"
    }
  }
}

resource "random_pet" "suffix" {
  length = 2
}

resource "aws_s3_bucket" "app_data" {
  bucket        = "tf-lab-app-${random_pet.suffix.id}"
  force_destroy = true
}

resource "aws_s3_bucket_public_access_block" "app_data" {
  bucket                  = aws_s3_bucket.app_data.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}


resource "random_password" "db" {
  length  = 24
  special = true
}


resource "time_sleep" "slow" {
  create_duration = "90s"
}
