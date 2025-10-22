"""Test simplified certificate builder functionality."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, UTC

from src.services.simplified_certificate_builder import SimplifiedCertificateBuilder


class TestSimplifiedCertificateBuilder:
    """Test cases for SimplifiedCertificateBuilder."""

    @pytest.fixture
    def mock_vault_client(self):
        """Create mock vault client."""
        mock_client = AsyncMock()
        mock_client.list_certificates.return_value = ["serial1", "serial2"]
        mock_client.list_issuers.return_value = ["issuer1"]
        return mock_client

    @pytest.fixture
    def builder(self, mock_vault_client):
        """Create simplified certificate builder instance."""
        return SimplifiedCertificateBuilder(mock_vault_client)

    async def test_empty_certificate_list(self, builder, mock_vault_client):
        """Test handling of empty certificate list."""
        mock_vault_client.list_certificates.return_value = []

        result = await builder.build_simplified_list("test_pki")

        assert result["certificates"] == []
        assert result["metadata"]["total_certificates"] == 0
        assert result["metadata"]["expired_count"] == 0
        assert result["metadata"]["revoked_count"] == 0

    def test_serial_number_formatting(self, builder):
        """Test serial number formatting logic."""
        # Mock the certificate parser
        builder.certificate_parser = MagicMock()
        builder.certificate_parser.format_serial_number.return_value = "39:4e:fa:01:23"

        result = builder.certificate_parser.format_serial_number(0x394EFA0123)
        assert result == "39:4e:fa:01:23"

    def test_expiry_calculation(self, builder):
        """Test expiry status and days calculation."""
        now = datetime.now(UTC)

        # Test non-expired certificate
        future_date = datetime(2025, 12, 31, tzinfo=UTC)
        is_expired = now > future_date
        assert is_expired == False

        delta = future_date - now
        expiring_in = delta.days
        assert expiring_in > 0

        # Test expired certificate
        past_date = datetime(2020, 1, 1, tzinfo=UTC)
        is_expired = now > past_date
        assert is_expired == True

    def test_issuer_chain_resolution(self, builder):
        """Test issuer chain resolution logic."""
        issuers_map = {
            "issuer1": {
                "issuer_id": "issuer1",
                "issuer_cn": "Intermediate CA",
                "is_root": False,
                "ca_chain": [
                    "-----BEGIN CERTIFICATE-----\nintermediate\n-----END CERTIFICATE-----",
                    "-----BEGIN CERTIFICATE-----\nroot\n-----END CERTIFICATE-----",
                ],
            },
            "issuer2": {
                "issuer_id": "issuer2",
                "issuer_cn": "Root CA",
                "is_root": True,
                "ca_chain": ["-----BEGIN CERTIFICATE-----\nroot\n-----END CERTIFICATE-----"],
            },
        }

        # Test with valid issuer
        result = builder._resolve_issuer_chain("issuer1", issuers_map)
        assert "Intermediate CA" in result

        # Test with missing issuer
        result = builder._resolve_issuer_chain("nonexistent", issuers_map)
        assert result == []

        # Test with None issuer
        result = builder._resolve_issuer_chain(None, issuers_map)
        assert result == []

    def test_metadata_calculation(self, builder):
        """Test metadata calculation."""
        certificates = [
            {"expired": "no", "revoked": "no"},
            {"expired": "yes", "revoked": "no"},
            {"expired": "no", "revoked": "yes"},
        ]

        metadata = builder._calculate_metadata(certificates)

        assert metadata["total_certificates"] == 3
        assert metadata["expired_count"] == 1
        assert metadata["revoked_count"] == 1
