"""MCP tool for listing PKI secrets engines in HashiCorp Vault."""

from typing import Any

from fastmcp import FastMCP

from ..models.pki_engine import PKISecretsEngine
from ..services.vault_client import VaultClient, format_mcp_error


def register_list_pki_engines_tool(mcp: FastMCP) -> None:
    """Register the list_pki_secrets_engines tool with FastMCP server.

    Args:
        mcp: FastMCP server instance
    """

    @mcp.tool
    async def list_pki_secrets_engines() -> dict[str, Any]:
        """
        List all PKI secrets engines mounted in HashiCorp Vault.

        This tool discovers all PKI secrets engines in your Vault instance, filtering out
        non-PKI mount points (kv, transit, database, etc.). Use this tool when you need
        to audit or discover PKI infrastructure in your Vault deployment.

        Example input:
            No input parameters required.

        Example response:
            {
                "pki_engines": [
                    {
                        "path": "pki",
                        "type": "pki",
                        "description": "Root CA for production environment",
                        "config": {
                            "default_lease_ttl": 86400,
                            "max_lease_ttl": 31536000
                        }
                    },
                    {
                        "path": "pki_int",
                        "type": "pki",
                        "description": "Intermediate CA",
                        "config": {
                            "default_lease_ttl": 86400,
                            "max_lease_ttl": 2592000
                        }
                    }
                ]
            }

        Args:
            None: This tool requires no input parameters. Authentication is handled
                  via environment variables (VAULT_ADDR, VAULT_TOKEN, optional VAULT_NAMESPACE).

        Returns:
            dict[str, Any]: A response object containing:
            - 'pki_engines' (list): List of PKI secrets engine objects, each containing:
                - 'path' (str): Mount path of the PKI secrets engine (e.g., "pki", "pki_int")
                - 'type' (str): Always "pki" for PKI secrets engines
                - 'description' (str): Human-readable description of the PKI mount
                - 'config' (dict): Configuration details including lease TTL settings

        Raises:
            VaultConnectionError: If connection to Vault server fails
            VaultAuthenticationError: If VAULT_TOKEN is invalid or expired
            VaultPermissionError: If token lacks 'read' capability on 'sys/mounts'
        """
        try:
            # Initialize Vault client with environment variables
            vault_client = VaultClient()

            # Validate connection before proceeding
            await vault_client.validate_connection()

            # Get all PKI engines
            pki_engines_data = await vault_client.list_pki_engines()

            # Convert to Pydantic models for validation
            pki_engines = [PKISecretsEngine(**engine_data) for engine_data in pki_engines_data]

            # Return MCP-compliant response
            return {"pki_engines": [engine.model_dump() for engine in pki_engines]}

        except Exception as error:
            # Convert any exception to MCP error format
            return format_mcp_error(error)
