# Quickstart Guide: Vault PKI MCP Tools

**Last Updated**: 2025-10-22  
**Target Audience**: Developers, DevOps Engineers, Security Auditors

## Overview

Vault PKI MCP Tools provide Model Context Protocol (MCP) tool functions to interact with HashiCorp Vault PKI secrets engines. These tools enable AI agents and applications to:

1. **List PKI Secrets Engines**: Discover all PKI mount points in your Vault instance
2. **List Certificates**: View certificate hierarchies organized by root and intermediate CAs, with expiration and revocation status

## Prerequisites

### Required

- **HashiCorp Vault**: Version 1.12.0 or higher with at least one PKI secrets engine enabled
- **Python**: Version 3.11 or higher
- **Environment Variables**:
  - `VAULT_ADDR`: Vault server address (e.g., `https://vault.example.com:8200`)
  - `VAULT_TOKEN`: Valid Vault authentication token with appropriate permissions

### Vault Permissions

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

Replace `pki` with your actual PKI mount path(s). Repeat for multiple PKI engines.

## Installation

### 1. Clone Repository

```bash
git clone https://github.com/your-org/vault-mcp-server.git
cd vault-mcp-server
```

### 2. Install Dependencies

```bash
# Using uv (recommended)
uv sync

# Install development dependencies
uv sync --dev
```

### 3. Set Environment Variables

```bash
export VAULT_ADDR="https://vault.example.com:8200"
export VAULT_TOKEN="hvs.CAES..."

# Optional: Skip TLS verification for development (NOT for production)
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
python vault-mcp-server/main.py

# With custom host/port
python vault-mcp-server/main.py --host 0.0.0.0 --port 8080
```

The server will start and register two MCP tools:
- `list_pki_secrets_engines`
- `list_certificates`

### Tool 1: List PKI Secrets Engines

**Purpose**: Retrieve all PKI secrets engines in your Vault instance

**Parameters**: None

**Example MCP Request** (via MCP client):

```json
{
  "method": "tools/call",
  "params": {
    "name": "list_pki_secrets_engines",
    "arguments": {}
  }
}
```

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
    },
    {
      "path": "pki_int",
      "type": "pki",
      "description": "Intermediate CA",
      "config": {
        "default_lease_ttl": 86400,
        "max_lease_ttl": 2592000
      }
    }
  ]
}
```

### Tool 2: List Certificates

**Purpose**: View all certificates from a PKI engine, grouped by CA hierarchy

**Parameters**:
- `pki_mount_path` (required, string): Mount path of the PKI secrets engine (e.g., "pki", "pki_int")

**Example MCP Request**:

```json
{
  "method": "tools/call",
  "params": {
    "name": "list_certificates",
    "arguments": {
      "pki_mount_path": "pki"
    }
  }
}
```

**Example Response**:

```json
{
  "hierarchy": {
    "root_issuers": [
      {
        "root_cn": "Root CA",
        "root_issuer_id": "b2c3d4e5-6789-01bc-def0-234567890abc",
        "intermediate_groups": [
          {
            "intermediate_cn": "Intermediate CA",
            "intermediate_issuer_id": "a1b2c3d4-5678-90ab-cdef-1234567890ab",
            "certificates": [
              {
                "serial_number": "39:4e:fa:01:23:45:67:89",
                "subject_cn": "webserver.example.com",
                "issuer_cn": "Intermediate CA",
                "not_before": "2024-01-01T00:00:00Z",
                "not_after": "2025-01-01T00:00:00Z",
                "is_expired": false,
                "is_revoked": false
              }
            ]
          }
        ],
        "direct_certificates": []
      }
    ],
    "warnings": [],
    "metadata": {
      "total_certificates": 1,
      "expired_count": 0,
      "revoked_count": 0,
      "root_ca_count": 1,
      "intermediate_ca_count": 1
    }
  }
}
```

## Common Use Cases

### 1. Audit Expired Certificates

```python
# Using MCP client library
from mcp import Client

client = Client("http://localhost:8080")
result = client.call_tool("list_certificates", {"pki_mount_path": "pki"})

# Filter expired certificates
expired = [
    cert for group in result["hierarchy"]["root_issuers"]
    for int_group in group["intermediate_groups"]
    for cert in int_group["certificates"]
    if cert["is_expired"]
]

print(f"Found {len(expired)} expired certificates")
```

### 2. Security Compliance Check

```python
# Check for revoked certificates
result = client.call_tool("list_certificates", {"pki_mount_path": "pki"})
revoked_count = result["hierarchy"]["metadata"]["revoked_count"]

if revoked_count > 0:
    print(f"Warning: {revoked_count} revoked certificates still in system")
```

### 3. Certificate Inventory Report

```python
# Generate inventory report across all PKI engines
engines = client.call_tool("list_pki_secrets_engines", {})

for engine in engines["pki_engines"]:
    result = client.call_tool("list_certificates", {"pki_mount_path": engine["path"]})
    metadata = result["hierarchy"]["metadata"]
    
    print(f"\nPKI Engine: {engine['path']}")
    print(f"  Total Certificates: {metadata['total_certificates']}")
    print(f"  Expired: {metadata['expired_count']}")
    print(f"  Revoked: {metadata['revoked_count']}")
    print(f"  Root CAs: {metadata['root_ca_count']}")
    print(f"  Intermediate CAs: {metadata['intermediate_ca_count']}")
