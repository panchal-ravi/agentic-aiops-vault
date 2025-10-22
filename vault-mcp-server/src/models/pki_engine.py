"""Pydantic models for PKI Secrets Engine entities."""

from pydantic import BaseModel, Field, field_validator


class PKISecretsEngine(BaseModel):
    """Represents a mounted PKI secrets engine in HashiCorp Vault.

    Attributes:
        path: Mount path of the PKI secrets engine (e.g., "pki", "pki_int")
        type: Secrets engine type, always "pki" for this entity
        description: Human-readable description of the PKI mount
        config: Configuration details (max_lease_ttl, default_lease_ttl)
    """

    path: str = Field(..., min_length=1, description="Mount path of the PKI secrets engine")
    type: str = Field(..., description="Secrets engine type, must be 'pki'")
    description: str | None = Field(None, description="Human-readable description of the PKI mount")
    config: dict | None = Field(None, description="Configuration details")

    @field_validator("path")
    @classmethod
    def normalize_path(cls, v: str) -> str:
        """Normalize path by removing trailing slash for consistency."""
        return v.rstrip("/")

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        """Ensure type is 'pki'."""
        if v != "pki":
            raise ValueError(f"Type must be 'pki', got '{v}'")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "path": "pki",
                "type": "pki",
                "description": "Root CA for production environment",
                "config": {"default_lease_ttl": 86400, "max_lease_ttl": 31536000},
            }
        }
    }
