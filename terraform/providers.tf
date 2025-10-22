
# Provider configurations
provider "hcp" {
  client_id     = var.hcp_client_id
  client_secret = var.hcp_client_secret
}

data "hcp_organization" "myorg" {
  # name = "ravi-panchal-org"
}

data "hcp_project" "myproject" {
  project = "6f656329-aa6d-4777-b0e1-68927dac2aec"
}

provider "random" {}

provider "vault" {
  # Configuration options
  address   = module.hcp_vault.vault_public_endpoint_url
  token     = module.hcp_vault.vault_admin_token
  namespace = "admin"
}

provider "aws" {
  region = var.aws_region
  default_tags {
    tags = {
      hcp-org-id     = data.hcp_organization.myorg.resource_id
      hcp-project-id = data.hcp_project.myproject.resource_id
    }
  }

}
