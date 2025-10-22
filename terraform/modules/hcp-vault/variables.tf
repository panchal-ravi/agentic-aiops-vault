variable "hvn_id" {
  description = "The ID of the HVN"
  type        = string
}

variable "hvn_cidr_block" {
  description = "The CIDR block for the HVN"
  type        = string
}

variable "hvn_region" {
  description = "The region where the HVN should be created"
  type        = string
}

variable "vault_cluster_id" {
  description = "The ID of the Vault cluster"
  type        = string
}

variable "vault_tier" {
  description = "The tier of the Vault cluster (plus, starter_small)"
  type        = string
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
