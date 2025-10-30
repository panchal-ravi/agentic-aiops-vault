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

    # Apply Vault-inspired theme with modern fonts and white backgrounds
    st.markdown(
        """
    <style>
    /* Import Noto Sans fonts with preload for better performance */
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans:ital,wght@0,100..900;1,100..900&family=Noto+Sans+Mono:wght@100..900&display=swap');
    
    /* Force font loading and apply globally with highest priority */
    * {
        font-family: 'Noto Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif !important;
    }
    
    /* Specific targeting for all text elements */
    body, html, div, span, p, h1, h2, h3, h4, h5, h6, 
    .stApp, .main, [data-testid="stAppViewContainer"],
    [data-testid="block-container"], .css-1d391kg,
    .css-18e3th9, .css-1dp5vir, .css-k1vhr4 {
        font-family: 'Noto Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
    }
    
    /* Code elements with Noto Sans Mono */
    code, pre, kbd, samp, tt, .stCode, [class*="code"],
    .css-1cpxqw2, .css-1x8cf1d {
        font-family: 'Noto Sans Mono', 'SF Mono', 'Monaco', 'Inconsolata', monospace !important;
    }
    
    /* Root variables for consistent theming */
    :root {
        --vault-primary: #1563ff;
        --vault-primary-dark: #0d47cc;
        --vault-secondary: #2563eb;
        --vault-bg: #ffffff;
        --vault-sidebar-bg: #f8fafc;
        --vault-content-bg: #ffffff;
        --vault-border: #e2e8f0;
        --vault-border-dark: #cbd5e0;
        --vault-text-primary: #1a202c;
        --vault-text-secondary: #4a5568;
        --vault-text-muted: #718096;
        --vault-success: #38a169;
        --vault-warning: #d69e2e;
        --vault-error: #e53e3e;
        --vault-info: #3182ce;
    }
    
    /* Modern font configuration - using Noto Sans with maximum specificity */
    html, body, [class*="css"], .stApp, .main,
    div, span, p, h1, h2, h3, h4, h5, h6, label, input, button, select, textarea,
    [data-testid="stAppViewContainer"], [data-testid="block-container"],
    [data-testid="stSidebar"], .css-1d391kg, .css-18e3th9 {
        font-family: 'Noto Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif !important;
    }
    
    /* Code font - using Noto Sans Mono with maximum specificity */
    code, pre, .stCode, [class*="code"], kbd, samp, tt,
    .css-1cpxqw2, .css-1x8cf1d, [data-testid="stCodeBlock"] {
        font-family: 'Noto Sans Mono', 'SF Mono', 'Monaco', 'Inconsolata', 'Roboto Mono', monospace !important;
    }
    
    /* Main app background */
    .stApp {
        background-color: var(--vault-bg) !important;
        color: var(--vault-text-primary) !important;
        font-family: 'Noto Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
    }
    
    /* Sidebar styling - white background */
    .stSidebar {
        background-color: var(--vault-sidebar-bg) !important;
        border-right: 1px solid var(--vault-border) !important;
    }
    
    .stSidebar .stMarkdown,
    .stSidebar .stMarkdown *,
    .stSidebar h1,
    .stSidebar h2,
    .stSidebar h3,
    .stSidebar h4,
    .stSidebar h5,
    .stSidebar h6,
    .stSidebar p,
    .stSidebar div,
    .stSidebar span {
        color: var(--vault-text-primary) !important;
        background-color: transparent !important;
    }
    
    /* Arc browser specific fixes for sidebar text */
    [data-testid="stSidebar"] *,
    [data-testid="stSidebar"] div,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: var(--vault-text-primary) !important;
        background-color: transparent !important;
    }
    
    /* Main content area - white background */
    .main .block-container,
    [data-testid="block-container"] {
        background-color: var(--vault-content-bg) !important;
        color: var(--vault-text-primary) !important;
        padding: 2rem !important;
        border-radius: 8px !important;
        margin: 1rem !important;
    }
    
    /* Main content text styling with modern fonts */
    .main h1,
    .main h2,
    .main h3,
    .main h4,
    .main h5,
    .main h6 {
        color: var(--vault-text-primary) !important;
        font-family: 'Noto Sans', sans-serif !important;
        font-weight: 600 !important;
        letter-spacing: -0.025em !important;
    }
    
    .main h1 {
        font-size: 2.5rem !important;
        font-weight: 700 !important;
        margin-bottom: 1rem !important;
        background: linear-gradient(135deg, var(--vault-primary), var(--vault-secondary)) !important;
        -webkit-background-clip: text !important;
        -webkit-text-fill-color: transparent !important;
        background-clip: text !important;
        letter-spacing: -0.05em !important;
    }
    
    .main p,
    .main .stMarkdown,
    .main .stText,
    .main div {
        color: var(--vault-text-secondary) !important;
        line-height: 1.6 !important;
        font-family: 'Noto Sans', sans-serif !important;
        font-weight: 400 !important;
    }
    
    /* Input fields with modern styling */
    .stTextInput > div > div > input {
        background-color: var(--vault-content-bg) !important;
        color: var(--vault-text-primary) !important;
        border: 2px solid var(--vault-border) !important;
        border-radius: 8px !important;
        font-family: 'Noto Sans', sans-serif !important;
        font-weight: 400 !important;
        padding: 0.75rem 1rem !important;
        font-size: 1rem !important;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: var(--vault-primary) !important;
        box-shadow: 0 0 0 3px rgba(21, 99, 255, 0.1) !important;
        outline: none !important;
    }
    
    .stTextInput > label {
        color: var(--vault-text-primary) !important;
        font-family: 'Noto Sans', sans-serif !important;
        font-weight: 500 !important;
        font-size: 0.875rem !important;
        margin-bottom: 0.5rem !important;
    }
    
    .stTextInput input::placeholder {
        color: var(--vault-text-muted) !important;
        font-family: 'Noto Sans', sans-serif !important;
    }
    
    /* Modern button styling */
    .stButton > button {
        background-color: var(--vault-primary) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-family: 'Noto Sans', sans-serif !important;
        font-weight: 500 !important;
        font-size: 0.875rem !important;
        padding: 0.75rem 1.5rem !important;
        transition: all 0.2s ease !important;
        letter-spacing: 0.025em !important;
    }
    
    .stButton > button:hover {
        background-color: var(--vault-primary-dark) !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 12px rgba(21, 99, 255, 0.3) !important;
    }
    
    /* Secondary buttons */
    .stButton > button[kind="secondary"] {
        background-color: transparent !important;
        border: 2px solid var(--vault-border) !important;
        color: var(--vault-text-secondary) !important;
    }
    
    .stButton > button[kind="secondary"]:hover {
        border-color: var(--vault-primary) !important;
        color: var(--vault-primary) !important;
        background-color: rgba(21, 99, 255, 0.05) !important;
    }
    
    /* Sidebar buttons with light blue gradient background - maximum specificity */
    [data-testid="stSidebar"] button[kind="secondary"],
    [data-testid="stSidebar"] .stButton > button,
    [data-testid="stSidebar"] button {
        background: linear-gradient(135deg, #e0f2fe 0%, #dbeafe 100%) !important;
        border: 1px solid #bfdbfe !important;
        color: #1e293b !important;
        width: 100% !important;
        font-family: 'Noto Sans', sans-serif !important;
        font-weight: 500 !important;
        transition: all 0.2s ease !important;
        text-align: left !important;
        padding: 0.75rem 1rem !important;
        border-radius: 8px !important;
    }
    
    [data-testid="stSidebar"] button[kind="secondary"]:hover,
    [data-testid="stSidebar"] .stButton > button:hover,
    [data-testid="stSidebar"] button:hover {
        background: linear-gradient(135deg, #bfdbfe 0%, #93c5fd 100%) !important;
        border-color: #60a5fa !important;
        color: #0f172a !important;
        transform: translateX(2px) !important;
        box-shadow: 0 2px 8px rgba(59, 130, 246, 0.2) !important;
    }
    
    /* Data frames and tables */
    .stDataFrame {
        background-color: var(--vault-content-bg) !important;
        border: 1px solid var(--vault-border) !important;
        border-radius: 8px !important;
        font-family: 'Noto Sans', sans-serif !important;
    }
    
    .stDataFrame table {
        background-color: var(--vault-content-bg) !important;
        color: var(--vault-text-primary) !important;
        font-family: 'Noto Sans', sans-serif !important;
    }
    
    .stDataFrame th {
        background-color: #f8fafc !important;
        color: var(--vault-text-primary) !important;
        font-weight: 600 !important;
        font-family: 'Noto Sans', sans-serif !important;
        border-bottom: 2px solid var(--vault-border) !important;
    }
    
    .stDataFrame td {
        color: var(--vault-text-secondary) !important;
        border-bottom: 1px solid var(--vault-border) !important;
        font-family: 'Noto Sans', sans-serif !important;
    }
    
    /* Metrics with modern typography */
    [data-testid="metric-container"] {
        background-color: #f8fafc !important;
        border: 1px solid var(--vault-border) !important;
        border-radius: 8px !important;
        padding: 1rem !important;
    }
    
    [data-testid="metric-container"] > div {
        color: var(--vault-text-primary) !important;
        font-family: 'Noto Sans', sans-serif !important;
    }
    
    [data-testid="metric-container"] [data-testid="metric-value"] {
        font-weight: 600 !important;
        font-size: 1.5rem !important;
    }
    
    /* Alert boxes */
    .stAlert {
        border-radius: 8px !important;
        border: none !important;
        margin: 1rem 0 !important;
        font-family: 'Noto Sans', sans-serif !important;
    }
    
    .stSuccess {
        background-color: rgba(56, 161, 105, 0.1) !important;
        color: var(--vault-success) !important;
        border-left: 4px solid var(--vault-success) !important;
    }
    
    .stError {
        background-color: rgba(229, 62, 62, 0.1) !important;
        color: var(--vault-error) !important;
        border-left: 4px solid var(--vault-error) !important;
    }
    
    .stWarning {
        background-color: rgba(214, 158, 46, 0.1) !important;
        color: var(--vault-warning) !important;
        border-left: 4px solid var(--vault-warning) !important;
    }
    
    .stInfo {
        background-color: rgba(49, 130, 206, 0.1) !important;
        color: var(--vault-info) !important;
        border-left: 4px solid var(--vault-info) !important;
    }
    
    /* Expanders */
    .streamlit-expanderHeader {
        background-color: #f8fafc !important;
        color: var(--vault-text-primary) !important;
        border: 1px solid var(--vault-border) !important;
        border-radius: 8px !important;
        font-family: 'Noto Sans', sans-serif !important;
        font-weight: 500 !important;
        margin: 1rem 0 !important;
        clear: both !important;
    }
    
    .streamlit-expanderContent {
        background-color: var(--vault-content-bg) !important;
        border: 1px solid var(--vault-border) !important;
        border-top: none !important;
        border-radius: 0 0 8px 8px !important;
        clear: both !important;
        margin-bottom: 1rem !important;
    }
    
    /* Fix text overlap issues */
    .main .block-container > div {
        clear: both !important;
        margin-bottom: 1rem !important;
        position: relative !important;
        z-index: 1 !important;
    }
    
    /* Ensure proper spacing between sections */
    .stMarkdown {
        margin-bottom: 1rem !important;
        clear: both !important;
        position: relative !important;
        overflow: hidden !important;
    }
    
    .stExpander {
        margin: 1rem 0 !important;
        clear: both !important;
        position: relative !important;
        z-index: 2 !important;
    }
    
    /* Prevent text from floating or overlapping */
    .main .element-container {
        clear: both !important;
        position: relative !important;
        margin-bottom: 0.5rem !important;
    }
    
    /* Ensure query history section is properly isolated */
    .stExpander [data-testid="stExpanderDetails"] {
        clear: both !important;
        position: relative !important;
        background-color: var(--vault-content-bg) !important;
        padding: 1rem !important;
        margin: 0 !important;
        overflow: hidden !important;
    }
    
    /* Dividers */
    hr {
        border-color: var(--vault-border) !important;
        margin: 2rem 0 !important;
    }
    
    /* Code blocks with Noto Sans Mono */
    .stCode {
        background-color: #f8fafc !important;
        border: 1px solid var(--vault-border) !important;
        border-radius: 6px !important;
        font-family: 'Noto Sans Mono', monospace !important;
    }
    
    code {
        background-color: #f8fafc !important;
        color: var(--vault-primary) !important;
        padding: 0.25rem 0.5rem !important;
        border-radius: 4px !important;
        font-family: 'Noto Sans Mono', 'SF Mono', 'Monaco', monospace !important;
        font-size: 0.875rem !important;
        font-weight: 500 !important;
    }
    
    /* Toggle switch styling */
    .stCheckbox > label {
        color: var(--vault-text-primary) !important;
        font-family: 'Noto Sans', sans-serif !important;
        font-weight: 400 !important;
    }
    
    /* Custom status indicators */
    .status-active { color: var(--vault-success) !important; }
    .status-warning { color: var(--vault-warning) !important; }
    .status-error { color: var(--vault-error) !important; }
    .status-info { color: var(--vault-info) !important; }
    
    /* Modern scrollbars */
    ::-webkit-scrollbar {
        width: 6px;
        height: 6px;
    }
    
    ::-webkit-scrollbar-track {
        background: #f1f5f9;
        border-radius: 3px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: var(--vault-border-dark);
        border-radius: 3px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: var(--vault-primary);
    }
    
    /* Hide Streamlit branding - but preserve sidebar toggle */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: visible !important;}
    
    /* Ensure sidebar toggle icon displays correctly */
    button[kind="header"] {
        visibility: visible !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }
    
    [data-testid="collapsedControl"] {
        visibility: visible !important;
        display: flex !important;
    }
    
    [data-testid="collapsedControl"] svg {
        display: block !important;
        visibility: visible !important;
    }
    
    /* Hide text, show only icon */
    button[kind="header"] span[data-testid="stHeaderActionElements"] {
        font-size: 0 !important;
    }
    
    button[kind="header"] svg {
        display: block !important;
        visibility: visible !important;
        width: 1.5rem !important;
        height: 1.5rem !important;
    }
    
    /* Custom animation for loading states */
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.5; }
        100% { opacity: 1; }
    }
    
    .loading {
        animation: pulse 1.5s ease-in-out infinite;
    }
    
    /* Improved typography scale */
    h1 { font-size: 2.5rem; line-height: 1.2; }
    h2 { font-size: 2rem; line-height: 1.3; }
    h3 { font-size: 1.5rem; line-height: 1.4; }
    h4 { font-size: 1.25rem; line-height: 1.4; }
    h5 { font-size: 1.125rem; line-height: 1.5; }
    h6 { font-size: 1rem; line-height: 1.5; }
    
    /* Better spacing for readability */
    p { margin-bottom: 1rem; }
    
    /* Focus states for accessibility */
    *:focus {
        outline: 2px solid var(--vault-primary) !important;
        outline-offset: 2px !important;
    }
    </style>
    """,
        unsafe_allow_html=True,
    )


