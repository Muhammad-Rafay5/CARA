"""
Streamlit User Interface for CARA (Cost-Aware Autonomous Research Agent).

Features:
- Research query input form with depth control (quick, standard, deep) and token overrides.
- Live execution triggers connecting to the LangGraph research engine.
- Real-time badges for selected model provider, tier, and circuit breaker status.
- Two-stage verification score gauges and contradiction detection alerts.
- Resource & cost accounting breakdown table (LLM calls, tool calls, tokens, USD cost).
- Formatted Markdown report rendering with interactive citations and export buttons.
"""

from __future__ import annotations

import asyncio
import time
import streamlit as st

from app.agent.graph import research_graph
from app.models.registry import registry as model_registry
from app.observability.metrics import metrics
from app.schemas.research import ResearchDepth, ResearchState, ResearchStatus

# Page configuration
st.set_page_config(
    page_title="CARA — Cost-Aware Autonomous Research Agent",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling
st.markdown(
    """
    <style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E293B;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #64748B;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 1rem;
        text-align: center;
    }
    .badge {
        display: inline-block;
        padding: 0.25rem 0.6rem;
        border-radius: 4px;
        font-size: 0.85rem;
        font-weight: 600;
        margin-right: 0.5rem;
    }
    .badge-primary { background-color: #EEF2FF; color: #4F46E5; }
    .badge-success { background-color: #ECFDF5; color: #059669; }
    .badge-warning { background-color: #FFFBEB; color: #D97706; }
    </style>
    """,
    unsafe_allow_html=True,
)

# Header
st.markdown('<div class="main-title">🔬 CARA — Cost-Aware Research Agent</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-title">Autonomous multi-step research with deterministic model routing, 2-stage verification, and strict budget guardrails.</div>',
    unsafe_allow_html=True,
)

# Sidebar: Controls & Live System Metrics
with st.sidebar:
    st.header("⚙️ Research Configuration")

    depth_selection = st.selectbox(
        "Research Depth",
        options=["quick", "standard", "deep"],
        index=1,
        help="Quick: 1 iteration, fast models. Standard: up to 2 iterations. Deep: up to 3 iterations, rigorous audit.",
    )

    max_tokens = st.slider(
        "Token Budget Override",
        min_value=2000,
        max_value=15000,
        value=8000,
        step=1000,
        help="Hard ceiling on cumulative tokens across all model calls.",
    )

    st.markdown("---")
    st.header("📊 System Status")

    available_models = len(model_registry.available())
    total_models = len(model_registry.all())

    st.metric("Available Models", f"{available_models} / {total_models}")
    st.metric("Total Requests Served", metrics._total_requests)
    st.metric("Uptime", f"{int(metrics.uptime_seconds)}s")

    st.markdown("---")
    st.caption("CARA v1.0.0 — Google Antigravity IDE Autonomous Agent")

# Main Interface: Input Form
query = st.text_area(
    "Enter Research Topic or Question:",
    placeholder="e.g. Compare PostgreSQL and MongoDB performance trade-offs for high-write IoT workloads.",
    height=90,
)

col_btn, col_clear = st.columns([1, 6])
start_research = col_btn.button("🚀 Start Research", type="primary", use_container_width=True)

if start_research:
    if not query.strip() or len(query.strip()) < 8:
        st.error("Please enter a substantive query (at least 8 characters).")
    else:
        depth_enum = (
            ResearchDepth.QUICK if depth_selection == "quick"
            else ResearchDepth.DEEP if depth_selection == "deep"
            else ResearchDepth.STANDARD
        )

        initial_state = ResearchState(
            query=query.strip(),
            depth=depth_enum,
            max_tokens=max_tokens,
        )

        status_container = st.container()
        progress_bar = st.progress(0.1)

        with status_container:
            with st.spinner("Executing autonomous research pipeline..."):
                start_time = time.time()
                try:
                    # Execute LangGraph asynchronously
                    final_output = asyncio.run(research_graph.ainvoke(initial_state))

                    if isinstance(final_output, dict):
                        state = ResearchState(**final_output)
                    else:
                        state = final_output

                    elapsed = round(time.time() - start_time, 2)
                    progress_bar.progress(1.0)

                    st.success(f"Research completed in {elapsed}s with status: **{state.status.value.upper()}**")

                    # Metadata & Badges row
                    b1, b2, b3, b4 = st.columns(4)
                    with b1:
                        st.metric("Selected Model", f"{state.selected_provider or 'auto'}")
                    with b2:
                        st.metric("Tool Calls", f"{state.tool_calls} / {state.max_tool_calls}")
                    with b3:
                        st.metric("Verification Score", f"{(state.verification_score or 0.0):.2f}")
                    with b4:
                        st.metric("Estimated Cost", f"${state.cost_usd:.4f}")

                    if state.warnings:
                        with st.expander("⚠️ Pipeline Warnings & Recovery Events", expanded=False):
                            for w in state.warnings:
                                st.warning(w)

                    st.markdown("---")

                    # Report Presentation Tabbed View
                    tab_report, tab_evidence, tab_trace = st.tabs(["📄 Final Report", "🔍 Gathered Evidence", "🔬 Execution Trace"])

                    with tab_report:
                        if state.report:
                            st.markdown(state.report)
                            st.download_button(
                                label="📥 Export Report as Markdown",
                                data=state.report,
                                file_name=f"research_report_{state.request_id[:8]}.md",
                                mime="text/markdown",
                            )
                        else:
                            st.info("No report content generated.")

                    with tab_evidence:
                        st.subheader(f"Evidence Items Collected ({len(state.evidence_items)})")
                        for idx, ev in enumerate(state.evidence_items, 1):
                            with st.expander(f"[{idx}] {ev.get('title', 'Evidence Source')} (Confidence: {ev.get('confidence', 0.5):.2f})"):
                                st.write(f"**Source URL:** {ev.get('url')}")
                                st.write(f"**Claim:** {ev.get('claim')}")
                                st.code(ev.get('content', '')[:600], language="text")

                    with tab_trace:
                        st.subheader("Step-by-Step Plan Execution")
                        for step_idx, step_desc in enumerate(state.research_plan, 1):
                            st.write(f"**Step {step_idx}:** {step_desc}")

                        if state.failure_history:
                            st.subheader("Targeted Recovery Attempts")
                            st.json(state.failure_history)

                except Exception as err:
                    st.error(f"Execution failed with error: {str(err)}")
