# Local Agent — portable Docker Edition
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

# Python Pakete installieren — einzeln fuer besseres Debugging
# 1. llama-cpp-python Prebuilt Wheel
RUN pip install --no-cache-dir \
    "https://github.com/abetlen/llama-cpp-python/releases/download/v0.3.23/llama_cpp_python-0.3.23-py3-none-manylinux_2_17_x86_64.manylinux2014_x86_64.whl"

# 2. Web Framework
RUN pip install --no-cache-dir fastapi==0.139.0 uvicorn==0.51.0 httpx==0.28.1 python-dotenv==1.2.2

# 3. LangChain
RUN pip install --no-cache-dir langchain==1.2.15 langchain-core==1.3.2 langchain-openai==1.2.1 langchain-mcp-adapters==0.2.2 langgraph==1.1.10

# 4. ChromaDB (braucht Rust)
RUN pip install --no-cache-dir chromadb==1.5.9

# 5. LlamaIndex
RUN pip install --no-cache-dir llama-index-core==0.14.23 llama-index-embeddings-litellm==0.5.0 llama-index-instrumentation==0.5.0 llama-index-workflows==2.22.2

# 6. LiteLLM
RUN pip install --no-cache-dir "litellm[proxy]==1.92.0"

# 7. Observability
RUN pip install --no-cache-dir arize-phoenix==18.0.0 openinference-instrumentation-langchain==0.1.67 opentelemetry-sdk==1.43.0 opentelemetry-exporter-otlp==1.43.0

# 8. MCP + Rest
RUN pip install --no-cache-dir mcp-server-git==2026.7.10 mcp-server-fetch==2026.7.10 "openai>=2.26.0" pydantic==2.12.5 numpy==2.4.4 tqdm==4.67.3 starlette-context==0.5.1

# Code kopieren
COPY agents/ ./agents/
COPY mcp/ ./mcp/
COPY scripts/ ./scripts/
COPY tests/ ./tests/
COPY docker/ ./docker/

# Bekannter Fix: mcp.json liegt nach Ordner-Umstrukturierung unter mcp/docker/
# statt mcp/mcp.json (siehe BUGS.md). Fest im Image korrigiert, kein Laufzeit-Workaround.
RUN mkdir -p mcp/docker && cp mcp/sandbox/mcp.json mcp/docker/mcp.json && \
    sed -i 's|PROJECT_ROOT / "mcp" / "mcp.json"|PROJECT_ROOT / "mcp" / "docker" / "mcp.json"|' \
      agents/server/tools.py

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
