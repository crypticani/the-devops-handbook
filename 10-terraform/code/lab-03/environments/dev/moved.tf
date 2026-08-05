# Refactor migration: keep for one release cycle so every environment
# and every colleague's working copy applies it, then delete.
moved {
  from = module.app_data
  to   = module.application_data
}
