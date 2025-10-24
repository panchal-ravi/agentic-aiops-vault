# Vault PKI Query Agent

A natural language interface for HashiCorp Vault PKI operations using AWS Strands Agent SDK and OpenAI.

## Overview

The Vault PKI Query Agent allows users to query Vault PKI secrets engines and audit events using natural language. Built with:

- **AWS Strands Agent SDK**: For AI agent capabilities and tool integration
- **OpenAI Models**: For natural language processing
- **Streamlit**: For the web-based user interface
- **MCP Integration**: Connects to vault-mcp-server for Vault operations

## Features

- Natural language queries for PKI operations
- Certificate expiration monitoring
- Revocation status checking
- PKI engine filtering
- Audit trail investigation
- Issuer attribution

## Quick Start

### Prerequisites

- Python 3.12+
- OpenAI API key
- Running vault-mcp-server
- HashiCorp Vault with PKI engines

### Installation

```bash
# Install dependencies
uv sync

# Create .env file
cp .env.example .env
# Edit .env with your configuration
```

### Environment Variables

```bash
# Required
OPENAI_API_KEY=your-openai-api-key

# Optional (with defaults)
MCP_SERVER_URL=http://localhost:8080/mcp
MCP_AUTH_TOKEN=your-mcp-auth-token
```

### Run the Application

```bash
# Start the Streamlit web interface
streamlit run main.py
```

The application will be available at `http://localhost:8501`

## Usage Examples

- "Show me all certificates expiring in next 30 days"
- "List all revoked certificates"
- "Show certificates from pki_int engine"
- "Who issued web.example.com certificate?"
- "Show audit events for api.example.com"

## Architecture

```
User Query → Streamlit UI → VaultPKIAgent → OpenAI LLM → MCP Tools → Vault
```

The agent uses the OpenAI model to understand natural language queries and automatically selects the appropriate MCP tools to retrieve information from Vault.

## Development

### Running Tests

```bash
uv run pytest
```

### Code Quality

```bash
uv run ruff check .
```

## Configuration

The agent connects to your vault-mcp-server which should be running on `localhost:8080/mcp` by default. Ensure your MCP server has access to:

- Vault PKI secrets engines
- Audit log sources (e.g., CloudWatch)
- Appropriate read permissions

## Security

- No authentication in web UI (relies on network-level access controls)
- Vault access is handled through the MCP server
- All operations are read-only
- Query history is session-only (not persisted)
