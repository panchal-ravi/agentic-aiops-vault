# Research: HashiCorp Vault PKI MCP Tools

**Date**: 2025-10-22  
**Feature**: HashiCorp Vault PKI MCP Tools  
**Purpose**: Technical research and decision rationale for implementation

## Overview

This document captures technical research, decisions, and best practices for implementing MCP tools that expose HashiCorp Vault PKI secrets engine functionality. The implementation uses Python with FastMCP framework and hvac SDK.

## Technical Decisions

### 1. MCP Framework Selection

**Decision**: Use FastMCP (Python MCP framework)

**Rationale**: 
- FastMCP provides declarative tool registration with automatic schema generation
- Native Python support aligns with hvac SDK (official HashiCorp Vault Python client)
- Built-in validation and error handling for MCP protocol compliance
- Minimal boilerplate compared to implementing raw MCP protocol
- Active development and community support

**Alternatives Considered**:
- **Raw MCP Protocol**: Too much boilerplate, requires manual schema definition and validation
- **TypeScript MCP SDK**: Would require language mismatch with hvac (Python), additional FFI complexity
- **Custom Protocol**: Violates MCP protocol compliance constitutional requirement

**Implementation Notes**:
- Use `@mcp.tool()` decorator for tool registration
- Leverage FastMCP's automatic parameter validation from type hints
- Return structured Python objects; FastMCP handles JSON serialization

### 2. Vault API Client Selection

**Decision**: Use hvac (HashiCorp Vault Python SDK)

**Rationale**:
- Official SDK maintained by HashiCorp community
- Comprehensive API coverage for PKI operations (list mounts, read certs, read issuers)
- Built-in authentication mechanisms (token, AppRole, Kubernetes, etc.)
- Handles retries, connection pooling, and TLS verification
- Type hints for better IDE support and validation

**Alternatives Considered**:
- **requests library**: Would require manual API endpoint construction, error handling, auth token management
- **VaultLib**: Less mature, limited community support
- **Direct HTTP calls**: Violates DRY principle, error-prone

**Implementation Notes**:
- Initialize hvac.Client with VAULT_ADDR from environment
- Set token via environment variable (VAULT_TOKEN)
- Use `sys.mounts.list_mounted_secrets_engines()` for listing engines
- Use PKI-specific methods: `secrets.pki.list_certificates()`, `secrets.pki.read_certificate()`, `secrets.pki.read_issuer()`

### 3. X.509 Certificate Parsing

**Decision**: Use cryptography library (pyca/cryptography)

**Rationale**:
- Industry-standard Python cryptography library
- Full X.509 parsing capabilities (subject, issuer, validity dates, extensions)
- Secure and actively maintained by Python Cryptographic Authority
- Handles PEM/DER encoding automatically
- Rich API for extracting certificate fields and checking revocation

**Alternatives Considered**:
- **OpenSSL subprocess calls**: Fragile, shell injection risks, parsing complexity
- **PyOpenSSL**: Deprecated, wraps OpenSSL C library (more error-prone)
- **asn1crypto**: Lower-level, requires more manual parsing

**Implementation Notes**:
- Parse PEM data using `x509.load_pem_x509_certificate()`
- Extract subject CN: `cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value`
- Extract issuer CN: `cert.issuer.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value`
- Check expiration: Compare `cert.not_valid_after` with `datetime.now(timezone.utc)`
- Check revocation: Parse CRL extension or query Vault revocation list

### 4. Certificate Hierarchy Construction

**Decision**: Build hierarchy by traversing CA chain from certificate to root

**Rationale**:
- Vault PKI stores certificates with issuer_id references
- Vault provides ca_chain in issuer details (PEM-encoded chain of CAs)
- Parsing ca_chain allows identifying intermediate → root relationships
- Grouping logic: root CN → intermediate CN → certificate subject CN

**Approach**:
1. List all certificates for PKI mount using `<pki>/certs` API
2. For each certificate serial:
   - Read certificate details from `<pki>/cert/<serial>`
   - Parse certificate PEM to extract subject CN, issuer CN, expiration
   - Read issuer details from `<pki>/issuer/<issuer_id>`
   - Parse ca_chain to identify root CA (last cert in chain)
