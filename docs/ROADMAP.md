---
type: Decision
status: current
updated_at: 2026-08-16
stale_after: 2027-02-16
environment: all
components: []
---
# ROADMAP — janhetzler/la

**Letzte Aktualisierung:** 2026-08-16
**Basis:** xaviervasques/chief-of-staff
**Ziel:** Selbstlernende, selbstverbessernde lokale Agentenplattform

---

## Architektur-Vision

```
Mensch
    ↓
Orchestrator  ←──── Scheduler / Task-Queue (SQLite)
    ↓
Supervisor (DSPy)  ←──── Planungs-DB / Memory Agent
    ↓
LangGraph Graph  ←──── Checkpointing (SQLite)
    ├── Agenten-Module (DSPy)
    ├── Deterministische Module (reines Python)
    └── Code Agent → neue Module bauen und testen

Continuous Improvement Loop:
Phoenix Traces → Metriken → Genetic-Pareto Evolution → bessere Prompts/Module
```

### Prinzipien

- **LA bleibt die Basis** — Infrastruktur (LiteLLM, Phoenix, ChromaDB, MCP,
  FastAPI) bleibt unangetastet. Nur der Kern wird umgebaut.
- **Vorhandene Frameworks** — nichts wird neu erfunden. DSPy, LangGraph,
  APScheduler, SQLite sind ausgereifte Lösungen.
- **Modellflexibilität** — Granite-Tiny oder Granite-350m sind jederzeit
  per LiteLLM-Config wechselbar, kein Stack-Neustart nötig.
- **HF Space als Entwicklungsumgebung** — Sandbox ist deprecated.
  Alle Tests und Entwicklung im HF Space mit echtem Tool-Calling.

---

## Architektur-Entscheidungen

| Komponente | Bisher | Neu | Grund |
|---|---|---|---|
| Supervisor | Router (ein Agent) | DSPy-Programm + LangGraph-Graph | Planung, Parallelität, Persistenz |
| Agenten | LangChain create_agent | DSPy-Module | Optimierbar, testbar, komponierbar |
| Routing | Heuristik + LLM-Fallback | DSPy Supervisor plant Ausführungsgraph | Mehrere Agenten parallel möglich |
| Persistenz | keine | LangGraph Checkpointing (SQLite) | Plan überlebt Fehler und Neustarts |
| Zeitsteuerung | keine | Orchestrator + APScheduler | Wiederkehrende und zeitgesteuerte Tasks |
| Task-Queue | keine | SQLite (Planungs-DB) | Tasks einreihen, State verfolgen |
| Memory | keine | Memory Agent (ChromaDB + Planungs-DB) | Supervisor kennt laufende Pläne |
| Prompt-Optimierung | manuell / Trial-and-Error | Genetic-Pareto Evolution via DSPy | Systematisch, messbar |
| Tests | strukturell falsch (6/6 nie echt) | Saubere Metriken + kontinuierliches Testen | Grundlage für Optimierung |
| Neue Agenten | manuell | Code Agent baut und testet selbstständig | Autonomer Loop |
| Determinismus | alles LLM | LLM oder reines Python je nach Aufgabe | Schneller, zuverlässiger wo möglich |

---

## Stack-Übersicht (Ziel)

```
cptr / opencomputer (Port 7860) — Frontend
    ↓
Orchestrator
    ├── Scheduler (APScheduler)
    ├── Task-Queue (SQLite)
    └── State-Monitor

    ↓
Supervisor (DSPy)
    ├── Plan-Phase: Ausführungsplan erstellen + in Planungs-DB persistieren
    ├── Context-Phase: Memory Agent liest relevante Infos
    └── Execute-Phase: LangGraph Graph

        LangGraph Graph
            ├── Researcher Agent (DSPy-Modul)
            ├── Comms Agent (DSPy-Modul)
            ├── Notes Agent (DSPy-Modul)
            ├── Code Agent (DSPy-Modul) → kann neue Module schreiben
            ├── Handoff Agent (DSPy-Modul)
            ├── Memory Agent (DSPy-Modul) — liest Planungs-DB + ChromaDB
            └── Deterministische Module (reines Python)

Infrastruktur (unverändert):
    ├── LiteLLM :4000 (Gateway, Modellwechsel ohne Neustart)
    ├── llama-server :8080 (Granite-Tiny, --jinja)
    ├── llama-server :8081 (Granite-Embedding-30m)
    ├── Phoenix :6006 (Tracing, Metriken, Basis für Optimierung)
    ├── ChromaDB (Vektorspeicher)
    └── MCP (git, fetch)

Continuous Improvement Loop:
    Phoenix Traces → Metriken → Genetic-Pareto Evolution → bessere Module
```

