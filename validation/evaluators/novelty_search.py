"""
validation/evaluators/novelty_search.py
========================================
NoveltySearcher — queries external sources to determine whether an
opportunity already exists in the market.

Search providers (attempted in order):
  1. Google Custom Search API  (requires GOOGLE_API_KEY + GOOGLE_CX env vars)
  2. YC company search         (public, no key)
  3. DuckDuckGo Instant Answer (public, no key)

Results are cached in the `novelty_cache` table of data/validation.db so
that re-running the suite on the same batch never repeats external calls.
"""

from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import quote_plus

import requests

from validation.models import NoveltyResult

logger = logging.getLogger(__name__)

# Root of the project: three levels up from this file
ROOT = Path(__file__).resolve().parent.parent.parent

_DEFAULT_DB_PATH = ROOT / "data" / "validation.db"

_REQUEST_TIMEOUT = 10  # seconds


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _extract_keywords(text: str, max_words: int = 4) -> list[str]:
    """
    Pull the most meaningful words from a text field.

    Strips common stop-words, punctuation, and very short tokens so the
    resulting keywords are suitable for a search query rather than raw
    verbatim text.
    """
    _STOP = {
        "a", "an", "the", "and", "or", "but", "in", "on", "at", "to",
        "for", "of", "with", "by", "from", "as", "is", "are", "was",
        "be", "been", "being", "have", "has", "had", "do", "does", "did",
        "will", "would", "could", "should", "may", "might", "that", "this",
        "it", "its", "we", "our", "their", "using", "use", "via", "into",
        "through", "which", "how", "what", "when", "where", "while",
        "based", "new", "can", "also", "than", "more", "better", "system",
        "approach", "model", "method", "solution", "platform", "tool",
    }
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9\-]*", text)
    seen: list[str] = []
    for tok in tokens:
        lower = tok.lower()
        if lower not in _STOP and len(tok) > 2 and tok not in seen:
            seen.append(tok)
        if len(seen) >= max_words:
            break
    return seen


def _build_query(opportunity: dict) -> str:
    """
    Construct a short search query (≤ 100 chars) from high-level keywords
    extracted from technology, problem, and market fields.

    Never embeds raw long text verbatim.
    """
    tech_kw = _extract_keywords(opportunity.get("technology", ""), max_words=3)
    prob_kw = _extract_keywords(opportunity.get("problem", ""), max_words=2)
    mkt_kw = _extract_keywords(opportunity.get("market", ""), max_words=2)

    parts = tech_kw + prob_kw + mkt_kw
    # Deduplicate while preserving order
    seen: list[str] = []
    for p in parts:
        if p not in seen:
            seen.append(p)

    query = " ".join(seen)
    # Hard cap at 100 characters
    if len(query) > 100:
        query = query[:100].rsplit(" ", 1)[0]
    return query