3. Build nested dictionary structure: `{root_cn: {intermediate_cn: [certificates]}}`
4. Handle edge cases:
   - Direct root issuance: No intermediate, group under root with `None` intermediate
   - Inactive issuer: Mark as "(issuer inactive)" when issuer_id doesn't resolve
   - Orphaned certificate: Group under "Unknown Root" or issuer CN from cert metadata

**Alternatives Considered**:
- **Flat listing**: Loses hierarchical context, harder to audit certificate chains
- **Graph database**: Over-engineering for POC scope, adds complexity

### 5. Revocation Status Checking

**Decision**: Check Vault's revocation metadata and CRL

**Rationale**:
- Vault maintains revocation list accessible via API
- Certificate metadata includes revocation time if revoked
- CRL extension in certificates provides OCSP/CRL distribution points

**Approach**:
1. Query `<pki>/certs/revoked` to get list of revoked serial numbers (if API available)
2. Check certificate metadata for `revocation_time` field
3. If neither available, parse CRL extension and mark as "Unknown" (per FR-018)

**Alternatives Considered**:
- **OCSP checking**: Requires external network calls, timeout risks, POC scope violation
- **CRL file parsing**: Requires downloading and parsing CRL, performance impact

### 6. Error Handling Strategy

**Decision**: Partial success with warnings for permission errors

**Rationale**:
- Requirement FR-015: Return available data with warnings on permission errors
- Better UX: Show what's accessible rather than complete failure
- Aligns with Vault's least-privilege access model

**Approach**:
- Wrap individual certificate/issuer reads in try-except blocks
- Accumulate warnings for failed operations (403 Forbidden)
- Return successful results + warning list in MCP response
- Use structured warnings: `{"type": "permission_denied", "resource": "<pki>/cert/<serial>", "message": "..."}`

**Alternatives Considered**:
- **Fail-fast**: Violates FR-015 requirement
- **Silent failures**: Poor UX, hides permission issues

### 7. Performance Optimization

**Decision**: Concurrent API calls with async/await

**Rationale**:
- Performance goal: <5 seconds for listing PKI engines with up to 50 engines
- No pagination requirement (FR-017): Return all certificates in single response
- Network I/O is bottleneck; concurrent requests reduce latency

**Approach**:
- Use `asyncio` for concurrent hvac API calls
- Batch certificate reads: `asyncio.gather()` for parallel fetches
- Connection pooling via hvac client's session management
- Respect Vault rate limits (if configured)

**Alternatives Considered**:
- **Sequential calls**: Violates <5 second performance goal for large deployments
- **Thread pool**: More complex than asyncio, GIL limitations in Python

**Implementation Notes**:
- FastMCP supports async tool functions
- hvac doesn't natively support async; use `asyncio.to_thread()` for blocking calls
- Consider caching issuer details to avoid redundant API calls for same issuer_id

## Vault API Usage Patterns

### List PKI Secrets Engines

```python
# API: GET /sys/mounts
client = hvac.Client(url=os.getenv('VAULT_ADDR'), token=os.getenv('VAULT_TOKEN'))
mounts = client.sys.list_mounted_secrets_engines()

# Filter for PKI type
pki_engines = [
    {"path": path.rstrip('/'), "type": details['type']}
    for path, details in mounts.items()
    if details.get('type') == 'pki'
]
```

### List Certificates for PKI Mount

```python
# API: LIST /<pki>/certs
certs_response = client.secrets.pki.list_certificates(mount_point='pki')
serial_numbers = certs_response['data']['keys']  # List of serial numbers
```

### Read Certificate Details

```python
# API: GET /<pki>/cert/<serial>
cert_data = client.secrets.pki.read_certificate(serial=serial_number, mount_point='pki')
pem_data = cert_data['data']['certificate']
issuer_id = cert_data['data'].get('issuer_id')  # UUID reference to issuer

# Parse PEM
from cryptography import x509
from cryptography.hazmat.backends import default_backend
cert = x509.load_pem_x509_certificate(pem_data.encode(), default_backend())
```

### Read Issuer Details

