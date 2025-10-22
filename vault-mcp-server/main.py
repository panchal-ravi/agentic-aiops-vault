"""MCP server entry point for Vault PKI tools.

This module initializes the FastMCP server with async and streamable-http transport
and validates environment configuration.
"""

import asyncio
import logging
import os
import sys

from fastmcp import FastMCP
from dotenv import load_dotenv

load_dotenv()

# Validate required environment variables on startup
REQUIRED_ENV_VARS = ["VAULT_ADDR", "VAULT_TOKEN"]


def validate_environment() -> None:
    """Validate that required environment variables are set.

    Raises:
        SystemExit: If required environment variables are missing
    """
    missing_vars = [var for var in REQUIRED_ENV_VARS if not os.getenv(var)]

    if missing_vars:
        print(f"ERROR: Missing required environment variables: {', '.join(missing_vars)}")
        print("\nRequired environment variables:")
        print("  VAULT_ADDR  - Vault server URL (e.g., https://vault.example.com:8200)")
        print("  VAULT_TOKEN - Valid Vault authentication token")
        print("\nOptional environment variables:")
        print("  VAULT_SKIP_VERIFY - Skip TLS verification (default: false, dev only)")
        print("  VAULT_NAMESPACE   - Vault Enterprise namespace")
        print("  MCP_SERVER_HOST   - MCP server host (default: localhost)")
        print("  MCP_SERVER_PORT   - MCP server port (default: 8000)")
        sys.exit(1)


async def main():
    """Initialize and run the MCP server with async and streamable-http transport."""
    # Configure logging for debugging
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Validate environment before starting
    validate_environment()

    # Initialize FastMCP server with async transport
    mcp = FastMCP("Vault PKI MCP Server")

    # Register MCP tools
    from src.tools.list_certificates import register_list_certificates_tool
    from src.tools.list_pki_engines import register_list_pki_engines_tool

    register_list_pki_engines_tool(mcp)
    register_list_certificates_tool(mcp)

    print("Vault PKI MCP Server initialized successfully")
    print(f"Connected to: {os.getenv('VAULT_ADDR')}")
    if os.getenv("VAULT_NAMESPACE"):
        print(f"Namespace: {os.getenv('VAULT_NAMESPACE')}")

    host = os.getenv("MCP_SERVER_HOST", "localhost")
    port = int(os.getenv("MCP_SERVER_PORT", "8000"))
    print(f"Starting MCP server on {host}:{port}")
    print("Using async transport with streamable-http")
    print("Waiting for MCP tool requests...")

    # Run the MCP server with async transport
    await mcp.run_async(
        transport="streamable-http",
        host=host,
        port=port,
    )


if __name__ == "__main__":
    asyncio.run(main())
