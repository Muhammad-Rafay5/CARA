"""
LangGraph Execution Graph for CARA.

Compiles stateful research workflow with:
- Deterministic task analysis & complexity classification
- Automatic model selection (zero prompt overhead)
- Bounded iterative tool execution & evidence gathering
- Stage 1 Evidence verification & Stage 2 Report verification
- Targeted recovery loops on gaps or errors without full restarts
- Comprehensive budget guardrails enforcing hard stop criteria
"""

from __future__ import annotations

from typing import Any, Dict
from langgraph.graph import END, START, StateGraph

from app.agent.nodes import (
    analyze_task,
    check_budget,
    classify_failure,
    collect_evidence,
    create_plan,
    evaluate_evidence,
    execute_research,
    final_verification,
    finalize,
    generate_report,
    recover,
    select_model,
    verify_research,
)
from app.agent.routing import (
    route_model,
    route_recovery,
    route_research,
    route_verification,
)
from app.observability.logging import get_logger
from app.schemas.research import ResearchState

logger = get_logger(__name__)


def build_research_graph() -> Any:
    """
    Construct and compile the stateful LangGraph agent execution graph.
    """
    workflow = StateGraph(ResearchState)

    # Register Nodes
    workflow.add_node("analyze_task", analyze_task)
    workflow.add_node("check_budget", check_budget)
    workflow.add_node("select_model", select_model)
    workflow.add_node("create_plan", create_plan)
    workflow.add_node("execute_research", execute_research)
    workflow.add_node("collect_evidence", collect_evidence)
    workflow.add_node("evaluate_evidence", evaluate_evidence)
    workflow.add_node("verify_research", verify_research)
    workflow.add_node("classify_failure", classify_failure)
    workflow.add_node("recover", recover)
    workflow.add_node("generate_report", generate_report)
    workflow.add_node("final_verification", final_verification)
    workflow.add_node("finalize", finalize)

    # Edges
    workflow.add_edge(START, "analyze_task")

    # Conditional edge from analyze_task: if cached -> finalize, else select_model
    workflow.add_conditional_edges(
        "analyze_task",
        route_model,
        {
            "finalize": "finalize",
            "select_model": "select_model",
        },
    )

    workflow.add_edge("select_model", "check_budget")
    workflow.add_edge("check_budget", "create_plan")
    workflow.add_edge("create_plan", "execute_research")

    # Conditional edge from execute_research: more steps -> execute_research, else collect_evidence
    workflow.add_conditional_edges(
        "execute_research",
        route_research,
        {
            "execute_research": "execute_research",
            "collect_evidence": "collect_evidence",
        },
    )

    workflow.add_edge("collect_evidence", "evaluate_evidence")
    workflow.add_edge("evaluate_evidence", "verify_research")

    # Conditional edge from verify_research: PASS -> generate_report, else classify_failure
    workflow.add_conditional_edges(
        "verify_research",
        route_verification,
        {
            "generate_report": "generate_report",
            "classify_failure": "classify_failure",
        },
    )

    workflow.add_edge("classify_failure", "recover")

    # Conditional edge from recover: retry research or generate partial report
    workflow.add_conditional_edges(
        "recover",
        route_recovery,
        {
            "execute_research": "execute_research",
            "generate_report": "generate_report",
        },
    )

    workflow.add_edge("generate_report", "final_verification")
    workflow.add_edge("final_verification", "finalize")
    workflow.add_edge("finalize", END)

    compiled_graph = workflow.compile()
    logger.info("Compiled LangGraph research workflow successfully")
    return compiled_graph


# Pre-compiled application singleton graph
research_graph = build_research_graph()
