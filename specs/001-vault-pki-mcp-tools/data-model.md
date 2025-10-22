# Data Model: HashiCorp Vault PKI MCP Tools

**Date**: 2025-10-22  
**Feature**: HashiCorp Vault PKI MCP Tools  
**Purpose**: Entity definitions and relationships for PKI certificate hierarchy

## Overview

This document defines the data models used throughout the Vault PKI MCP tools implementation. Models are implemented as Pydantic classes for validation and serialization.

## Core Entities

### 1. PKISecretsEngine

Represents a mounted PKI secrets engine in HashiCorp Vault.

**Fields**:
- `path` (str, required): Mount path of the PKI secrets engine (e.g., "pki/", "pki_int/")
- `type` (str, required): Secrets engine type, always "pki" for this entity
- `description` (str, optional): Human-readable description of the PKI mount
- `config` (dict, optional): Configuration details (max_lease_ttl, default_lease_ttl)

**Validation Rules**:
- `path` must not be empty
- `type` must equal "pki"
- `path` normalized to remove trailing slash for consistency

**State Transitions**: N/A (read-only entity)

**Example**:
```json
{
  "path": "pki",
  "type": "pki",
  "description": "Root CA for production environment",
  "config": {
    "default_lease_ttl": 86400,
    "max_lease_ttl": 31536000
  }
}
```

---

### 2. Certificate

Represents an X.509 certificate issued by a PKI secrets engine.

**Fields**:
- `serial_number` (str, required): Unique serial number in colon-separated hex format (e.g., "39:4e:fa:01:23")
- `subject_cn` (str, required): Subject Common Name from certificate
- `issuer_cn` (str, required): Issuer Common Name from certificate
- `issuer_id` (str, optional): Vault UUID reference to issuer entity
- `not_before` (datetime, required): Certificate validity start date
- `not_after` (datetime, required): Certificate validity end date
- `is_expired` (bool, required): Whether certificate is past validity period
- `is_revoked` (bool, required): Whether certificate has been revoked
- `revocation_time` (datetime, optional): When certificate was revoked (if applicable)
- `pem_data` (str, optional): Full PEM-encoded certificate (excluded from default serialization)

**Validation Rules**:
- `serial_number` must match hex format pattern
- `not_after` must be after `not_before`
- `is_expired` computed from `not_after` vs current UTC time
- `is_revoked` requires `revocation_time` if True
- `subject_cn` and `issuer_cn` must not be empty

**State Transitions**:
- Valid → Expired: When current time exceeds `not_after`
- Active → Revoked: When administrator revokes certificate (irreversible)

**Example**:
```json
{
  "serial_number": "39:4e:fa:01:23:45:67:89",
  "subject_cn": "webserver.example.com",
  "issuer_cn": "Intermediate CA",
  "issuer_id": "a1b2c3d4-5678-90ab-cdef-1234567890ab",
  "not_before": "2024-01-01T00:00:00Z",
  "not_after": "2025-01-01T00:00:00Z",
  "is_expired": false,
  "is_revoked": false,
  "revocation_time": null
}
```

---

### 3. Issuer

Represents a Certificate Authority (root or intermediate) in the PKI hierarchy.

**Fields**:
- `issuer_id` (str, required): Vault UUID for the issuer
- `issuer_cn` (str, required): Common Name of the CA certificate
- `issuer_type` (str, required): "root" or "intermediate"
- `parent_issuer_id` (str, optional): UUID of parent CA (null for root CAs)
- `ca_chain` (List[str], required): PEM-encoded CA certificate chain
- `is_active` (bool, required): Whether issuer is currently available in Vault
- `certificate` (str, optional): PEM-encoded issuer certificate

**Validation Rules**:
- `issuer_id` must be valid UUID format
- `issuer_type` must be "root" or "intermediate"
- Root CAs must have `parent_issuer_id` as null
- Intermediate CAs must have non-null `parent_issuer_id`
- `ca_chain` must not be empty

**State Transitions**:
- Active → Inactive: When issuer is rotated or removed from Vault

**Example**:
```json
{
  "issuer_id": "a1b2c3d4-5678-90ab-cdef-1234567890ab",
  "issuer_cn": "Intermediate CA",
  "issuer_type": "intermediate",
  "parent_issuer_id": "b2c3d4e5-6789-01bc-def0-234567890abc",
  "ca_chain": ["-----BEGIN CERTIFICATE-----\n...", "-----BEGIN CERTIFICATE-----\n..."],
  "is_active": true
}
```

---

### 4. CertificateHierarchy

Represents the complete certificate hierarchy grouped by root and intermediate CAs.

