"""Streamlit web interface for the Vault PKI Query Agent."""

import streamlit as st
from datetime import datetime
from typing import List, Optional

from ..models.query import QueryResult, CertificateSummary, AuditEvent
from .example_prompts import get_prompts_by_category


def setup_page_config():
    """Configure Streamlit page settings."""
    st.set_page_config(
        page_title="Vault PKI Query Agent",
        page_icon="🔐",
        layout="wide",
        initial_sidebar_state="expanded",
    )


def render_header():
    """Render the main page header."""
    st.title("🔐 Vault PKI Query Agent")
    st.markdown("""
    **Natural language interface for HashiCorp Vault PKI operations**
    
    Ask questions about your certificates, audit events, and PKI infrastructure using plain English.
    """)


def render_sidebar():
    """Render the sidebar with example prompts and help."""
    with st.sidebar:
        st.header("📚 Example Queries")

        prompts_by_category = get_prompts_by_category()

        for category, prompts in prompts_by_category.items():
            st.subheader(category)
            for prompt in prompts:
                if st.button(
                    prompt["prompt"],
                    key=f"example_{hash(prompt['prompt'])}",
                    help=prompt["description"],
                    use_container_width=True,
                ):
                    st.session_state.selected_prompt = prompt["prompt"]

        st.divider()

        st.header("ℹ️ System Info")

        # Display connection status
        mcp_url = st.session_state.get("mcp_server_url", "Not configured")
        st.text(f"MCP Server: {mcp_url}")

        # Health check button
        if st.button("🔄 Check Health", use_container_width=True):
            st.session_state.health_check_requested = True


def render_query_input() -> Optional[str]:
    """Render the query input interface.

    Returns:
        Query text if submitted, None otherwise
    """
    # Check if an example prompt was selected
    if "selected_prompt" in st.session_state:
        prompt_text = st.session_state.selected_prompt
        del st.session_state.selected_prompt
    else:
        prompt_text = ""

    # Query input
    query_text = st.text_input(
        "Enter your question about Vault PKI:",
        value=prompt_text,
        placeholder="e.g., Show me all certificates expiring in next 30 days",
        help="Type your question in natural language",
    )

    col1, col2, col3 = st.columns([1, 1, 4])

    with col1:
        submit_clicked = st.button("🔍 Query", type="primary", use_container_width=True)

    with col2:
        clear_clicked = st.button("🗑️ Clear", use_container_width=True)
        if clear_clicked:
            st.rerun()

    if submit_clicked and query_text.strip():
        return query_text.strip()

    return None


def render_query_result(result: QueryResult):
    """Render query results in an organized layout.

    Args:
        result: QueryResult object containing response data
    """
    if not result.success:
        st.error(f"Query failed: {result.message}")
        if result.errors:
            with st.expander("Error Details"):
                for error in result.errors:
                    st.text(error)
        return

    # Success message
    st.success(result.message)

    # Query metadata
    if result.query_metadata:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Execution Time", f"{result.query_metadata.execution_time_ms} ms")
        with col2:
            st.metric("Results", result.query_metadata.results_count)
        with col3:
            st.metric("MCP Calls", result.query_metadata.mcp_calls_made or 0)

    # Render different result types
    if result.certificates:
        render_certificates(result.certificates)

    if result.audit_events:
        render_audit_events(result.audit_events)

    # Show any warnings
    if result.errors:
        with st.expander("⚠️ Warnings"):
            for error in result.errors:
                st.warning(error)


