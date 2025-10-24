"""Main entry point for the Vault PKI Query Agent Streamlit application."""

import asyncio
import os
import streamlit as st
from dotenv import load_dotenv

from src.agent.vault_pki_agent import VaultPKIAgent
from src.ui.streamlit_app import (
    setup_page_config,
    render_header,
    render_sidebar,
    render_query_input,
    render_query_history,
    add_to_query_history,
    show_connection_status,
    render_footer,
)


def load_environment():
    """Load environment variables from .env file."""
    load_dotenv()

    # Verify required environment variables
    required_vars = ["OPENAI_API_KEY"]
    missing_vars = []

    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        st.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        st.stop()


def initialize_session_state():
    """Initialize Streamlit session state variables."""
    if "agent" not in st.session_state:
        try:
            st.session_state.agent = VaultPKIAgent()
            st.session_state.mcp_server_url = st.session_state.agent.mcp_server_url
        except Exception as e:
            st.error(f"Failed to initialize agent: {str(e)}")
            st.stop()

    if "query_history" not in st.session_state:
        st.session_state.query_history = []


async def process_query_async(agent: VaultPKIAgent, query_text: str) -> None:
    """Process a query asynchronously and update session state.

    Args:
        agent: VaultPKIAgent instance
        query_text: User query text
    """
    try:
        with st.spinner("Processing your query..."):
            response = await agent.query(query_text)
            st.session_state.last_response = response
            add_to_query_history(
                query_text, bool(response and not response.startswith("Error"))
            )
    except Exception as e:
        error_message = f"Error processing query: {str(e)}"
        st.session_state.last_response = error_message
        add_to_query_history(query_text, False)


def main():
    """Main application function."""
    # Setup page configuration
    setup_page_config()

    # Load environment variables
    load_environment()

    # Initialize session state
    initialize_session_state()

    # Render main interface
    render_header()

    # Create main layout
    main_col, sidebar_col = st.columns([3, 1])

    with sidebar_col:
        render_sidebar()

    with main_col:
        # Query input
        query_text = render_query_input()

        # Process query if submitted
        if query_text:
            # Run async query processing
            asyncio.run(process_query_async(st.session_state.agent, query_text))

        # Show last result if available
        if "last_response" in st.session_state:
            st.markdown("### Response")
            st.markdown(st.session_state.last_response)

        # Query history
        render_query_history()

        # Connection status
        show_connection_status()

    # Footer
    render_footer()


if __name__ == "__main__":
    main()
