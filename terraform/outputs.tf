# Resource naming
output "resource_name_prefix" {
  description = "The generated resource name prefix with random suffix"
  value       = local.name_prefix
}

output "vault_private_endpoint_url" {
  description = "Private endpoint URL of the Vault cluster"
  value       = module.hcp_vault.vault_private_endpoint_url
}

output "vault_public_endpoint_url" {
  description = "Public endpoint URL of the Vault cluster"
  value       = module.hcp_vault.vault_public_endpoint_url
}

output "vault_admin_token" {
  description = "Admin token for the Vault cluster"
  value       = module.hcp_vault.vault_admin_token
  sensitive   = true
}