def render_certificates(certificates: List[CertificateSummary]):
    """Render certificate information in a table.

    Args:
        certificates: List of certificate summaries
    """
    st.subheader(f"📜 Certificates ({len(certificates)})")

    if not certificates:
        st.info("No certificates found matching your query.")
        return

    # Create data for the table
    data = []
    for cert in certificates:
        status = (
            "🔴 Revoked"
            if cert.is_revoked
            else (
                "🟠 Expired"
                if cert.is_expired
                else ("🟡 Expiring" if cert.days_until_expiry <= 30 else "🟢 Active")
            )
        )

        data.append(
            {
                "Status": status,
                "Common Name": cert.subject_cn,
                "Serial Number": cert.serial_number,
                "PKI Engine": cert.pki_engine,
                "Days Until Expiry": cert.days_until_expiry,
                "Issuer Chain": " → ".join(cert.issuer_hierarchy)
                if cert.issuer_hierarchy
                else "N/A",
            }
        )

    st.dataframe(
        data,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Status": st.column_config.TextColumn("Status", width="small"),
            "Common Name": st.column_config.TextColumn("Common Name", width="medium"),
            "Serial Number": st.column_config.TextColumn(
                "Serial Number", width="medium"
            ),
            "PKI Engine": st.column_config.TextColumn("PKI Engine", width="small"),
            "Days Until Expiry": st.column_config.NumberColumn(
                "Days Until Expiry", width="small"
            ),
            "Issuer Chain": st.column_config.TextColumn("Issuer Chain", width="large"),
        },
    )

    # Detailed view
    with st.expander("🔍 Detailed Certificate Information"):
        for i, cert in enumerate(certificates):
            st.markdown(f"**Certificate {i + 1}: {cert.subject_cn}**")

            col1, col2, col3 = st.columns(3)
            with col1:
                st.text(f"Serial: {cert.serial_number}")
                st.text(f"Engine: {cert.pki_engine}")
            with col2:
                st.text(f"Expires in: {cert.days_until_expiry} days")
                st.text(f"Status: {cert.status_display}")
            with col3:
                if cert.issuer_hierarchy:
                    st.text("Issuer Chain:")
                    for issuer in cert.issuer_hierarchy:
                        st.text(f"  • {issuer}")

            st.divider()


def render_audit_events(audit_events: List[AuditEvent]):
    """Render audit event information.

    Args:
        audit_events: List of audit events
    """
    st.subheader(f"📋 Audit Events ({len(audit_events)})")

    if not audit_events:
        st.info("No audit events found matching your query.")
        return

    # Create data for the table
    data = []
    for event in audit_events:
        data.append(
            {
                "Timestamp": event.timestamp,
                "Event Type": event.event_type.replace("_", " ").title(),
                "Certificate": event.certificate_subject,
                "Actor": event.actor_name,
                "Remote Address": event.remote_address or "N/A",
                "Request Path": event.request_path or "N/A",
            }
        )

    st.dataframe(
        data,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Timestamp": st.column_config.DatetimeColumn("Timestamp", width="medium"),
            "Event Type": st.column_config.TextColumn("Event Type", width="small"),
            "Certificate": st.column_config.TextColumn("Certificate", width="medium"),
            "Actor": st.column_config.TextColumn("Actor", width="medium"),
            "Remote Address": st.column_config.TextColumn(
                "Remote Address", width="small"
            ),
            "Request Path": st.column_config.TextColumn("Request Path", width="large"),
        },
    )

    # Detailed view
    with st.expander("🔍 Detailed Audit Information"):
        for i, event in enumerate(audit_events):
            st.markdown(
                f"**Event {i + 1}: {event.event_type.replace('_', ' ').title()}**"
            )

            col1, col2 = st.columns(2)
            with col1:
                st.text(f"Certificate: {event.certificate_subject}")
                st.text(f"Actor: {event.actor_name}")
                st.text(f"Actor ID: {event.actor_id or 'N/A'}")
            with col2:
                st.text(f"Timestamp: {event.timestamp}")
                st.text(f"Remote Address: {event.remote_address or 'N/A'}")
                st.text(f"Request Path: {event.request_path or 'N/A'}")

            if event.mount_accessor:
                st.text(f"Mount Accessor: {event.mount_accessor}")

            st.divider()


def render_query_history():
    """Render query history section."""
    if "query_history" not in st.session_state:
        st.session_state.query_history = []

    if st.session_state.query_history:
        with st.expander("📜 Query History"):
            for i, (timestamp, query, success) in enumerate(
                reversed(st.session_state.query_history[-10:])
            ):
                status_icon = "✅" if success else "❌"
                st.text(f"{status_icon} {timestamp}: {query}")


def add_to_query_history(query: str, success: bool):
    """Add a query to the session history.

    Args:
        query: Query text
        success: Whether the query was successful
    """
    if "query_history" not in st.session_state:
        st.session_state.query_history = []

    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.query_history.append((timestamp, query, success))

    # Keep only last 50 queries
    if len(st.session_state.query_history) > 50:
        st.session_state.query_history = st.session_state.query_history[-50:]


def show_connection_status():
    """Show MCP server connection status."""
    if st.session_state.get("health_check_requested"):
        st.session_state.health_check_requested = False

        # This would be replaced with actual health check
        st.info(
            "Health check functionality will be implemented with actual MCP client."
        )


def render_footer():
    """Render page footer."""
    st.divider()
    st.markdown(
        """
    <div style='text-align: center; color: #666; font-size: 0.8em;'>
    Vault PKI Query Agent | Built with Streamlit and AWS Strands Agent SDK
    </div>
    """,
        unsafe_allow_html=True,
    )
