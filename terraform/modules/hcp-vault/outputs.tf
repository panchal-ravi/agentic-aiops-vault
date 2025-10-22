output "hvn_id" {
  description = "The ID of the HVN"
  value       = hcp_hvn.main.hvn_id
}

output "hvn_self_link" {
  description = "The self link of the HVN"
  value       = hcp_hvn.main.self_link
}

output "hvn_cidr_block" {
  description = "The CIDR block of the HVN"
  value       = hcp_hvn.main.cidr_block
}

output "hvn_region" {
  description = "The region of the HVN"
  value       = hcp_hvn.main.region
}

output "vault_cluster_id" {
  description = "The ID of the Vault cluster"
  value       = hcp_vault_cluster.main.cluster_id
}

output "vault_private_endpoint_url" {
  description = "The private endpoint URL of the Vault cluster"
  value       = hcp_vault_cluster.main.vault_private_endpoint_url
}

output "vault_public_endpoint_url" {
  description = "The public endpoint URL of the Vault cluster"
  value       = hcp_vault_cluster.main.vault_public_endpoint_url
}

output "vault_admin_token" {
  description = "The admin token for the Vault cluster"
  value       = hcp_vault_cluster_admin_token.main.token
  sensitive   = true
}
