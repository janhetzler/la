"""
RAG Ingestion — ChromaDB Edition (janhet)
Ersetzt Qdrant/QdrantVectorStore durch lokale ChromaDB.
"""
import sys
import os
import hashlib
from pathlib import Path
from uuid import uuid4
from typing import Optional

import chromadb
from llama_index.embeddings.litellm import LiteLLMEmbedding

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "server"))
import config

EMBED_MODEL = LiteLLMEmbedding(
    model_name=f"openai/{config.EMBED_MODEL}",
    api_base=f"{config.LITELLM_URL}/v1",
    api_key=config.LITELLM_KEY,
)

def get_chroma_collection(collection_name: str = config.CHROMA_COLLECTION):
    client = chromadb.PersistentClient(path=config.CHROMA_PATH)
    return client.get_or_create_collection(name=collection_name)

async def ingest_text(
    text: str,
    metadata: Optional[dict] = None,
    collection_name: str = config.CHROMA_COLLECTION,
) -> str:
    """
    Vektorisiert einen Text und speichert ihn in ChromaDB.
    Gibt die generierte ID zurück.
    """
    collection = get_chroma_collection(collection_name)
    vector = EMBED_MODEL.get_text_embedding(text)
    
    doc_id = f"doc_{uuid4().hex[:12]}"
    meta = metadata or {}
    meta["length"] = len(text)
    
    collection.add(
        ids=[doc_id],
        embeddings=[vector],
        documents=[text],
        metadatas=[meta],
    )
    return doc_id

async def ingest_file(
    file_path: str,
    category: str = "notes",
    collection_name: str = config.CHROMA_COLLECTION,
) -> dict:
    """
    Liest eine Datei, chunked sie und speichert alle Chunks in ChromaDB.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Datei nicht gefunden: {file_path}")
    
    text = path.read_text(encoding="utf-8")
    
    # Einfaches Chunking: 1000 Zeichen mit 100 Overlap
    chunk_size = 1000
    overlap = 100
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        start += chunk_size - overlap
    
    ids = []
    for i, chunk in enumerate(chunks):
        doc_id = await ingest_text(
            chunk,
            metadata={
                "source": str(path),
                "filename": path.name,
                "category": category,
                "chunk": i,
                "total_chunks": len(chunks),
            },
            collection_name=collection_name,
        )
        ids.append(doc_id)
    
    return {"file": str(path), "chunks": len(chunks), "ids": ids}

async def save_chat_history(
    session_id: str,
    chat_text: str,
    collection_name: str = "history",
) -> str:
    """
    Speichert Chat-Verlauf in ChromaDB für spätere RAG-Abfragen.
    """
    return await ingest_text(
        chat_text,
        metadata={
            "session_id": session_id,
            "type": "chat_archive",
        },
        collection_name=collection_name,
    )
