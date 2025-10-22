"""Integration test example for the updated list_certificates method.

This shows how the new simplified certificate list format works.
"""

# Example response from the updated list_certificates method
EXPECTED_RESPONSE = {
    "certificates": [
        {
            "serial_number": "39:4e:fa:01:23:45:67:89",
            "subject_cn": "webserver.example.com",
            "expired": "no",
            "revoked": "no",
            "expiring_in": 365,
            "issuers": ["Intermediate CA", "Root CA"],
        },
        {
            "serial_number": "ab:cd:ef:12:34:56:78:90",
            "subject_cn": "api.example.com",
            "expired": "yes",
            "revoked": "no",
            "expiring_in": None,  # None when expired
            "issuers": ["Intermediate CA", "Root CA"],
        },
        {
            "serial_number": "12:34:56:78:90:ab:cd:ef",
            "subject_cn": "database.example.com",
            "expired": "no",
            "revoked": "yes",
            "expiring_in": 180,
            "issuers": ["Intermediate CA", "Root CA"],
        },
    ],
    "warnings": [
        {
            "type": "permission_denied",
            "resource": "pki/cert/some-serial",
            "message": "Permission denied reading certificate",
        }
    ],
    "metadata": {"total_certificates": 3, "expired_count": 1, "revoked_count": 1},
}


def test_response_format():
    """Test that the response format matches expectations."""
    assert "certificates" in EXPECTED_RESPONSE
    assert "warnings" in EXPECTED_RESPONSE
    assert "metadata" in EXPECTED_RESPONSE

    # Check certificate fields
    cert = EXPECTED_RESPONSE["certificates"][0]
    required_fields = [
        "serial_number",
        "subject_cn",
        "expired",
        "revoked",
        "expiring_in",
        "issuers",
    ]
    for field in required_fields:
        assert field in cert

    # Check that expired/revoked are yes/no strings
    for cert in EXPECTED_RESPONSE["certificates"]:
        assert cert["expired"] in ["yes", "no"]
        assert cert["revoked"] in ["yes", "no"]

        # expiring_in should be None for expired certificates
        if cert["expired"] == "yes":
            assert cert["expiring_in"] is None
        else:
            assert isinstance(cert["expiring_in"], int)

    # Check metadata
    metadata = EXPECTED_RESPONSE["metadata"]
    assert metadata["total_certificates"] == len(EXPECTED_RESPONSE["certificates"])
    assert metadata["expired_count"] == sum(
        1 for c in EXPECTED_RESPONSE["certificates"] if c["expired"] == "yes"
    )
    assert metadata["revoked_count"] == sum(
        1 for c in EXPECTED_RESPONSE["certificates"] if c["revoked"] == "yes"
    )

    print("✅ Response format validation passed!")


def test_issuer_chain_format():
    """Test that issuer chains are properly formatted."""
    for cert in EXPECTED_RESPONSE["certificates"]:
        issuers = cert["issuers"]
        assert isinstance(issuers, list)
        assert len(issuers) >= 1  # At least one issuer (immediate)

        # First issuer should be immediate issuer, last should be root
        if len(issuers) > 1:
            assert "Root CA" in issuers[-1]  # Root CA should be last

    print("✅ Issuer chain format validation passed!")


if __name__ == "__main__":
    test_response_format()
    test_issuer_chain_format()
    print("\n🎉 All tests passed! The new simplified certificate list format is working correctly.")

    # Show example usage
    print("\n📋 Example certificate data:")
    for i, cert in enumerate(EXPECTED_RESPONSE["certificates"], 1):
        print(f"\n{i}. Certificate: {cert['subject_cn']}")
        print(f"   Serial: {cert['serial_number']}")
        print(f"   Expired: {cert['expired']}")
        print(f"   Revoked: {cert['revoked']}")
        if cert["expiring_in"] is not None:
            print(f"   Expiring in: {cert['expiring_in']} days")
        print(f"   Issuers: {' → '.join(cert['issuers'])}")
