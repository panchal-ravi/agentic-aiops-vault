"""Certificate-specific data models and utilities."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class CertificateDetails(BaseModel):
    """Detailed certificate information from Vault API."""

    serial_number: str = Field(..., description="Certificate serial number")
    certificate_pem: str = Field(..., description="PEM-encoded certificate")
    issuing_ca: Optional[str] = Field(None, description="Issuing CA certificate")
    ca_chain: List[str] = Field(default_factory=list, description="Full CA chain")
    private_key: Optional[str] = Field(None, description="Private key if available")
    private_key_type: Optional[str] = Field(None, description="Private key type")


class CertificateFilter(BaseModel):
    """Criteria for filtering certificates."""

    pki_engine: Optional[str] = Field(
        None, description="PKI engine mount path to filter by"
    )
    expired: Optional[bool] = Field(None, description="Filter by expiration status")
    revoked: Optional[bool] = Field(None, description="Filter by revocation status")
    expiring_within_days: Optional[int] = Field(
        None, description="Filter by days until expiration"
    )
    subject_pattern: Optional[str] = Field(
        None, description="Pattern to match in subject CN"
    )


def calculate_days_until_expiry(expiration_date: datetime) -> int:
    """Calculate days until certificate expiration.

    Args:
        expiration_date: Certificate expiration timestamp

    Returns:
        int: Days until expiration (negative if expired)
    """
    now = datetime.now()
    # Handle timezone-aware vs naive datetime
    if expiration_date.tzinfo is not None and now.tzinfo is None:
        from datetime import timezone

        now = now.replace(tzinfo=timezone.utc)
    elif expiration_date.tzinfo is None and now.tzinfo is not None:
        now = now.replace(tzinfo=None)

    delta = expiration_date - now
    return delta.days


def format_expiry_display(days_until_expiry: int) -> str:
    """Format expiry information for user display.

    Args:
        days_until_expiry: Days until expiration (negative if expired)

    Returns:
        str: Human-readable expiry status
    """
    if days_until_expiry < 0:
        return f"Expired {abs(days_until_expiry)} days ago"
    elif days_until_expiry == 0:
        return "Expires today"
    elif days_until_expiry == 1:
        return "Expires tomorrow"
    elif days_until_expiry <= 30:
        return f"Expires in {days_until_expiry} days"
    elif days_until_expiry <= 365:
        weeks = days_until_expiry // 7
        return f"Expires in {weeks} weeks"
    else:
        years = days_until_expiry // 365
        remaining_days = days_until_expiry % 365
        if remaining_days < 30:
            return f"Expires in {years} years"
        else:
            months = remaining_days // 30
            return f"Expires in {years} years, {months} months"
