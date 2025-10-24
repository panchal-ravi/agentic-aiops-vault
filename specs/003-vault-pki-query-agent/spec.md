# Feature Specification: Vault PKI Query Agent

**Feature Branch**: `003-vault-pki-query-agent`  
**Created**: 2025-10-24  
**Status**: Draft  
**Input**: User description: "Build an agent that allows users to query Vault PKI secrets engine and audit events related to certificate lifecycle management, governance and compliance. The user should be able to interact with the agent using a modern web-based UI. The user should be provided with example prompts to interact with Vault."

## Clarifications

### Session 2025-10-24

- Q: When the MCP server cannot connect to Vault, what should the agent do? → A: Show "Cannot connect to Vault. Please verify Vault is running and accessible" with a retry button
- Q: How should the agent handle queries that would return thousands of certificates (e.g., "Show all certificates")? → A: Return all results without limit (may cause performance issues)
- Q: What happens when audit logs are not enabled or accessible in Vault? → A: Audit logs are stored in external system such as AWS CloudWatch
- Q: When a user lacks permissions to access certain PKI engines or audit logs, what should happen? → A: Show authorized results and display message "Some results hidden due to insufficient permissions"
- Q: What authentication mechanism should the web UI use to verify user identity before allowing queries? → A: No authentication - rely on network-level access controls only

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Certificate Expiration Monitoring (Priority: P1)

Security and infrastructure teams need to proactively monitor certificate expiration to prevent service outages caused by expired certificates. The agent allows users to query certificates approaching expiration using natural language.

**Why this priority**: Certificate expiration is a critical operational concern that directly impacts service availability. Proactive monitoring prevents outages.

**Independent Test**: Can be fully tested by querying "Show me all certificates expiring in next 30 days" and verifying the agent returns accurate expiration data from Vault PKI. Delivers immediate value for operational monitoring.

**Acceptance Scenarios**:

1. **Given** the Vault PKI secrets engine contains certificates with various expiration dates, **When** user enters "Show me all certificates expiring in next 30 days", **Then** the agent displays all certificates expiring within 30 days with expiration dates and certificate identifiers
2. **Given** no certificates are expiring in the specified timeframe, **When** user queries for expiring certificates, **Then** the agent clearly indicates no certificates are expiring soon
3. **Given** the user queries for certificates expiring in a custom timeframe (e.g., 60 days, 90 days), **When** the query is submitted, **Then** the agent adapts the query logic to the specified timeframe

---

### User Story 2 - Certificate Status Investigation (Priority: P1)

Compliance and security teams need to investigate revoked certificates to verify proper governance procedures were followed and to audit certificate lifecycle events.

**Why this priority**: Compliance requirements mandate tracking and auditing of certificate revocations. Critical for security incident response and regulatory compliance.

**Independent Test**: Can be fully tested by querying "Show me all revoked certificates" and verifying the agent returns accurate revocation data. Delivers immediate value for compliance audits.

**Acceptance Scenarios**:

1. **Given** the Vault PKI contains both active and revoked certificates, **When** user enters "Show me all revoked certificates", **Then** the agent displays all revoked certificates with revocation dates and reasons
2. **Given** a user wants to filter revoked certificates by time period, **When** user specifies a date range, **Then** the agent returns only certificates revoked within that period
3. **Given** no certificates have been revoked, **When** user queries for revoked certificates, **Then** the agent clearly indicates no revocations found

---

### User Story 3 - PKI Engine Certificate Inventory (Priority: P2)

Operations teams need to understand which certificates are managed by specific PKI engines for inventory management and capacity planning.

**Why this priority**: Essential for managing multiple PKI engines and understanding certificate distribution. Important for operational planning but not as time-critical as expiration monitoring.

**Independent Test**: Can be fully tested by querying "List all certificates issued by [pki-name] secrets engine" and verifying accurate inventory results. Delivers value for capacity planning and inventory management.

**Acceptance Scenarios**:

1. **Given** multiple PKI secrets engines exist in Vault, **When** user enters "List all certificates issued by [pki-name] secrets engine", **Then** the agent displays all certificates from that specific engine
2. **Given** the user wants to compare certificate volumes across engines, **When** user requests certificates from multiple engines, **Then** the agent can handle multiple queries and present comparative results
3. **Given** an invalid PKI engine name is provided, **When** the query is submitted, **Then** the agent indicates the engine does not exist and suggests available engines

---

### User Story 4 - Certificate Audit Trail Investigation (Priority: P2)

Security and compliance teams need to investigate the complete audit trail of certificate lifecycle events (issuance, renewal, revocation) for specific certificates.

