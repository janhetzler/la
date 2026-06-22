"""
Semantic search in Qdrant.

Usage:
  python search.py "your question" [top_k] [category]

Examples:
  python search.py "what is attention mechanism?"
  python search.py "neuroscience papers" 10 idn
  python search.py "fiscal contract details" 5 admin
"""
import json
import sys
from typing import List, Optional

import httpx
from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue


# ===== Configuration =====
QDRANT_URL = "http://localhost:6333"
COLLECTION = "documents"
LITELLM_URL = "http://localhost:4000"
LITELLM_KEY = "sk-cos-local-dev"
EMBED_MODEL = "granite-embed"

VALID_CATEGORIES = {"idn", "research", "personal", "admin", "inbox", "default"}


def embed_query(query: str) -> List[float]:
    """Embed a query via the LiteLLM proxy."""
    with httpx.Client(timeout=60) as client:
        r = client.post(
            f"{LITELLM_URL}/v1/embeddings",
            headers={"Authorization": f"Bearer {LITELLM_KEY}"},
            json={"model": EMBED_MODEL, "input": query},
        )
        r.raise_for_status()
        return r.json()["data"][0]["embedding"]


def build_filter(
    category: Optional[str] = None,
    project: Optional[str] = None,
) -> Optional[Filter]:
    """Build a Qdrant filter from optional metadata constraints."""
    conditions = []

    if category:
        conditions.append(
            FieldCondition(key="category", match=MatchValue(value=category))
        )

    if project:
        conditions.append(
            FieldCondition(key="project", match=MatchValue(value=project))
        )

    if not conditions:
        return None

    return Filter(must=conditions)


def extract_text(payload: dict) -> str:
    """
    Extract the actual text from a Qdrant payload.
    LlamaIndex stores it either in 'text' or inside '_node_content' (JSON).
    """
    text = payload.get("text", "")
    if text:
        return text

    node_content = payload.get("_node_content")
    if node_content:
        try:
            node = json.loads(node_content)
            return node.get("text", "")
        except Exception:
            return str(node_content)[:400]

    return ""


def search(
    query: str,
    top_k: int = 5,
    category: Optional[str] = None,
    project: Optional[str] = None,
) -> List[dict]:
    """
    Search the top_k most relevant chunks.

    Args:
        query: Natural-language query.
        top_k: Number of chunks to return.
        category: Optional filter — one of {idn, research, personal, admin, inbox}.
        project: Optional project tag filter.

    Returns:
        List of dicts with keys: score, source, category, project, text.
    """
    if category and category not in VALID_CATEGORIES:
        print(f"⚠️  Unknown category '{category}', searching across all categories.")
        category = None

    # Console output
    print(f"🔍 Query: {query}")
    if category:
        print(f"   Category filter: {category}")
    if project:
        print(f"   Project filter: {project}")

    # 1. Embed the query
    query_vec = embed_query(query)

    # 2. Search Qdrant with optional filter
    client = QdrantClient(url=QDRANT_URL)
    query_filter = build_filter(category=category, project=project)

    points = client.query_points(
        collection_name=COLLECTION,
        query=query_vec,
        limit=top_k,
        query_filter=query_filter,
        with_payload=True,
    ).points

    # 3. Build structured results
    results = []
    for p in points:
        payload = p.payload or {}
        results.append({
            "score": p.score,
            "source": payload.get("source", "?"),
            "category": payload.get("category", "?"),
            "project": payload.get("project", "?"),
            "text": extract_text(payload),
        })

    return results


def print_results(results: List[dict]):
    """Pretty-print search results to the console."""
    print(f"\n📚 Top {len(results)} results:\n")
    for i, r in enumerate(results, 1):
        snippet = r["text"][:400].replace("\n", " ")
        print(
            f"━━━ [{i}] score={r['score']:.3f} | "
            f"{r['source']} | category={r['category']} | project={r['project']} ━━━"
        )
        print(f"{snippet}...\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Usage: python search.py "your question" [top_k] [category]')
        print(f"Categories: {sorted(VALID_CATEGORIES)}")
        sys.exit(1)

    query = sys.argv[1]
    top_k = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    category = sys.argv[3] if len(sys.argv) > 3 else None

    results = search(query, top_k=top_k, category=category)
    print_results(results)