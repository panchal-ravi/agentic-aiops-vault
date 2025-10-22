"""Pydantic models for Certificate and CA hierarchy entities."""

import re
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class Certificate(BaseModel):
    """Represents an X.509 certificate issued by a PKI secrets engine.

    Attributes:
        serial_number: Unique serial number in colon-separated hex format
        subject_cn: Subject Common Name from certificate
        issuer_cn: Issuer Common Name from certificate
        issuer_id: Vault UUID reference to issuer entity
        not_before: Certificate validity start date
        not_after: Certificate validity end date
        is_expired: Whether certificate is past validity period
        is_revoked: Whether certificate has been revoked
        revocation_time: When certificate was revoked (if applicable)
        pem_data: Full PEM-encoded certificate (excluded from default serialization)
    """

    serial_number: str = Field(
        ..., description="Unique serial number in colon-separated hex format"
    )
    subject_cn: str = Field(..., min_length=1, description="Subject Common Name")
    issuer_cn: str = Field(..., min_length=1, description="Issuer Common Name")
    issuer_id: str | None = Field(None, description="Vault UUID reference to issuer")
    not_before: datetime = Field(..., description="Certificate validity start date")
    not_after: datetime = Field(..., description="Certificate validity end date")
    is_expired: bool = Field(..., description="Whether certificate is expired")
    is_revoked: bool = Field(..., description="Whether certificate has been revoked")
    revocation_time: datetime | None = Field(None, description="When certificate was revoked")
    pem_data: str | None = Field(None, exclude=True, description="Full PEM-encoded certificate")

    @field_validator("serial_number")
    @classmethod
    def validate_serial_format(cls, v: str) -> str:
        """Validate serial number is in colon-separated hex format."""
        pattern = r"^([0-9a-f]{2}:)+[0-9a-f]{2}$"
        if not re.match(pattern, v.lower()):
            raise ValueError(f"Serial number must be colon-separated hex format, got '{v}'")
        return v

    @field_validator("not_after")
    @classmethod
    def validate_date_order(cls, v: datetime, info) -> datetime:
        """Ensure not_after is after not_before."""
        if "not_before" in info.data and v <= info.data["not_before"]:
            raise ValueError("not_after must be after not_before")
        return v

    model_config = {
        "json_encoders": {datetime: lambda v: v.isoformat()},
        "json_schema_extra": {
            "example": {
                "serial_number": "39:4e:fa:01:23:45:67:89",
                "subject_cn": "webserver.example.com",
                "issuer_cn": "Intermediate CA",
                "issuer_id": "a1b2c3d4-5678-90ab-cdef-1234567890ab",
                "not_before": "2024-01-01T00:00:00Z",
                "not_after": "2025-01-01T00:00:00Z",
                "is_expired": False,
                "is_revoked": False,
            }
        },
    }


class Issuer(BaseModel):
    """Represents a Certificate Authority (root or intermediate) in PKI hierarchy.

    Attributes:
        issuer_id: Vault UUID for the issuer
        issuer_cn: Common Name of the CA certificate
        issuer_type: "root" or "intermediate"
        parent_issuer_id: UUID of parent CA (null for root CAs)
        ca_chain: PEM-encoded CA certificate chain
        is_active: Whether issuer is currently available in Vault
        certificate: PEM-encoded issuer certificate
    """

    issuer_id: str = Field(..., description="Vault UUID for the issuer")
    issuer_cn: str = Field(..., min_length=1, description="Common Name of the CA")
    issuer_type: str = Field(..., description="Type of CA: root or intermediate")
    parent_issuer_id: str | None = Field(None, description="UUID of parent CA (null for root)")
    ca_chain: list[str] = Field(..., description="PEM-encoded CA certificate chain")
    is_active: bool = Field(..., description="Whether issuer is available in Vault")
    certificate: str | None = Field(None, description="PEM-encoded issuer certificate")

    @field_validator("issuer_type")
    @classmethod
    def validate_issuer_type(cls, v: str) -> str:
        """Ensure issuer_type is 'root' or 'intermediate'."""
        if v not in ["root", "intermediate"]:
            raise ValueError(f"issuer_type must be 'root' or 'intermediate', got '{v}'")
        return v

    @field_validator("ca_chain")
    @classmethod
    def validate_ca_chain_not_empty(cls, v: list[str]) -> list[str]:
        """Ensure ca_chain is not empty."""
        if not v:
            raise ValueError("ca_chain must not be empty")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "issuer_id": "a1b2c3d4-5678-90ab-cdef-1234567890ab",
                "issuer_cn": "Intermediate CA",
                "issuer_type": "intermediate",
                "parent_issuer_id": "b2c3d4e5-6789-01bc-def0-234567890abc",
                "ca_chain": ["-----BEGIN CERTIFICATE-----\\n..."],
                "is_active": True,
            }
        }
    }


