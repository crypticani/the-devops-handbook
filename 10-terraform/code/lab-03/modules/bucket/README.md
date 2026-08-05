# Module: bucket

An opinionated, secure-by-default S3 bucket. Public access is always blocked and
encryption is always on — neither is configurable, on purpose.

## Usage

```hcl
module "app_data" {
  source = "../../modules/bucket"

  name        = "myapp-data"
  environment = "prod"

  lifecycle_rules = {
    transition_to_ia_days = 60
    expiration_days       = 365
  }

  tags = { CostCentre = "platform" }
}
```

## Inputs

| Name | Type | Default | Required | Description |
|------|------|---------|:--------:|-------------|
| `name` | `string` | — | yes | Base name; a random suffix is appended |
| `environment` | `string` | — | yes | One of `dev`, `staging`, `prod` |
| `versioning_enabled` | `bool` | `true` | no | Enable object versioning |
| `lifecycle_rules` | `object` | `{}` | no | Transition and expiry days |
| `force_destroy` | `bool` | `false` | no | ⚠️ Never `true` in prod |
| `tags` | `map(string)` | `{}` | no | Merged over the module's own tags |

## Outputs

| Name | Description |
|------|-------------|
| `id` | Bucket name |
| `arn` | Bucket ARN |
| `domain_name` | Regional domain name |
| `tags` | Effective tags after merge |

## Notes

- Public access blocking and encryption are **not** configurable. If you need a
  public bucket, this is the wrong module.
- The module declares no `provider` block; the caller supplies region and credentials.
