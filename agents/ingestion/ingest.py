"""
Document ingestion pipeline: file -> chunks -> embeddings -> Qdrant.

Supports multiple formats (PDF, DOCX, PPTX, MD, HTML, TXT) via Docling.
Each document is tagged with a category metadata for filtered search.
Uses HTTP client directly against the LiteLLM proxy (port 4000).
"""
import sys
from pathlib import Path
from typing import List, Optional

import httpx
from docling.document_converter import DocumentConverter
from llama_index.core import Document, VectorStoreIndex, StorageContext, Settings
from llama_index.core.embeddings import BaseEmbedding
from llama_index.core.node_parser import SentenceSplitter
from llama_index.vector_stores.qdrant import QdrantVectorStore
from qdrant_client import QdrantClient


# ===== Configuration =====
QDRANT_URL = "http://localhost:6333"
COLLECTION = "documents"
LITELLM_URL = "http://localhost:4000"
LITELLM_KEY = "sk-cos-local-dev"
EMBED_MODEL = "granite-embed"
EMBED_DIM = 384  # Granite Embedding 30M outputs 384 dimensions


# Supported file extensions
DOCLING_EXTENSIONS = {".pdf", ".docx", ".pptx", ".html", ".htm"}
TEXT_EXTENSIONS = {".md", ".txt", ".markdown"}
SUPPORTED_EXTENSIONS = DOCLING_EXTENSIONS | TEXT_EXTENSIONS

# Valid categories for the library
VALID_CATEGORIES = {"idn", "research", "personal", "admin", "inbox", "default"}


# ===== Custom embedder for our LiteLLM proxy =====
class CoSEmbedding(BaseEmbedding):
    """Embedder that talks to the LiteLLM proxy via HTTP."""

    def _embed(self, texts: List[str]) -> List[List[float]]:
        with httpx.Client(timeout=120) as client:
            r = client.post(
                f"{LITELLM_URL}/v1/embeddings",
                headers={"Authorization": f"Bearer {LITELLM_KEY}"},
                json={"model": EMBED_MODEL, "input": texts},
            )
            r.raise_for_status()
            data = r.json()
            return [item["embedding"] for item in data["data"]]

    def _get_query_embedding(self, query: str) -> List[float]:
        return self._embed([query])[0]

    def _get_text_embedding(self, text: str) -> List[float]:
        return self._embed([text])[0]

    def _get_text_embeddings(self, texts: List[str]) -> List[List[float]]:
        return self._embed(texts)

    async def _aget_query_embedding(self, query: str) -> List[float]:
        return self._get_query_embedding(query)

    async def _aget_text_embedding(self, text: str) -> List[float]:
        return self._get_text_embedding(text)


def setup_embedding():
    """Configure embedding via the LiteLLM proxy."""
    embed = CoSEmbedding()
    Settings.embed_model = embed
    Settings.chunk_size = 512
    Settings.chunk_overlap = 64
    return embed


def extract_text(filepath: Path) -> str:
    """
    Extract text from a document, dispatching to Docling or plain reading
    based on the file extension.
    """
    ext = filepath.suffix.lower()

    if ext in DOCLING_EXTENSIONS:
        print(f"📄 Converting {filepath.name} via Docling...")
        converter = DocumentConverter()
        result = converter.convert(str(filepath))
        return result.document.export_to_markdown()

    if ext in TEXT_EXTENSIONS:
        print(f"📄 Reading {filepath.name} as plain text...")
        return filepath.read_text(encoding="utf-8", errors="replace")

    raise ValueError(f"Unsupported file extension: {ext}")


def ingest_document(
    filepath: Path,
    category: str = "default",
    project: Optional[str] = None,
) -> int:
    """
    Full pipeline: file -> chunks -> embeddings -> Qdrant.

    Args:
        filepath: Path to the document to ingest.
        category: One of {idn, research, personal, admin, inbox, default}.
                  Used as a metadata field for filtered RAG search.
        project: Optional project tag (defaults to None).

    Returns:
        Number of chunks indexed.
    """
    if isinstance(filepath, str):
        filepath = Path(filepath)

    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    if filepath.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported extension {filepath.suffix}. "
            f"Supported: {sorted(SUPPORTED_EXTENSIONS)}"
        )

    if category not in VALID_CATEGORIES:
        print(f"⚠️  Unknown category '{category}', falling back to 'default'")
        category = "default"

    setup_embedding()

    # 1. Extract text
    text = extract_text(filepath)
    print(f"   → {len(text)} characters extracted")

    # 2. Build LlamaIndex Document with category metadata
    metadata = {
        "source": filepath.name,
        "category": category,
        "type": filepath.suffix.lower().lstrip("."),
    }
    if project:
        metadata["project"] = project

    doc = Document(text=text, metadata=metadata)

    # 3. Semantic chunking
    splitter = SentenceSplitter(chunk_size=512, chunk_overlap=64)
    nodes = splitter.get_nodes_from_documents([doc])
    print(f"   → {len(nodes)} chunks generated")

    # 4. Connect to Qdrant
    client = QdrantClient(url=QDRANT_URL)
    vector_store = QdrantVectorStore(
        client=client,
        collection_name=COLLECTION,
    )
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    # 5. Index
    print(f"💾 Indexing into Qdrant (category='{category}')...")
    VectorStoreIndex(nodes, storage_context=storage_context)
    print(f"✅ Document indexed in collection '{COLLECTION}'")

    return len(nodes)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python ingest.py <filepath> [category] [project]")
        print(f"Categories: {sorted(VALID_CATEGORIES)}")
        sys.exit(1)

    filepath = Path(sys.argv[1])
    category = sys.argv[2] if len(sys.argv) > 2 else "default"
    project = sys.argv[3] if len(sys.argv) > 3 else None

    chunks = ingest_document(filepath, category=category, project=project)
    print(f"\n🎉 {chunks} chunks indexed from {filepath.name} (category: {category})")