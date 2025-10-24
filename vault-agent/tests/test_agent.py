"""Tests for the agent functionality."""

import pytest
from unittest.mock import Mock, patch

from src.agent.vault_pki_agent import VaultPKIAgent


class TestVaultPKIAgent:
    """Test cases for VaultPKIAgent."""

    def test_agent_initialization_missing_api_key(self):
        """Test agent initialization fails without OpenAI API key."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="OpenAI API key is required"):
                VaultPKIAgent()

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    @patch("src.agent.vault_pki_agent.OpenAIModel")
    @patch("src.agent.vault_pki_agent.MCPClient")
    def test_agent_initialization_success(self, mock_mcp_client, mock_openai_model):
        """Test successful agent initialization."""
        mock_model = Mock()
        mock_openai_model.return_value = mock_model

        agent = VaultPKIAgent()

        assert agent.model == mock_model
        assert agent.system_prompt is not None
        assert "PKI expert" in agent.system_prompt
        mock_openai_model.assert_called_once_with(api_key="test-key")

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    @patch("src.agent.vault_pki_agent.OpenAIModel")
    @patch("src.agent.vault_pki_agent.MCPClient")
    @patch("src.agent.vault_pki_agent.Agent")
    async def test_query_success(
        self, mock_agent_class, mock_mcp_client, mock_openai_model
    ):
        """Test successful query processing."""
        # Mock agent result
        mock_agent_result = Mock()
        mock_agent_result.message = {
            "content": [{"text": "Found 3 certificates expiring in 30 days"}]
        }

        mock_agent_instance = Mock()
        mock_agent_instance.invoke_async.return_value = mock_agent_result
        mock_agent_class.return_value = mock_agent_instance

        # Mock MCP client
        mock_mcp_instance = Mock()
        mock_mcp_instance.list_tools_sync.return_value = []
        mock_mcp_client.return_value = mock_mcp_instance

        agent = VaultPKIAgent()
        result = await agent.query("Show certificates expiring in 30 days")

        assert result == "Found 3 certificates expiring in 30 days"
        mock_agent_instance.invoke_async.assert_called_once_with(
            "Show certificates expiring in 30 days"
        )

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    @patch("src.agent.vault_pki_agent.OpenAIModel")
    @patch("src.agent.vault_pki_agent.MCPClient")
    @patch("src.agent.vault_pki_agent.Agent")
    async def test_query_empty_response(
        self, mock_agent_class, mock_mcp_client, mock_openai_model
    ):
        """Test query with empty agent response."""
        # Mock empty agent result
        mock_agent_result = Mock()
        mock_agent_result.message = {"content": []}

        mock_agent_instance = Mock()
        mock_agent_instance.invoke_async.return_value = mock_agent_result
        mock_agent_class.return_value = mock_agent_instance

        # Mock MCP client
        mock_mcp_instance = Mock()
        mock_mcp_instance.list_tools_sync.return_value = []
        mock_mcp_client.return_value = mock_mcp_instance

        agent = VaultPKIAgent()
        result = await agent.query("Test query")

        assert "encountered an issue" in result

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    @patch("src.agent.vault_pki_agent.OpenAIModel")
    @patch("src.agent.vault_pki_agent.MCPClient")
    async def test_query_exception_handling(self, mock_mcp_client, mock_openai_model):
        """Test query exception handling."""
        # Mock MCP client to raise exception
        mock_mcp_instance = Mock()
        mock_mcp_instance.__enter__.side_effect = Exception("Connection failed")
        mock_mcp_client.return_value = mock_mcp_instance

        agent = VaultPKIAgent()
        result = await agent.query("Test query")

        assert "Error processing query" in result
        assert "Connection failed" in result
