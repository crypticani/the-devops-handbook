variable "region" {
  type    = string
  default = "us-east-1"
}

variable "state_bucket" {
  description = "Bucket holding the shared Terraform state"
  type        = string
}
