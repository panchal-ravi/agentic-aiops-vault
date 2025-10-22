# Generate random suffix for unique resource naming
resource "random_string" "suffix" {
  length  = 3
  special = false
  upper   = false
}

# Create resource name prefix with suffix
locals {
  name_prefix = "${var.resource_prefix}-${random_string.suffix.result}"
}

# Module 1: HCP Infrastructure (HVN + Vault)
module "hcp_vault" {
  source = "./modules/hcp-vault"

  hvn_id           = "${local.name_prefix}-${var.hvn_id}"
  hvn_cidr_block   = var.hvn_cidr_block
  hvn_region       = var.hvn_region
  vault_cluster_id = "${local.name_prefix}-${var.vault_cluster_id}"
  vault_tier       = var.vault_tier

  tags = var.common_tags
}
