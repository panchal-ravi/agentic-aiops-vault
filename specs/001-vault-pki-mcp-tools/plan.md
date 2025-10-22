````markdown
# Implementation Plan: HashiCorp Vault PKI MCP Tools

**Branch**: `001-vault-pki-mcp-tools` | **Date**: 2025-10-22 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-vault-pki-mcp-tools/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Implement MCP tool functions to expose HashiCorp Vault PKI secrets engine management capabilities. The solution will provide two core tools: (1) listing all PKI secrets engines in the Vault instance, and (2) retrieving certificates from a specified PKI engine, organized hierarchically by root and intermediate CAs with expiration and revocation status. Implementation uses Python with FastMCP framework and hvac (HashiCorp Vault Python SDK) for Vault API interactions. Authentication via environment variables (VAULT_ADDR, VAULT_TOKEN).

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: FastMCP (MCP server framework), hvac (HashiCorp Vault Python SDK), cryptography (X.509 certificate parsing)  
**Storage**: N/A (read-only operations against Vault API)  
**Testing**: pytest for unit and integration tests  
**Target Platform**: Cross-platform (Linux, macOS, Windows) - MCP server process  
**Project Type**: Single project (MCP server)  
**Performance Goals**: <5 seconds to list PKI engines (up to 50 engines), all certificates returned in single response  
**Constraints**: Environment-based authentication only, no pagination for certificate listing, partial results on permission errors  
**Scale/Scope**: POC scope - supports multiple PKI engines, handles thousands of certificates per engine, basic error handling

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

✅ **MCP Protocol Compliance**: All functionality exposed through MCP tool definitions with proper schemas, standardized error handling, and resource patterns.

✅ **Security-First Design**: Environment-based authentication (VAULT_ADDR, VAULT_TOKEN), input validation via MCP schemas, no secret leakage in logs/responses, principle of least privilege.

✅ **API-First Development**: Tool contracts defined before implementation, following MCP specification for tool definitions and responses.

**Status**: PASSED - No constitutional violations. All requirements align with security-first design and MCP protocol compliance.

## Project Structure

### Documentation (this feature)

```text
specs/001-vault-pki-mcp-tools/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   └── mcp-tools.json  # MCP tool definitions (OpenAPI-style)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
vault-mcp-server/
├── main.py                    # MCP server entry point with tool registrations
├── pyproject.toml            # Dependencies: fastmcp, hvac, cryptography
├── README.md                 # Setup and usage instructions
├── src/
│   ├── __init__.py
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── list_pki_engines.py      # List PKI secrets engines tool
│   │   └── list_certificates.py      # List certificates with hierarchy tool
│   ├── services/
│   │   ├── __init__.py
│   │   ├── vault_client.py          # hvac client wrapper with auth
│   │   ├── certificate_parser.py    # X.509 parsing and status checks
│   │   └── certificate_hierarchy.py  # Build CA hierarchy from chains
│   └── models/
│       ├── __init__.py
│       ├── pki_engine.py            # PKI engine data model
│       └── certificate.py           # Certificate data model
└── tests/
    ├── __init__.py
    ├── unit/
    │   ├── test_certificate_parser.py
    │   ├── test_certificate_hierarchy.py
    │   └── test_vault_client.py
    └── integration/
        ├── test_list_pki_engines.py
        └── test_list_certificates.py
```

**Structure Decision**: Single project structure chosen as this is an MCP server providing tool functions. All code resides in `vault-mcp-server/` with clear separation between tools (MCP layer), services (business logic), and models (data structures).

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No complexity violations. The design adheres to POC scope with simple, direct patterns: MCP tools call services, services call Vault API, no unnecessary abstractions.

## Post-Design Constitution Re-Check

*Re-evaluation after Phase 1 design completion*

✅ **MCP Protocol Compliance**: Confirmed via contracts/mcp-tools.json
  - Tool schemas defined with proper input/output validation
  - Error handling follows MCP error response patterns
  - Structured responses with nested hierarchy for certificate data

✅ **Security-First Design**: Confirmed via data-model.md and research.md
  - Authentication: Environment variables only (VAULT_ADDR, VAULT_TOKEN)
  - Input validation: Pydantic models for all tool parameters
  - Authorization: Token-based with documented permission requirements
  - Secret handling: No PEM data in default serialization, no token logging

✅ **API-First Development**: Confirmed via contracts/mcp-tools.json
  - Complete OpenAPI-style contract with schemas before implementation
  - All tool definitions include input/output schemas and error conditions
  - Standardized JSON responses for programmatic consumption

**Final Status**: PASSED - Design maintains full constitutional compliance. Ready for Phase 2 implementation.
````
