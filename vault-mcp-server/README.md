# Vault MCP Server

A Model Context Protocol (MCP) server that provides tools for interacting with HashiCorp Vault PKI engines and AWS CloudWatch Logs. This server offers comprehensive certificate management and log analysis capabilities through a standardized MCP interface.

## Features

### Vault PKI Tools
- **List PKI Engines**: Discover and enumerate PKI secrets engines
- **List Certificates**: Retrieve certificate hierarchies with detailed metadata
- **Certificate Analysis**: Expiration tracking, revocation status, and hierarchy mapping

### CloudWatch Logs Tools  
- **Filter Logs**: Advanced log filtering with pattern matching, time ranges, and log level detection
- **List Log Groups**: Discover available CloudWatch log groups with metadata
- **List Log Streams**: Browse log streams within groups with sorting and filtering

## Installation

### Prerequisites
- Python 3.11+
- Valid Vault token and server access
- AWS credentials (for CloudWatch features)

### Dependencies
```bash
pip install fastmcp hvac cryptography boto3 botocore
```

## Configuration

### Environment Variables

#### Required (Vault)
- `VAULT_ADDR`: Vault server URL (e.g., `https://vault.example.com:8200`)
- `VAULT_TOKEN`: Valid Vault authentication token

#### Optional (Vault)
- `VAULT_SKIP_VERIFY`: Skip TLS verification (default: false, dev only)
- `VAULT_NAMESPACE`: Vault Enterprise namespace
- `MCP_SERVER_HOST`: MCP server host (default: localhost)
- `MCP_SERVER_PORT`: MCP server port (default: 8000)

#### Optional (AWS CloudWatch)
- `AWS_ACCESS_KEY_ID`: AWS access key (or use IAM roles/profiles)
- `AWS_SECRET_ACCESS_KEY`: AWS secret key  
- `AWS_DEFAULT_REGION`: AWS region (default: us-east-1)
- `AWS_PROFILE`: AWS profile name for credentials

## Usage

### Starting the Server
```bash
python main.py
```

### MCP Tools

#### Vault PKI Tools
- `list_pki_engines`: List all PKI secrets engines
- `list_certificates`: Get certificate details from a PKI engine

#### CloudWatch Tools
- `filter_logs`: Filter log events with advanced criteria
- `list_log_groups`: List available CloudWatch log groups
- `list_log_streams`: List log streams within a group

### Example Requests

#### Filter CloudWatch Logs
```json
{
  "tool": "filter_logs",
  "arguments": {
    "log_group_name": "/aws/lambda/my-function",
    "text_pattern": "ERROR",
    "start_time": "2023-10-22T10:00:00Z",
    "max_events": 100
  }
}
```

#### List PKI Certificates
```json
{
  "tool": "list_certificates", 
  "arguments": {
    "pki_mount_path": "pki"
  }
}
```

## Development

### Architecture
```
src/
├── models/          # Data models
│   ├── certificate.py    # Certificate structures
│   ├── pki_engine.py     # PKI engine models
│   └── cloudwatch.py     # CloudWatch models
├── services/        # Business logic
│   ├── vault_client.py        # Vault API client
│   ├── cloudwatch_client.py   # AWS CloudWatch client
│   ├── pattern_matcher.py     # Log pattern matching
│   └── log_filter.py          # Log filtering orchestration
└── tools/           # MCP tool implementations
    ├── list_certificates.py
    ├── list_pki_engines.py
    ├── filter_logs.py
    ├── list_log_groups.py
    └── list_log_streams.py
```

### Testing
```bash
# Install test dependencies
pip install moto pytest

# Run tests
pytest tests/
```
