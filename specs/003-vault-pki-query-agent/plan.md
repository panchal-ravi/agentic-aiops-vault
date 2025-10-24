# Implementation Plan: Vault PKI Query Agent

**Branch**: `003-vault-pki-query-agent` | **Date**: 2025-10-24 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-vault-pki-query-agent/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Build an AI agent that allows users to query Vault PKI secrets engine and audit events related to certificate lifecycle management through natural language queries. The agent will use AWS Strands Agent Python SDK with OpenAI models, provide a Streamlit web interface for POC, and integrate with existing MCP server tools via streamable_httpclient for Vault PKI operations.

## Technical Context

**Language/Version**: Python 3.12 (already configured in vault-agent directory)  
**Primary Dependencies**: strands-agents[openai] (AWS Strands Agent SDK), streamlit (web UI), streamable_httpclient (MCP integration)  
**Storage**: N/A (stateless queries against Vault and CloudWatch)  
**Testing**: pytest (following existing project patterns)  
**Target Platform**: Local development with Streamlit web interface (POC only)
**Project Type**: single (agent application in vault-agent directory)  
**Performance Goals**: <10 seconds for certificate queries, <15 seconds for audit trail queries, responsive UI interactions <2 seconds  
**Constraints**: Query result sets up to 1000 certificates (POC scope), no authentication in web UI (network-level access controls only)  
**Scale/Scope**: POC for 10 concurrent users, 5 distinct natural language query patterns, integration with existing 3 MCP tools

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

✅ **MCP Protocol Compliance**: Agent integrates with existing MCP server tools via streamable_httpclient, maintaining MCP protocol adherence  
✅ **Security-First Design**: Uses existing Vault token authentication, input validation through MCP tools, no additional security exposure  
✅ **API-First Development**: Leverages existing well-defined MCP tool contracts, follows structured error response patterns  
✅ **Dependency Management Standards**: Uses `uv` for Python dependency management (already configured in vault-agent directory)  
✅ **Development Workflow**: POC implementation with basic testing against existing MCP server functionality  

**Post-Design Re-evaluation**:
✅ **MCP Compliance**: Agent design maintains strict MCP protocol usage through streamable_httpclient integration
✅ **Security Controls**: No new security surface introduced - leverages existing Vault authentication and MCP tool validation
✅ **API Contracts**: OpenAPI specification defined with comprehensive error handling and response structures
✅ **uv Dependencies**: Builds on existing vault-agent uv configuration, adds only strands-agents, streamlit, and streamable_httpclient

**Gate Status**: ✅ PASSED - Design maintains constitutional compliance with no violations introduced

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
vault-agent/                    # Main agent application directory (existing)
├── main.py                    # Entry point - Streamlit web application
├── pyproject.toml             # Dependencies with uv package management (existing)
├── src/
│   ├── __init__.py
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── vault_pki_agent.py    # Core Strands Agent implementation
│   │   └── query_processor.py   # Natural language query parsing
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── streamlit_app.py     # Streamlit UI components
│   │   └── example_prompts.py   # Example query prompts
│   ├── mcp/
│   │   ├── __init__.py
│   │   └── client.py            # streamable_httpclient MCP integration
│   └── models/
│       ├── __init__.py
│       ├── query.py             # Query request/response models
│       └── certificate.py      # Certificate data models
└── tests/
    ├── __init__.py
    ├── test_agent.py            # Agent functionality tests
    ├── test_mcp_client.py       # MCP integration tests
    └── test_query_processor.py  # Query processing tests
```

**Structure Decision**: Single project structure chosen because the agent is a standalone application that integrates with existing MCP server. The vault-agent directory already exists and contains the basic project setup with uv dependency management.

## Complexity Tracking

> **No constitutional violations identified** - This section is not required as the Constitution Check passed completely.

The agent implementation follows established patterns:
- Uses existing MCP server integration approach
- Leverages proven Strands Agent SDK for AI capabilities  
- Builds on existing vault-agent project structure
- Follows constitutional dependency management with `uv`
