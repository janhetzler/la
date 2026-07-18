# Project Context

## Local Agent (LA)
- Repository: github.com/janhetzler/la
- Stack: llama-server, LiteLLM, ChromaDB, Arize Phoenix
- Environment: Sandbox (Claude.ai) and Host (AMD EPYC, Debian 12)
- Current Phase: [z.B. Agent refactoring, Host deployment preparation]

## Active Tasks
- [Aufgabe 1]
- [Aufgabe 2]

## Architecture Decisions
- LLM: Granite-4.0-H-Tiny on Host, Granite-350m in Sandbox
- Gateway: LiteLLM on Port 4000
- Observability: Arize Phoenix on Port 6006
- Vector DB: ChromaDB embedded
- Agent Prompts: prompts/agents/*.md with YAML-Frontmatter
- Shared Context: prompts/shared/*.md injected via agent_loader

## Agents
- comms: emails, messages, announcements
- code: programming, debugging, GitHub issues
- notes: personal notes in ChromaDB
- researcher: information lookup, RAG search
- handoff: enriched prompts for Claude.ai or ChatGPT