**Why this priority**: Critical for security investigations and compliance audits, but typically used reactively rather than for daily operations. Supports forensic analysis and compliance reporting.

**Independent Test**: Can be fully tested by querying "List all audit events related to web.example.com certificate" and verifying complete audit trail retrieval. Delivers value for security investigations.

**Acceptance Scenarios**:

1. **Given** a certificate has undergone multiple lifecycle events, **When** user enters "List all audit events related to web.example.com certificate", **Then** the agent displays chronological audit events including issuance, renewals, and any revocations
2. **Given** the user needs to filter events by type, **When** user specifies event types (e.g., only revocations), **Then** the agent returns filtered audit results
3. **Given** no audit events exist for the specified certificate, **When** user queries for audit events, **Then** the agent indicates no events found and confirms the certificate name

---

### User Story 5 - Certificate Issuance Attribution (Priority: P3)

Compliance and security teams need to identify who issued specific certificates for accountability and audit purposes.

**Why this priority**: Important for accountability and compliance but typically queried less frequently. Supports audit requirements but not immediate operational needs.

**Independent Test**: Can be fully tested by querying "Who issued test.example.com certificate?" and verifying accurate issuer attribution. Delivers value for accountability tracking.

**Acceptance Scenarios**:

1. **Given** a certificate was issued by a specific user or system, **When** user enters "Who issued test.example.com certificate?", **Then** the agent displays the issuer identity, timestamp, and issuance context
2. **Given** the certificate was automatically renewed, **When** user queries for the issuer, **Then** the agent distinguishes between manual issuance and automated renewal
3. **Given** multiple certificates exist with similar names, **When** user queries for issuer, **Then** the agent clarifies which specific certificate instance is being referenced

---

### User Story 6 - Interactive Prompt Guidance (Priority: P3)

New users need guidance on how to interact with the agent effectively through example prompts and suggestions.

**Why this priority**: Improves user experience and reduces learning curve, but users can discover queries through trial and error. Nice-to-have for usability.

**Independent Test**: Can be fully tested by accessing the web UI and verifying example prompts are displayed and clickable. Delivers value for user onboarding.

**Acceptance Scenarios**:

1. **Given** a user first accesses the web UI, **When** the page loads, **Then** example prompts are displayed prominently for common query patterns
2. **Given** a user clicks an example prompt, **When** the prompt is selected, **Then** it populates the query input and can be executed immediately
3. **Given** a user enters a malformed query, **When** the agent cannot parse it, **Then** suggestions for correct query formats are provided

---

### Edge Cases

- **Vault Connection Failure**: When MCP server cannot connect to Vault, display "Cannot connect to Vault. Please verify Vault is running and accessible" with a retry button allowing users to reattempt the query
- **Large Result Sets**: Agent returns all matching certificates without pagination or limiting, regardless of result set size. Users should refine queries if performance degrades with large result sets.
- **Audit Log Unavailability**: Audit logs are stored in external systems (e.g., AWS CloudWatch). Agent must query external audit system to retrieve certificate lifecycle events. If audit system is unreachable, display appropriate error message indicating the external system connection issue.
- **Permission Restrictions**: When user lacks permissions to access certain PKI engines or audit logs, display authorized results with message "Some results hidden due to insufficient permissions" to inform user of partial result set
- How does the agent handle queries for non-existent certificates or PKI engines?
- What happens when audit logs are not enabled or accessible in Vault?
- How does the agent handle queries that would return thousands of certificates (pagination)?
- What happens when a user's query is ambiguous and could match multiple certificates?
- How does the agent respond when a user lacks permissions to access certain PKI engines or audit logs?
- What happens when the natural language query uses terminology not recognized by the agent?
- How does the agent handle concurrent queries from multiple users?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a web-based user interface for entering natural language queries about Vault PKI certificates and audit events
- **FR-002**: System MUST support querying certificates by expiration timeframe (e.g., "expiring in next 30 days", "expiring in next 90 days")
- **FR-003**: System MUST retrieve and display all revoked certificates with revocation metadata (date, reason)
- **FR-004**: System MUST filter certificates by specific PKI secrets engine
- **FR-005**: System MUST retrieve audit events related to specific certificates, including issuance, renewal, and revocation events
- **FR-006**: System MUST identify and display the issuer (user or system) of specific certificates
- **FR-007**: System MUST integrate with existing MCP server tools for Vault PKI interaction
- **FR-008**: System MUST display example prompts to guide users on supported query patterns
- **FR-009**: System MUST parse natural language queries and translate them to appropriate Vault API calls via MCP tools
- **FR-010**: System MUST handle errors gracefully when Vault is unreachable or returns errors
- **FR-011**: System MUST display query results in a user-friendly format with relevant certificate metadata (common name, serial number, expiration date, status)
- **FR-012**: System MUST validate certificate names and PKI engine names before querying
- **FR-013**: System MUST handle queries that return no results by providing clear feedback
- **FR-014**: System MUST support filtering and sorting of query results
- **FR-015**: System MUST operate within the "vault-agent" folder structure
- **FR-016**: System MUST maintain query history for the current user session
- **FR-017**: System MUST support multiple concurrent user sessions without data leakage between users
- **FR-018**: System MUST authenticate with Vault using token-based authentication with secure token storage
- **FR-019**: System MUST return all query results without pagination or limiting, regardless of result set size (users accept potential performance impact for large result sets)
- **FR-020**: System MUST log basic audit information including user identity, query text, timestamp, and success/failure status for accountability and compliance tracking
- **FR-021**: System MUST handle permission restrictions gracefully by displaying authorized results with message "Some results hidden due to insufficient permissions" when user lacks access to certain PKI engines or audit logs

