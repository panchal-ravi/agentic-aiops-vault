"""Filter CloudWatch logs tool for MCP server.

Provides comprehensive filtering of AWS CloudWatch log streams with support
for text patterns, regular expressions, time range filtering, and log level classification.
"""

import json
import logging
import os
from datetime import datetime
from typing import Any

from fastmcp import FastMCP
from cryptography import x509

from ..models.cloudwatch import FilterCriteria
from ..services.log_filter import LogFilter

logger = logging.getLogger(__name__)


def register_filter_logs_tool(mcp: FastMCP) -> None:
    """Register the filter_pki_audit_events tool with FastMCP server.

    Args:
        mcp: FastMCP server instance
    """

    @mcp.tool
    async def filter_pki_audit_events(
        vault_certificate_subject: str,
        vault_pki_path: str,
        start_time: str | None = None,
        end_time: str | None = None,
    ) -> dict[str, Any]:
        """Search for Vault audit events related to PKI certificate issuance or revocation.

        This tool searches AWS CloudWatch logs for audit events that record PKI certificate
        issuance or revocation operations. It returns information about which Vault entity
        performed the certificate operation and when it was performed. The tool uses HMAC-SHA256
        hashing to securely match the certificate subject against audit logs.

        Key Features:
        - Identifies the Vault entity that issued or revoked a specific certificate
        - Provides timestamp and authentication details of the operation
        - Uses secure HMAC-SHA256 hashing for certificate subject matching
        - Filters for certificate issuance and revocation operations
        - Returns entity display name, entity ID, and remote address information

        The log group name is configured via the AWS_LOG_GROUP_NAME environment variable.
        Log stream names can be optionally configured via AWS_LOG_STREAM_NAMES (comma-separated).
        If no log streams are specified, all streams in the log group will be searched.

        Example input:
            vault_certificate_subject: "web.example.com"
            vault_pki_path: "pki_int"
            start_time: "2023-10-22T10:00:00Z"
            end_time: "2023-10-22T11:00:00Z"

        Example output:
            {
                "success": true,
                "message": "Found 1 events matching filter criteria",
                "data": {
                    "events": [
                        {
                            "timestamp": "2023-10-22T10:30:45.123456Z",
                            "auth_display_name": "token-service-account",
                            "auth_entity_id": "550e8400-e29b-41d4-a716-446655440000",
                            "request_remote_address": "10.0.1.42",
                            "request_path": "pki_int/issue/web-server-role",
                            "response_mount_accessor": "pki_abc123",
                            "time": "2023-10-22T10:30:45.123456789Z"
                        }
                    ],
                    "statistics": {
                        "events_scanned": 1500,
                        "events_matched": 1,
                        "api_calls_made": 2
                    }
                }
            }

        Args:
            vault_certificate_subject (str): The certificate subject/common name to search for
                (e.g., "web.example.com"). This will be HMAC-SHA256 hashed using Vault's
                audit-hash API for secure comparison against audit logs.
            vault_pki_path (str): The Vault PKI mount path where the certificate was issued
                (e.g., "pki_int"). The tool will automatically append "/issue/*" to search
                for issuance operations.
            start_time (str | None): Filter events after this timestamp. Accepts ISO 8601 format
                (e.g., "2023-10-22T10:00:00Z") or Unix timestamp strings. Optional - if not
                provided, searches from the beginning of available logs.
            end_time (str | None): Filter events before this timestamp. Same format as start_time.
                Optional - if not provided, searches up to the most recent logs.

        Returns:
            dict[str, Any]: Structured response containing:
            - 'success' (bool): True if the search completed successfully, False on error.
            - 'message' (str): Human-readable description of the results (e.g., "Found 1 events").
            - 'data' (dict): Contains 'events' list and 'statistics' dictionary.
                - 'events' (list): List of matching audit events, each containing:
                    - 'timestamp' (str): ISO 8601 timestamp of the certificate issuance.
                    - 'auth_display_name' (str): Display name of the Vault entity that
                        issued the cert.
                    - 'auth_entity_id' (str): Unique ID of the Vault entity that issued the cert.
                    - 'request_remote_address' (str): IP address of the client that
                        requested issuance.
                    - 'request_path' (str): Full Vault path of the issuance operation.
                    - 'response_mount_accessor' (str): Accessor ID of the PKI mount.
                    - 'time' (str): High-precision timestamp from the audit log.
                - 'statistics' (dict): Query execution statistics including events_scanned,
                    events_matched, and api_calls_made.
            - On error: 'error_code' (str) and 'details' (dict) with diagnostic information.

        """
        try:
            # Get log group name from environment variable
            log_group_name = os.getenv("AWS_LOG_GROUP_NAME")
            if not log_group_name:
                return {
                    "success": False,
                    "message": "AWS_LOG_GROUP_NAME environment variable is required",
                    "error_code": "MISSING_CONFIGURATION",
                    "details": {
                        "required_env_var": "AWS_LOG_GROUP_NAME",
                        "description": (
                            "CloudWatch log group name must be configured via environment variable"
                        ),
                    },
                }

            # Get log stream names from environment variable (optional)
            log_stream_names = None
            log_stream_names_env = os.getenv("AWS_LOG_STREAM_NAMES")
            if log_stream_names_env:
                log_stream_names = [
                    name.strip() for name in log_stream_names_env.split(",") if name.strip()
                ]

            # Parse time parameters
            start_datetime = None
            end_datetime = None

            if start_time:
                try:
                    start_datetime = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                except ValueError:
                    # Try parsing as Unix timestamp
                    try:
                        start_datetime = datetime.fromtimestamp(float(start_time))
                    except ValueError:
                        return {
                            "success": False,
                            "message": "Invalid start_time format",
                            "error_code": "INVALID_PARAMETERS",
                            "details": {
                                "field": "start_time",
                                "expected_format": (
                                    "ISO 8601 (2023-10-22T10:00:00Z) or Unix timestamp"
                                ),
                            },
                        }

            if end_time:
                try:
                    end_datetime = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
                except ValueError:
                    try:
                        end_datetime = datetime.fromtimestamp(float(end_time))
                    except ValueError:
                        return {
                            "success": False,
                            "message": "Invalid end_time format",
                            "error_code": "INVALID_PARAMETERS",
                            "details": {
                                "field": "end_time",
                                "expected_format": (
                                    "ISO 8601 (2023-10-22T10:00:00Z) or Unix timestamp"
                                ),
                            },
                        }

            # Handle Vault PKI filtering - always required now
            try:
                # Import Vault client and hash the certificate subject
                from ..services.compound_expression_parser import create_vault_pki_expression
                from ..services.vault_client import VaultClient

                vault_client = VaultClient()
                audit_device = "hcp-main-audit"

                # List all certificates in the PKI path to verify the path exists and get certificate serials
                certificates = await vault_client.list_certificates(vault_pki_path)
                if not certificates:
                    logger.warning(
                        f"No certificates found in PKI path '{vault_pki_path}' or path does not exist"
                    )
                    return {
                        "success": False,
                        "message": f"No certificates found in PKI path '{vault_pki_path}'",
                        "error_code": "PKI_PATH_NOT_FOUND",
                        "details": {
                            "vault_pki_path": vault_pki_path,
                            "suggestion": "Verify the PKI path exists and contains certificates",
                        },
                    }
                logger.info(
                    f"Found {len(certificates)} certificates in PKI path '{vault_pki_path}'"
                )

                # Find the certificate that matches the subject
                matching_certificate_serial = None
                for cert_serial in certificates:
                    try:
                        # Get certificate details
                        cert_details = await vault_client.read_certificate(
                            vault_pki_path, cert_serial
                        )

                        # logger.info(f"cert_details: {cert_details}")

                        # Check if the certificate subject matches
                        if cert_details and cert_details.get("certificate"):
                            # Parse the certificate to extract subject

                            cert_pem = cert_details["certificate"]
                            cert = x509.load_pem_x509_certificate(cert_pem.encode())

                            # Extract common name from subject
                            common_name = None
                            for attribute in cert.subject:
                                if attribute.oid == x509.NameOID.COMMON_NAME:
                                    common_name = attribute.value
                                    break

                            if common_name == vault_certificate_subject:
                                matching_certificate_serial = cert_serial
                                logger.info(
                                    f"Found matching certificate with serial: {cert_serial}"
                                )
                                break

                    except Exception as e:
                        logger.warning(f"Failed to check certificate {cert_serial}: {e}")
                        continue

                if not matching_certificate_serial:
                    return {
                        "success": False,
                        "message": f"No certificate found with subject '{vault_certificate_subject}' in PKI path '{vault_pki_path}'",
                        "error_code": "CERTIFICATE_NOT_FOUND",
                        "details": {
                            "vault_certificate_subject": vault_certificate_subject,
                            "vault_pki_path": vault_pki_path,
                        },
                    }

                # Calculate HMAC-SHA256 hash of certificate serial number
                hashed_subject = await vault_client.calculate_audit_hash(
                    audit_device, matching_certificate_serial
                )

                logger.info(
                    f"Calculated HMAC-SHA256 hash for serial number "
                    f"'{matching_certificate_serial}', hash: {hashed_subject}"
                )

                # Create path pattern by appending /issue/* to the PKI path
                vault_pki_path_pattern = f"{vault_pki_path.rstrip('/')}"

                # Create compound expression for Vault PKI filtering
                vault_expression = create_vault_pki_expression(
                    vault_pki_path_pattern,
                    hashed_subject,
                )

                # Add the new filter conditions
                final_compound_expression = (
                    f"{vault_expression} && "
                    f'($.auth.entity_id != "") && '
                    f"($.response.data.expiration != "
                    f'"__CLOUDWATCH_KEY_EXISTS_CHECK_PLACEHOLDER__")'
                )

            except Exception as e:
                return {
                    "success": False,
                    "message": f"Failed to process Vault PKI filter: {str(e)}",
                    "error_code": "VAULT_PKI_ERROR",
                    "details": {"error_type": type(e).__name__, "error_message": str(e)},
                }

            logger.info(f"Final compound expression: {final_compound_expression}")
            # Create filter criteria
            try:
                criteria = FilterCriteria(
                    log_group_name=log_group_name,
                    log_stream_names=log_stream_names,
                    start_time=start_datetime,
                    end_time=end_datetime,
                    text_pattern=None,
                    regex_pattern=None,
                    log_levels=None,
                    filter_pattern=final_compound_expression,
                    # Reduced to 10 for fastest response - user can paginate if needed
                    max_events=10,
                    start_from_head=True,
                    next_token=None,
                )
            except ValueError as e:
                return {
                    "success": False,
                    "message": f"Invalid filter criteria: {e}",
                    "error_code": "INVALID_PARAMETERS",
                    "details": {"validation_error": str(e)},
                }

            # Initialize filter service and process logs
            log_filter = LogFilter()
            results = await log_filter.filter_logs(criteria)

            # Format successful response
            events_list = []
            for event in results.events:
                event_data = {
                    "timestamp": event.timestamp.isoformat() + "Z",
                }

                # Try to parse the message as JSON and extract specified fields
                try:
                    message_json = json.loads(event.message)

                    # Extract auth.display_name
                    if "auth" in message_json and "display_name" in message_json["auth"]:
                        event_data["auth_display_name"] = message_json["auth"]["display_name"]

                    # Extract auth.entity_id
                    if "auth" in message_json and "entity_id" in message_json["auth"]:
                        event_data["auth_entity_id"] = message_json["auth"]["entity_id"]

                    # Extract request.remote_address
                    if "request" in message_json and "remote_address" in message_json["request"]:
                        event_data["request_remote_address"] = message_json["request"][
                            "remote_address"
                        ]

                    # Extract request.path
                    if "request" in message_json and "path" in message_json["request"]:
                        event_data["request_path"] = message_json["request"]["path"]

                    # Extract response.mount_accessor
                    if "response" in message_json and "mount_accessor" in message_json["response"]:
                        event_data["response_mount_accessor"] = message_json["response"][
                            "mount_accessor"
                        ]

                    # Extract time
                    if "time" in message_json:
                        event_data["time"] = message_json["time"]

                except (json.JSONDecodeError, KeyError, TypeError) as e:
                    # If JSON parsing fails, log the error but continue with just timestamp
                    logger.warning(f"Failed to parse event message as JSON: {e}")

                events_list.append(event_data)

            return {
                "success": True,
                "message": f"Found {len(results.events)} events matching filter criteria",
                "data": {
                    "events": events_list,
                    "statistics": {
                        "events_scanned": results.events_scanned,
                        "events_matched": results.events_matched,
                        "api_calls_made": results.api_calls_made,
                    },
                },
            }

        except ValueError as e:
            # Handle known validation or AWS errors
            logger.error(f"Validation error in filter_logs: {e}")
            error_msg = str(e)

            return {
                "success": False,
                "message": f"Filter operation failed: {error_msg}",
                "error_code": "VALIDATION_ERROR",
                "details": {"error_type": "ValueError", "error_message": error_msg},
            }

        except Exception as e:
            # Handle unexpected errors
            logger.error(f"Unexpected error in filter_logs: {e}", exc_info=True)
            return {
                "success": False,
                "message": "An unexpected error occurred while filtering logs",
                "error_code": "INTERNAL_ERROR",
                "details": {"error_type": type(e).__name__, "error_message": str(e)},
            }