---

## Phasen

### Phase 1 — Fundament: Saubere Tests + BUG-027 (AKTUELL)

**Ziel:** Ehrliche Testergebnisse als Basis für alles weitere.
Kein Umbau ohne funktionierenden Researcher.

**Warum zuerst:** Genetic-Pareto Evolution und DSPy-Optimierung brauchen
ein Evaluierungs-Signal. Solange unsere Tests strukturell falsch sind,
optimieren wir ins Nichts.

- [ ] BUG-027 lösen: ExceptionGroup im Researcher — vollständigen Traceback
      mit eigenem Code-Frame sichern (Phoenix Traces, nicht Log-Stückwerk)
- [ ] Testlauf überarbeiten: „Maximale Tool-Runden erreicht" = FAIL,
      inhaltliche Antwort = Pflicht
- [ ] Metriken definieren: was ist eine gute Researcher-Antwort,
      was ist korrektes Tool-Calling, was ist korrektes Routing
- [ ] Researcher-Prompt anpassen: mcp_git für Repo-Inhalte,
      nicht ChromaDB

**Erfolgskriterium:** Researcher liefert inhaltlich korrekte Antwort
auf „Was steht in ROADMAP.md?" — verifiziert via Phoenix Trace.

---

### Phase 2 — Supervisor: DSPy + LangGraph Graph

**Voraussetzung:** Phase 1 abgeschlossen, Researcher funktioniert.

**Ziel:** Supervisor wird zum echten Planungs- und Ausführungssystem.

- [ ] DSPy installieren und in requirements.txt aufnehmen
- [ ] Supervisor als DSPy-Programm umbauen:
      Plan-Phase (welche Agenten, welche Reihenfolge, welche Inputs)
- [ ] LangGraph: Supervisor wird zum echten Graphen mit Kanten und Knoten
- [ ] LangGraph Checkpointing: Planungs-DB (SQLite) einrichten
- [ ] Parallele Ausführung: mehrere Agenten gleichzeitig wenn unabhängig
- [ ] Human-in-the-Loop: Plan wird angezeigt, Mensch bestätigt vor Ausführung
- [ ] Memory Agent: liest Planungs-DB + ChromaDB, liefert Kontext für Planung

**Erfolgskriterium:** „Recherchiere LangGraph und schreib mir eine
Zusammenfassung als Mail" — ein Aufruf, Researcher + Comms parallel,
eine Antwort. Plan in DB persistent.

---

### Phase 3 — Agenten: DSPy-Module + Skills

**Voraussetzung:** Phase 2 abgeschlossen.

**Ziel:** Alle Agenten werden zu DSPy-Modulen. Skills werden zu Submodulen.

- [ ] Agenten-Signaturen definieren (DSPy Signature für jeden Agenten)
- [ ] Agenten als dspy.Module umbauen — Researcher zuerst als Pilot
- [ ] Skills als DSPy-Submodule: dynamisch je nach Aufgabe injiziert
- [ ] Deterministische Module: wo kein LLM nötig ist, reines Python
- [ ] Code Agent erweitert: kann neue DSPy-Module schreiben und testen
- [ ] Agent-Registry dynamisch: neue Module werden automatisch erkannt

**Erfolgskriterium:** Neuer Agent = neue .py Datei, keine manuelle
Registrierung nötig. Code Agent schreibt einen einfachen neuen Agenten
selbstständig.

