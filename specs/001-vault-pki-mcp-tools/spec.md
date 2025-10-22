# Feature Specification: HashiCorp Vault PKI MCP Tools

**Feature Branch**: `001-vault-pki-mcp-tools`  
**Created**: 22 October 2025  
**Status**: Draft  
**Input**: User description: "I would like to create MCP tool functions that exposes below functionality from HashiCorp Vault: List all PKI secrets engines. This tool function should only list secrets engine for mount_type \"pki\" and no other secrets engine. List all certificates issued by a given secrets engine. The result should return a list of following fields grouped by \"root issuer CN\" and \"intermediate issuer CN\": \"subject CN\", \"Expired (Yes/No)\", \"Revoked (Yes/No)\""

## Clarifications

### Session 2025-10-22

- Q: When the user lacks permissions to read certain certificates or issuers in a PKI secrets engine, how should the system behave? → A: Return available certificates with a warning about inaccessible items (partial success)
- Q: How should the system handle certificates that were issued by an intermediate CA that has since been rotated or removed from the PKI secrets engine? → A: Display the issuer CN from certificate metadata with notation "(issuer inactive)"
- Q: How should the system handle pagination when there are thousands of certificates in a single PKI mount? → A: Return all certificates at once (no pagination)
- Q: How should the system authenticate to HashiCorp Vault? → A: Environment variables only (VAULT_ADDR, VAULT_TOKEN)
- Q: What happens when certificate metadata is incomplete or malformed in Vault? → A: Display the certificate with available fields and mark missing fields as "N/A" or "Unknown"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View All PKI Secrets Engines (Priority: P1)

As a Vault administrator or developer, I want to retrieve a list of all PKI secrets engines in my Vault instance so that I can understand which PKI mount points are available for certificate management operations.

**Why this priority**: This is the foundational capability required before any certificate operations can be performed. Without knowing which PKI secrets engines exist, users cannot proceed to inspect certificates or manage PKI infrastructure.

**Independent Test**: Can be fully tested by calling the list PKI secrets engines tool function and verifying it returns only mount points with type "pki" and excludes all other secrets engine types (kv, transit, etc.).

**Acceptance Scenarios**:

1. **Given** a Vault instance with multiple secrets engines including PKI and non-PKI types, **When** the list PKI secrets engines function is called, **Then** only secrets engines with mount_type "pki" are returned
2. **Given** a Vault instance with no PKI secrets engines enabled, **When** the list PKI secrets engines function is called, **Then** an empty list is returned
3. **Given** a Vault instance with multiple PKI secrets engines at different paths (e.g., pki/, pki_int/, pki_root/), **When** the list PKI secrets engines function is called, **Then** all PKI mount points are included in the results
4. **Given** an authenticated connection to Vault, **When** the list PKI secrets engines function is called, **Then** the response includes the mount path for each PKI secrets engine

---

### User Story 2 - View Certificates Grouped by Issuer Hierarchy (Priority: P1)

As a Vault administrator or security auditor, I want to view all certificates issued by a specific PKI secrets engine, organized by their root and intermediate issuer hierarchy, so that I can understand the certificate chain structure and quickly identify which certificates are expired or revoked.

**Why this priority**: This is the core certificate inspection capability that enables certificate lifecycle management, security auditing, and compliance verification. The hierarchical grouping by root and intermediate issuers provides essential context for understanding certificate relationships.

**Independent Test**: Can be fully tested by calling the list certificates function for a known PKI secrets engine path and verifying the results are correctly grouped by root issuer CN and intermediate issuer CN, with each certificate showing subject CN, expiration status, and revocation status.

**Acceptance Scenarios**:

1. **Given** a PKI secrets engine with issued certificates, **When** the list certificates function is called with the secrets engine path, **Then** all certificates are returned grouped by their root issuer common name (CN)
2. **Given** certificates issued by both root and intermediate CAs, **When** the list certificates function is called, **Then** certificates are grouped first by root issuer CN, then by intermediate issuer CN within each root group
3. **Given** a certificate that has not expired, **When** the list certificates function is called, **Then** the certificate shows "Expired: No" based on the current date compared to the certificate's validity period
4. **Given** a certificate that has expired, **When** the list certificates function is called, **Then** the certificate shows "Expired: Yes"
5. **Given** a certificate that has been revoked, **When** the list certificates function is called, **Then** the certificate shows "Revoked: Yes"
6. **Given** a certificate that has not been revoked, **When** the list certificates function is called, **Then** the certificate shows "Revoked: No"
7. **Given** a PKI secrets engine path that does not exist, **When** the list certificates function is called, **Then** an appropriate error message is returned
8. **Given** a PKI secrets engine with no issued certificates, **When** the list certificates function is called, **Then** an empty result set is returned

---

### Edge Cases