**Fields**:
- `root_issuers` (List[RootIssuerGroup], required): List of root CA groups
- `warnings` (List[Warning], optional): Warnings for permission errors or missing data
- `metadata` (HierarchyMetadata, required): Summary statistics

**Nested Structure**:

```python
class RootIssuerGroup:
    root_cn: str                           # Root CA common name
    root_issuer_id: str | None             # UUID or null if inactive
    intermediate_groups: List[IntermediateIssuerGroup]
    direct_certificates: List[Certificate]  # Certs issued directly by root

class IntermediateIssuerGroup:
    intermediate_cn: str                   # Intermediate CA common name
    intermediate_issuer_id: str | None     # UUID or null if inactive
    certificates: List[Certificate]        # Leaf certificates

class Warning:
    type: str                              # "permission_denied", "parse_error", "missing_issuer"
    resource: str                          # Resource path or identifier
    message: str                           # Human-readable description

class HierarchyMetadata:
    total_certificates: int
    expired_count: int
    revoked_count: int
    root_ca_count: int
    intermediate_ca_count: int
```

**Validation Rules**:
- At least one root issuer or warning must exist (not both empty)
- Certificate counts in metadata must match actual certificate lists
- Warnings must have non-empty type and message

**Example**:
```json
{
  "root_issuers": [
    {
      "root_cn": "Root CA",
      "root_issuer_id": "b2c3d4e5-6789-01bc-def0-234567890abc",
      "intermediate_groups": [
        {
          "intermediate_cn": "Intermediate CA",
          "intermediate_issuer_id": "a1b2c3d4-5678-90ab-cdef-1234567890ab",
          "certificates": [
            {
              "serial_number": "39:4e:fa:01:23:45:67:89",
              "subject_cn": "webserver.example.com",
              "issuer_cn": "Intermediate CA",
              "is_expired": false,
              "is_revoked": false
            }
          ]
        }
      ],
      "direct_certificates": []
    }
  ],
  "warnings": [],
  "metadata": {
    "total_certificates": 1,
    "expired_count": 0,
    "revoked_count": 0,
    "root_ca_count": 1,
    "intermediate_ca_count": 1
  }
}
```

---

## Relationships

### Certificate → Issuer
- **Type**: Many-to-One
- **Description**: Each certificate is issued by exactly one CA (issuer)
- **Implementation**: `Certificate.issuer_id` references `Issuer.issuer_id`
- **Constraints**: `issuer_id` may be null for certificates with inactive issuers

### Issuer → Parent Issuer
- **Type**: Many-to-One (self-referential)
- **Description**: Intermediate CAs reference their parent CA (root or intermediate)
- **Implementation**: `Issuer.parent_issuer_id` references another `Issuer.issuer_id`
- **Constraints**: Root CAs have null `parent_issuer_id`

### PKISecretsEngine → Certificate
- **Type**: One-to-Many
- **Description**: Each PKI secrets engine can issue multiple certificates
- **Implementation**: Implicit via API queries (certificates fetched by mount path)
- **Constraints**: Certificates only exist within context of their PKI mount

### CertificateHierarchy → Root Issuer → Intermediate Issuer → Certificate
- **Type**: Hierarchical composition
- **Description**: Represents the full trust chain from root CA to leaf certificates
- **Implementation**: Nested structure in `CertificateHierarchy` model
- **Constraints**: Ensures proper grouping for reporting and auditing

---

## Entity Lifecycle

### Certificate Lifecycle States

```
┌─────────┐  Issue   ┌────────┐  Time   ┌─────────┐
│ (None)  │─────────→│ Valid  │────────→│ Expired │
└─────────┘          └───┬────┘         └─────────┘
                         │                     │
                         │ Revoke              │ Revoke
                         ↓                     ↓
                    ┌─────────┐          ┌──────────────┐
                    │ Revoked │          │ Revoked +    │
                    │         │          │ Expired      │
                    └─────────┘          └──────────────┘
```

**Transitions**:
1. **Issue**: Certificate created by Vault PKI, starts in Valid state
2. **Time**: Automatic transition to Expired when `not_after` is reached
3. **Revoke**: Administrator action, irreversible, can happen in Valid or Expired state

### Issuer Lifecycle States

```
┌─────────┐  Create   ┌────────┐  Rotate/Remove  ┌──────────┐
│ (None)  │──────────→│ Active │────────────────→│ Inactive │
└─────────┘           └────────┘                 └──────────┘
```

**Transitions**:
1. **Create**: Issuer created in Vault PKI, starts in Active state
2. **Rotate/Remove**: CA key rotation or issuer deletion, becomes Inactive

---

## Derived Fields

