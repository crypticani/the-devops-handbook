terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  # ⚠️ NEVER put a `provider` block in a module.
  # The caller must control region and credentials.
}
