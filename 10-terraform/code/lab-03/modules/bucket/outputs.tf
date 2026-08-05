output "id" {
  description = "Bucket name."
  value       = aws_s3_bucket.this.id
}

output "arn" {
  description = "Bucket ARN."
  value       = aws_s3_bucket.this.arn
}

output "domain_name" {
  description = "Regional domain name for the bucket."
  value       = aws_s3_bucket.this.bucket_regional_domain_name
}

output "tags" {
  description = "Tags actually applied, after merging."
  value       = aws_s3_bucket.this.tags_all
}
