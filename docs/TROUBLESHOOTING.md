# Troubleshooting

## Common issues

### "docker: command not found"

Docker isn't installed or isn't in your PATH.

- **macOS**: `brew install --cask orbstack` (recommended) or `--cask docker-desktop`, then launch the app
- **Linux**: `curl -fsSL https://get.docker.com | sh && sudo usermod -aG docker $USER` (log out and back in)
- **Windows**: Install Docker Desktop with WSL2 backend

### "Cannot connect to the Docker daemon"

Docker is installed but the daemon isn't running.

- **macOS / Windows**: launch Docker Desktop (or OrbStack); wait until it's stable
- **Linux**: `sudo systemctl start docker`

### Ollama doesn't respond (port 11434)

```bash
# Start Ollama
ollama serve &

# Verify
curl http://localhost:11434
```

If port 11434 is taken by something else, kill it: `lsof -ti:11434 | xargs kill -9`.

### Model pull stuck or slow

The Granite tiny-h model is ~4 GB. On a 10 Mbps connection that's ~1 hour. Be patient. If it's stuck (no progress for >5 min):

```bash
# Kill the pull
pkill -f "ollama pull"

# Retry
ollama pull ibm/granite4:tiny-h
```

### Open WebUI can't reach LiteLLM

Check that all containers are running:

```bash
cd docker
docker compose ps
```

If `cos-litellm` is restarting, check its logs:

```bash
docker compose logs litellm
```

Common cause: Postgres not ready yet. Wait 30 seconds and retry.

### Agents API not responding (port 8002)

Check the log:

```bash
tail -f logs/agents.log
```

Common causes:
- Python venv not activated (start.sh handles this automatically; if running manually, `source .venv/bin/activate`)
- A required Python package is missing — re-run `pip install -r requirements.txt`
- Granite model not pulled — `ollama list` to confirm

### "host.docker.internal does not resolve" (Linux)

By default, Linux Docker containers can't reach the host via `host.docker.internal`. The `docker-compose.yml` includes:

```yaml
extra_hosts:
  - "host.docker.internal:host-gateway"
```

If this still fails, add `--network host` to the container or use the host's actual IP.

### Meeting recording produces fabricated content

If a recording with silence produces a hallucinated meeting summary, the anti-hallucination guard in `process.py` is not catching the noise. Check that `is_transcript_meaningful()` is in place:

```bash
grep is_transcript_meaningful agents/notes/process.py
```

If missing, pull the latest from the repo.

### Recording captures only microphone (Teams/Zoom audio missing)

On macOS, you need to route the system audio through BlackHole 2ch:

1. Install BlackHole: `brew install blackhole-2ch`
2. Open Audio MIDI Setup (built-in macOS app)
3. Create a "Multi-Output Device" combining your speakers + BlackHole 2ch
4. Before the meeting, set this Multi-Output as your **System Output** in Sound preferences

Verify with `sd.query_devices()` in Python — BlackHole 2ch should appear as an input device.

### Open WebUI shows "Phantom router responses" in logs

These are auto-generated follow-up requests from Open WebUI. The supervisor filters them already. To stop them at the source:

Settings → Interface → Follow Up Generation → **Off**

### Granite calls `read_text_file` on a directory (EISDIR error)

Known bug, documented in [BUGS.md](../BUGS.md). The workaround is in the system prompt of the Researcher. A proper fix requires LangChain `middleware` (good first contribution).

### Out of memory during inference

Granite tiny-h needs ~5 GB free RAM. If you have only 12 GB:

```bash
# Close memory-heavy apps (Chrome, Slack)
# Or switch to the smaller model:
# Edit agents/server/*.py and change "ibm/granite4:tiny-h" to "ibm/granite4:micro-h"
```

Performance drops noticeably but it stays usable.

### Library watcher not ingesting files

Check the watcher log:

```bash
tail -f logs/watcher.log
```

Common causes:
- File extension not supported (must be `.pdf`, `.docx`, `.pptx`, `.html`, `.md`, `.txt`)
- File still being written (the watcher waits 2 sec for file size to stabilize)
- Docling can't parse the file → check `data/library/_errors/<category>/`

### "Tavily API key invalid"

Your key probably has the `tvly-` prefix duplicated. Common copy-paste error.

```bash
# Check
grep TAVILY_API_KEY .env
```

If it shows `tvly-tvly-...`, fix it manually. The key from https://tavily.com should be `tvly-XXXXX` (one prefix).

### Stack doesn't fully shut down with `./stop.sh`

If processes linger:

```bash
# Kill all uvicorn instances
pkill -f uvicorn

# Kill MCP server zombies
pkill -f "node.*tavily-mcp"
pkill -f "node.*server-github"
pkill -f "node.*server-filesystem"

# Force-stop Docker stack
cd docker && docker compose down --volumes
```

## Getting more help

- Open an issue on GitHub with: OS, RAM, error message, relevant log excerpt
- Check [BUGS.md](../BUGS.md) for known issues
- The Medium article has a deeper walkthrough of the architecture
