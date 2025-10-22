# Create HVN (HashiCorp Virtual Network)
resource "hcp_hvn" "main" {
  hvn_id         = var.hvn_id
  cloud_provider = "aws"
  region         = var.hvn_region
  cidr_block     = var.hvn_cidr_block
}

# Create HCP Vault Plus cluster
resource "hcp_vault_cluster" "main" {
  cluster_id      = var.vault_cluster_id
  hvn_id          = hcp_hvn.main.hvn_id
  tier            = var.vault_tier
  public_endpoint = true

  audit_log_config {
    cloudwatch_access_key_id     = aws_iam_access_key.hcp_vault_log_user.id
    cloudwatch_secret_access_key = aws_iam_access_key.hcp_vault_log_user.secret
    cloudwatch_region            = var.hvn_region
  }

  lifecycle {
    prevent_destroy = false
  }
}

# Get admin token for the Vault cluster
resource "hcp_vault_cluster_admin_token" "main" {
  cluster_id = hcp_vault_cluster.main.cluster_id
}

locals {
  my_email = split("/", data.aws_caller_identity.current.arn)[2]
}


data "aws_caller_identity" "current" {}

data "aws_region" "current" {}
data "aws_iam_policy" "demo_user_permissions_hcp_vault_log" {
  name = "DemoUser"
}

resource "aws_iam_user" "hcp_vault_log_user" {
  name                 = "demo-${local.my_email}-hcpvaultlog"
  permissions_boundary = data.aws_iam_policy.demo_user_permissions_hcp_vault_log.arn
  force_destroy        = true


}

resource "aws_iam_user_policy_attachment" "hcp_vault_log" {
  user       = aws_iam_user.hcp_vault_log_user.name
  policy_arn = aws_iam_policy.hcp_vault_log_policy.arn
}


resource "aws_iam_policy" "hcp_vault_log_policy" {
  name        = "hcp-vault-log-policy"
  description = "HCP Vault log policy"

  # Terraform's "jsonencode" function converts a
  # Terraform expression result to valid JSON syntax.
  policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Sid" : "HCPLogStreaming",
        "Effect" : "Allow",
        "Action" : [
          "logs:PutLogEvents",
          "logs:DescribeLogStreams",
          "logs:DescribeLogGroups",
          "logs:CreateLogStream",
          "logs:CreateLogGroup",
          "logs:TagLogGroup"
        ],
        "Resource" : "*"
      }
    ]
  })
}

resource "aws_iam_access_key" "hcp_vault_log_user" {
  user = aws_iam_user.hcp_vault_log_user.name
}
