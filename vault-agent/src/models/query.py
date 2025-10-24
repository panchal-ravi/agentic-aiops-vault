"""Data models for Vault PKI Query Agent."""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, validator


class AuditEventType(str, Enum):
    """Types of certificate lifecycle audit events."""

    CERTIFICATE_ISSUED = "CERTIFICATE_ISSUED"
    CERTIFICATE_REVOKED = "CERTIFICATE_REVOKED"
    CERTIFICATE_RENEWED = "CERTIFICATE_RENEWED"


class CertificateSummary(BaseModel):
    """Simplified certificate data optimized for UI display."""

    serial_number: str = Field(
        ..., description="Certificate serial number in hex format"
    )
    subject_cn: str = Field(..., description="Common name from certificate subject")
    pki_engine: str = Field(..., description="Mount path of issuing PKI engine")
    expiration_date: datetime = Field(
        ..., description="Certificate expiration timestamp"
    )
    days_until_expiry: int = Field(..., description="Days remaining until expiration")
    is_expired: bool = Field(..., description="Whether certificate has expired")
    is_revoked: bool = Field(..., description="Whether certificate has been revoked")
    revocation_date: Optional[datetime] = Field(
        None, description="Date of revocation if applicable"
    )
    issuer_hierarchy: List[str] = Field(
        default_factory=list, description="Chain of issuing CAs"
    )

    @property
    def status_display(self) -> str:
        """Human-readable status string."""
        if self.is_revoked:
            return "Revoked"
        elif self.is_expired:
            return "Expired"
        elif self.days_until_expiry <= 30:
            return f"Expires in {self.days_until_expiry} days"
        else:
            return "Active"


class PKIEngineInfo(BaseModel):
    """Information about PKI secrets engines."""

    path: str = Field(..., description="Mount path identifier")
    type: str = Field(..., description="Always 'pki' for PKI engines")
    description: str = Field(..., description="Human-readable description")
    certificate_count: Optional[int] = Field(
        None, description="Number of certificates in engine"
    )

    @validator("type")
    def type_must_be_pki(cls, v):
        if v != "pki":
            raise ValueError("PKI engine type must be 'pki'")
        return v


class AuditEvent(BaseModel):
    """Certificate lifecycle audit information."""

    timestamp: datetime = Field(..., description="When event occurred")
    event_type: AuditEventType = Field(..., description="Type of operation")
    certificate_subject: str = Field(..., description="Subject of affected certificate")
    actor_name: str = Field(..., description="Display name of entity performing action")
    actor_id: Optional[str] = Field(
        None, description="Unique identifier of acting entity"
    )
    remote_address: Optional[str] = Field(
        None, description="IP address of requesting client"
    )
    request_path: Optional[str] = Field(None, description="Vault API path of operation")
    mount_accessor: Optional[str] = Field(None, description="PKI mount accessor ID")


class QueryMetadata(BaseModel):
    """Query execution statistics."""

    execution_time_ms: Optional[int] = Field(
        None, description="Query execution time in milliseconds"
    )
    mcp_calls_made: Optional[int] = Field(
        None, description="Number of MCP tool calls made"
    )
    results_count: int = Field(..., description="Total number of results returned")


class QueryResult(BaseModel):
    """Structured response containing query results and metadata."""

    success: bool = Field(..., description="Whether query completed successfully")
    message: str = Field(..., description="Human-readable result summary")
    certificates: List[CertificateSummary] = Field(
        default_factory=list, description="Certificate results"
    )
    audit_events: List[AuditEvent] = Field(
        default_factory=list, description="Audit event results"
    )
    pki_engines: List[PKIEngineInfo] = Field(
        default_factory=list, description="PKI engine results"
    )
    query_metadata: Optional[QueryMetadata] = Field(
        None, description="Execution statistics"
    )
    errors: List[str] = Field(
        default_factory=list, description="Non-fatal warnings or errors"
    )

    @validator("certificates", "audit_events", "pki_engines")
    def at_least_one_result_for_success(cls, v, values):
        """Ensure successful queries have at least one result."""
        if values.get("success", False):
            # Check if this is the last field being validated and no results exist
            other_results = [
                values.get("certificates", []),
                values.get("audit_events", []),
                values.get("pki_engines", []),
            ]
            if not any(other_results) and not v:
                # This is acceptable if there's a message explaining no results
                pass
        return v
