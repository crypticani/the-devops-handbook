# The consumer side of the bake. Terraform never builds an image — it takes the one Packer
# published and runs it. The interface between the two tools is a single immutable tag.
#
# This uses the Docker provider so the lab is free; with the AWS provider the shape is
# identical — a data source resolves the image, a launch template references it.

terraform {
  required_version = ">= 1.5"
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
    }
  }
}

provider "docker" {}

variable "image_version" {
  type        = string
  description = "The exact tag Packer built. Never 'latest' — see Break It scenario 4."

  validation {
    # ⭐ A guardrail, not a style preference: a mutable tag makes rollback impossible,
    # because the thing you would roll back TO has already been overwritten.
    condition     = var.image_version != "latest"
    error_message = "Refusing a mutable tag. Pass the version Packer stamped (e.g. the git SHA)."
  }
}

variable "replicas" {
  type        = number
  default     = 2
  description = "How many containers to run from the baked image."
}

# Resolve the tag to a digest ONCE, here. Every container below is pinned to that digest,
# so a rebuild of the tag mid-apply cannot give you a mixed fleet.
data "docker_image" "app_base" {
  name = "app-base:${var.image_version}"
}

resource "docker_container" "app" {
  count = var.replicas

  name  = "app-${count.index}"
  image = data.docker_image.app_base.repo_digest # ⭐ the digest, not the tag

  command = ["sleep", "3600"]
  restart = "unless-stopped"

  # Proof, from outside the image, that the baked defaults survived.
  labels {
    label = "platform.base-version"
    value = var.image_version
  }
}

output "image_digest" {
  description = "What is actually running. Put this in your deploy record."
  value       = data.docker_image.app_base.repo_digest
}

output "running" {
  value = [for c in docker_container.app : c.name]
}
