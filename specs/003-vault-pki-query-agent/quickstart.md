# Quickstart: Vault PKI Query Agent

## Prerequisites

- Python 3.12+ with `uv` package manager
- Running HashiCorp Vault with PKI secrets engines configured
- Running vault-mcp-server (see vault-mcp-server/README.md)
- Valid Vault token with read permissions for PKI engines and audit logs
- AWS credentials configured for CloudWatch access (for audit queries)

## Installation

```bash
# Navigate to the vault-agent directory
cd vault-agent

# Install dependencies using uv
uv sync

# Activate the virtual environment
source .venv/bin/activate
```

## Configuration

Create a `.env` file in the `vault-agent` directory:

```bash
# Vault Configuration
VAULT_ADDR=https://your-vault-instance.com
VAULT_TOKEN=your-vault-token

# MCP Server Configuration  
MCP_SERVER_URL=http://localhost:8000

# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key

# AWS Configuration (for audit queries)
AWS_REGION=us-east-1
AWS_LOG_GROUP_NAME=/aws/vault/audit
AWS_LOG_STREAM_NAMES=vault-audit-stream-1,vault-audit-stream-2
```

## Quick Start

### 1. Start the Streamlit Web Interface

```bash
# From the vault-agent directory
streamlit run main.py
```

The web interface will be available at `http://localhost:8501`

### 2. Try Example Queries

Click on any of the example prompts in the web interface, or type queries like:

**Certificate Expiration Monitoring:**
- "Show me all certificates expiring in next 30 days"
- "List certificates expiring in the next week"

**Revocation Status:**
- "Show all revoked certificates"
- "List revoked certificates from last month"

**PKI Engine Queries:**
- "List all certificates from pki_int engine"
- "Show certificates issued by the root CA"

**Audit Trail Investigation:**
- "Show audit events for web.example.com certificate"
- "Who issued the api.example.com certificate?"

### 3. Understanding Results

The agent returns structured results with:
- **Certificate information**: Common name, expiration status, PKI engine
- **Audit events**: Who performed operations and when
- **Operational insights**: Days until expiry, revocation status

## Architecture Overview

```
User Query → Streamlit UI → Strands Agent → Query Processor 
                ↓
         Natural Language Processing → Query Pattern Matching
                ↓
         MCP Client → vault-mcp-server → HashiCorp Vault
                ↓                    ↓
         Certificate Data ←    Audit Events (CloudWatch)
                ↓
         Structured Results → UI Display
```

## Supported Query Patterns

| Pattern | Example | MCP Tools Used |
|---------|---------|----------------|
| Expiration Check | "expiring in next 30 days" | `list_certificates` |
| Revocation Status | "show revoked certificates" | `list_certificates` |
| PKI Engine Filter | "certificates from pki_int" | `list_pki_secrets_engines`, `list_certificates` |
| Audit Trail | "audit events for cert.example.com" | `filter_pki_audit_events` |
| Issuer Attribution | "who issued cert.example.com" | `filter_pki_audit_events` |

## Error Handling

Common errors and solutions:

**"Cannot connect to Vault MCP server"**
- Verify vault-mcp-server is running on configured port
- Check MCP_SERVER_URL in .env file

**"No certificates found"**
- Verify PKI engines are configured and contain certificates
- Check Vault token permissions for PKI read access

**"Audit events not found"**
- Verify AWS CloudWatch access and log group configuration
- Ensure Vault audit logging is enabled and forwarded to CloudWatch

## Development

### Running Tests

```bash
# Run all tests
uv run pytest

# Run specific test modules
uv run pytest tests/test_agent.py
uv run pytest tests/test_mcp_client.py
```

### Code Structure

```
vault-agent/
├── main.py                    # Streamlit application entry point
├── src/
│   ├── agent/                 # Core agent implementation
│   ├── ui/                    # Streamlit UI components
│   ├── mcp/                   # MCP client integration
│   └── models/                # Data models and types
└── tests/                     # Test suite
```

### Adding New Query Patterns

1. Define pattern in `src/agent/query_processor.py`
2. Add pattern matching logic
3. Implement MCP tool mapping
4. Add example to `src/ui/example_prompts.py`
5. Write tests in `tests/test_query_processor.py`

## Performance Notes

- Certificate queries typically complete in <10 seconds
- Audit queries may take 10-15 seconds due to CloudWatch log scanning
- Results are not cached - each query hits live data sources
- UI is optimized for up to 1000 certificate results (POC scope)

## Security Considerations

- No authentication in web UI - relies on network-level access controls
- Vault token stored in environment variable
- AWS credentials use standard AWS credential chain
- All queries are read-only operations
- Query history stored only in browser session (not persisted)