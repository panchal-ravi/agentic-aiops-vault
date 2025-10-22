"""Simplified certificate list builder service.

This module provides functionality to build simplified certificate lists
from Vault PKI data with the specific fields requested by the user.
"""

import asyncio
import logging
from datetime import datetime, UTC
from typing import Any

from cryptography import x509

from ..services.certificate_parser import CertificateParser
from ..services.vault_client import (
    VaultClient,
    VaultConnectionError,
    VaultPermissionError,
)


class SimplifiedCertificateBuilderError(Exception):
    """Base exception for simplified certificate builder errors."""

    pass


class SimplifiedCertificateBuilder:
    """Service for building simplified certificate lists from Vault PKI data.

    This service:
    - Fetches all certificates from a PKI mount
    - Fetches issuer information and CA chains
    - Returns simplified certificate data with specific fields:
      - subject-CN: subject of the certificate
      - expired: yes/no
      - revoked: yes/no
      - expiring_in: (no. of days) if not expired
      - issuers: [intermediate CA and root CA]
    """

    def __init__(self, vault_client: VaultClient):
        """Initialize simplified certificate builder with Vault client.

        Args:
            vault_client: Authenticated Vault client instance
        """
        self.vault_client = vault_client
        self.certificate_parser = CertificateParser()

    async def build_simplified_list(self, pki_mount_path: str) -> dict[str, Any]:
        """Build simplified certificate list for a PKI mount.

        Args:
            pki_mount_path: Mount path of the PKI secrets engine

        Returns:
            dict: Simplified certificate list response
        """
        warnings: list[dict[str, str]] = []
        certificates: list[dict[str, Any]] = []

        try:
            # Step 1: List all certificate serial numbers
            logging.info(f"Listing certificates for PKI mount: {pki_mount_path}")
            serial_numbers = await self.vault_client.list_certificates(pki_mount_path)
            logging.info(f"Found {len(serial_numbers)} certificates")

            if not serial_numbers:
                # No certificates found - return empty list
                return {
                    "certificates": [],
                    "warnings": [],
                    "metadata": {
                        "total_certificates": 0,
                        "expired_count": 0,
                        "revoked_count": 0,
                    },
                }

            # Step 2: Fetch all issuers and build issuer map for CA chain resolution
            issuers_map, issuer_warnings = await self._fetch_issuers_map(pki_mount_path)
            warnings.extend(issuer_warnings)

            # Step 3: Fetch all certificates and build simplified list
            certificates, cert_warnings = await self._fetch_simplified_certificates(
                pki_mount_path, serial_numbers, issuers_map
            )
            warnings.extend(cert_warnings)

            # Step 4: Calculate metadata
            metadata = self._calculate_metadata(certificates)

            return {
                "certificates": certificates,
                "warnings": warnings,
                "metadata": metadata,
            }

        except VaultConnectionError as e:
            # Connection errors are critical - re-raise
            raise SimplifiedCertificateBuilderError(f"Vault connection failed: {str(e)}") from e

        except VaultPermissionError as e:
            # Permission errors for mount listing are critical
            raise SimplifiedCertificateBuilderError(
                f"Permission denied accessing PKI mount '{pki_mount_path}': {str(e)}"
            ) from e

        except Exception as e:
            # Unexpected errors - try to provide partial results with warnings
            logging.error(f"Unexpected error building simplified certificate list: {str(e)}")
            warnings.append(
                {
                    "type": "parse_error",
                    "resource": pki_mount_path,
                    "message": f"Unexpected error building certificate list: {str(e)}",
                }
            )

            # Return partial list with available data
            metadata = self._calculate_metadata(certificates)
            return {
                "certificates": certificates,
                "warnings": warnings,
                "metadata": metadata,
            }

    async def _fetch_issuers_map(
        self, pki_mount_path: str
    ) -> tuple[dict[str, dict[str, Any]], list[dict[str, str]]]:
        """Fetch all issuers and build issuer map for CA chain resolution.

        Args:
            pki_mount_path: PKI mount path

        Returns:
            tuple: (issuer_map, warnings) - map of issuer_id to issuer data
        """
        issuers_map: dict[str, dict[str, Any]] = {}
        warnings: list[dict[str, str]] = []

        try:
            # List all issuer IDs
            issuer_ids = await self.vault_client.list_issuers(pki_mount_path)
            logging.info(f"Found {len(issuer_ids)} issuers")

            if not issuer_ids:
                return issuers_map, warnings

            # Control concurrency for issuer fetching
            semaphore = asyncio.Semaphore(5)  # Fewer concurrent requests for issuers

            async def fetch_single_issuer(issuer_id: str) -> dict[str, Any] | None:
                async with semaphore:
                    try:
                        # Fetch issuer data from Vault
                        issuer_data = await self.vault_client.read_issuer(pki_mount_path, issuer_id)

                        # Extract issuer CN from certificate
                        certificate = issuer_data.get("certificate", "")
                        ca_chain = issuer_data.get("ca_chain", [])

                        if not certificate:
                            warnings.append(
                                {
                                    "type": "parse_error",
                                    "resource": f"{pki_mount_path}/issuer/{issuer_id}",
                                    "message": "Issuer certificate data missing",
                                }
                            )
                            return None

                        # Extract issuer CN from certificate
                        try:
                            cert = x509.load_pem_x509_certificate(certificate.encode())
                            issuer_cn = self.certificate_parser._extract_cn_from_name(cert.subject)
                            if not issuer_cn:
                                issuer_cn = "Unknown"
                        except Exception as e:
                            logging.warning(
                                f"Error parsing issuer certificate {issuer_id}: {str(e)}"
                            )
                            issuer_cn = "Unknown"

                        # Determine if it's a root CA (self-signed)
                        is_root = self.certificate_parser.is_self_signed(certificate)

                        return {
                            "issuer_id": issuer_id,
                            "issuer_cn": issuer_cn,
                            "is_root": is_root,
                            "ca_chain": ca_chain,
                            "certificate": certificate,
                        }

                    except VaultPermissionError as e:
                        warnings.append(
                            {
                                "type": "permission_denied",
                                "resource": f"{pki_mount_path}/issuer/{issuer_id}",
                                "message": f"Permission denied reading issuer: {str(e)}",
                            }
                        )
                        return None

                    except Exception as e:
                        logging.warning(f"Error fetching issuer {issuer_id}: {str(e)}")
                        warnings.append(
                            {
                                "type": "parse_error",
                                "resource": f"{pki_mount_path}/issuer/{issuer_id}",
                                "message": f"Error reading issuer: {str(e)}",
                            }
                        )
                        return None

            # Execute all issuer fetches concurrently
            tasks = [fetch_single_issuer(issuer_id) for issuer_id in issuer_ids]
            results = await asyncio.gather(*tasks, return_exceptions=False)

            # Build issuer map
            for issuer_data in results:
                if issuer_data is not None:
                    issuers_map[issuer_data["issuer_id"]] = issuer_data

            logging.info(f"Successfully fetched {len(issuers_map)} issuers")

        except VaultPermissionError as e:
            warnings.append(
                {
                    "type": "permission_denied",
                    "resource": f"{pki_mount_path}/issuers",
                    "message": f"Permission denied listing issuers: {str(e)}",
                }
            )

        except Exception as e:
            logging.warning(f"Error fetching issuers: {str(e)}")
            warnings.append(
                {
                    "type": "parse_error",
                    "resource": f"{pki_mount_path}/issuers",
                    "message": f"Error listing issuers: {str(e)}",
                }
            )

        return issuers_map, warnings

    async def _fetch_simplified_certificates(
        self, pki_mount_path: str, serial_numbers: list[str], issuers_map: dict[str, dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
        """Fetch all certificates and build simplified list.

        Args:
            pki_mount_path: PKI mount path
            serial_numbers: List of certificate serial numbers to fetch
            issuers_map: Map of issuer_id to issuer data

        Returns:
            tuple: (simplified_certificates, warnings)
        """
        certificates: list[dict[str, Any]] = []
        warnings: list[dict[str, str]] = []

        # Control concurrency to avoid overwhelming Vault
        semaphore = asyncio.Semaphore(10)  # Max 10 concurrent requests

        async def fetch_single_certificate(serial: str) -> dict[str, Any] | None:
            async with semaphore:
                try:
                    # Fetch certificate data from Vault
                    cert_data = await self.vault_client.read_certificate(pki_mount_path, serial)

                    # Extract PEM data
                    pem_data = cert_data.get("certificate", "")
                    if not pem_data:
                        warnings.append(
                            {
                                "type": "parse_error",
                                "resource": f"{pki_mount_path}/cert/{serial}",
                                "message": "Certificate PEM data missing from response",
                            }
                        )
                        return None

                    # Parse certificate data
                    cert = x509.load_pem_x509_certificate(pem_data.encode())

                    # Extract subject CN
                    subject_cn = self.certificate_parser._extract_cn_from_name(cert.subject)
                    if not subject_cn:
                        subject_cn = "Unknown"

                    # Extract issuer CN
                    issuer_cn = self.certificate_parser._extract_cn_from_name(cert.issuer)
                    if not issuer_cn:
                        issuer_cn = "Unknown"

                    # Get validity dates
                    not_after = cert.not_valid_after.replace(tzinfo=UTC)

                    # Check if expired
                    now = datetime.now(UTC)

                    logging.info(f"not_after: {not_after}, now: {now}")
                    is_expired = now > not_after
                    expired = "yes" if is_expired else "no"

                    # Check if revoked
                    revocation_time = cert_data.get("revocation_time")
                    is_revoked = revocation_time is not None and revocation_time > 0
                    revoked = "yes" if is_revoked else "no"

                    # Calculate days until expiry (only if not expired)
                    expiring_in = None
                    if not is_expired:
                        delta = not_after - now
                        total_seconds = int(delta.total_seconds())

                        if total_seconds >= 86400:  # More than 1 day (86400 seconds)
                            days = delta.days
                            expiring_in = f"{days} day{'s' if days != 1 else ''}"
                        else:
                            hours = total_seconds // 3600
                            minutes = (total_seconds % 3600) // 60
                            expiring_in = f"{hours}h {minutes}m"

                    # Get issuer chain from issuer_id
                    issuer_id = cert_data.get("issuer_id")
                    # If no issuer_id, try to get default issuer from PKI config
                    if not issuer_id:
                        try:
                            config_data = await self.vault_client.read_issuer_config(pki_mount_path)
                            issuer_id = config_data.get("default")
                        except Exception as e:
                            logging.warning(
                                f"Error reading issuer config for default issuer: {str(e)}"
                            )

                    issuers = self._resolve_issuer_chain(issuer_id, issuers_map)

                    # Format serial number
                    serial_formatted = self.certificate_parser.format_serial_number(
                        cert.serial_number
                    )

                    return {
                        "serial_number": serial_formatted,
                        "subject_cn": subject_cn,
                        "expired": expired,
                        "revoked": revoked,
                        "expiring_in": expiring_in,
                        "issuers": issuers,
                    }

                except VaultPermissionError as e:
                    warnings.append(
                        {
                            "type": "permission_denied",
                            "resource": f"{pki_mount_path}/cert/{serial}",
                            "message": f"Permission denied reading certificate: {str(e)}",
                        }
                    )
                    return None

                except Exception as e:
                    logging.warning(f"Error fetching certificate {serial}: {str(e)}")
                    warnings.append(
                        {
                            "type": "parse_error",
                            "resource": f"{pki_mount_path}/cert/{serial}",
                            "message": f"Error reading certificate: {str(e)}",
                        }
                    )
                    return None

        # Execute all certificate fetches concurrently
        logging.info(f"Fetching {len(serial_numbers)} certificates concurrently")
        tasks = [fetch_single_certificate(serial) for serial in serial_numbers]
        results = await asyncio.gather(*tasks, return_exceptions=False)

        # Filter out None results (failed fetches)
        certificates = [cert for cert in results if cert is not None]
        logging.info(f"Successfully fetched {len(certificates)} certificates")

        return certificates, warnings

    def _resolve_issuer_chain(
        self, issuer_id: str | None, issuers_map: dict[str, dict[str, Any]]
    ) -> list[str]:
        """Resolve the full issuer chain (intermediate and root CAs) for a certificate.

        Args:
            issuer_id: Vault issuer UUID
            issuers_map: Map of issuer_id to issuer data

        Returns:
            list[str]: List of CA common names from immediate issuer to root
        """
        issuers: list[str] = []

        if not issuer_id or issuer_id not in issuers_map:
            return issuers

        issuer_data = issuers_map[issuer_id]

        # Add the immediate issuer
        issuers.append(issuer_data["issuer_cn"])

        # If this issuer has a CA chain, extract the root CA from it
        ca_chain = issuer_data.get("ca_chain", [])
        if ca_chain and len(ca_chain) > 1:
            # The last certificate in the chain is typically the root CA
            try:
                root_cert = x509.load_pem_x509_certificate(ca_chain[-1].encode())
                root_cn = self.certificate_parser._extract_cn_from_name(root_cert.subject)
                if root_cn and root_cn != issuer_data["issuer_cn"]:
                    issuers.append(root_cn)
            except Exception as e:
                logging.warning(f"Error parsing root CA from chain: {str(e)}")

        # If no root CA found in chain but issuer is not root, try to find root CAs
        elif not issuer_data.get("is_root", False):
            # Look for root CAs in the issuers map
            for other_issuer in issuers_map.values():
                if other_issuer.get("is_root", False):
                    root_cn = other_issuer["issuer_cn"]
                    if root_cn not in issuers:
                        issuers.append(root_cn)
                        break  # Just add the first root CA found

        return issuers

    def _calculate_metadata(self, certificates: list[dict[str, Any]]) -> dict[str, int]:
        """Calculate metadata for simplified certificate list.

        Args:
            certificates: List of simplified certificate data

        Returns:
            dict: Summary statistics
        """
        total_certificates = len(certificates)
        expired_count = sum(1 for cert in certificates if cert["expired"] == "yes")
        revoked_count = sum(1 for cert in certificates if cert["revoked"] == "yes")

        return {
            "total_certificates": total_certificates,
            "expired_count": expired_count,
            "revoked_count": revoked_count,
        }
