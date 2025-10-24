"""Vault PKI Query Agent using AWS Strands Agent SDK."""

import os
from typing import Optional

from dotenv import load_dotenv
from strands import Agent
from strands.agent import AgentResult
from strands.tools.mcp.mcp_client import MCPClient
from strands.models.openai import OpenAIModel
from mcp.client.streamable_http import streamablehttp_client


class VaultPKIAgent:
    """Main agent for processing Vault PKI queries using natural language."""

    def __init__(
        self, mcp_server_url: Optional[str] = None, openai_api_key: Optional[str] = None
    ):
        """Initialize the Vault PKI Agent.

        Args:
            mcp_server_url: URL of the MCP server. Uses MCP_SERVER_URL env var if not provided.
            openai_api_key: OpenAI API key. Uses OPENAI_API_KEY env var if not provided.
        """
        self.mcp_server_url = mcp_server_url or os.getenv(
            "MCP_SERVER_URL", "http://localhost:8080/mcp"
        )

        # Initialize MCP client using Strands Agent SDK pattern
        self.mcp_client = MCPClient(lambda: streamablehttp_client(self.mcp_server_url))

        # Initialize OpenAI model
        api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OpenAI API key is required. Set OPENAI_API_KEY environment variable."
            )

        self.model = OpenAIModel(
            client_args={"api_key": api_key},
            model_id="gpt-4o",
            params={"max_tokens": 1000, "temperature": 0.7},
        )

        # System prompt for PKI domain expertise
        self.system_prompt = self._get_system_prompt()

    def _get_system_prompt(self) -> str:
        """Get the system prompt for the agent."""
        return """
You are a HashiCorp Vault PKI expert assistant. You help users query and understand 
certificate information from Vault PKI secrets engines and related audit events.

Your capabilities include:
- Finding certificates expiring within specified timeframes
- Identifying revoked certificates and their status
- Filtering certificates by PKI secrets engine
- Retrieving audit trails for certificate lifecycle events
- Identifying who issued specific certificates

Available MCP tools:
- list_pki_secrets_engines: Lists all PKI secrets engines in Vault
- list_certificates: Lists certificates from a specific PKI engine (requires pki_mount_path parameter)
- filter_pki_audit_events: Searches audit events for certificate operations (requires vault_certificate_subject and vault_pki_path parameters)

When responding:
- Use the available MCP tools to get current data from Vault
- Provide clear, actionable information about certificate status
- Include relevant details like expiration dates, serial numbers, and issuer information
- Explain security implications when appropriate
- Suggest follow-up actions for expiring or revoked certificates
- Always prioritize security and operational clarity in your responses

For certificate expiration queries, use list_certificates on all PKI engines and filter results.
For revocation queries, use list_certificates and look for revoked certificates.
For audit queries, use filter_pki_audit_events with the certificate subject and PKI path.
For PKI engine queries, use list_certificates on the specific engine.
"""

    async def query(self, user_prompt: str) -> str:
        """Process a natural language query about Vault PKI and return response.

        Args:
            user_prompt: Natural language query from user

        Returns:
            str: Response from the agent with PKI information
        """
        try:
            # Get MCP tools for the agent
            with self.mcp_client:
                tools = self.mcp_client.list_tools_sync()

                # Create agent with tools
                agent = Agent(
                    model=self.model,
                    tools=tools,
                    system_prompt=self.system_prompt,
                )

                # Invoke agent with user query
                result: AgentResult = await agent.invoke_async(user_prompt)

                if result.message and result.message.get("content"):
                    # Extract response text
                    response_text = ""
                    for msg in result.message["content"]:
                        if msg.get("text"):
                            response_text += msg["text"].strip() + " "

                    return (
                        response_text.strip()
                        if response_text.strip()
                        else "I apologize, but I encountered an issue processing your request. Please try again or contact support."
                    )
                else:
                    return "I apologize, but I encountered an issue processing your request. Please try again or contact support."

        except Exception as e:
            return f"Error processing query: {str(e)}. Please check your connection to the MCP server and try again."


if __name__ == "__main__":
    # Simple test run
    import asyncio

    load_dotenv()

    async def test_agent():
        user_prompt1 = "List all PKI secrets engines in Vault."
        user_prompt2 = "Show me all certificates expiring in the next 30 days."
        user_prompt3 = "Who issued the certificate test.example.com"
        user_prompt4 = "Show me audit events for test.example.com"

        agent = VaultPKIAgent()
        response = await agent.query(user_prompt4)
        print("Agent Response:", response)

    asyncio.run(test_agent())
