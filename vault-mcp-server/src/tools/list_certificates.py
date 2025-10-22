"""List certificates tool for MCP server.

Provides the list_certificates tool function that organizes certificates
from a PKI secrets engine into hierarchical structure by root and intermediate CAs.
"""

import re
from typing import Any

from fastmcp import FastMCP

# Import will be done inline to avoid circular dependencies
from ..services.vault_client import (
    VaultClient,
    VaultAuthenticationError,
    VaultConnectionError,
    VaultPermissionError,
    format_mcp_error,
)


def validate_pki_mount_path(pki_mount_path: str) -> bool:
    """Validate PKI mount path format.

    Args:
        pki_mount_path: Mount path to validate

    Returns:
        bool: True if valid format (alphanumeric, underscore, hyphen only)
    """
    # Allow alphanumeric characters, underscores, and hyphens
    pattern = r"^[a-zA-Z0-9_-]+$"
    return bool(re.match(pattern, pki_mount_path))


def register_list_certificates_tool(mcp: FastMCP) -> None:
    """Register the list_certificates tool with FastMCP server.

    Args:
        mcp: FastMCP server instance
    """

    @mcp.tool
    async def list_certificates(pki_mount_path: str) -> dict[str, Any]:
        """List all certificates from a PKI secrets engine with simplified output.

        Retrieves all certificates from the specified PKI secrets engine mount and
        returns simplified certificate data including subject CN, expiration status,
        revocation status, days until expiry, and issuer hierarchy.

        Args:
            pki_mount_path: Mount path of the PKI secrets engine (e.g., 'pki', 'pki_int').
                           Must contain only alphanumeric characters, underscores, and hyphens.
                           Do not include leading or trailing slashes.

        Returns:
            dict: Response containing simplified certificate data:
                {
                    "certificates": [
                        {
                            "serial_number": "39:4e:fa:01:23",
                            "subject_cn": "webserver.example.com",
                            "expired": "no",
                            "revoked": "no",
                            "expiring_in": 365,
                            "issuers": ["Intermediate CA", "Root CA"]
                        }
                    ],
                    "warnings": [],
                    "metadata": {
                        "total_certificates": 1,
                        "expired_count": 0,
                        "revoked_count": 0
                    }
                }

        Raises:
            VAULT_CONNECTION_ERROR: Failed to connect to Vault server. Check VAULT_ADDR
                                   environment variable and network connectivity.
            AUTHENTICATION_ERROR: Vault authentication failed. Check VAULT_TOKEN
                                  environment variable and ensure token is valid.
            PKI_MOUNT_NOT_FOUND: The specified PKI mount path does not exist or is not
                                of type 'pki'.
            PERMISSION_ERROR: Token lacks permission to list or read certificates at the
                             specified path. Requires read capability on '<pki>/certs'
                             and '<pki>/cert/*'.
            INVALID_MOUNT_PATH: Mount path contains invalid characters or format. Use
                               alphanumeric, underscore, and hyphen only.
        """
        try:
            # Input validation
            if not pki_mount_path:
                return {
                    "error": {
                        "code": "INVALID_MOUNT_PATH",
                        "message": "PKI mount path cannot be empty",
                        "details": {"provided_path": pki_mount_path},
                    }
                }

            if not validate_pki_mount_path(pki_mount_path):
                return {
                    "error": {
                        "code": "INVALID_MOUNT_PATH",
                        "message": (
                            "Mount path contains invalid characters. "
                            "Use alphanumeric characters, underscores, and hyphens only."
                        ),
                        "details": {"provided_path": pki_mount_path},
                    }
                }

            # Initialize Vault client
            vault_client = VaultClient()

            # Validate connection and authentication
            await vault_client.validate_connection()

            # Verify that the mount exists and is a PKI engine
            try:
                pki_engines = await vault_client.list_pki_engines()
                mount_exists = any(engine["path"] == pki_mount_path for engine in pki_engines)

                if not mount_exists:
                    return {
                        "error": {
                            "code": "PKI_MOUNT_NOT_FOUND",
                            "message": (
                                f"PKI mount '{pki_mount_path}' not found or not accessible. "
                                "Ensure the mount exists and is of type 'pki'."
                            ),
                            "details": {
                                "mount_path": pki_mount_path,
                                "available_pki_mounts": [e["path"] for e in pki_engines],
                            },
                        }
                    }
            except VaultPermissionError:
                # If we can't list mounts, we'll try to proceed anyway
                # The user might have access to the specific mount but not sys/mounts
                pass

            # Build simplified certificate list
            from ..services.simplified_certificate_builder import SimplifiedCertificateBuilder

            simplified_builder = SimplifiedCertificateBuilder(vault_client)
            result = await simplified_builder.build_simplified_list(pki_mount_path)

            # Return successful response
            return result

        except VaultConnectionError as e:
            return format_mcp_error(e)

        except VaultAuthenticationError as e:
            return format_mcp_error(e)

        except VaultPermissionError as e:
            return {
                "error": {
                    "code": "PERMISSION_ERROR",
                    "message": str(e),
                    "details": {"mount_path": pki_mount_path},
                }
            }

        except Exception as e:
            # Unexpected error - return generic error response
            return {
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": (
                        f"Unexpected error processing PKI mount '{pki_mount_path}': {str(e)}"
                    ),
                    "details": {"mount_path": pki_mount_path, "error_type": type(e).__name__},
                }
            }