### Key Entities

- **Certificate**: Represents an X.509 certificate managed by Vault PKI, including common name, serial number, expiration date, revocation status, and issuing PKI engine
- **PKI Secrets Engine**: A Vault secrets engine configured for PKI certificate management, identified by mount path
- **Audit Event**: A record of certificate lifecycle actions (issuance, renewal, revocation) including timestamp, actor, and event details
- **User Query**: Natural language input from the user requesting information about certificates or audit events
- **Query Result**: Structured response containing certificates or audit events matching the user's query criteria

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can identify certificates expiring within a specified timeframe in under 10 seconds from query submission
- **SC-002**: Users can retrieve complete audit trails for specific certificates in under 15 seconds
- **SC-003**: 90% of supported query patterns execute successfully on first attempt without requiring query refinement
- **SC-004**: Users with no prior Vault CLI experience can successfully query certificate data using example prompts within 5 minutes of first use
- **SC-005**: System accurately parses and executes at least 5 distinct query patterns (expiration, revocation, PKI filtering, audit events, issuer attribution)
- **SC-006**: Query results display all relevant certificate metadata required for operational decision-making (common name, expiration, status, issuer)
- **SC-007**: System maintains responsive performance (UI interactions under 2 seconds) when displaying query results up to 100 certificates
- **SC-008**: Error conditions (Vault unreachable, invalid queries) provide actionable feedback within 3 seconds
- **SC-009**: System supports at least 10 concurrent user sessions without performance degradation
- **SC-010**: Certificate expiration queries reduce time to identify at-risk certificates by 80% compared to manual Vault CLI investigation

## Assumptions

- Vault PKI secrets engines are already configured and contain certificate data
- MCP server tools for Vault PKI interaction exist or will be developed in parallel
- Audit logging is enabled in Vault and forwarded to external audit system (e.g., AWS CloudWatch)
- Agent has read access to external audit log system to query certificate lifecycle events
- Users have appropriate Vault permissions to read PKI data and audit logs
- Web UI will be accessed by authenticated users (web UI authentication separate from Vault authentication)
- Web UI relies on network-level access controls (VPN, security groups, private network) for user authentication rather than application-level authentication
- Network connectivity exists between the agent and Vault server
- This is a proof-of-concept implementation with expected result sets under 1000 records (no pagination required)
- Certificate data volume per query typically stays under 1000 records for POC scenarios
- Natural language processing will use pattern matching or AI/LLM capabilities (implementation detail for planning phase)
- The agent will be deployed in the same network zone as Vault for low-latency access
- A valid Vault token with appropriate read permissions will be securely stored and accessible to the agent

## Dependencies

- Existing Vault deployment with PKI secrets engines configured
- MCP server implementation with Vault PKI tools
- External audit log system (e.g., AWS CloudWatch) storing Vault audit events with read access
- Web application framework for UI (technology selection in planning phase)
- Vault authentication credentials with appropriate read permissions
- Audit logging enabled in Vault configuration and forwarded to external system

## Scope Boundaries

**In Scope**:
- Querying existing certificates and audit events
- Natural language query parsing for the 5 example query patterns
- Web-based user interface
- Integration with MCP server tools
- Display of certificate and audit event metadata

**Out of Scope**:
- Certificate issuance, renewal, or revocation actions (read-only queries only)
- Modifying Vault PKI configuration or policies
- User authentication/authorization for web UI (relies on network-level access controls)
- Real-time alerting or notifications for expiring certificates
- Exporting query results to external formats (CSV, PDF, etc.)
- Integration with external ticketing or monitoring systems
- Managing multiple Vault clusters simultaneously
- Historical trend analysis or reporting dashboards