def render_header():
    """Render the main page header."""
    # Custom header with Vault styling
    st.markdown(
        """
    <div style="
        padding: 2rem 0 1rem 0;
        border-bottom: 1px solid var(--vault-border);
        margin-bottom: 2rem;
    ">
        <h1 style="
            font-size: 2.5rem !important;
            font-weight: 700 !important;
            margin: 0 0 0.5rem 0 !important;
            background: linear-gradient(135deg, #1563ff, #2563eb) !important;
            -webkit-background-clip: text !important;
            -webkit-text-fill-color: transparent !important;
            background-clip: text !important;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        ">
            🔐 Vault PKI Query Agent
        </h1>
        <p style="
            font-size: 1.1rem !important;
            color: var(--vault-text-secondary) !important;
            margin: 0 !important;
            font-weight: 400 !important;
            line-height: 1.5 !important;
        ">
            Natural language interface for HashiCorp Vault PKI operations
        </p>
        <p style="
            font-size: 0.95rem !important;
            color: var(--vault-text-muted) !important;
            margin: 0.5rem 0 0 0 !important;
            font-weight: 300 !important;
        ">
            Ask questions about your certificates, audit events, and PKI infrastructure using plain English.
        </p>
    </div>
    """,
        unsafe_allow_html=True,
    )


