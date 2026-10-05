"""
Unit tests for Research Planner and CitationMapper.
"""

from app.research.citation import CitationMapper
from app.research.planner import ResearchPlanner
from app.schemas.evidence import Evidence
from app.schemas.research import ResearchComplexity, ResearchDepth


def test_research_planner():
    planner = ResearchPlanner()
    comp_quick = planner.analyze_complexity("what is python", ResearchDepth.QUICK)
    assert comp_quick == ResearchComplexity.SIMPLE

    plan = planner.create_plan("what is python", comp_quick)
    assert len(plan) > 0


def test_citation_mapper():
    mapper = CitationMapper()
    ev1 = Evidence(
        claim="Claim 1",
        content="Evidence content 1",
        url="https://python.org",
        title="Python Docs",
    )
    ev2 = Evidence(
        claim="Claim 2",
        content="Evidence content 2",
        url="https://python.org",
        title="Python Docs Repeat",
    )

    idx1 = mapper.get_or_create_citation(ev1)
    idx2 = mapper.get_or_create_citation(ev2)
    # Identical URL should yield identical index
    assert idx1 == idx2 == 1

    bib = mapper.format_bibliography_markdown()
    assert "[1] [Python Docs]" in bib
