# Data Model: Vault PKI Query Agent

## Core Entities

### User Query
Represents a natural language query from the user requesting PKI information.

**Fields**:
- `query_text` (str): Original natural language query
- `query_type` (QueryType): Identified query pattern  
- `parameters` (dict): Extracted parameters (timeframe, certificate name, etc.)
- `timestamp` (datetime): When query was submitted
- `session_id` (str): User session identifier

**Validation Rules**:
- `query_text` must be non-empty and max 500 characters
- `query_type` must be one of defined enum values
- `parameters` validated based on query type requirements

**State Transitions**:
- SUBMITTED → PROCESSING → COMPLETED/FAILED

### Certificate Summary
Simplified certificate data optimized for UI display and operational queries.

**Fields**:
- `serial_number` (str): Unique certificate identifier
- `subject_cn` (str): Common name from certificate subject
- `pki_engine` (str): Mount path of issuing PKI engine
- `expiration_date` (datetime): Certificate expiration timestamp
- `days_until_expiry` (int): Calculated days remaining (negative if expired)
- `is_expired` (bool): Whether certificate has expired
- `is_revoked` (bool): Whether certificate has been revoked
- `revocation_date` (Optional[datetime]): Date of revocation if applicable
- `issuer_hierarchy` (List[str]): Chain of issuing CAs

**Validation Rules**:
- `serial_number` must be valid hex format
- `subject_cn` must be valid hostname or identifier
- `expiration_date` must be future date for active certificates
- `days_until_expiry` calculated from current time to expiration

### PKI Engine Info
Information about PKI secrets engines available for queries.

**Fields**:
- `path` (str): Mount path identifier
- `type` (str): Always "pki" for PKI engines
- `description` (str): Human-readable description
- `certificate_count` (int): Number of certificates in engine

**Validation Rules**:
- `path` must match vault mount path format
- `type` must equal "pki"

### Audit Event
Certificate lifecycle audit information from external audit logs.

**Fields**:
- `timestamp` (datetime): When event occurred
- `event_type` (AuditEventType): Type of operation (issue, revoke, etc.)
- `certificate_subject` (str): Subject of affected certificate
- `actor_name` (str): Display name of entity performing action
- `actor_id` (str): Unique identifier of acting entity
- `remote_address` (str): IP address of requesting client
- `request_path` (str): Vault API path of operation
- `mount_accessor` (str): PKI mount accessor ID

**Validation Rules**:
- `timestamp` must be valid datetime
- `event_type` must be recognized audit event type
- `certificate_subject` must match certificate naming patterns

### Query Result
Structured response containing query results and metadata.

**Fields**:
- `success` (bool): Whether query completed successfully
- `message` (str): Human-readable result summary
- `certificates` (List[CertificateSummary]): Certificate results if applicable
- `audit_events` (List[AuditEvent]): Audit event results if applicable
- `pki_engines` (List[PKIEngineInfo]): PKI engine results if applicable
- `query_metadata` (QueryMetadata): Execution statistics
- `errors` (List[str]): Any non-fatal warnings or errors

**Validation Rules**:
- Either `certificates`, `audit_events`, or `pki_engines` must be populated for successful queries
- `message` should provide clear context about result contents

## Enumerations

### QueryType
- `EXPIRATION_CHECK`: Queries about certificate expiration
- `REVOCATION_STATUS`: Queries about revoked certificates  
- `PKI_ENGINE_FILTER`: Queries filtering by PKI engine
- `AUDIT_TRAIL`: Queries for certificate audit events
- `ISSUER_ATTRIBUTION`: Queries about certificate issuers
- `HELP_REQUEST`: Requests for usage guidance

### AuditEventType  
- `CERTIFICATE_ISSUED`: New certificate issuance
- `CERTIFICATE_REVOKED`: Certificate revocation
- `CERTIFICATE_RENEWED`: Certificate renewal operation

## Relationships

```
User Query (1) → (1) Query Result
Query Result (1) → (0..n) Certificate Summary
Query Result (1) → (0..n) Audit Event  
Query Result (1) → (0..n) PKI Engine Info
Certificate Summary (n) → (1) PKI Engine Info
Audit Event (n) → (1) Certificate Summary
```

## Data Flow

1. **Query Processing**: User submits natural language query → QueryType classification → Parameter extraction
2. **MCP Tool Invocation**: Based on QueryType → Call appropriate MCP tools → Receive structured responses
3. **Result Aggregation**: Transform MCP responses → Build Certificate/Audit/Engine objects → Create QueryResult
4. **UI Presentation**: Format QueryResult → Display in Streamlit interface → Store in session history