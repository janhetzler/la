# OKF Frontmatter Schema

Every documentation file starts with a YAML frontmatter block.

## Required Fields

```yaml
---
type: Runbook
status: current
updated_at: 2026-08-07
---
```

## Full Schema

```yaml
---
type: Runbook
status: current
updated_at: 2026-08-07
stale_after: 2027-02-07
environment: host
topic: llama-server-start
tags: [llama, debian, host]
---
```

## Field Reference

| Field | Required | Language | Allowed Values |
|-------|----------|----------|----------------|
| `type` | yes | EN | see types below |
| `status` | yes | EN | `current` · `draft` · `stale` · `deprecated` |
| `updated_at` | yes | EN | ISO date `YYYY-MM-DD` |
| `stale_after` | no | EN | ISO date — omit for Log, Tracker, Overview, Index |
| `environment` | no | EN | `host` · `webserver` · `container` · `sandbox` · `docker` · `all` |
| `topic` | no | EN | kebab-case short label |
| `tags` | no | EN | plain words, no prefixes — e.g. `[llama, nginx, python]` |

## Document Types

| `type` | DITA equivalent | Purpose |
|--------|----------------|---------|
| `Runbook` | Task | Step-by-step instructions |
| `Decision` | Concept | Architecture decision record |
| `Reference` | Concept | Explanation, architecture, best practices |
| `Observation` | Reference | Test results, traces, measurements |
| `Tracker` | Reference | Ongoing collection — bugs, issues |
| `Overview` | — | Project entry point |
| `Log` | — | Chronological admin log |
| `Index` | — | Folder navigation entry point |

## stale_after by Type

| Type | stale_after |
|------|-------------|
| Runbook | 6 months |
| Decision | 3 months |
| Reference | 12 months |
| Observation, Tracker, Log, Overview, Index | omit |

## Tags — Rules

- Plain words, no prefixes: `llama` not `tech-llama`
- Derived from actual content — not invented
- Technology names: `debian`, `llama`, `nginx`, `cloudflare`, `python`,
  `chromadb`, `incus`, `sqlite`, `langchain`, `fastapi`
- Infrastructure: `host`, `container`, `webserver`, `network`, `tunnel`
- Domain: `security`, `benchmark`, `backup`, `email`, `monitoring`