### Certificate.is_expired
- **Computation**: `datetime.now(timezone.utc) > certificate.not_after`
- **Type**: Boolean
- **Purpose**: Quick identification of expired certificates

### Certificate.is_revoked
- **Computation**: Check if `serial_number` exists in Vault's revocation list OR `revocation_time` is not null
- **Type**: Boolean
- **Purpose**: Security auditing and compliance

### Issuer.issuer_type
- **Computation**: 
  - "root" if `parent_issuer_id` is null AND certificate is self-signed (subject == issuer)
  - "intermediate" if `parent_issuer_id` is not null OR certificate issued by another CA
- **Type**: String enum ["root", "intermediate"]
- **Purpose**: Hierarchy construction

### HierarchyMetadata.expired_count
- **Computation**: Count of certificates where `is_expired == True`
- **Type**: Integer
- **Purpose**: Summary statistics for reporting

### HierarchyMetadata.revoked_count
- **Computation**: Count of certificates where `is_revoked == True`
- **Type**: Integer
- **Purpose**: Summary statistics for reporting

---

## Special Cases

### 1. Inactive Issuer
When a certificate references an `issuer_id` that no longer exists in Vault:
- `Issuer.is_active` = False
- `Certificate.issuer_cn` displays actual CN from cert + "(issuer inactive)" notation
- Warning added to `CertificateHierarchy.warnings`

### 2. Direct Root Issuance
When a certificate is issued directly by root CA (no intermediate):
- Certificate appears in `RootIssuerGroup.direct_certificates`
- No `IntermediateIssuerGroup` created for this certificate
- `Certificate.issuer_cn` equals root CA CN

### 3. Multi-Level Intermediate Chain
When certificate chain has multiple intermediate CAs (root → int1 → int2 → leaf):
- Only immediate parent shown in primary grouping
- Full chain available in `Issuer.ca_chain` for detailed inspection
- Future enhancement: Recursive intermediate grouping

### 4. Orphaned Certificate
When certificate has no resolvable issuer (corrupt data or permission issue):
- Group under "Unknown Root" with `root_issuer_id` = null
- `Certificate.issuer_cn` uses value from certificate metadata
- Warning added with type "missing_issuer"

### 5. Malformed Certificate Data
When certificate PEM parsing fails or fields are missing:
- Include certificate in results with available fields
- Missing fields set to "N/A" or "Unknown"
- Warning added with type "parse_error"

---

## Data Flow

```
Vault API           Services              Models
─────────           ────────              ──────

sys/mounts    →    VaultClient      →    PKISecretsEngine
                   .list_mounts()

<pki>/certs   →    VaultClient      →    List[serial_number]
                   .list_certs()

<pki>/cert/   →    CertificateParser →   Certificate
<serial>           .parse_pem()          (with is_expired, is_revoked)

<pki>/issuer/ →    CertificateParser →   Issuer
<issuer_id>        .parse_ca_chain()     (with parent resolution)

Aggregation   →    HierarchyBuilder  →   CertificateHierarchy
                   .build_hierarchy()    (grouped by root/intermediate)
```

---

## Model Implementation Notes

### Pydantic Configuration

```python
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import List, Optional

class Certificate(BaseModel):
    serial_number: str = Field(..., pattern=r'^([0-9a-f]{2}:)+[0-9a-f]{2}$')
    subject_cn: str = Field(..., min_length=1)
    issuer_cn: str = Field(..., min_length=1)
    issuer_id: Optional[str] = None
    not_before: datetime
    not_after: datetime
    is_expired: bool
    is_revoked: bool
    revocation_time: Optional[datetime] = None
    
    @field_validator('not_after')
    def validate_dates(cls, v, info):
        if info.data.get('not_before') and v <= info.data['not_before']:
            raise ValueError('not_after must be after not_before')
        return v
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
```

### JSON Serialization

- Use ISO 8601 format for datetime fields
- Exclude `pem_data` from default serialization (large field)
- Include computed fields (`is_expired`, `is_revoked`) in output
- Pretty-print JSON for debugging (configurable)

### Validation Strategy

- **Constructor Validation**: Pydantic validates all fields on creation
- **Business Logic Validation**: Services validate relationships (e.g., issuer_id exists)
- **API Response Validation**: Validate Vault API responses match expected schema
- **Graceful Degradation**: Mark invalid fields as "N/A" instead of failing (per FR-018)

---

## Summary

This data model provides a complete representation of Vault PKI certificate hierarchies with proper validation, relationships, and error handling. The hierarchical structure (Root → Intermediate → Certificate) enables intuitive reporting and auditing while handling edge cases like inactive issuers and permission errors gracefully.
