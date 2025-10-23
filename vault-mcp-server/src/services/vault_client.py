"""Vault client wrapper for hvac with authentication and error handling."""

import logging
import os
from typing import Any

import hvac


class VaultClientError(Exception):
    """Base exception for Vault client errors."""

    pass


class VaultConnectionError(VaultClientError):
    """Raised when connection to Vault fails."""

    pass


class VaultAuthenticationError(VaultClientError):
    """Raised when Vault authentication fails."""

    pass


class VaultPermissionError(VaultClientError):
    """Raised when token lacks required permissions."""

    pass


class VaultClient:
    """Wrapper around hvac.Client with environment-based authentication.

    Authenticates using VAULT_ADDR and VAULT_TOKEN environment variables.
    Supports Vault Enterprise namespaces via VAULT_NAMESPACE environment variable.
    Provides methods for PKI secrets engine operations with proper error handling.
    """

    def __init__(self):
        """Initialize Vault client with environment variables."""
        self.vault_addr = os.getenv("VAULT_ADDR")
        self.vault_token = os.getenv("VAULT_TOKEN")
        self.vault_namespace = os.getenv("VAULT_NAMESPACE")
        self.vault_skip_verify = os.getenv("VAULT_SKIP_VERIFY", "false").lower() == "true"

        if not self.vault_addr:
            raise VaultConnectionError(
                "VAULT_ADDR environment variable is not set. "
                "Please set it to your Vault server address (e.g., https://vault.example.com:8200)"
            )

        if not self.vault_token:
            raise VaultAuthenticationError(
                "VAULT_TOKEN environment variable is not set. "
                "Please set it to a valid Vault authentication token"
            )

        try:
            # Initialize hvac client with namespace support
            client_kwargs = {
                "url": self.vault_addr,
                "token": self.vault_token,
                "verify": not self.vault_skip_verify,
            }

            # Add namespace if provided (Vault Enterprise feature)
            if self.vault_namespace:
                client_kwargs["namespace"] = self.vault_namespace

            self.client = hvac.Client(**client_kwargs)
        except Exception as e:
            raise VaultConnectionError(f"Failed to initialize Vault client: {str(e)}") from e

    async def validate_connection(self) -> bool:
        """Validate connection to Vault and token authentication.

        Returns:
            bool: True if connection and authentication are valid

        Raises:
            VaultConnectionError: If cannot connect to Vault
            VaultAuthenticationError: If token is invalid
        """
        try:
            # Verify token is valid by checking authentication status
            # This is safer than checking sys.is_initialized() which may not be
            # accessible on managed Vault instances like HCP Vault
            if not self.client.is_authenticated():
                raise VaultAuthenticationError("Vault token is invalid or expired")

            # Additional validation: try to lookup token info to ensure it's working
            try:
                token_info = self.client.auth.token.lookup_self()
                if not token_info:
                    raise VaultAuthenticationError("Unable to retrieve token information")
            except hvac.exceptions.Forbidden:
                raise VaultAuthenticationError("Token lacks permission to lookup self")

            return True

        except hvac.exceptions.VaultError as e:
            if "permission denied" in str(e).lower():
                raise VaultAuthenticationError(f"Authentication failed: {str(e)}") from e
            raise VaultConnectionError(f"Vault connection error: {str(e)}") from e

        except Exception as e:
            raise VaultConnectionError(
                f"Unexpected error validating Vault connection: {str(e)}"
            ) from e

    async def list_mounted_secrets_engines(self) -> dict[str, Any]:
        """List all mounted secrets engines in Vault.

        Returns:
            dict: Dictionary of mount points and their details

        Raises:
            VaultConnectionError: If connection to Vault fails
            VaultPermissionError: If token lacks permission to list mounts
        """
        try:
            return self.client.sys.list_mounted_secrets_engines()

        except hvac.exceptions.Forbidden as e:
            raise VaultPermissionError(
                "Token lacks permission to list secrets engines. "
                "Requires 'read' capability on 'sys/mounts'"
            ) from e

        except hvac.exceptions.VaultError as e:
            raise VaultConnectionError(f"Failed to list secrets engines: {str(e)}") from e

        except Exception as e:
            raise VaultConnectionError(f"Unexpected error listing secrets engines: {str(e)}") from e

    async def list_pki_engines(self) -> list[dict[str, Any]]:
        """List all PKI secrets engines, filtering out non-PKI mounts.

        Returns:
            list: List of PKI secrets engine details

        Raises:
            VaultConnectionError: If connection to Vault fails
            VaultPermissionError: If token lacks permissions
        """
        mounts = await self.list_mounted_secrets_engines()

        # Debug logging to understand the data structure
        logging.info(f"Raw mounts data type: {type(mounts)}")
        logging.info(f"Raw mounts data: {mounts}")

        # Handle different possible return formats from hvac
        if isinstance(mounts, dict):
            # Check if it's wrapped in a 'data' key (common in Vault API responses)
            if "data" in mounts:
                mounts_data = mounts["data"]
                logging.info(f"Using 'data' key, type: {type(mounts_data)}")
            else:
                mounts_data = mounts
                logging.info(f"Using direct mounts data, type: {type(mounts_data)}")
        else:
            raise VaultConnectionError(f"Unexpected mounts data format: {type(mounts)}")

        logging.info(f"Processing mounts_data: {mounts_data}")

        pki_engines = []
        for path, details in mounts_data.items():
            logging.info(
                f"Processing path: {path}, details type: {type(details)}, details: {details}"
            )

            # Handle case where details might be a string instead of dict
            if isinstance(details, dict):
                if details.get("type") == "pki":
                    pki_engines.append(
                        {
                            "path": path.rstrip("/"),
                            "type": details["type"],
                            "description": details.get("description", ""),
                            "config": details.get("config", {}),
                        }
                    )
            else:
                logging.warning(
                    f"Skipping mount {path}: details is not a dict (type: {type(details)})"
                )

        logging.info(f"Found {len(pki_engines)} PKI engines: {pki_engines}")
        return pki_engines

    async def list_certificates(self, pki_mount_path: str) -> list[str]:
        """List all certificate serial numbers for a PKI secrets engine.

        Args:
            pki_mount_path: Mount path of the PKI secrets engine (e.g., "pki")

        Returns:
            list[str]: List of certificate serial numbers

        Raises:
            VaultConnectionError: If connection to Vault fails
            VaultPermissionError: If token lacks permission to list certificates
        """
        try:
            # Vault API endpoint: GET /<pki_mount>/certs
            path = f"{pki_mount_path.rstrip('/')}/certs"
            response = self.client.list(path)

            # Handle different response formats
            if response is None:
                return []

            if isinstance(response, dict):
                if "data" in response and "keys" in response["data"]:
                    return response["data"]["keys"]
                elif "keys" in response:
                    return response["keys"]
                else:
                    logging.warning(f"Unexpected certificate list response format: {response}")
                    return []
            else:
                logging.warning(f"Unexpected certificate list response type: {type(response)}")
                return []

        except hvac.exceptions.Forbidden as e:
            raise VaultPermissionError(
                f"Token lacks permission to list certificates for PKI mount '{pki_mount_path}'. "
                f"Requires 'list' capability on '{pki_mount_path}/certs'"
            ) from e

        except hvac.exceptions.InvalidPath as e:
            raise VaultConnectionError(
                f"PKI mount '{pki_mount_path}' not found or not accessible"
            ) from e

        except hvac.exceptions.VaultError as e:
            raise VaultConnectionError(f"Failed to list certificates: {str(e)}") from e

        except Exception as e:
            raise VaultConnectionError(f"Unexpected error listing certificates: {str(e)}") from e

    async def read_certificate(self, pki_mount_path: str, serial_number: str) -> dict[str, Any]:
        """Read certificate details by serial number.

        Args:
            pki_mount_path: Mount path of the PKI secrets engine
            serial_number: Certificate serial number

        Returns:
            dict: Certificate details including PEM data and metadata

        Raises:
            VaultConnectionError: If connection to Vault fails
            VaultPermissionError: If token lacks permission to read certificate
        """
        try:
            # Vault API endpoint: GET /<pki_mount>/cert/<serial>
            path = f"{pki_mount_path.rstrip('/')}/cert/{serial_number}"
            response = self.client.read(path)

            if response is None:
                raise VaultConnectionError(f"Certificate {serial_number} not found")

            # Return the response data
            if isinstance(response, dict) and "data" in response:
                return response["data"]
            elif isinstance(response, dict):
                return response
            else:
                raise VaultConnectionError(
                    f"Unexpected certificate response format: {type(response)}"
                )

        except hvac.exceptions.Forbidden as e:
            raise VaultPermissionError(
                f"Token lacks permission to read certificate {serial_number} "
                f"from PKI mount '{pki_mount_path}'. "
                f"Requires 'read' capability on '{pki_mount_path}/cert/{serial_number}'"
            ) from e

        except hvac.exceptions.InvalidPath as e:
            raise VaultConnectionError(
                f"Certificate {serial_number} not found in PKI mount '{pki_mount_path}'"
            ) from e

        except hvac.exceptions.VaultError as e:
            raise VaultConnectionError(
                f"Failed to read certificate {serial_number}: {str(e)}"
            ) from e

        except Exception as e:
            raise VaultConnectionError(f"Unexpected error reading certificate: {str(e)}") from e

    async def read_issuer(self, pki_mount_path: str, issuer_id: str) -> dict[str, Any]:
        """Read issuer (CA) details and certificate chain by issuer ID.

        Args:
            pki_mount_path: Mount path of the PKI secrets engine
            issuer_id: Vault UUID of the issuer

        Returns:
            dict: Issuer details including CA chain and metadata

        Raises:
            VaultConnectionError: If connection to Vault fails
            VaultPermissionError: If token lacks permission to read issuer
        """
        try:
            # Vault API endpoint: GET /<pki_mount>/issuer/<issuer_id>
            path = f"{pki_mount_path.rstrip('/')}/issuer/{issuer_id}"
            response = self.client.read(path)

            if response is None:
                raise VaultConnectionError(f"Issuer {issuer_id} not found")

            # Return the response data
            if isinstance(response, dict) and "data" in response:
                return response["data"]
            elif isinstance(response, dict):
                return response
            else:
                raise VaultConnectionError(f"Unexpected issuer response format: {type(response)}")

        except hvac.exceptions.Forbidden as e:
            raise VaultPermissionError(
                f"Token lacks permission to read issuer {issuer_id} "
                f"from PKI mount '{pki_mount_path}'. "
                f"Requires 'read' capability on '{pki_mount_path}/issuer/{issuer_id}'"
            ) from e

        except hvac.exceptions.InvalidPath as e:
            raise VaultConnectionError(
                f"Issuer {issuer_id} not found in PKI mount '{pki_mount_path}'"
            ) from e

        except hvac.exceptions.VaultError as e:
            raise VaultConnectionError(f"Failed to read issuer {issuer_id}: {str(e)}") from e

        except Exception as e:
            raise VaultConnectionError(f"Unexpected error reading issuer: {str(e)}") from e

    async def list_issuers(self, pki_mount_path: str) -> list[str]:
        """List all issuer IDs for a PKI secrets engine.

        Args:
            pki_mount_path: Mount path of the PKI secrets engine

        Returns:
            list[str]: List of issuer UUIDs

        Raises:
            VaultConnectionError: If connection to Vault fails
            VaultPermissionError: If token lacks permission to list issuers
        """
        try:
            # Vault API endpoint: LIST /<pki_mount>/issuers
            path = f"{pki_mount_path.rstrip('/')}/issuers"
            response = self.client.list(path)

            # Handle different response formats
            if response is None:
                return []

            if isinstance(response, dict):
                if "data" in response and "keys" in response["data"]:
                    return response["data"]["keys"]
                elif "keys" in response:
                    return response["keys"]
                else:
                    logging.warning(f"Unexpected issuer list response format: {response}")
                    return []
            else:
                logging.warning(f"Unexpected issuer list response type: {type(response)}")
                return []

        except hvac.exceptions.Forbidden as e:
            raise VaultPermissionError(
                f"Token lacks permission to list issuers for PKI mount '{pki_mount_path}'. "
                f"Requires 'list' capability on '{pki_mount_path}/issuers'"
            ) from e

        except hvac.exceptions.InvalidPath as e:
            raise VaultConnectionError(
                f"PKI mount '{pki_mount_path}' not found or not accessible"
            ) from e

        except hvac.exceptions.VaultError as e:
            raise VaultConnectionError(f"Failed to list issuers: {str(e)}") from e

        except Exception as e:
            raise VaultConnectionError(f"Unexpected error listing issuers: {str(e)}") from e

    async def read_issuer_config(self, pki_mount_path: str) -> dict[str, Any]:
        """Read PKI issuer configuration including default issuer.

        Args:
            pki_mount_path: Mount path of the PKI secrets engine

        Returns:
            dict: PKI issuer configuration including default issuer ID

        Raises:
            VaultConnectionError: If connection to Vault fails
            VaultPermissionError: If token lacks permission to read config
        """
        try:
            # Vault API endpoint: GET /<pki_mount>/config/issuers
            path = f"{pki_mount_path.rstrip('/')}/config/issuers"
            response = self.client.read(path)

            if response is None:
                # Return empty config if not found
                return {}

            # Return the response data
            if isinstance(response, dict) and "data" in response:
                return response["data"]
            elif isinstance(response, dict):
                return response
            else:
                raise VaultConnectionError(
                    f"Unexpected issuer config response format: {type(response)}"
                )

        except hvac.exceptions.Forbidden as e:
            raise VaultPermissionError(
                f"Token lacks permission to read issuer config "
                f"from PKI mount '{pki_mount_path}'. "
                f"Requires 'read' capability on '{pki_mount_path}/config/issuers'"
            ) from e

        except hvac.exceptions.InvalidPath as e:
            raise VaultConnectionError(
                f"PKI mount '{pki_mount_path}' not found or issuer config not accessible"
            ) from e

        except hvac.exceptions.VaultError as e:
            raise VaultConnectionError(f"Failed to read issuer config: {str(e)}") from e

        except Exception as e:
            raise VaultConnectionError(f"Unexpected error reading issuer config: {str(e)}") from e

    async def calculate_audit_hash(self, audit_device: str, input_value: str) -> str:
        """Calculate HMAC-SHA256 hash for audit logs using Vault's audit-hash API.

        Args:
            audit_device: Name of the audit device (e.g., 'hcp-main-audit')
            input_value: Value to hash (e.g., certificate subject name)

        Returns:
            str: HMAC-SHA256 hash as returned by Vault

        Raises:
            VaultConnectionError: If connection to Vault fails
            VaultPermissionError: If token lacks permission to use audit-hash
        """
        try:
            # Vault API endpoint: POST /sys/audit-hash/<device>
            path = f"sys/audit-hash/{audit_device}"
            data = {"input": input_value}

            response = self.client.write(path, **data)

            if response is None:
                raise VaultConnectionError("No response from audit-hash API")

            # Extract the hash from response
            if isinstance(response, dict):
                if "data" in response and "hash" in response["data"]:
                    return response["data"]["hash"]
                elif "hash" in response:
                    return response["hash"]
                else:
                    raise VaultConnectionError(f"Unexpected audit-hash response format: {response}")
            else:
                raise VaultConnectionError(f"Unexpected audit-hash response type: {type(response)}")

        except hvac.exceptions.Forbidden as e:
            raise VaultPermissionError(
                f"Token lacks permission to use audit-hash for device '{audit_device}'. "
                f"Requires 'update' capability on 'sys/audit-hash/{audit_device}'"
            ) from e

        except hvac.exceptions.InvalidPath as e:
            raise VaultConnectionError(
                f"Audit device '{audit_device}' not found or not accessible"
            ) from e

        except hvac.exceptions.VaultError as e:
            raise VaultConnectionError(f"Failed to calculate audit hash: {str(e)}") from e

        except Exception as e:
            raise VaultConnectionError(f"Unexpected error calculating audit hash: {str(e)}") from e


def format_mcp_error(error: Exception) -> dict[str, Any]:
    """Format error as MCP error response.

    Args:
        error: Exception to format

    Returns:
        dict: MCP-compliant error response
    """
    error_type = type(error).__name__

    if isinstance(error, VaultConnectionError):
        return {
            "error": {
                "code": "VAULT_CONNECTION_ERROR",
                "message": str(error),
                "details": {"error_type": error_type},
            }
        }

    elif isinstance(error, VaultAuthenticationError):
        return {
            "error": {
                "code": "AUTHENTICATION_ERROR",
                "message": str(error),
                "details": {"error_type": error_type},
            }
        }

    elif isinstance(error, VaultPermissionError):
        return {
            "error": {
                "code": "PERMISSION_ERROR",
                "message": str(error),
                "details": {"error_type": error_type},
            }
        }

    else:
        return {
            "error": {
                "code": "INTERNAL_ERROR",
                "message": f"Unexpected error: {str(error)}",
                "details": {"error_type": error_type},
            }
        }
