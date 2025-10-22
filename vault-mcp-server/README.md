# Vault PKI MCP Server

Model Context Protocol server for HashiCorp Vault PKI secrets engine operations.

## Overview

This MCP server provides tool functions to interact with HashiCorp Vault PKI secrets engines:

1. **List PKI Secrets Engines**: Discover all PKI mount points in your Vault instance
2. **List Certificates**: View certificate hierarchies organized by root and intermediate CAs, with expiration and revocation status

## Prerequisites

- **Python**: Version 3.11 or higher
- **HashiCorp Vault**: Version 1.12.0+ with at least one PKI secrets engine enabled
- **Vault Token**: Valid authentication token with appropriate permissions

### Required Vault Permissions

Your Vault token must have the following capabilities:

```hcl
# List all secrets engines
path "sys/mounts" {
  capabilities = ["read"]
}

# List certificates in PKI mount
path "pki/certs" {
  capabilities = ["list"]
}

# Read certificate details
path "pki/cert/*" {
  capabilities = ["read"]
}

# Read issuer details
path "pki/issuer/*" {
  capabilities = ["read"]
}
```

Replace `pki` with your actual PKI mount path(s).

## Installation

### 1. Clone Repository

```bash
git clone <repository-url>
cd vault-mcp-server
```

### 2. Install Dependencies

```bash
# Using uv (recommended)
uv sync

# Install with development dependencies
uv sync --dev
```

### 3. Set Environment Variables

```bash
export VAULT_ADDR="https://vault.example.com:8200"
export VAULT_TOKEN="hvs.CAES..."

# Optional: Skip TLS verification (development only - NOT for production)
export VAULT_SKIP_VERIFY="false"
```

### 4. Verify Connection

```bash
python -c "import hvac; client = hvac.Client(); print('Vault Status:', client.sys.read_health_status())"
```

Expected output: `Vault Status: {'initialized': True, 'sealed': False, ...}`

## Usage

### Starting the MCP Server

```bash
# Run the MCP server
python main.py

# With custom configuration (if supported)
python main.py --host 0.0.0.0 --port 8080
```

### Available Tools

#### 1. list_pki_secrets_engines

List all PKI secrets engines in your Vault instance.

**Parameters**: None

**Example Response**:
```json
{
  "pki_engines": [
    {
      "path": "pki",
      "type": "pki",
      "description": "Root CA for production environment",
      "config": {
        "default_lease_ttl": 86400,
        "max_lease_ttl": 31536000
      }
    }
  ]
}
```

#### 2. list_certificates

View all certificates from a PKI engine, grouped by CA hierarchy.

**Parameters**:
- `pki_mount_path` (required): Mount path of the PKI secrets engine (e.g., "pki")

**Example Response**:
```json
{
  "hierarchy": {
    "root_issuers": [
      {
        "root_cn": "Root CA",
        "intermediate_groups": [
          {
            "intermediate_cn": "Intermediate CA",
            "certificates": [
              {
                "serial_number": "39:4e:fa:01:23:45:67:89",
                "subject_cn": "webserver.example.com",
                "is_expired": false,
                "is_revoked": false
              }
            ]
          }
        ]
      }
    ],
    "metadata": {
      "total_certificates": 1,
      "expired_count": 0,
      "revoked_count": 0
    }
  }
}
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `VAULT_ADDR` | Yes | None | Vault server URL (e.g., `https://vault.example.com:8200`) |
| `VAULT_TOKEN` | Yes | None | Vault authentication token |
| `VAULT_SKIP_VERIFY` | No | `false` | Skip TLS certificate verification (dev only) |
| `VAULT_NAMESPACE` | No | None | Vault Enterprise namespace |

## Development

### Install Development Dependencies

```bash
uv sync --dev
```

### Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_vault_client.py
```

### Code Formatting

```bash
# Format code with black
black .

# Lint with ruff
ruff check .

# Auto-fix linting issues
ruff check --fix .
```

## Troubleshooting

### Error: "Vault connection failed"

**Cause**: Cannot reach Vault server

**Solution**:
1. Verify VAULT_ADDR: `echo $VAULT_ADDR`
2. Test connectivity: `curl -k $VAULT_ADDR/v1/sys/health`
3. Check firewall and network access

### Error: "Authentication failed"

**Cause**: Invalid or expired VAULT_TOKEN

**Solution**:
1. Check token: `vault token lookup`
2. Renew token: `vault token renew`
3. Create new token with correct policies

### Error: "Permission denied"

**Cause**: Token lacks required capabilities

**Solution**:
1. Review required permissions in Prerequisites section
2. Update Vault policy to grant necessary capabilities
3. Attach policy to token or create new token

## Security Best Practices

1. **Least Privilege**: Grant Vault tokens only minimum required capabilities
2. **Token Rotation**: Regularly rotate VAULT_TOKEN and use short TTLs
3. **TLS Verification**: Always enable TLS verification in production (`VAULT_SKIP_VERIFY=false`)
4. **Secrets Management**: Never hardcode tokens; use environment variables or secrets managers
5. **Audit Logging**: Enable Vault audit logs to track certificate access
6. **Network Isolation**: Run MCP server on internal network, not exposed to public internet

## Project Structure

```
vault-mcp-server/
├── main.py                    # MCP server entry point
├── pyproject.toml            # Dependencies and configuration
├── README.md                 # This file
├── src/
│   ├── tools/                # MCP tool definitions
│   ├── services/             # Business logic (Vault client, parsers)
│   └── models/               # Pydantic data models
└── tests/
    ├── unit/                 # Unit tests
    └── integration/          # Integration tests
```

## License

[Your License Here]

## Support

For issues and questions:
- **Documentation**: See `/specs/001-vault-pki-mcp-tools/` for detailed specifications
- **Issue Tracker**: [Link to issue tracker]
- **Vault API Docs**: https://developer.hashicorp.com/vault/api-docs/secret/pki
- **MCP Protocol**: https://modelcontextprotocol.io/docs
