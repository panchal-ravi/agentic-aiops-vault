# agentic-ai-vault Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-10-22

## Active Technologies
- Python 3.11+ + FastMCP (MCP server framework), boto3 (AWS SDK), botocore (AWS core library) (002-cloudwatch-logs-filter)
- N/A (CloudWatch Logs API only) (002-cloudwatch-logs-filter)
- Python 3.12 (already configured in vault-agent directory) + strands-agents[openai] (AWS Strands Agent SDK), streamlit (web UI), streamable_httpclient (MCP integration) (003-vault-pki-query-agent)
- N/A (stateless queries against Vault and CloudWatch) (003-vault-pki-query-agent)

- Python 3.11+ + FastMCP (MCP server framework), hvac (HashiCorp Vault Python SDK), cryptography (X.509 certificate parsing) (001-vault-pki-mcp-tools)

## Project Structure

```text
src/
tests/
```

## Commands

cd src [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style

Python 3.11+: Follow standard conventions

## Recent Changes
- 003-vault-pki-query-agent: Added Python 3.12 (already configured in vault-agent directory) + strands-agents[openai] (AWS Strands Agent SDK), streamlit (web UI), streamable_httpclient (MCP integration)
- 002-cloudwatch-logs-filter: Added Python 3.11+ + FastMCP (MCP server framework), boto3 (AWS SDK), botocore (AWS core library)

- 001-vault-pki-mcp-tools: Added Python 3.11+ + FastMCP (MCP server framework), hvac (HashiCorp Vault Python SDK), cryptography (X.509 certificate parsing)

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