```python
# API: GET /<pki>/issuer/<issuer_id>
issuer_data = client.secrets.pki.read_issuer(issuer_ref=issuer_id, mount_point='pki')
ca_chain_pem = issuer_data['data']['ca_chain']  # List of PEM-encoded CA certs

# Parse CA chain to identify root (last cert in chain)
ca_certs = []
for pem_cert in ca_chain_pem:
    ca_cert = x509.load_pem_x509_certificate(pem_cert.encode(), default_backend())
    ca_certs.append(ca_cert)

root_ca = ca_certs[-1]  # Root is last in chain
intermediate_ca = ca_certs[0] if len(ca_certs) > 1 else None
```

## Best Practices

### MCP Tool Design

1. **Clear Tool Descriptions**: Each tool must have comprehensive description for AI agent understanding
2. **Structured Responses**: Return consistent JSON structure with nested grouping
3. **Error Messages**: Include actionable context (e.g., "Check VAULT_TOKEN permissions for path <pki>/cert/<serial>")
4. **Schema Validation**: Use Pydantic models for tool parameters and responses

### Security

1. **No Secret Logging**: Never log VAULT_TOKEN or certificate private keys
2. **Input Validation**: Validate PKI mount paths against injection attacks
3. **Environment Variables**: Fail fast if VAULT_ADDR or VAULT_TOKEN not set
4. **TLS Verification**: Enable by default; allow disable only for development (via env var)

### Code Organization

1. **Separation of Concerns**: 
   - Tools: MCP interface layer
   - Services: Business logic (Vault API calls, certificate parsing)
   - Models: Data structures (Pydantic models)
2. **Testability**: Services should be unit-testable without MCP server running
3. **Reusability**: Certificate parsing logic shared between tools

## Testing Strategy

### Unit Tests

- **VaultClient**: Mock hvac responses, test error handling
- **CertificateParser**: Test with sample PEM data (expired, revoked, valid certs)
- **CertificateHierarchy**: Test grouping logic with mock certificate data

### Integration Tests

- **Prerequisites**: Running Vault instance with PKI engines enabled
- **Setup**: Use Terraform to provision test PKI mounts and certificates
- **Test Cases**:
  - List PKI engines with multiple types (pki, kv, transit)
  - List certificates with multi-level CA hierarchy
  - Handle permission errors (restricted token)
  - Handle inactive issuers

### Contract Tests

- **MCP Protocol Compliance**: Validate tool responses match MCP schema
- **Tool Schema**: Verify parameter schemas allow valid inputs, reject invalid inputs

## Dependencies

### Production

- **fastmcp**: `>=0.1.0` - MCP server framework
- **hvac**: `>=2.0.0` - HashiCorp Vault Python client
- **cryptography**: `>=41.0.0` - X.509 certificate parsing
- **pydantic**: `>=2.0.0` - Data validation and serialization

### Development

- **pytest**: `>=7.4.0` - Testing framework
- **pytest-asyncio**: `>=0.21.0` - Async test support
- **pytest-mock**: `>=3.11.0` - Mocking utilities
- **black**: `>=23.0.0` - Code formatting
- **ruff**: `>=0.1.0` - Linting

## Implementation Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Vault API changes | High - Breaking changes | Pin hvac version, monitor deprecations |
| Large certificate lists timeout | Medium - Performance degradation | Implement concurrent fetching, consider streaming |
| Certificate parsing failures | Medium - Incomplete results | Graceful degradation per FR-018 (mark as N/A) |
| Permission errors block all results | Low - Poor UX | Partial success pattern per FR-015 |
| CRL unavailable for revocation check | Low - Missing data | Mark as "Unknown", document limitation |

## Open Questions for Implementation

None - All clarifications resolved in feature specification Phase 2 Q&A.

## References

- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [hvac Documentation](https://hvac.readthedocs.io/)
- [Vault PKI Secrets Engine API](https://developer.hashicorp.com/vault/api-docs/secret/pki)
- [Python cryptography X.509 Guide](https://cryptography.io/en/latest/x509/)
- [MCP Protocol Specification](https://modelcontextprotocol.io/docs)
