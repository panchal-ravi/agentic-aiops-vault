"""Certificate hierarchy builder service.

This module provides functionality to build hierarchical certificate structures
from Vault PKI data, organizing certificates by root and intermediate CAs.
"""

import asyncio
import logging
from datetime import datetime, timezone

from cryptography import x509

from ..models.certificate import (
    Certificate,
    CertificateHierarchy,
    HierarchyMetadata,
    Issuer,
    IntermediateIssuerGroup,
    RootIssuerGroup,
    Warning,
)
from ..services.certificate_parser import CertificateParser
from ..services.vault_client import (
    VaultClient,
    VaultConnectionError,
    VaultPermissionError,
)


class HierarchyBuilderError(Exception):
    """Base exception for hierarchy builder errors."""

    pass


class HierarchyBuilder:
    """Service for building certificate hierarchies from Vault PKI data.

    This service:
    - Fetches all certificates from a PKI mount
    - Fetches issuer information and CA chains
    - Organizes certificates into root and intermediate CA groups
    - Handles edge cases like inactive issuers and permission errors
    - Calculates hierarchy metadata and statistics
    """

    def __init__(self, vault_client: VaultClient):
        """Initialize hierarchy builder with Vault client.

        Args:
            vault_client: Authenticated Vault client instance
        """
        self.vault_client = vault_client
        self.certificate_parser = CertificateParser()

    async def build_hierarchy(self, pki_mount_path: str) -> CertificateHierarchy:
        """Build complete certificate hierarchy for a PKI mount.

        Args:
            pki_mount_path: Mount path of the PKI secrets engine

        Returns:
            CertificateHierarchy: Complete hierarchy with certificates grouped by CAs

        Raises:
            HierarchyBuilderError: If critical errors prevent hierarchy construction
        """
        warnings: list[Warning] = []
        certificates: list[Certificate] = []
        issuers: dict[str, Issuer] = {}

        try:
            # Step 1: List all certificate serial numbers
            logging.info(f"Listing certificates for PKI mount: {pki_mount_path}")
            serial_numbers = await self.vault_client.list_certificates(pki_mount_path)
            logging.info(f"Found {len(serial_numbers)} certificates")

            if not serial_numbers:
                # No certificates found - return empty hierarchy
                return CertificateHierarchy(
                    root_issuers=[],
                    warnings=[],
                    metadata=HierarchyMetadata(
                        total_certificates=0,
                        expired_count=0,
                        revoked_count=0,
                        root_ca_count=0,
                        intermediate_ca_count=0,
                    ),
                )

            # Step 2: Fetch all certificates concurrently (with controlled concurrency)
            certificates, cert_warnings = await self._fetch_certificates_concurrent(
                pki_mount_path, serial_numbers
            )
            warnings.extend(cert_warnings)

            # Step 3: Fetch all issuers and build issuer map
            issuers, issuer_warnings = await self._fetch_issuers_concurrent(pki_mount_path)
            warnings.extend(issuer_warnings)

            # Step 4: Build hierarchy structure
            root_issuers = self._organize_into_hierarchy(certificates, issuers, warnings)

            # Step 5: Calculate metadata
            metadata = self._calculate_metadata(certificates, issuers)

            return CertificateHierarchy(
                root_issuers=root_issuers, warnings=warnings, metadata=metadata
            )

        except VaultConnectionError as e:
            # Connection errors are critical - re-raise
            raise HierarchyBuilderError(f"Vault connection failed: {str(e)}") from e

        except VaultPermissionError as e:
            # Permission errors for mount listing are critical
            raise HierarchyBuilderError(
                f"Permission denied accessing PKI mount '{pki_mount_path}': {str(e)}"
            ) from e

        except Exception as e:
            # Unexpected errors - try to provide partial results with warnings
            logging.error(f"Unexpected error building hierarchy: {str(e)}")
            warnings.append(
                Warning(
                    type="parse_error",
                    resource=pki_mount_path,
                    message=f"Unexpected error building hierarchy: {str(e)}",
                )
            )

            # Return partial hierarchy with available data
            metadata = self._calculate_metadata(certificates, issuers)
            return CertificateHierarchy(
                root_issuers=self._organize_into_hierarchy(certificates, issuers, warnings),
                warnings=warnings,
                metadata=metadata,
            )

    async def _fetch_certificates_concurrent(
        self, pki_mount_path: str, serial_numbers: list[str]
    ) -> tuple[list[Certificate], list[Warning]]:
        """Fetch all certificates concurrently with controlled concurrency.

        Args:
            pki_mount_path: PKI mount path
            serial_numbers: List of certificate serial numbers to fetch

        Returns:
            tuple: (certificates, warnings) - certificates that were successfully parsed
        """
        certificates: list[Certificate] = []
        warnings: list[Warning] = []

        # Control concurrency to avoid overwhelming Vault
        semaphore = asyncio.Semaphore(10)  # Max 10 concurrent requests

        async def fetch_single_certificate(serial: str) -> Certificate | None:
            async with semaphore:
                try:
                    # Fetch certificate data from Vault
                    cert_data = await self.vault_client.read_certificate(pki_mount_path, serial)

                    # Extract PEM data (usually in 'certificate' field)
                    pem_data = cert_data.get("certificate", "")
                    if not pem_data:
                        warnings.append(
                            Warning(
                                type="parse_error",
                                resource=f"{pki_mount_path}/cert/{serial}",
                                message="Certificate PEM data missing from response",
                            )
                        )
                        return None

                    # Check if certificate is revoked
                    revocation_time = cert_data.get("revocation_time")
                    if revocation_time:
                        # Convert Unix timestamp to datetime if needed
                        # Vault typically returns revocation_time as Unix timestamp
                        if isinstance(revocation_time, (int, float)):
                            revocation_time = datetime.fromtimestamp(
                                revocation_time, tz=timezone.utc
                            )

                    # Parse certificate using graceful degradation
                    cert = self.certificate_parser.parse_pem_safe(
                        pem_data=pem_data,
                        serial_number=serial,
                        issuer_id=cert_data.get("issuer_id"),
                        revocation_time=revocation_time,
                    )

                    return cert

                except VaultPermissionError as e:
                    # Log permission error but continue with other certificates
                    warnings.append(
                        Warning(
                            type="permission_denied",
                            resource=f"{pki_mount_path}/cert/{serial}",
                            message=f"Permission denied reading certificate: {str(e)}",
                        )
                    )
                    return None

                except Exception as e:
                    # Log parse error but continue with other certificates
                    logging.warning(f"Error fetching certificate {serial}: {str(e)}")
                    warnings.append(
                        Warning(
                            type="parse_error",
                            resource=f"{pki_mount_path}/cert/{serial}",
                            message=f"Error reading certificate: {str(e)}",
                        )
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

    async def _fetch_issuers_concurrent(
        self, pki_mount_path: str
    ) -> tuple[dict[str, Issuer], list[Warning]]:
        """Fetch all issuers and build issuer map.

        Args:
            pki_mount_path: PKI mount path

        Returns:
            tuple: (issuer_map, warnings) - map of issuer_id to Issuer objects
        """
        issuers: dict[str, Issuer] = {}
        warnings: list[Warning] = []

        try:
            # List all issuer IDs
            issuer_ids = await self.vault_client.list_issuers(pki_mount_path)
            logging.info(f"Found {len(issuer_ids)} issuers")

            if not issuer_ids:
                return issuers, warnings

            # Control concurrency for issuer fetching
            semaphore = asyncio.Semaphore(5)  # Fewer concurrent requests for issuers

            async def fetch_single_issuer(issuer_id: str) -> Issuer | None:
                async with semaphore:
                    try:
                        # Fetch issuer data from Vault
                        issuer_data = await self.vault_client.read_issuer(pki_mount_path, issuer_id)

                        # Extract issuer CN from certificate
                        certificate = issuer_data.get("certificate", "")
                        ca_chain = issuer_data.get("ca_chain", [])

                        if not certificate:
                            warnings.append(
                                Warning(
                                    type="parse_error",
                                    resource=f"{pki_mount_path}/issuer/{issuer_id}",
                                    message="Issuer certificate data missing",
                                )
                            )
                            return None

                        # Extract issuer CN from certificate
                        issuer_cn = self.certificate_parser._extract_cn_from_name(
                            x509.load_pem_x509_certificate(certificate.encode()).subject
                        )
                        if not issuer_cn:
                            issuer_cn = "Unknown"

                        # Determine issuer type and parent
                        is_root = self.certificate_parser.is_self_signed(certificate)
                        issuer_type = "root" if is_root else "intermediate"

                        # For intermediate CAs, try to find parent from CA chain
                        parent_issuer_id = None
                        if not is_root and len(ca_chain) > 1:
                            # Parent is typically the next cert in the chain
                            # This is a simplified approach - production code might need more logic
                            pass  # Will be filled in later if needed

                        issuer = Issuer(
                            issuer_id=issuer_id,
                            issuer_cn=issuer_cn,
                            issuer_type=issuer_type,
                            parent_issuer_id=parent_issuer_id,
                            ca_chain=ca_chain,
                            is_active=True,  # If we can read it, it's active
                            certificate=certificate,
                        )

                        return issuer

                    except VaultPermissionError as e:
                        warnings.append(
                            Warning(
                                type="permission_denied",
                                resource=f"{pki_mount_path}/issuer/{issuer_id}",
                                message=f"Permission denied reading issuer: {str(e)}",
                            )
                        )
                        return None

                    except Exception as e:
                        logging.warning(f"Error fetching issuer {issuer_id}: {str(e)}")
                        warnings.append(
                            Warning(
                                type="parse_error",
                                resource=f"{pki_mount_path}/issuer/{issuer_id}",
                                message=f"Error reading issuer: {str(e)}",
                            )
                        )
                        return None

            # Execute all issuer fetches concurrently
            tasks = [fetch_single_issuer(issuer_id) for issuer_id in issuer_ids]
            results = await asyncio.gather(*tasks, return_exceptions=False)

            # Build issuer map
            for issuer in results:
                if issuer is not None:
                    issuers[issuer.issuer_id] = issuer

            logging.info(f"Successfully fetched {len(issuers)} issuers")

        except VaultPermissionError as e:
            warnings.append(
                Warning(
                    type="permission_denied",
                    resource=f"{pki_mount_path}/issuers",
                    message=f"Permission denied listing issuers: {str(e)}",
                )
            )

        except Exception as e:
            logging.warning(f"Error fetching issuers: {str(e)}")
            warnings.append(
                Warning(
                    type="parse_error",
                    resource=f"{pki_mount_path}/issuers",
                    message=f"Error listing issuers: {str(e)}",
                )
            )

        return issuers, warnings

    def _organize_into_hierarchy(
        self, certificates: list[Certificate], issuers: dict[str, Issuer], warnings: list[Warning]
    ) -> list[RootIssuerGroup]:
        """Organize certificates into hierarchical structure by root and intermediate CAs.

        Args:
            certificates: List of all certificates
            issuers: Map of issuer_id to Issuer objects
            warnings: List to append warnings to

        Returns:
            list[RootIssuerGroup]: List of root CA groups with nested structure
        """
        # Group certificates by issuer CN (since issuer_id might be missing)
        cert_groups: dict[str, list[Certificate]] = {}
        for cert in certificates:
            issuer_cn = cert.issuer_cn
            if issuer_cn not in cert_groups:
                cert_groups[issuer_cn] = []
            cert_groups[issuer_cn].append(cert)

        # Find root CAs from issuers
        root_cas: dict[str, Issuer] = {}
        intermediate_cas: dict[str, Issuer] = {}

        for issuer in issuers.values():
            if issuer.issuer_type == "root":
                root_cas[issuer.issuer_cn] = issuer
            else:
                intermediate_cas[issuer.issuer_cn] = issuer

        # If no issuers available, infer from certificates
        if not issuers:
            # Try to infer root CAs from certificate data
            for issuer_cn, certs in cert_groups.items():
                # Check if any certificate with this issuer CN is self-signed
                for cert in certs:
                    if cert.subject_cn == cert.issuer_cn:
                        # Self-signed certificate suggests this is a root CA
                        root_cas[issuer_cn] = None  # Placeholder
                        break

        # Build root issuer groups
        root_groups: list[RootIssuerGroup] = []

        # Process each root CA
        for root_cn, root_issuer in root_cas.items():
            # Find certificates issued directly by this root
            direct_certificates = cert_groups.get(root_cn, [])

            # Find intermediate CAs issued by this root
            intermediate_groups: list[IntermediateIssuerGroup] = []

            # For now, simple approach: assume any intermediate CA that's not a root
            # belongs to the first root (this can be improved with proper chain parsing)
            if root_groups == []:  # Only for the first root
                for int_cn, int_issuer in intermediate_cas.items():
                    int_certificates = cert_groups.get(int_cn, [])
                    if int_certificates:
                        intermediate_groups.append(
                            IntermediateIssuerGroup(
                                intermediate_cn=int_cn,
                                intermediate_issuer_id=int_issuer.issuer_id if int_issuer else None,
                                certificates=int_certificates,
                            )
                        )

            root_groups.append(
                RootIssuerGroup(
                    root_cn=root_cn,
                    root_issuer_id=root_issuer.issuer_id if root_issuer else None,
                    intermediate_groups=intermediate_groups,
                    direct_certificates=direct_certificates,
                )
            )

        # Handle orphaned certificates (no identifiable issuer)
        orphaned_certificates = []
        processed_cns = set(root_cas.keys()) | set(intermediate_cas.keys())

        for issuer_cn, certs in cert_groups.items():
            if issuer_cn not in processed_cns:
                orphaned_certificates.extend(certs)

        if orphaned_certificates:
            # Create "Unknown Root" group for orphaned certificates
            root_groups.append(
                RootIssuerGroup(
                    root_cn="Unknown Root",
                    root_issuer_id=None,
                    intermediate_groups=[],
                    direct_certificates=orphaned_certificates,
                )
            )

            warnings.append(
                Warning(
                    type="missing_issuer",
                    resource="certificates",
                    message=(
                        f"Found {len(orphaned_certificates)} certificates with unresolvable issuers"
                    ),
                )
            )

        return root_groups

    def _calculate_metadata(
        self, certificates: list[Certificate], issuers: dict[str, Issuer]
    ) -> HierarchyMetadata:
        """Calculate hierarchy metadata and statistics.

        Args:
            certificates: List of all certificates
            issuers: Map of issuer objects

        Returns:
            HierarchyMetadata: Summary statistics
        """
        total_certificates = len(certificates)
        expired_count = sum(1 for cert in certificates if cert.is_expired)
        revoked_count = sum(1 for cert in certificates if cert.is_revoked)

        root_ca_count = sum(1 for issuer in issuers.values() if issuer.issuer_type == "root")
        intermediate_ca_count = sum(
            1 for issuer in issuers.values() if issuer.issuer_type == "intermediate"
        )

        return HierarchyMetadata(
            total_certificates=total_certificates,
            expired_count=expired_count,
            revoked_count=revoked_count,
            root_ca_count=root_ca_count,
            intermediate_ca_count=intermediate_ca_count,
        )