---

### Phase 4 — Orchestrator: Zeitsteuerung + Task-Queue

**Voraussetzung:** Phase 3 abgeschlossen.

**Ziel:** System initiiert selbst, wartet nicht nur auf menschlichen Input.

- [ ] APScheduler installieren
- [ ] Task-Queue in SQLite (Planungs-DB erweitern)
- [ ] Orchestrator als Schicht über dem Supervisor
- [ ] Zeitgesteuerte Tasks: Cron-ähnliche Konfiguration
- [ ] Wiederkehrende Tasks: Intervall-basiert
- [ ] State-Monitor: was läuft, was wartet, was ist fertig
- [ ] Orchestrator-API: Tasks einreihen, Status abfragen

**Erfolgskriterium:** „Jeden Montag 08:00 Statusreport aus JOURNAL.md"
läuft ohne menschlichen Trigger. State ist in DB persistent.

---

### Phase 5 — Continuous Improvement: Genetic-Pareto Evolution

**Voraussetzung:** Phase 4 abgeschlossen, Metriken aus Phase 1 vorhanden.

**Ziel:** System verbessert sich selbst kontinuierlich.

- [ ] DSPy-Optimierer einrichten (MIPROv2 als Basis)
- [ ] Genetic-Pareto Evolution: mehrere Optimierungsziele gleichzeitig
      (Antwortqualität, Token-Effizienz, Tool-Calling-Zuverlässigkeit)
- [ ] Phoenix Traces als Trainingsdaten: automatisch aus laufendem Betrieb
- [ ] Optimierungsloop als Orchestrator-Task: läuft im Hintergrund
- [ ] Vergleich: alte vs. neue Prompts/Module — Pareto-Front visualisieren
- [ ] Automatisches Deployment verbesserter Module nach Validierung

**Erfolgskriterium:** Researcher-Qualität verbessert sich messbar über
4 Wochen Betrieb ohne manuellen Eingriff.

---

## Offene Bugs (vor Phase 2 zu lösen)

| Bug | Priorität | Beschreibung |
|-----|-----------|--------------|
| BUG-027 | KRITISCH | Researcher ExceptionGroup — Phase 1 |
| BUG-020 | mittel | Researcher EISDIR (read_text_file auf Verzeichnis) |
| BUG-026 | niedrig | Hardcodierter llama-server Pfad in start_full.py |
| mcp.json Pfad | mittel | tools.py hardcodiert — Umgebungsvariable fehlt |

---

## Was entfernt / deprecated ist

| Was | Grund |
|-----|-------|
| Sandbox (docs/SANDBOX.md) | Deprecated — HF Space ist die Entwicklungsumgebung |
| llmtrim / Bifrost | Statisch gelinkt, nicht erweiterbar — kein Mehrwert |
| Heuristisches Routing (router_heuristic.py) | Wird von DSPy Supervisor übernommen |
| Manuelle Prompt-Dateien (.md) | Werden zu DSPy-Signaturen |

---

## Infrastruktur bleibt unverändert

| Komponente | Port | Status |
|---|---|---|
| llama-server (Granite-Tiny, --jinja) | 8080 | aktiv |
| llama-server (Granite-Embedding-30m) | 8081 | aktiv |
| LiteLLM | 4000 | aktiv |
| Phoenix | 6006 | aktiv, Tracing verifiziert |
| Agent Server (FastAPI) | 8002 | aktiv |
| cptr / opencomputer | 7860 | aktiv, Frontend |
| ChromaDB | embedded | aktiv |
| MCP (git, fetch) | stdio | aktiv |

---

## Referenzen

- Repo: https://github.com/janhetzler/la
- Original: https://github.com/xaviervasques/chief-of-staff
- DSPy: https://dspy.ai
- LangGraph: https://langchain-ai.github.io/langgraph/
- Arize Phoenix: https://github.com/Arize-ai/phoenix
- APScheduler: https://apscheduler.readthedocs.io
