terraform {
  required_version = ">= 1.5"
  required_providers {
    hcp = {
      source  = "hashicorp/hcp"
      version = "~> 0.94"
    }
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.9.0"
    }
  }
}
