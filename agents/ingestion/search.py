"""
RAG Search — ChromaDB Edition (janhet)
Ersetzt Qdrant durch lokale ChromaDB Instanz.
"""
import sys
import os
from pathlib import Path
from typing import Optional

import chromadb
from llama_index.embeddings.litellm import LiteLLMEmbedding

# Pfad zu config
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "server"))
import config

VALID_CATEGORIES = ["personal", "work", "research", "notes", "history"]

EMBED_MODEL = LiteLLMEmbedding(
    model_name=f"openai/{config.EMBED_MODEL}",
    api_base=f"{config.LITELLM_URL}/v1",
    api_key=config.LITELLM_KEY,
)

def get_chroma_collection(collection_name: str = config.CHROMA_COLLECTION):
    client = chromadb.PersistentClient(path=config.CHROMA_PATH)
    return client.get_or_create_collection(name=collection_name)

def search(
    query: str,
    category: Optional[str] = None,
    top_k: int = 5,
    collection_name: str = config.CHROMA_COLLECTION,
) -> list[dict]:
    """
    Semantische Suche in ChromaDB.
    Gibt Liste von {text, score, metadata} zurück.
    """
    collection = get_chroma_collection(collection_name)
    vector = EMBED_MODEL.get_text_embedding(query)
    
    where = {"category": category} if category and category in VALID_CATEGORIES else None
    
    results = collection.query(
        query_embeddings=[vector],
        n_results=top_k,
        where=where,
        include=["documents", "distances", "metadatas"],
    )
    
    output = []
    if results and results["documents"]:
        for doc, dist, meta in zip(
            results["documents"][0],
            results["distances"][0],
            results["metadatas"][0],
        ):
            output.append({
                "text": doc,
                "score": 1 - dist,  # Cosine similarity
                "metadata": meta,
            })
    return output
