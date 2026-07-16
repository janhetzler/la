# Chief-of-Staff — janhet Edition
# Selbstständiges Image mit beiden Granite Modellen
# Basis: python:3.12-slim-bookworm (kein nvidia, kein torch)

FROM python:3.12-slim-bookworm

# System Dependencies (chromadb benötigt Rust + build-essential)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    ca-certificates \
    build-essential \
    pkg-config \
    && curl --proto =https --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="/root/.cargo/bin:${PATH}"

# Arbeitsverzeichnis
WORKDIR /app

# Python Pakete installieren
# 1. llama-cpp-python Prebuilt Wheel (kein C++ Build nötig)
RUN pip install --no-cache-dir \
    "https://github.com/abetlen/llama-cpp-python/releases/download/v0.3.23/llama_cpp_python-0.3.23-py3-none-manylinux_2_17_x86_64.manylinux2014_x86_64.whl"

# 2. Alle anderen Pakete
COPY requirements-janhet.txt .
RUN pip install --no-cache-dir -r requirements-janhet.txt

# Code kopieren
COPY agents/ ./agents/
COPY mcp/ ./mcp/
COPY scripts/ ./scripts/
COPY tests/ ./tests/
COPY docker/ ./docker/

# Modelle herunterladen (direkt im Image)
# GitHub Token wird als Build-Arg übergeben
ARG GITHUB_TOKEN
RUN mkdir -p /app/models && \
    curl -L -o /app/models/granite-350m-Q4_K_M.gguf \
      -H "Authorization: Bearer ${GITHUB_TOKEN}" \
      "https://github.com/janhetzler/la/releases/download/granite-models/granite-4.0-h-350m-Q4_K_M.gguf" && \
    curl -L -o /app/models/granite-embedding-30m-Q4_0.gguf \
      -H "Authorization: Bearer ${GITHUB_TOKEN}" \
      "https://github.com/janhetzler/la/releases/download/granite-models/granite-embedding-30m-english-Q4_0.gguf" && \
    ls -lh /app/models/

# ChromaDB Datenverzeichnis
RUN mkdir -p /app/data/chroma

# Entrypoint
COPY docker/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Ports
EXPOSE 8080 8081 4000 6006 8002

# Umgebungsvariablen
ENV LITELLM_URL=http://127.0.0.1:4000
ENV LITELLM_KEY=sk-cos-local-dev
ENV DEFAULT_LLM=granite-tiny
ENV CHROMA_PATH=/app/data/chroma
ENV OPENAI_API_KEY=sk-cos-local-dev
ENV PHOENIX_COLLECTOR_ENDPOINT=http://127.0.0.1:6006/v1/traces

ENTRYPOINT ["/app/entrypoint.sh"]
