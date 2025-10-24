# Research: Vault PKI Query Agent

## Decision: AWS Strands Agent SDK Architecture

**Rationale**: Strands Agent SDK provides production-ready patterns for building AI agents with tool integration, conversation management, and model abstraction. The vault-agent directory already includes strands-agents[openai] dependency.

**Alternatives considered**: 
- LangChain: More complex, unnecessary features for focused PKI domain
- Direct OpenAI API: Would require building agent conversation management from scratch
- LlamaIndex: Focused on document retrieval, not tool-based agent interactions

**Implementation approach**:
- Use `Agent` class with OpenAI model integration
- Implement tool integration pattern for MCP client calls
- Leverage built-in conversation management for multi-turn queries
- Use structured prompts for PKI domain expertise

## Decision: Streamlit for POC Web Interface

**Rationale**: Streamlit provides rapid prototyping for AI applications with minimal boilerplate. Excellent for POC requirements with built-in session state management and real-time updates.

**Alternatives considered**:
- FastAPI + React: Over-engineered for POC, requires separate frontend build
- Gradio: Similar to Streamlit but less flexible for custom layouts
- Jupyter notebooks: Not suitable for end-user interface

**Implementation approach**:
- Main page with query input and example prompts
- Session state for query history
- Real-time results display with structured formatting
- Error handling with user-friendly messages

## Decision: streamable_httpclient for MCP Integration

**Rationale**: Provides HTTP client specifically designed for MCP protocol communication, maintaining compatibility with existing vault-mcp-server tools.

**Alternatives considered**:
- Direct HTTP requests: Would require manual MCP protocol implementation
- Python MCP SDK: Might be overkill for client-side integration
- Custom client: Unnecessary when streamable_httpclient exists

**Implementation approach**:
- Configure client to connect to vault-mcp-server endpoint
- Implement tool invocation methods for each MCP tool
- Handle connection errors and timeouts gracefully
- Parse MCP response format to agent-friendly data structures

## Decision: Pattern-Based Natural Language Processing

**Rationale**: For POC scope, pattern matching with predefined query templates provides reliable results without complex NLP infrastructure. The 5 required query patterns are well-defined and can be mapped to specific MCP tool calls.

**Alternatives considered**:
- OpenAI function calling: Could work but adds complexity and token usage
- Intent classification models: Over-engineered for 5 specific patterns
- Regex-only parsing: Too brittle for natural language variations

**Implementation approach**:
- Define query patterns for each user story (expiration, revocation, etc.)
- Use fuzzy matching for parameter extraction (timeframes, certificate names)
- Fallback to OpenAI for ambiguous queries that don't match patterns
- Provide suggested corrections for unrecognized queries

## Decision: Certificate Data Model Simplification

**Rationale**: Focus on operational metadata required for the 6 user stories rather than full X.509 certificate details. This reduces complexity and improves response time.

**Alternatives considered**:
- Full certificate parsing: Would require complex cryptography library usage
- Raw Vault API responses: Too detailed for end-user consumption
- External certificate analysis tools: Adds unnecessary dependencies

**Implementation approach**:
- Extract key fields: common name, expiration date, serial number, status
- Aggregate revocation and expiration status for filtering
- Format dates in user-friendly relative terms ("expires in 30 days")
- Group certificates by PKI engine for organizational clarity

## PKI Domain Query Patterns

Based on user stories analysis, these are the core query patterns to implement:

1. **Expiration queries**: "Show certificates expiring in [timeframe]"
2. **Revocation queries**: "List all revoked certificates"
3. **PKI engine queries**: "List certificates from [engine-name]"
4. **Audit queries**: "Show audit events for [certificate-name]"
5. **Issuer queries**: "Who issued [certificate-name]?"
6. **General help**: "What can I ask?" / "Show examples"

Each pattern maps to specific MCP tool calls with parameter extraction and result formatting.