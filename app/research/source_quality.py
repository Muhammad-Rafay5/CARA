"""
Source Quality Scoring Engine for CARA.

Determines the credibility and trustworthiness of sources using deterministic heuristics:
Hierarchy:
    OFFICIAL_DOCS (1.0): python.org, docs.github.com, developer.mozilla.org, cloud providers, gov, edu
    ACADEMIC (0.9): arxiv.org, sciencedirect, ieee, acm, ncbi, nature, springer
    NEWS (0.7): reuters, bbc, bloomberg, nytimes, wsj, techcrunch, theverge
    GITHUB (0.7): github.com, gitlab.com
    BLOG (0.5): medium.com, dev.to, substack.com, personal tech blogs
    FORUM (0.4): stackoverflow.com, reddit.com, news.ycombinator.com
    UNKNOWN (0.2): general unclassified web domains
"""

from __future__ import annotations

from urllib.parse import urlparse
from app.schemas.evidence import SourceType

# Known authoritative domain registries
OFFICIAL_DOMAINS = {
    "python.org", "docs.python.org", "github.com/docs", "docs.github.com",
    "developer.mozilla.org", "w3.org", "kubernetes.io", "docker.com",
    "aws.amazon.com", "cloud.google.com", "learn.microsoft.com", "fastapi.tiangolo.com",
    "pydantic.dev", "docs.pydantic.dev", "sqlalchemy.org", "postgresql.org",
}

ACADEMIC_DOMAINS = {
    "arxiv.org", "biorxiv.org", "medrxiv.org", "nature.com", "science.org",
    "ieee.org", "acm.org", "ncbi.nlm.nih.gov", "sciencedirect.com", "springer.com",
    "scholar.google.com", "openalex.org",
}

NEWS_DOMAINS = {
    "reuters.com", "bloomberg.com", "apnews.com", "bbc.com", "bbc.co.uk",
    "nytimes.com", "wsj.com", "techcrunch.com", "theverge.com", "wired.com",
    "arstechnica.com", "zdnet.com", "ft.com",
}

GITHUB_DOMAINS = {
    "github.com", "gitlab.com", "bitbucket.org",
}

BLOG_DOMAINS = {
    "medium.com", "dev.to", "hashnode.dev", "substack.com",
}

FORUM_DOMAINS = {
    "stackoverflow.com", "stackexchange.com", "reddit.com", "news.ycombinator.com", "quora.com",
}

CREDIBILITY_SCORES = {
    SourceType.OFFICIAL_DOCS: 1.0,
    SourceType.ACADEMIC: 0.9,
    SourceType.NEWS: 0.7,
    SourceType.GITHUB: 0.7,
    SourceType.BLOG: 0.5,
    SourceType.FORUM: 0.4,
    SourceType.UNKNOWN: 0.2,
}


def classify_source_type(url: str) -> SourceType:
    """Classify the source type based on URL domain heuristics."""
    if not url:
        return SourceType.UNKNOWN

    parsed = urlparse(url.lower())
    hostname = parsed.hostname or ""

    # Check top-level domain rules
    if hostname.endswith(".gov") or hostname.endswith(".edu"):
        return SourceType.OFFICIAL_DOCS

    # Check exact/subdomain matches
    for d in OFFICIAL_DOMAINS:
        if hostname == d or hostname.endswith(f".{d}"):
            return SourceType.OFFICIAL_DOCS

    for d in ACADEMIC_DOMAINS:
        if hostname == d or hostname.endswith(f".{d}"):
            return SourceType.ACADEMIC

    for d in NEWS_DOMAINS:
        if hostname == d or hostname.endswith(f".{d}"):
            return SourceType.NEWS

    for d in GITHUB_DOMAINS:
        if hostname == d or hostname.endswith(f".{d}"):
            return SourceType.GITHUB

    for d in BLOG_DOMAINS:
        if hostname == d or hostname.endswith(f".{d}"):
            return SourceType.BLOG

    for d in FORUM_DOMAINS:
        if hostname == d or hostname.endswith(f".{d}"):
            return SourceType.FORUM

    if "blog." in hostname or "/blog/" in parsed.path:
        return SourceType.BLOG

    return SourceType.UNKNOWN


def get_source_credibility(url: str) -> float:
    """Return numeric confidence [0.0 - 1.0] for a source URL."""
    source_type = classify_source_type(url)
    return CREDIBILITY_SCORES.get(source_type, 0.2)
