# General variables
variable "resource_prefix" {
  description = "Prefix for all resource names"
  type        = string
  default     = "ai"
  validation {
    condition     = can(regex("^[a-zA-Z][a-zA-Z0-9-]*[a-zA-Z0-9]$", var.resource_prefix)) && length(var.resource_prefix) <= 20
    error_message = "Resource prefix must start with a letter, contain only alphanumeric characters and hyphens, end with alphanumeric character, and be 20 characters or less."
  }
}

variable "common_tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default = {
    Environment = "dev"
    Project     = "ai-confused-deputy"
    ManagedBy   = "terraform"
  }
}

# HCP variables
variable "hvn_id" {
  description = "The ID of the HVN"
  type        = string
  default     = "ai-vault-hvn"
}

variable "hvn_cidr_block" {
  description = "The CIDR block for the HVN"
  type        = string
  default     = "172.25.16.0/20"
}

variable "hvn_region" {
  description = "The region where the HVN should be created"
  type        = string
  default     = "ap-southeast-1"
}

variable "vault_cluster_id" {
  description = "The ID of the Vault cluster"
  type        = string
  default     = "ai-vault-cluster"
}

variable "vault_tier" {
  description = "The tier of the Vault cluster"
  type        = string
  default     = "standard_small"
}

variable "hcp_client_id" {
  description = "HCP client ID"
  type        = string
}

variable "hcp_client_secret" {
  description = "HCP client secret"
  type        = string
}

variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "ap-southeast-1"
}
