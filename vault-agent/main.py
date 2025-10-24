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
    """Process a query asynchronously with real-time streaming and update session state.

    Args:
        agent: VaultPKIAgent instance
        query_text: User query text
    """
    try:
        # Create placeholders for streaming output
        status_placeholder = st.empty()
        response_placeholder = st.empty()
        tool_placeholder = st.empty()

        status_placeholder.info("🔄 Processing your query...")

        full_response = ""
        current_tools = []

        async for event in agent.query_stream(query_text):
            # Handle different event types with error checking
            try:
                if "data" in event:
                    # Stream text output in real-time
                    text_chunk = event["data"]
                    if isinstance(text_chunk, str):
                        full_response += text_chunk
                        response_placeholder.markdown(f"### Response\n{full_response}")

                elif "current_tool_use" in event and event["current_tool_use"].get(
                    "name"
                ):
                    # Show tool usage
                    tool_use_info = event["current_tool_use"]
                    if isinstance(tool_use_info, dict):
                        tool_name = tool_use_info.get("name", "Unknown Tool")
                        tool_input = tool_use_info.get("input", {})

                        # Add to current tools if not already there
                        tool_info = f"🔧 Using: **{tool_name}**"
                        if tool_input:
                            # Show key parameters for context
                            key_params = []
                            # Check if tool_input is a dictionary before calling .items()
                            if isinstance(tool_input, dict):
                                for key, value in tool_input.items():
                                    if key in [
                                        "pki_mount_path",
                                        "vault_certificate_subject",
                                        "vault_pki_path",
                                    ]:
                                        key_params.append(f"{key}: {value}")
                            elif isinstance(tool_input, str):
                                # If tool_input is a string, just show it directly
                                key_params.append(f"input: {tool_input}")

                            if key_params:
                                tool_info += f" ({', '.join(key_params)})"

                        if tool_info not in current_tools:
                            current_tools.append(tool_info)
                            tool_placeholder.markdown(
                                "#### Tools Used\n" + "\n".join(current_tools)
                            )

                elif "init_event_loop" in event and event["init_event_loop"]:
                    status_placeholder.info("🔄 Initializing agent...")

                elif "start_event_loop" in event and event["start_event_loop"]:
                    status_placeholder.info("▶️ Starting query processing...")

                elif "complete" in event and event["complete"]:
                    status_placeholder.success("✅ Processing cycle completed")

                elif "result" in event:
                    status_placeholder.success("🎯 Query completed successfully!")
                    break

                elif "error" in event:
                    status_placeholder.error(f"❌ Error: {event['message']}")
                    full_response = event.get("message", "Unknown error occurred")
                    break

            except Exception as event_error:
                # Handle individual event processing errors
                st.warning(f"Warning: Error processing event - {str(event_error)}")
                continue

        # Store final response and update history
        st.session_state.last_response = full_response
        st.session_state.last_tools_used = current_tools
        add_to_query_history(
            query_text, bool(full_response and not full_response.startswith("Error"))
        )

    except Exception as e:
        error_message = f"Error processing query: {str(e)}"
        st.error(error_message)
        st.session_state.last_response = error_message
        st.session_state.last_tools_used = []
        add_to_query_history(query_text, False)


async def process_query_regular(agent: VaultPKIAgent, query_text: str) -> None:
    """Process a query using the regular (non-streaming) method.

    Args:
        agent: VaultPKIAgent instance
        query_text: User query text
    """
    try:
        with st.spinner("Processing your query..."):
            response = await agent.query(query_text)
            st.session_state.last_response = response
            st.session_state.last_tools_used = []  # No tool visibility in regular mode
            add_to_query_history(
                query_text, bool(response and not response.startswith("Error"))
            )

            # Show result immediately
            st.markdown("### Response")
            st.markdown(response)

    except Exception as e:
        error_message = f"Error processing query: {str(e)}"
        st.error(error_message)
        st.session_state.last_response = error_message
        st.session_state.last_tools_used = []
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
        # Streaming mode toggle
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown("### Query Options")
        with col2:
            use_streaming = st.toggle(
                "🔄 Real-time Streaming",
                value=True,
                help="Enable real-time streaming of responses",
            )
            # Store streaming preference in session state for sidebar display
            st.session_state.streaming_enabled = use_streaming

        # Query input
        query_text = render_query_input()

        # Process query if submitted
        if query_text:
            if use_streaming:
                # Run streaming query processing
                asyncio.run(process_query_async(st.session_state.agent, query_text))
            else:
                # Run regular query processing (legacy mode)
                asyncio.run(process_query_regular(st.session_state.agent, query_text))

        # Show previous results if available (when not actively processing)
        if "last_response" in st.session_state and query_text is None:
            st.markdown("### Previous Response")
            st.markdown(st.session_state.last_response)

            # Show tools used in the last query
            if (
                "last_tools_used" in st.session_state
                and st.session_state.last_tools_used
            ):
                with st.expander("🔧 Tools Used in Last Query"):
                    for tool in st.session_state.last_tools_used:
                        st.markdown(tool)

        # Query history
        render_query_history()

        # Connection status
        show_connection_status()

    # Footer
    render_footer()


if __name__ == "__main__":
    main()