class Warning(BaseModel):
    """Warning for permission errors or missing data.

    Attributes:
        type: Type of warning (permission_denied, parse_error, missing_issuer, etc.)
        resource: Resource path or identifier
        message: Human-readable description
    """

    type: str = Field(..., description="Type of warning")
    resource: str = Field(..., description="Resource path or identifier")
    message: str = Field(..., min_length=1, description="Human-readable description")

    @field_validator("type")
    @classmethod
    def validate_warning_type(cls, v: str) -> str:
        """Validate warning type is one of the expected values."""
        valid_types = ["permission_denied", "parse_error", "missing_issuer", "inactive_issuer"]
        if v not in valid_types:
            raise ValueError(f"Warning type must be one of {valid_types}, got '{v}'")
        return v


class HierarchyMetadata(BaseModel):
    """Summary statistics for certificate hierarchy.

    Attributes:
        total_certificates: Total number of certificates
        expired_count: Number of expired certificates
        revoked_count: Number of revoked certificates
        root_ca_count: Number of root CAs
        intermediate_ca_count: Number of intermediate CAs
    """

    total_certificates: int = Field(..., ge=0, description="Total number of certificates")
    expired_count: int = Field(..., ge=0, description="Number of expired certificates")
    revoked_count: int = Field(..., ge=0, description="Number of revoked certificates")
    root_ca_count: int = Field(..., ge=0, description="Number of root CAs")
    intermediate_ca_count: int = Field(..., ge=0, description="Number of intermediate CAs")


class IntermediateIssuerGroup(BaseModel):
    """Group of certificates issued by an intermediate CA.

    Attributes:
        intermediate_cn: Intermediate CA common name
        intermediate_issuer_id: UUID or null if inactive
        certificates: Leaf certificates issued by this intermediate
    """

    intermediate_cn: str = Field(..., description="Intermediate CA common name")
    intermediate_issuer_id: str | None = Field(None, description="UUID or null if inactive")
    certificates: list[Certificate] = Field(default_factory=list, description="Leaf certificates")


class RootIssuerGroup(BaseModel):
    """Group of certificates under a root CA.

    Attributes:
        root_cn: Root CA common name
        root_issuer_id: UUID or null if inactive
        intermediate_groups: Intermediate CA groups under this root
        direct_certificates: Certificates issued directly by root CA
    """

    root_cn: str = Field(..., description="Root CA common name")
    root_issuer_id: str | None = Field(None, description="UUID or null if inactive")
    intermediate_groups: list[IntermediateIssuerGroup] = Field(
        default_factory=list, description="Intermediate CA groups"
    )
    direct_certificates: list[Certificate] = Field(
        default_factory=list, description="Certificates issued directly by root"
    )


class CertificateHierarchy(BaseModel):
    """Complete certificate hierarchy grouped by root and intermediate CAs.

    Attributes:
        root_issuers: List of root CA groups
        warnings: Warnings for permission errors or missing data
        metadata: Summary statistics
    """

    root_issuers: list[RootIssuerGroup] = Field(
        default_factory=list, description="List of root CA groups"
    )
    warnings: list[Warning] = Field(
        default_factory=list, description="Warnings for errors or missing data"
    )
    metadata: HierarchyMetadata = Field(..., description="Summary statistics")

    @field_validator("root_issuers")
    @classmethod
    def validate_not_empty_without_warnings(
        cls, v: list[RootIssuerGroup], info
    ) -> list[RootIssuerGroup]:
        """Ensure at least one root issuer or warning exists."""
        if not v and "warnings" in info.data and not info.data["warnings"]:
            raise ValueError("Must have at least one root issuer or warning")
        return v