- What happens when a PKI secrets engine path contains special characters or non-standard naming conventions?
- Certificates issued by an intermediate CA that has since been rotated or removed display the issuer CN from certificate metadata with notation "(issuer inactive)"
- What happens when a certificate's issuer information cannot be resolved (orphaned certificate)?
- How does the system handle certificates issued directly by the root CA without an intermediate?
- When the user lacks permissions to read certain certificates or issuers, the system returns available certificates with a warning about inaccessible items (partial success approach)
- The system returns all certificates at once without pagination, regardless of the number of certificates in a PKI mount
- Certificates with incomplete or malformed metadata are displayed with available fields shown and missing fields marked as "N/A" or "Unknown"
- How does the system handle certificates with multi-level intermediate CA chains (e.g., root → intermediate1 → intermediate2 → leaf)?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a tool function to list all secrets engines of type "pki" in the Vault instance
- **FR-002**: System MUST exclude all non-PKI secrets engines (kv, transit, database, etc.) from the PKI secrets engine list
- **FR-003**: System MUST return the mount path for each PKI secrets engine
- **FR-004**: System MUST provide a tool function to list all certificates issued by a specified PKI secrets engine path
- **FR-005**: System MUST group certificates by root issuer common name (CN)
- **FR-006**: System MUST group certificates by intermediate issuer common name (CN) within each root issuer group
- **FR-007**: System MUST display the subject common name (CN) for each certificate
- **FR-008**: System MUST determine and display expiration status as "Yes" or "No" for each certificate based on the certificate's validity period compared to the current date
- **FR-009**: System MUST determine and display revocation status as "Yes" or "No" for each certificate by checking if the certificate appears in the Certificate Revocation List (CRL) or has revocation metadata
- **FR-010**: System MUST handle certificates issued directly by root CAs (without intermediates) by grouping them under the root issuer with no intermediate grouping
- **FR-011**: System MUST authenticate to Vault using environment variables VAULT_ADDR (for Vault server address) and VAULT_TOKEN (for authentication token)
- **FR-012**: System MUST return meaningful error messages when a specified PKI secrets engine path does not exist
- **FR-013**: System MUST return an empty result set when a valid PKI secrets engine has no issued certificates
- **FR-014**: System MUST traverse the certificate chain to correctly identify root and intermediate issuers for proper grouping
- **FR-015**: System MUST return available certificates with a warning message when the user lacks permissions to read certain certificates or issuers, providing partial results rather than failing the entire operation
- **FR-016**: System MUST display the issuer CN from certificate metadata with notation "(issuer inactive)" when a certificate was issued by an intermediate CA that has since been rotated or removed from the PKI secrets engine
- **FR-017**: System MUST return all certificates at once without pagination, regardless of the number of certificates in a PKI mount
- **FR-018**: System MUST display certificates with incomplete or malformed metadata by showing available fields and marking missing fields as "N/A" or "Unknown" rather than skipping the certificate

### Key Entities

- **PKI Secrets Engine**: Represents a mounted PKI backend in Vault at a specific path (e.g., pki/, pki_int/), capable of issuing and managing certificates. Key attributes include mount path and mount type.
- **Certificate**: Represents an X.509 certificate issued by a PKI secrets engine. Key attributes include serial number, subject CN, issuer CN, validity period (not_before, not_after), revocation status, and issuer reference.
- **Issuer**: Represents a certificate authority (CA) that issues certificates, either a root CA or intermediate CA. Key attributes include issuer ID, common name (CN), and parent issuer reference (for intermediates).
- **Certificate Chain**: Represents the hierarchical relationship between root CAs, intermediate CAs, and leaf certificates, showing the trust path from a certificate to its root CA.
- **Vault Connection**: Represents the authenticated connection to HashiCorp Vault, configured via environment variables VAULT_ADDR (server address) and VAULT_TOKEN (authentication token).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can retrieve a complete list of all PKI secrets engines in under 5 seconds for Vault instances with up to 50 secrets engines
- **SC-002**: The PKI secrets engine list excludes 100% of non-PKI mount types (zero false positives)
- **SC-003**: Users can retrieve and view all certificates from a PKI secrets engine organized by issuer hierarchy, with all certificates returned in a single response without pagination
- **SC-004**: Certificate expiration status accuracy is 100% when compared to certificate validity dates
- **SC-005**: Certificate revocation status accuracy is 100% when compared to Vault's CRL and revocation records
- **SC-006**: The hierarchical grouping correctly reflects the certificate chain structure with 100% accuracy (root → intermediate → certificate relationships are correctly identified)
- **SC-007**: Users can immediately identify expired or revoked certificates without needing to inspect individual certificate details
- **SC-008**: The tool functions integrate seamlessly with MCP protocol, allowing any MCP-compatible client to invoke them successfully
