locals {
  # The module owns these; the caller can add to them but not remove them.
  common_tags = merge(
    {
      Environment = var.environment
      Module      = "bucket"
      ManagedBy   = "terraform"
    },
    var.tags,
  )
}

resource "random_id" "suffix" {
  byte_length = 4
}

resource "aws_s3_bucket" "this" {
  bucket        = "${var.name}-${var.environment}-${random_id.suffix.hex}"
  force_destroy = var.force_destroy
  tags          = local.common_tags

  lifecycle {
    # ⭐ A module consumer can't accidentally delete a prod bucket by removing
    #    the module block, IF they set force_destroy = false.
    ignore_changes = [tags["LastScanned"]]
  }
}

resource "aws_s3_bucket_public_access_block" "this" {
  bucket                  = aws_s3_bucket.this.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "this" {
  bucket = aws_s3_bucket.this.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_versioning" "this" {
  bucket = aws_s3_bucket.this.id
  versioning_configuration {
    status = var.versioning_enabled ? "Enabled" : "Suspended"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "this" {
  bucket = aws_s3_bucket.this.id
  # Lifecycle config requires versioning to be settled first
  depends_on = [aws_s3_bucket_versioning.this]

  rule {
    id     = "tiering"
    status = "Enabled"
    filter {}

    transition {
      days          = var.lifecycle_rules.transition_to_ia_days
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = var.lifecycle_rules.transition_to_glacier_days
      storage_class = "GLACIER_IR"
    }

    dynamic "expiration" {
      for_each = var.lifecycle_rules.expiration_days > 0 ? [1] : []
      content {
        days = var.lifecycle_rules.expiration_days
      }
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}