def _is_exact_match(query_keywords: list[str], result_title: str) -> bool:
    """
    Heuristic: consider a result a 'near-exact match' when at least half of
    the meaningful query keywords appear in the result title/snippet.
    """
    if not query_keywords:
        return False
    title_lower = result_title.lower()
    matched = sum(1 for kw in query_keywords if kw.lower() in title_lower)
    return matched >= max(1, len(query_keywords) // 2)


# ---------------------------------------------------------------------------
# Search provider implementations
# ---------------------------------------------------------------------------

def _search_google(query: str) -> list[str]:
    """
    Query Google Custom Search API.
    Returns a list of result titles/snippets, or raises on failure.
    Requires GOOGLE_API_KEY and GOOGLE_CX environment variables.
    """
    api_key = os.environ.get("GOOGLE_API_KEY", "")
    cx = os.environ.get("GOOGLE_CX", "")
    if not api_key or not cx:
        raise EnvironmentError("GOOGLE_API_KEY or GOOGLE_CX not set")

    url = (
        f"https://www.googleapis.com/customsearch/v1"
        f"?key={api_key}&cx={cx}&q={quote_plus(query)}"
    )
    resp = requests.get(url, timeout=_REQUEST_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()

    titles: list[str] = []
    for item in data.get("items", []):
        title = item.get("title", "")
        snippet = item.get("snippet", "")
        if title:
            titles.append(title)
        if snippet:
            titles.append(snippet)
    return titles


def _search_yc(query: str) -> list[str]:
    """
    Query YC's public company search page.
    Returns a list of company name strings found in the response HTML.
    """
    url = f"https://www.ycombinator.com/companies?query={quote_plus(query)}"
    resp = requests.get(url, timeout=_REQUEST_TIMEOUT, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    # YC is a React SPA; look for company names in JSON embedded in the page
    # The page may not hydrate fully, but we can still parse any inline JSON
    companies: list[str] = re.findall(r'"name"\s*:\s*"([^"]{2,80})"', resp.text)
    return companies[:20]  # cap to avoid noise


def _search_duckduckgo(query: str) -> list[str]:
    """
    Query DuckDuckGo Instant Answer API (no API key required).
    Returns a list of result title strings.
    """
    url = (
        f"https://api.duckduckgo.com/"
        f"?q={quote_plus(query)}&format=json&no_html=1"
    )
    resp = requests.get(url, timeout=_REQUEST_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()

    titles: list[str] = []
    # Top result
    if data.get("Heading"):
        titles.append(data["Heading"])
    # Related topics
    for topic in data.get("RelatedTopics", []):
        text = topic.get("Text", "") or topic.get("Name", "")
        if text:
            titles.append(text)
    return titles


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class NoveltySearcher:
    """
    Determines whether an opportunity already exists in the market by
    querying external search providers.

    Usage::

        searcher = NoveltySearcher()
        result = searcher.search(opportunity)
        results = searcher.batch_search(opportunities)
    """

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self._db_path = Path(db_path) if db_path else _DEFAULT_DB_PATH

    # ------------------------------------------------------------------
    # Cache helpers
    # ------------------------------------------------------------------

    def _get_cached(self, opportunity_id: str) -> Optional[NoveltyResult]:
        """Return a cached NoveltyResult if one exists, otherwise None."""
        try:
            con = sqlite3.connect(str(self._db_path))
            con.row_factory = sqlite3.Row
            with con:
                row = con.execute(
                    "SELECT * FROM novelty_cache WHERE opportunity_id = ?",
                    (opportunity_id,),
                ).fetchone()
            con.close()
            if row is None:
                return None
            return NoveltyResult(
                opportunity_id=row["opportunity_id"],
                verdict=row["verdict"],
                matching_products=json.loads(row["matching_products_json"] or "[]"),
                search_queries=json.loads(row["search_queries_json"] or "[]"),
                confidence=row["confidence"] or 0.0,
            )
        except Exception as exc:
            logger.warning("Cache read failed for %s: %s", opportunity_id, exc)
            return None

    def _save_cache(self, result: NoveltyResult) -> None:
        """Persist a NoveltyResult to the novelty_cache table."""
        try:
            con = sqlite3.connect(str(self._db_path))
            with con:
                con.execute(
                    """
                    INSERT OR REPLACE INTO novelty_cache
                        (opportunity_id, verdict, matching_products_json,
                         search_queries_json, confidence, cached_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        result.opportunity_id,
                        result.verdict,
                        json.dumps(result.matching_products),
                        json.dumps(result.search_queries),
                        result.confidence,
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )
            con.close()
        except Exception as exc:
            logger.warning("Cache write failed for %s: %s", result.opportunity_id, exc)

    # ------------------------------------------------------------------
    # Core search logic
    # ------------------------------------------------------------------

    def _run_providers(self, query: str) -> tuple[str, list[str]]:
        """
        Try each provider in order; return (status, results) where status is
        one of 'found', 'not_found', or 'uncertain'.

        'found'     — at least one provider returned results with a near-exact
                      keyword match
        'not_found' — at least one provider returned successfully but no match
        'uncertain' — all providers timed out or failed
        """
        keywords = _extract_keywords(query, max_words=6)
        any_succeeded = False
        matching_products: list[str] = []

        providers = [
            ("google", _search_google),
            ("yc", _search_yc),
            ("duckduckgo", _search_duckduckgo),
        ]

        for provider_name, provider_fn in providers:
            try:
                titles = provider_fn(query)
                any_succeeded = True
                for title in titles:
                    if _is_exact_match(keywords, title):
                        matching_products.append(f"[{provider_name}] {title[:120]}")
                # Once we have a confirmed match we can stop early
                if matching_products:
                    return "found", matching_products
            except requests.exceptions.Timeout:
                logger.info("Provider %s timed out for query: %s", provider_name, query)
                # timeout → continue to next provider
            except EnvironmentError:
                # Google credentials not set — skip silently
                pass
            except Exception as exc:
                logger.info("Provider %s failed: %s", provider_name, exc)
                # Any other network/HTTP error → try next provider

        if not any_succeeded:
            return "uncertain", []
        return "not_found", []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def search(self, opportunity: dict) -> NoveltyResult:
        """
        Search external sources to classify one opportunity.

        Returns a NoveltyResult with verdict:
          - 'novel'     — no matching product found
          - 'exists'    — at least one source returned a near-exact match
          - 'uncertain' — all requests timed out
        """
        opp_id = str(opportunity.get("id", opportunity.get("opportunity_id", "")))

        # Check cache first
        cached = self._get_cached(opp_id) if opp_id else None
        if cached is not None:
            logger.debug("Cache hit for opportunity %s", opp_id)
            return cached

        query = _build_query(opportunity)
        queries_used = [query]

        logger.debug("Searching for opportunity %s | query: %s", opp_id, query)

        status, matching_products = self._run_providers(query)

        if status == "found":
            verdict: str = "exists"
            confidence = 0.9
        elif status == "not_found":
            verdict = "novel"
            confidence = 0.7
        else:  # uncertain
            verdict = "uncertain"
            confidence = 0.0

        result = NoveltyResult(
            opportunity_id=opp_id,
            verdict=verdict,  # type: ignore[arg-type]
            matching_products=matching_products,
            search_queries=queries_used,
            confidence=confidence,
        )

        if opp_id:
            self._save_cache(result)

        return result

    def batch_search(
        self, opportunities: list[dict]
    ) -> tuple[list[NoveltyResult], list[str]]:
        """
        Search all opportunities in the batch.

        Returns a tuple of:
          - list[NoveltyResult]   — one result per opportunity (same order)
          - list[str]             — any warnings generated

        A warning is added when the uncertain rate exceeds 20 %.
        """
        results: list[NoveltyResult] = []
        uncertain_count = 0
        total = len(opportunities)

        for opp in opportunities:
            result = self.search(opp)
            results.append(result)
            if result.verdict == "uncertain":
                uncertain_count += 1

        warnings: list[str] = []
        if total > 0 and (uncertain_count / total) > 0.2:
            warnings.append(
                f"High uncertainty rate: {uncertain_count}/{total} opportunities "
                f"({uncertain_count / total:.0%}) could not be classified due to "
                "search timeouts. Consider re-running T4 with a stable network "
                "connection or configured API keys."
            )

        return results, warnings