```

## Troubleshooting

### Error: "Vault connection failed"

**Cause**: Cannot reach Vault server at VAULT_ADDR

**Solution**:
1. Verify VAULT_ADDR is correct: `echo $VAULT_ADDR`
2. Test connectivity: `curl -k $VAULT_ADDR/v1/sys/health`
3. Check firewall rules and network access

### Error: "Authentication failed"

**Cause**: VAULT_TOKEN is invalid or expired

**Solution**:
1. Verify token is set: `echo $VAULT_TOKEN` (should not be empty)
2. Check token validity: `vault token lookup`
3. Renew token: `vault token renew` or generate new token
4. Ensure token has required permissions (see Vault Permissions above)

### Error: "Permission denied"

**Cause**: Token lacks required capabilities for the operation

**Solution**:
1. Review required permissions in Prerequisites section
2. Check current token policies: `vault token lookup -format=json | jq .data.policies`
3. Update Vault policy to grant necessary capabilities
4. Attach policy to token or create new token with correct policy

### Error: "PKI mount path not found"

**Cause**: Specified PKI mount does not exist or is not type "pki"

**Solution**:
1. List all secrets engines: Call `list_pki_secrets_engines` tool
2. Verify mount path exists in returned list
3. Check mount type is "pki" (not "kv" or other types)
4. Use exact path from list (without leading/trailing slashes)

### Partial Results with Warnings

**Behavior**: Tool returns certificates but includes warnings array

**Cause**: Token has permission to list certificates but not read some individual certificates or issuers

**Solution**:
1. Check warnings array in response for specific resources
2. Update Vault policy to grant read access to those paths
3. Alternatively, accept partial results if some certificates are intentionally restricted

### Empty Certificate List

**Cause**: PKI mount has no issued certificates OR all certificates are inaccessible due to permissions

**Solution**:
1. Verify certificates exist using Vault CLI: `vault list pki/certs`
2. If CLI shows certificates, check token permissions for `<pki>/cert/*` read capability
3. If no certificates exist, issue test certificate: `vault write pki/issue/example common_name=test.example.com`

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `VAULT_ADDR` | Yes | None | Vault server URL (e.g., `https://vault.example.com:8200`) |
| `VAULT_TOKEN` | Yes | None | Vault authentication token |
| `VAULT_SKIP_VERIFY` | No | `false` | Skip TLS certificate verification (dev only) |
| `VAULT_NAMESPACE` | No | None | Vault Enterprise namespace |
| `MCP_HOST` | No | `127.0.0.1` | MCP server bind address |
| `MCP_PORT` | No | `8080` | MCP server port |

### Performance Tuning

For large certificate inventories (>1000 certificates):

```bash
# Increase connection pool size
export VAULT_MAX_CONNECTIONS=50

# Adjust request timeout
export VAULT_TIMEOUT=30
```

## Integration Examples

### Claude Desktop (MCP Client)

Add to Claude Desktop's MCP configuration:

```json
{
  "mcpServers": {
    "vault-pki": {
      "command": "python",
      "args": ["/path/to/vault-mcp-server/main.py"],
      "env": {
        "VAULT_ADDR": "https://vault.example.com:8200",
        "VAULT_TOKEN": "hvs.CAES..."
      }
    }
  }
}
```

### GitHub Copilot Chat

```typescript
// Use MCP client in VS Code extension
import { MCPClient } from '@modelcontextprotocol/sdk';

const client = new MCPClient({
  serverUrl: 'http://localhost:8080'
});

const result = await client.callTool('list_certificates', {
  pki_mount_path: 'pki'
});
```

### Custom Python Application

```python
import requests

MCP_SERVER = "http://localhost:8080"

def list_pki_engines():
    response = requests.post(f"{MCP_SERVER}/tools/call", json={
        "name": "list_pki_secrets_engines",
        "arguments": {}
    })
    return response.json()

def list_certificates(mount_path):
    response = requests.post(f"{MCP_SERVER}/tools/call", json={
        "name": "list_certificates",
        "arguments": {"pki_mount_path": mount_path}
    })
    return response.json()
```

## Security Best Practices

1. **Least Privilege**: Grant Vault tokens only the minimum required capabilities
2. **Token Rotation**: Regularly rotate VAULT_TOKEN and use short TTLs
3. **TLS Verification**: Always enable TLS verification in production (`VAULT_SKIP_VERIFY=false`)
4. **Secrets Management**: Never hardcode tokens; use environment variables or secrets management systems
5. **Audit Logging**: Enable Vault audit logs to track certificate access
6. **Network Isolation**: Run MCP server on internal network, not exposed to public internet

## Next Steps

1. **Configure Vault Policies**: Set up granular policies for different user roles
2. **Automate Certificate Audits**: Schedule periodic certificate expiration checks
3. **Integrate with Monitoring**: Send alerts for expired/revoked certificates
4. **Explore Advanced Features**: Multi-level intermediate CA hierarchies, CRL checking
5. **Read Full Documentation**: See [data-model.md](data-model.md) and [contracts/mcp-tools.json](contracts/mcp-tools.json)

## Support & Resources

- **Vault API Documentation**: https://developer.hashicorp.com/vault/api-docs/secret/pki
- **MCP Protocol Specification**: https://modelcontextprotocol.io/docs
- **hvac SDK Documentation**: https://hvac.readthedocs.io/
- **Issue Tracker**: https://github.com/your-org/vault-mcp-server/issues

## License

[Your License Here]

---

**Document Version**: 1.0.0  
**Last Reviewed**: 2025-10-22
