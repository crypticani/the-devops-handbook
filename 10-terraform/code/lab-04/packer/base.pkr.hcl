# A golden image, built locally with the Docker builder so this lab costs nothing.
#
# Everything here maps one-to-one onto the amazon-ebs builder you'd use for an AMI: same
# sources → provisioners → post-processors shape, same reproducibility problems, same fixes.

packer {
  required_plugins {
    docker = {
      version = ">= 1.0.9"
      source  = "github.com/hashicorp/docker"
    }
  }
}

variable "base_image" {
  type = string
  # ⚠️ A TAG, not a digest — deliberately. Break It scenario 1 is about what that costs,
  # and how to resolve and pin the real digest yourself.
  default     = "python:3.12-slim"
  description = "Base image to bake on top of. Pass a digest to make builds reproducible."
}

variable "image_version" {
  type        = string
  default     = "dev"
  description = "Immutable tag for the built image. In CI this is the git SHA."
}

variable "git_commit" {
  type        = string
  default     = "unknown"
  description = "Stamped into the image so any running container traces back to a commit."
}

source "docker" "base" {
  image  = var.base_image
  commit = true # keep the container's final state as an image

  changes = [
    "USER appuser",
    "WORKDIR /app",
    "EXPOSE 8080",
    "ENV APP_HOME=/app",
    "LABEL org.opencontainers.image.revision=${var.git_commit}",
    "LABEL platform.base-version=${var.image_version}",
    "ENTRYPOINT [\"/usr/local/bin/app-entrypoint\"]",
  ]
}

build {
  name    = "app-base"
  sources = ["source.docker.base"]

  # 1. Bake the slow, shared things: packages, agents, a non-root user.
  provisioner "shell" {
    script = "scripts/install.sh"
    # ⭐ Without this the script runs under a shell that doesn't stop on error, and a
    # failed install produces a SUCCESSFUL build of a broken image. Scenario 3.
    execute_command = "/bin/sh -euxc '{{ .Path }}'"
  }

  # 2. Verify before the image is allowed to exist. A build that only proves "the
  #    commands exited" proves nothing about the image you're about to deploy fleet-wide.
  provisioner "shell" {
    script          = "scripts/verify.sh"
    execute_command = "/bin/sh -euxc '{{ .Path }}'"
  }

  # 3. Tag immutably. `latest` here is what makes scenario 4 possible.
  post-processor "docker-tag" {
    repository = "app-base"
    tags       = [var.image_version]
  }

  # 4. Machine-readable output for whatever consumes the image next.
  post-processor "manifest" {
    output     = "manifest.json"
    strip_path = true
    custom_data = {
      base_image = var.base_image
      git_commit = var.git_commit
    }
  }
}
