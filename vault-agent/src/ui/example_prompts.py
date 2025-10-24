"""Example prompts for the Vault PKI Query Agent UI."""

from typing import List, Dict


def get_example_prompts() -> List[Dict[str, str]]:
    """Get list of example prompts organized by category.

    Returns:
        List of dictionaries with category, prompt, and description
    """
    return [
        {
            "category": "🔥 Certificate Expiration",
            "prompt": "Show me all certificates expiring in next 30 days",
            "description": "Lists certificates that will expire within the next 30 days",
        },
        {
            "category": "🔥 Certificate Expiration",
            "prompt": "List certificates expiring in next week",
            "description": "Shows certificates expiring within 7 days",
        },
        {
            "category": "❌ Revocation Status",
            "prompt": "Show all revoked certificates",
            "description": "Displays all certificates that have been revoked",
        },
        {
            "category": "❌ Revocation Status",
            "prompt": "List revoked certificates from last month",
            "description": "Shows certificates revoked in the past 30 days",
        },
        {
            "category": "🏗️ PKI Engine Filter",
            "prompt": "List all certificates from pki_int engine",
            "description": "Shows all certificates issued by the pki_int PKI engine",
        },
        {
            "category": "🏗️ PKI Engine Filter",
            "prompt": "Show certificates issued by root CA",
            "description": "Displays certificates from the root CA PKI engine",
        },
        {
            "category": "📋 Audit Trail",
            "prompt": "Show audit events for web.example.com certificate",
            "description": "Displays the complete audit trail for a specific certificate",
        },
        {
            "category": "📋 Audit Trail",
            "prompt": "List all audit events for api.example.com",
            "description": "Shows all lifecycle events for the specified certificate",
        },
        {
            "category": "👤 Issuer Attribution",
            "prompt": "Who issued test.example.com certificate?",
            "description": "Identifies the entity that issued the specified certificate",
        },
        {
            "category": "👤 Issuer Attribution",
            "prompt": "Show issuer for server.example.com",
            "description": "Displays attribution information for certificate issuance",
        },
        {
            "category": "❓ Help",
            "prompt": "What can I ask?",
            "description": "Shows available query patterns and examples",
        },
        {
            "category": "❓ Help",
            "prompt": "Show me examples",
            "description": "Displays example queries you can try",
        },
    ]


def get_prompts_by_category() -> Dict[str, List[Dict[str, str]]]:
    """Get example prompts grouped by category.

    Returns:
        Dictionary with categories as keys and lists of prompts as values
    """
    prompts = get_example_prompts()
    by_category = {}

    for prompt in prompts:
        category = prompt["category"]
        if category not in by_category:
            by_category[category] = []
        by_category[category].append(prompt)

    return by_category
