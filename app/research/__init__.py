"""
Research subsystem for CARA.

Exports:
- ResearchPlanner
- Researcher
- EvidenceCollector
- ContradictionDetector, ContradictionRecord
- CitationMapper
- classify_source_type, get_source_credibility
"""

from app.research.citation import CitationMapper
from app.research.contradiction import ContradictionDetector, ContradictionRecord
from app.research.evidence import EvidenceCollector
from app.research.planner import ResearchPlanner
from app.research.researcher import Researcher
from app.research.source_quality import classify_source_type, get_source_credibility

__all__ = [
    "CitationMapper",
    "ContradictionDetector",
    "ContradictionRecord",
    "EvidenceCollector",
    "ResearchPlanner",
    "Researcher",
    "classify_source_type",
    "get_source_credibility",
]
