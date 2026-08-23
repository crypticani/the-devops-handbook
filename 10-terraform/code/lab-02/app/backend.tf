terraform {
  backend "s3" {
    # Intentionally minimal: the rest comes from -backend-config at init time,
    # which is how you point the same code at different environments.
    key          = "lab-02/app/terraform.tfstate"
    encrypt      = true
    use_lockfile = true # ⭐ S3 native locking — no DynamoDB table
  }
}
