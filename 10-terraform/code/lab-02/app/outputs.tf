output "bucket_name" {
  description = "Name of the application data bucket"
  value       = aws_s3_bucket.app_data.id
}

output "bucket_arn" {
  description = "ARN of the application data bucket"
  value       = aws_s3_bucket.app_data.arn
}
