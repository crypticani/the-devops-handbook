variable "name" {
  description = "Base name for the bucket. A suffix is appended for global uniqueness."
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]{1,40}[a-z0-9]$", var.name))
    error_message = "name must be lowercase alphanumeric with hyphens, 3-42 characters."
  }
}

variable "environment" {
  description = "Deployment environment."
  type        = string

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be one of: dev, staging, prod."
  }
}

variable "versioning_enabled" {
  description = "Enable S3 object versioning."
  type        = bool
  default     = true
}

variable "lifecycle_rules" {
  description = "Object lifecycle transitions and expiry."
  type = object({
    transition_to_ia_days      = optional(number, 30)
    transition_to_glacier_days = optional(number, 90)
    expiration_days            = optional(number, 0) # 0 = never expire
  })
  default = {}
}

variable "force_destroy" {
  description = "Allow terraform destroy to delete a non-empty bucket. NEVER true in prod."
  type        = bool
  default     = false
}

variable "tags" {
  description = "Additional tags merged over the module's own."
  type        = map(string)
  default     = {}
}