def render_sidebar():
    """Render the sidebar with example prompts and help."""
    with st.sidebar:
        # Vault-style sidebar header
        st.markdown(
            """
        <div style="
            text-align: center;
            padding: 1rem 0;
            border-bottom: 1px solid var(--vault-border);
            margin-bottom: 1.5rem;
        ">
            <h2 style="
                font-size: 1.25rem !important;
                margin: 0 !important;
                color: var(--vault-text-primary) !important;
                font-weight: 600 !important;
            ">📚 Example Queries</h2>
        </div>
        """,
            unsafe_allow_html=True,
        )

        prompts_by_category = get_prompts_by_category()

        for category, prompts in prompts_by_category.items():
            # Category header with better styling
            st.markdown(
                f"""
            <div style="
                margin: 1rem 0 0.5rem 0;
                padding: 0.5rem 0;
                border-bottom: 1px solid var(--vault-border);
            ">
                <h3 style="
                    font-size: 1rem !important;
                    margin: 0 !important;
                    color: var(--vault-primary) !important;
                    font-weight: 500 !important;
                ">{category}</h3>
            </div>
            """,
                unsafe_allow_html=True,
            )

            for prompt in prompts:
                if st.button(
                    prompt["prompt"],
                    key=f"example_{hash(prompt['prompt'])}",
                    help=prompt["description"],
                    use_container_width=True,
                ):
                    st.session_state.selected_prompt = prompt["prompt"]

        st.markdown(
            '<div style="margin: 2rem 0;"><hr style="border: 1px solid var(--vault-border);"></div>',
            unsafe_allow_html=True,
        )

        # System Info section
        st.markdown(
            """
        <div style="
            padding: 1rem 0 0.5rem 0;
        ">
            <h2 style="
                font-size: 1.25rem !important;
                margin: 0 0 1rem 0 !important;
                color: var(--vault-text-primary) !important;
                font-weight: 600 !important;
            ">ℹ️ System Info</h2>
        </div>
        """,
            unsafe_allow_html=True,
        )

        # Display connection status with better styling
        mcp_url = st.session_state.get("mcp_server_url", "Not configured")
        st.markdown(
            f"""
        <div style="
            background-color: var(--vault-content-bg);
            padding: 0.75rem;
            border-radius: 6px;
            border: 1px solid var(--vault-border);
            margin-bottom: 1rem;
        ">
            <div style="
                font-size: 0.85rem;
                color: var(--vault-text-muted);
                margin-bottom: 0.25rem;
            ">MCP Server</div>
            <div style="
                color: var(--vault-text-primary);
                font-family: 'JetBrains Mono', monospace;
                font-size: 0.8rem;
            ">{mcp_url}</div>
        </div>
        """,
            unsafe_allow_html=True,
        )

        # Health check button
        if st.button("🔄 Check Health", use_container_width=True):
            st.session_state.health_check_requested = True

        st.markdown(
            '<div style="margin: 2rem 0;"><hr style="border: 1px solid var(--vault-border);"></div>',
            unsafe_allow_html=True,
        )

        # Streaming Info section
        st.markdown(
            """
        <div style="
            padding: 1rem 0 0.5rem 0;
        ">
            <h2 style="
                font-size: 1.25rem !important;
                margin: 0 0 1rem 0 !important;
                color: var(--vault-text-primary) !important;
                font-weight: 600 !important;
            ">🔄 Streaming Info</h2>
        </div>
        """,
            unsafe_allow_html=True,
        )

        # Streaming mode info with cards
        streaming_enabled = st.session_state.get("streaming_enabled", True)
        if streaming_enabled:
            st.markdown(
                """
            <div style="
                background-color: rgba(56, 161, 105, 0.1);
                border: 1px solid var(--vault-success);
                border-radius: 6px;
                padding: 1rem;
                margin-bottom: 1rem;
            ">
                <div style="
                    color: var(--vault-success);
                    font-weight: 600;
                    margin-bottom: 0.5rem;
                ">Real-time streaming: Enabled</div>
                <div style="
                    color: var(--vault-text-secondary);
                    font-size: 0.85rem;
                    line-height: 1.4;
                ">
                    <strong>Benefits:</strong><br>
                    • See responses as they generate<br>
                    • Monitor tool usage in real-time<br>
                    • Better user experience<br>
                    • Early error detection
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                """
            <div style="
                background-color: rgba(49, 130, 206, 0.1);
                border: 1px solid var(--vault-info);
                border-radius: 6px;
                padding: 1rem;
                margin-bottom: 1rem;
            ">
                <div style="
                    color: var(--vault-info);
                    font-weight: 600;
                    margin-bottom: 0.5rem;
                ">Regular mode: Enabled</div>
                <div style="
                    color: var(--vault-text-secondary);
                    font-size: 0.85rem;
                    line-height: 1.4;
                ">
                    <strong>Mode:</strong><br>
                    • Complete response at once<br>
                    • Traditional query processing<br>
                    • No real-time feedback
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )

        # Show performance tips
        with st.expander("💡 Performance Tips"):
            st.markdown(
                """
            <div style="
                color: var(--vault-text-secondary);
                font-size: 0.85rem;
                line-height: 1.5;
            ">
            • Use <strong>streaming mode</strong> for complex queries<br>
            • Streaming shows tool usage in real-time<br>
            • Regular mode for simple, quick queries<br>
            • Watch the status indicators during processing
            </div>
            """,
                unsafe_allow_html=True,
            )


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

    # Query input section with improved styling
    st.markdown(
        """
    <div style="
        background-color: var(--vault-sidebar-bg);
        padding: 1.5rem;
        border-radius: 8px;
        border: 1px solid var(--vault-border);
        margin-bottom: 2rem;
    ">
        <h3 style="
            font-size: 1.1rem !important;
            margin: 0 0 1rem 0 !important;
            color: var(--vault-text-primary) !important;
            font-weight: 500 !important;
        ">🔍 Ask Your Question</h3>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # Use a form to enable Enter key submission
    with st.form(key="query_form", clear_on_submit=False):
        # Query input
        query_text = st.text_input(
            "Enter your question about Vault PKI:",
            value=prompt_text,
            placeholder="e.g., Show me all certificates expiring in next 30 days",
            help="Type your question in natural language and press Enter or click Query to submit. In streaming mode, you'll see real-time responses and tool usage.",
            label_visibility="collapsed",
        )

        col1, col2, col3 = st.columns([1, 1, 4])

        with col1:
            submit_clicked = st.form_submit_button(
                "🔍 Query", type="primary", use_container_width=True
            )

        with col2:
            clear_clicked = st.form_submit_button("🗑️ Clear", use_container_width=True)

        # Handle form submission - the form submits when ANY button is clicked or Enter is pressed
        # We need to check which button was clicked
        if clear_clicked:
            # Clear the session state for selected prompt
            if "selected_prompt" in st.session_state:
                del st.session_state.selected_prompt
            st.rerun()
            return None

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
        # Add proper spacing and isolation for query history
        st.markdown(
            """
        <div style="
            margin-top: 2rem;
            clear: both;
            position: relative;
            z-index: 1;
        "></div>
        """,
            unsafe_allow_html=True,
        )

        with st.expander("📜 Query History"):
            st.markdown(
                """
            <div style="
                padding: 0.5rem 0;
                clear: both;
                overflow: hidden;
            ">
            """,
                unsafe_allow_html=True,
            )

            for i, (timestamp, query, success) in enumerate(
                reversed(st.session_state.query_history[-10:])
            ):
                status_icon = "✅" if success else "❌"
                st.markdown(
                    f"""
                <div style="
                    margin: 0.5rem 0;
                    padding: 0.25rem 0;
                    clear: both;
                    line-height: 1.4;
                    font-family: 'Noto Sans', sans-serif;
                ">
                    {status_icon} {timestamp}: {query}
                </div>
                """,
                    unsafe_allow_html=True,
                )

            st.markdown("</div>", unsafe_allow_html=True)


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
    st.markdown(
        '<div style="margin: 3rem 0 1rem 0;"><hr style="border: 1px solid var(--vault-border);"></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        """
    <div style='
        text-align: center;
        color: var(--vault-text-muted);
        font-size: 0.85rem;
        padding: 1rem;
        background-color: var(--vault-sidebar-bg);
        border-radius: 8px;
        border: 1px solid var(--vault-border);
        margin: 1rem 0;
    '>
        <div style='margin-bottom: 0.5rem; font-weight: 500; color: var(--vault-text-secondary);'>
            🔐 Vault PKI Query Agent
        </div>
        <div style='font-size: 0.8rem;'>
            Built with Streamlit and AWS Strands Agent SDK<br>
            ✨ Features real-time streaming responses and tool monitoring
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )
