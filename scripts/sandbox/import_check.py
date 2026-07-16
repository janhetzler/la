"""
import_check.py — schnellster Sanity-Check ohne Stack-Start.

Testet nur ob alle zentralen Python-Module fehlerfrei importieren.
Kein llama-server, kein LiteLLM, kein Agent Server.
Läuft in ~2 Sekunden.

Verwendung:
  cd /home/claude/la && python3 scripts/sandbox/import_check.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../agents/server'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../agents/ingestion'))

MODULES = [
    ('config',          'Basis-Konfiguration'),
    ('supervisor',      'Supervisor + Routing (VALID_AGENTS, ROUTER_PROMPT)'),
    ('server',          'FastAPI Agent Server + alle Agent-Importe'),
    ('telemetry',       'Phoenix Tracing Init'),
    ('tool_formatter',  'Generischer Tool-Formatter (Granite/Qwen/Llama)'),
    ('tools',           'MCP Tool-Loader'),
    ('ingest',          'ChromaDB Ingestion Pipeline'),
    ('search',          'ChromaDB Suche'),
]

print("=== IMPORT CHECK ===\n", flush=True)
errors = []
for mod, desc in MODULES:
    try:
        __import__(mod)
        print(f"  ✓ {mod:20} {desc}", flush=True)
    except Exception as e:
        print(f"  ✗ {mod:20} FEHLER: {e}", flush=True)
        errors.append((mod, str(e)))

print(f"\n{'='*40}", flush=True)
if errors:
    print(f"FEHLER: {len(errors)}/{len(MODULES)} Module nicht importierbar", flush=True)
    for mod, err in errors:
        print(f"  ✗ {mod}: {err}", flush=True)
    sys.exit(1)
else:
    print(f"OK: alle {len(MODULES)} Module importierbar", flush=True)

# Bonus: VALID_AGENTS und registrierte Modelle zeigen
from supervisor import VALID_AGENTS
from server import AGENTS
print(f"\nVALID_AGENTS:     {sorted(VALID_AGENTS)}", flush=True)
print(f"AGENTS in server: {sorted(AGENTS.keys())}", flush=True)

# Warnung wenn Diskrepanz
routing = set(VALID_AGENTS)
registered = set(k.replace('agent-','') for k in AGENTS.keys() if k != 'agent-local')
only_registered = registered - routing - {'local'}
if only_registered:
    print(f"\n⚠️  In server.py registriert aber NICHT in VALID_AGENTS: {only_registered}", flush=True)
else:
    print(f"\n✓ Keine Diskrepanz zwischen VALID_AGENTS und server.py AGENTS", flush=True)
