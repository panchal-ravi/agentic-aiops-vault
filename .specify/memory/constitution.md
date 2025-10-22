<!--
Sync Impact Report:
- Version change: 1.0.0 → 1.1.0
- Modified principles: MCP Protocol Compliance (added specific function pattern requirements)
- Added sections: Dependency Management Standards
- Templates requiring updates: ✅ All templates verified and compatible
- Follow-up TODOs: None - all placeholders filled
- Note: POC-focused constitution excludes comprehensive testing and monitoring requirements
-->

# Vault MCP Server Constitution

## Core Principles

### I. MCP Protocol Compliance
All functionality MUST be exposed through the Model Context Protocol (MCP) specification. Every tool and resource must follow MCP standard patterns with the exact function signature pattern:

```python
@mcp.tool()
async def function_name(param: Type) -> ResponseType:
    """
    Brief function description.

    Detailed description of the tool's purpose and usage. Include when to use this tool
    and how it fits into user workflows.

    Example input:
        param (Type): "example_value"
        object_param (ObjectType):
            {
                "field1": "value1",
                "field2": 42.0
            }

    Example response:
        {
            "success": true,
            "message": "Operation completed successfully",
            "data": {...}
        }

    Args:
        param (Type): Description of parameter including constraints and format.

    Returns:
        ResponseType: Description of return object structure including:
        - 'success' (bool): Indicates operation success status.
        - 'message' (str): Human-readable operation result description.
        - Additional response fields as appropriate.

    """
```

No direct API endpoints outside the MCP framework are permitted. All tools must include comprehensive docstrings with examples and type annotations.

**Rationale**: Ensures seamless integration with AI agents, maintains protocol consistency, and provides clear usage documentation for LLM consumption.

### II. Security-First Design
Security controls MUST be implemented at every layer: input validation, authentication tokens, authorization checks, and audit logging. All Vault operations require proper token-based authentication. Sensitive data (tokens, secrets) must never be logged or exposed in responses.

**Rationale**: HashiCorp Vault handles sensitive secrets and certificates; any security breach could compromise organizational infrastructure.

### III. API-First Development
Every feature starts as a well-defined API contract following OpenAPI specifications. Implementation follows the contract, not the reverse. All endpoints must support both JSON responses for programmatic access and structured error responses for debugging.

**Rationale**: Enables independent development, testing, and integration while ensuring consistent interfaces for AI agent consumption.

## Dependency Management Standards

All Python projects MUST use `uv` as the primary dependency manager:

- **Package Installation**: Use `uv add package_name` for production dependencies
- **Development Dependencies**: Use `uv add --dev package_name` for development tools
- **Environment Creation**: Use `uv venv` for virtual environment creation
- **Dependency Resolution**: Maintain `uv.lock` file for reproducible builds
- **Project Structure**: Use `pyproject.toml` with `uv` build system configuration

Traditional `pip` and `requirements.txt` workflows are prohibited. All dependency management operations must leverage `uv`'s modern package resolution and environment management capabilities.

**Rationale**: `uv` provides faster dependency resolution, better lock file management, and more reliable virtual environment handling compared to legacy tools.

## Security Requirements

All code MUST implement basic security measures appropriate for POC:

- **Authentication**: Valid Vault token required for all operations
- **Input Validation**: Schema validation on all MCP tool parameters
- **Authorization**: Principle of least privilege for Vault policy assignments
- **Secret Handling**: No secret leakage in logs, responses, or error messages

## Development Workflow

Development process follows iterative POC practices:

- **Code Review**: PRs reviewed for security and MCP compliance before merge
- **Integration Testing**: Basic tests against live Vault instance for critical paths
- **Documentation**: Core functionality and security implications documented
- **Compliance Verification**: Changes verified against MCP specification requirements

## Governance

This constitution supersedes all other development practices. Security principles and dependency management standards are non-negotiable for POC validation and require explicit justification for any exceptions. All PRs and code reviews must verify constitutional compliance, with particular attention to security controls, MCP protocol adherence, and `uv` dependency management practices.

Version control and amendment process requires documentation of any constitutional changes affecting security posture, MCP compliance, or dependency management workflows.

**Version**: 1.1.0 | **Ratified**: 2025-10-22 | **Last Amended**: 2025-10-22
