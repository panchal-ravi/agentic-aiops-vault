"""Certificate parsing service for X.509 certificate operations.

This module provides parsing functionality for X.509 certificates including:
- PEM certificate parsing and validation
- Expiration status checking
- Revocation status checking (placeholder for CRL/OCSP checks)
- Graceful degradation for malformed certificate data
"""

import logging
from datetime import datetime, timezone

from cryptography import x509

from ..models.certificate import Certificate


class CertificateParserError(Exception):
    """Base exception for certificate parsing errors."""

    pass


class CertificateParseError(CertificateParserError):
    """Raised when certificate PEM parsing fails."""

    pass


class CertificateParser:
    """Service for parsing X.509 certificates and extracting metadata.

    Provides methods to:
    - Parse PEM-encoded certificates
    - Extract subject and issuer information
    - Check expiration status
    - Check revocation status (placeholder)
    - Handle malformed certificate data gracefully
    """

    @staticmethod
    def parse_pem(
        pem_data: str,
        serial_number: str | None = None,
        issuer_id: str | None = None,
        revocation_time: datetime | None = None,
    ) -> Certificate:
        """Parse PEM-encoded certificate and extract metadata.

        Args:
            pem_data: PEM-encoded certificate string
            serial_number: Optional serial number (will extract from cert if not provided)
            issuer_id: Optional Vault issuer UUID
            revocation_time: Optional revocation timestamp

        Returns:
            Certificate: Parsed certificate with metadata

        Raises:
            CertificateParseError: If certificate parsing fails
        """
        try:
            # Parse the PEM certificate
            cert = x509.load_pem_x509_certificate(pem_data.encode())

            # Extract serial number
            if not serial_number:
                # Convert serial to colon-separated hex format
                serial_hex = f"{cert.serial_number:x}"
                # Pad to even length
                if len(serial_hex) % 2:
                    serial_hex = "0" + serial_hex
                # Add colons every 2 characters
                serial_number = ":".join(
                    serial_hex[i : i + 2] for i in range(0, len(serial_hex), 2)
                )

            # Extract subject CN
            subject_cn = CertificateParser._extract_cn_from_name(cert.subject)
            if not subject_cn:
                subject_cn = "Unknown"
                logging.warning(f"Certificate {serial_number}: No subject CN found")

            # Extract issuer CN
            issuer_cn = CertificateParser._extract_cn_from_name(cert.issuer)
            if not issuer_cn:
                issuer_cn = "Unknown"
                logging.warning(f"Certificate {serial_number}: No issuer CN found")

            # Extract validity dates
            not_before = cert.not_valid_before.replace(tzinfo=timezone.utc)
            not_after = cert.not_valid_after.replace(tzinfo=timezone.utc)

            # Check if expired
            now = datetime.now(timezone.utc)
            is_expired = now > not_after

            # Check if revoked (using provided revocation_time)
            is_revoked = revocation_time is not None

            return Certificate(
                serial_number=serial_number,
                subject_cn=subject_cn,
                issuer_cn=issuer_cn,
                issuer_id=issuer_id,
                not_before=not_before,
                not_after=not_after,
                is_expired=is_expired,
                is_revoked=is_revoked,
                revocation_time=revocation_time,
                pem_data=pem_data,
            )

        except ValueError as e:
            raise CertificateParseError(f"Certificate parsing error: {str(e)}") from e
        except Exception as e:
            raise CertificateParseError(f"Unexpected error parsing certificate: {str(e)}") from e

    @staticmethod
    def parse_pem_safe(
        pem_data: str,
        serial_number: str | None = None,
        issuer_id: str | None = None,
        revocation_time: datetime | None = None,
    ) -> Certificate:
        """Parse PEM certificate with graceful degradation for malformed data.

        This method implements FR-018 requirement for graceful degradation.
        If parsing fails, returns a Certificate with available data and
        "N/A" or "Unknown" values for missing fields.

        Args:
            pem_data: PEM-encoded certificate string
            serial_number: Optional serial number
            issuer_id: Optional Vault issuer UUID
            revocation_time: Optional revocation timestamp

        Returns:
            Certificate: Parsed certificate or degraded certificate with available data
        """
        try:
            return CertificateParser.parse_pem(pem_data, serial_number, issuer_id, revocation_time)
        except CertificateParseError as e:
            logging.warning(f"Certificate parsing failed, using degraded data: {str(e)}")

            # Create degraded certificate with minimal data
            fallback_serial = serial_number if serial_number else "N/A"
            now = datetime.now(timezone.utc)

            return Certificate(
                serial_number=fallback_serial,
                subject_cn="Unknown",
                issuer_cn="Unknown",
                issuer_id=issuer_id,
                not_before=now,  # Use current time as fallback
                not_after=now,  # Use current time as fallback (will be marked expired)
                is_expired=True,  # Mark as expired since we can't determine validity
                is_revoked=revocation_time is not None,
                revocation_time=revocation_time,
                pem_data=pem_data,
            )

    @staticmethod
    def _extract_cn_from_name(name: x509.Name) -> str | None:
        """Extract Common Name (CN) from X.509 Name object.

        Args:
            name: X.509 Name object (subject or issuer)

        Returns:
            str: Common Name if found, None otherwise
        """
        try:
            cn_attributes = name.get_attributes_for_oid(x509.NameOID.COMMON_NAME)
            if cn_attributes:
                return cn_attributes[0].value
        except Exception as e:
            logging.warning(f"Error extracting CN from name: {str(e)}")

        return None

    @staticmethod
    def is_certificate_expired(cert: Certificate) -> bool:
        """Check if certificate is expired based on current time.

        Args:
            cert: Certificate to check

        Returns:
            bool: True if certificate is expired
        """
        now = datetime.now(timezone.utc)
        return now > cert.not_after

    @staticmethod
    def days_until_expiry(cert: Certificate) -> int:
        """Calculate days until certificate expiry.

        Args:
            cert: Certificate to check

        Returns:
            int: Days until expiry (negative if already expired)
        """
        now = datetime.now(timezone.utc)
        delta = cert.not_after - now
        return delta.days

    @staticmethod
    def extract_issuer_from_ca_chain(ca_chain: list[str]) -> str | None:
        """Extract issuer CN from the first certificate in CA chain.

        The first certificate in the chain is typically the immediate issuer.
        This is used when the certificate itself doesn't have issuer info.

        Args:
            ca_chain: List of PEM-encoded certificates

        Returns:
            str: Issuer CN if found, None otherwise
        """
        if not ca_chain:
            return None

        try:
            # Parse the first certificate in the chain (immediate issuer)
            first_cert = x509.load_pem_x509_certificate(ca_chain[0].encode())
            return CertificateParser._extract_cn_from_name(first_cert.subject)
        except Exception as e:
            logging.warning(f"Error extracting issuer from CA chain: {str(e)}")
            return None

    @staticmethod
    def extract_root_ca_from_chain(ca_chain: list[str]) -> str | None:
        """Extract root CA CN from the last certificate in CA chain.

        The last certificate in the chain is typically the root CA.

        Args:
            ca_chain: List of PEM-encoded certificates

        Returns:
            str: Root CA CN if found, None otherwise
        """
        if not ca_chain:
            return None

        try:
            # Parse the last certificate in the chain (root CA)
            last_cert = x509.load_pem_x509_certificate(ca_chain[-1].encode())
            return CertificateParser._extract_cn_from_name(last_cert.subject)
        except Exception as e:
            logging.warning(f"Error extracting root CA from chain: {str(e)}")
            return None

    @staticmethod
    def is_self_signed(pem_data: str) -> bool:
        """Check if certificate is self-signed (subject == issuer).

        Args:
            pem_data: PEM-encoded certificate

        Returns:
            bool: True if certificate is self-signed
        """
        try:
            cert = x509.load_pem_x509_certificate(pem_data.encode())
            return cert.subject == cert.issuer
        except Exception as e:
            logging.warning(f"Error checking if certificate is self-signed: {str(e)}")
            return False

    @staticmethod
    def format_serial_number(serial_int: int) -> str:
        """Format serial number integer as colon-separated hex string.

        Args:
            serial_int: Serial number as integer

        Returns:
            str: Colon-separated hex format (e.g., "39:4e:fa:01")
        """
        # Convert to hex, remove 0x prefix
        hex_str = f"{serial_int:x}"

        # Pad to even length
        if len(hex_str) % 2:
            hex_str = "0" + hex_str

        # Add colons every 2 characters
        return ":".join(hex_str[i : i + 2] for i in range(0, len(hex_str), 2))
