# MCP Server — Installation und Konfiguration

Local Agent nutzt MCP (Model Context Protocol) Server um den Agenten
Zugriff auf externe Tools zu geben: Git Repository, Web-Fetch, und mehr.

---

## Installation

```bash
source venv/bin/activate  # aktives Python-Environment
pip install mcp-server-git mcp-server-fetch
```

---

## Verfügbare Server

### 1. mcp-server-git (Python)

**12 Tools:** git_log, git_status, git_diff, git_diff_staged, git_diff_unstaged,
git_commit, git_add, git_reset, git_create_branch, git_checkout, git_show, git_branch

```bash
# Testen
python3 -m mcp_server_git --repository .
```

**Konfiguration in mcp/mcp.json:**
```json
{
  "mcpServers": {
    "git": {
      "command": "python3",
      "args": ["-m", "mcp_server_git", "--repository", "."],
      "transport": "stdio"
    }
  }
}
```

### 2. mcp-server-fetch (Python)

**1 Tool:** fetch — Web-Inhalte abrufen und für LLM aufbereiten

```bash
# Testen
python3 -m mcp_server_fetch
```

---

## Integration in den Agent Stack

Der Researcher-Agent lädt automatisch alle MCP Tools beim Start über `tools.py`.
Der Pfad zum Repository wird aus dem Arbeitsverzeichnis (`"."`) abgeleitet.

**Wichtig:** Die MCP Server müssen im selben Python-Environment sein wie der Agent Server:
```bash
source venv/bin/activate  # aktives Python-Environment
pip install mcp-server-git mcp-server-fetch
cd agents/server  # relativ zum Repository-Root
uvicorn server:app --host 127.0.0.1 --port 8002
```

---

## Testergebnisse (2026-07-14)

| Tool | Status | Detail |
|------|--------|--------|
| git_log | ✓ | Commit History korrekt gelesen |
| git_status | ✓ | Branch Status korrekt |
| git_diff | ✓ | Änderungen anzeigbar |
| git_branch | ✓ | Branch-Liste korrekt |
| git_show | ✓ | Commit-Inhalte lesbar |
| fetch | ✓* | *Benötigt Netzwerkzugang — auf Host verifiziert werden, sobald real getestet |

**MCP durch Agent System:** Supervisor routet Git-Anfragen zum Researcher-Agent,
der MCP Tools lädt und aufruft. Verifiziert am 2026-07-14.

---

## Weitere MCP Server (optional)

Von https://github.com/modelcontextprotocol/servers:

```bash
# Sequential Thinking (Python)
pip install mcp-server-sequential-thinking

# Memory / Knowledge Graph (Node.js)
npx -y @modelcontextprotocol/server-memory

# Filesystem (Node.js)
npx -y @modelcontextprotocol/server-filesystem .
```

In mcp/mcp.json eintragen und Agent Server neu starten.
