# AGENT_SANDBOX.md -- Anleitung fuer Claude Agenten in der Sandbox-Umgebung

Dieses Dokument ist fuer Claude Agenten geschrieben die in der Claude Sandbox (bash_tool)
arbeiten. Lies es zuerst bevor du irgendwas baust.

---

## 1. Prozess-Lebensdauer

**Prozesse laufen WEITER wenn ein bash_tool Call endet.**

Das ist der wichtigste Punkt. Viele Agenten denken faelschlicherweise dass Prozesse
sterben wenn der Call endet. Das stimmt NICHT.

Was WEITERLAEUFT nach Call-Ende:
- Hintergrundprozesse (llama-server, uvicorn, bifrost, etc.)
- Dateien in /tmp/ und /home/
- Installierte Pakete (pip install, npm install)

Was NICHT persistiert:
- Shell-Variablen (export PATH=... gilt nur im aktuellen Call)
- Aktuelles Verzeichnis (cd /tmp gilt nur im aktuellen Call)
- Python-Objekte im Speicher

---

## 2. Netzwerk-Allowlist

Erlaubt:
- github.com, raw.githubusercontent.com, release-assets.githubusercontent.com
- pypi.org, files.pythonhosted.org
- registry.npmjs.org, npmjs.com
- codeload.github.com

Blockiert:
- go.dev (Go Downloads)
- Bifrost Binary Download von maximhq-Servern (403)
- Docker Hub Registry API (teilweise)

Lokales Netzwerk funktioniert:
- 127.0.0.1 und localhost sind erreichbar
- Ports innerhalb der Sandbox funktionieren

---

## 3. Die 10-Sekunden-Regel

Jede Aktion muss innerhalb von 10 Sekunden eine Rueckmeldung geben.
Baue immer Fortschrittsmeldungen mit Timestamp ein:

    echo "$(date +%H:%M:%S) Starte Service..."
    for i in 1 2 3 4 5 6 7 8 9 10; do
      sleep 3
      STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8081/health)
      echo "$(date +%H:%M:%S) Versuch $i: HTTP $STATUS"
      [ "$STATUS" = "200" ] && echo "OK!" && break
    done

---

## 4. Alles in einem Call starten

Wenn mehrere Services miteinander kommunizieren muessen, starte sie alle
in einem einzigen bash_tool Call. Nutze das Python wait_for() Pattern:

    import subprocess, time, urllib.request

    def wait_for(url, timeout=120, interval=3):
        start = time.time()
        while time.time() - start < timeout:
            try:
                urllib.request.urlopen(url, timeout=2)
                return True
            except:
                time.sleep(interval)
                print(f"Warte auf {url}...", flush=True)
        return False

    proc = subprocess.Popen(["/opt/llama/llama-server", "--model", "..."],
        stdout=open("/tmp/llama.log","w"), stderr=subprocess.STDOUT)

    if wait_for("http://127.0.0.1:8081/health"):
        print("llama-server bereit!", flush=True)

---

## 5. Python-Dateien schreiben -- NIEMALS Shell-Heredocs

Shell-Heredocs zerstoeren Python-Code wenn Backticks oder Sonderzeichen
enthalten sind. Immer Python-Heredocs nutzen:

    python3 << 'PYEOF'
    content = """
    import json
    # Python Code hier
    """
    with open('/tmp/script.py', 'w') as f:
        f.write(content)
    PYEOF

---

## 6. GitHub Pushes -- NIEMALS Shell-Pipes

    # FALSCH -- leert Dateien zuverlaessig
    echo "Inhalt" | base64 | curl ...

    # RICHTIG -- Python urllib mit base64
    python3 << 'PYEOF'
    import base64, json, urllib.request
    TOKEN = "ghp_..."
    # SHA erst holen via GET, dann PUT
    PYEOF

---

## 7. Projekt-Ressourcen

GitHub: https://github.com/janhetzler/la

Release Assets:
- Granite 350m: https://github.com/janhetzler/la/releases/download/granite-models/granite-4.0-h-350m-Q4_K_M.gguf
- Granite Embedding: https://github.com/janhetzler/la/releases/download/granite-models/granite-embedding-30m-english-Q8_0.gguf
- Bifrost Binary: https://github.com/janhetzler/la/releases/download/granite-models/bifrost-http-0

llama-server installieren:
    curl -L https://github.com/ggml-org/llama.cpp/releases/download/b9895/llama-b9895-bin-ubuntu-x64.tar.gz -o /tmp/llama.tar.gz
    mkdir -p /opt/llama && tar -xzf /tmp/llama.tar.gz -C /opt/llama --strip-components=1
    chmod +x /opt/llama/llama-server

llama-server starten (bewiesene Konfiguration):
    /opt/llama/llama-server \
      --model /data/models/granite-350m.gguf \
      --host 127.0.0.1 --port 8081 \
      --ctx-size 4096 --threads 4 --parallel 1 -ngl 0 \
      --jinja --tools all > /tmp/llama.log 2>&1 &

---

## 8. Typische Fehler

| Fehler | Ursache | Loesung |
|--------|---------|---------|
| Port nicht erreichbar | Prozess noch nicht bereit | wait_for() Polling nutzen |
| Shell-Variable fehlt | Persistiert nicht | Im naechsten Call neu setzen |
| Python-Syntax kaputt | Heredoc-Problem | PYEOF Block nutzen |
| GitHub Push leert Datei | Shell-Pipe | Python urllib Pattern nutzen |
| Go nicht installierbar | go.dev blockiert | Go aus anderem Release holen |
| Bifrost Binary 403 | maximhq-Server blockiert | Unsere Binary aus janhetzler/la nutzen |

---

## 9. Bekannte Einschraenkungen

- llama-server mit --jinja funktioniert in der Sandbox (bewiesen)
- Tool-Calling mit Granite 350m funktioniert mit --jinja (bewiesen)
- Bifrost statisch gelinkt -- keine Custom Go Plugins (bewiesen via ldd)
- llmtrim compress funktioniert als stdin/stdout Tool (bewiesen)
- Python FastAPI Proxy als llmtrim-Middleware funktioniert (bewiesen)

---

Letzte Aktualisierung: 2026-07-19
Erstellt aus Erfahrungen in Sandbox 1 und Sandbox 2 des janhetzler/la Projekts
