# Meta-Agent Diagnose -- 2026-07-31

**Modell:** granite-350m-Q4_K_M
**Stack:** llama-server :8080 direkt (kein LiteLLM)
**Gesamtdauer:** 14.4s

---

## Test A -- Voller Prompt, default max_tokens

| max_tokens | default |
| Prompt-Laenge | 1399 Zeichen |
| prompt_tokens | 341 |
| completion_tokens | 26 |
| finish_reason | stop |
| Antwortlaenge | 113 Zeichen |
| Dauer | 8.8s |

**Rohe Antwort:**
```
Hello! 👋 I am the Local Agent, your personal assistant designed for local operations. How may I assist you today?
```

---

## Test B -- Voller Prompt, max_tokens=512

| max_tokens | 512 |
| Prompt-Laenge | 1399 Zeichen |
| prompt_tokens | 341 |
| completion_tokens | 3 |
| finish_reason | stop |
| Antwortlaenge | 6 Zeichen |
| Dauer | 1.5s |

**Rohe Antwort:**
```
Hello!
```

---

## Test C -- Gekuerzter Prompt, max_tokens=512

| max_tokens | 512 |
| Prompt-Laenge | 228 Zeichen |
| prompt_tokens | 78 |
| completion_tokens | 8 |
| finish_reason | stop |
| Antwortlaenge | 31 Zeichen |
| Dauer | 4.0s |

**Rohe Antwort:**
```
I can provide a brief overview.
```

---

## Zusammenfassung

| Test | max_tokens | prompt_tokens | completion_tokens | finish_reason | Antwortlaenge |
|------|-----------|--------------|------------------|---------------|--------------|
| A | None | 341 | 26 | stop | 113 |
| B | 512 | 341 | 3 | stop | 6 |
| C | 512 | 78 | 8 | stop | 31 |

---

## Konsolen-Output (komplett)

```
=== inspect_meta.py ===
Modell: /tmp/granite-350m-Q4_K_M.gguf

llama-server OK
Warte auf Inference-Bereitschaft...
llama-server Inference OK

=== TEST A -- Voller Prompt, default max_tokens ===
max_tokens:    (default)
Prompt-Laenge: 1399 Zeichen
Dauer:              8.8s
finish_reason:      stop
prompt_tokens:      341
completion_tokens:  26
Antwortlaenge:      113 Zeichen

Rohe Antwort:
Hello! 👋 I am the Local Agent, your personal assistant designed for local operations. How may I assist you today?

=== TEST B -- Voller Prompt, max_tokens=512 ===
max_tokens:    512
Prompt-Laenge: 1399 Zeichen
Dauer:              1.5s
finish_reason:      stop
prompt_tokens:      341
completion_tokens:  3
Antwortlaenge:      6 Zeichen

Rohe Antwort:
Hello!

=== TEST C -- Gekuerzter Prompt, max_tokens=512 ===
max_tokens:    512
Prompt-Laenge: 228 Zeichen
Dauer:              4.0s
finish_reason:      stop
prompt_tokens:      78
completion_tokens:  8
Antwortlaenge:      31 Zeichen

Rohe Antwort:
I can provide a brief overview.

=== ZUSAMMENFASSUNG ===
Test                                      max_tok  p_tok  c_tok finish          len
----------------------------------------------------------------------------------
A -- Voller Prompt, default max_tokens       None    341     26 stop            113
B -- Voller Prompt, max_tokens=512            512    341      3 stop              6
C -- Gekuerzter Prompt, max_tokens=512        512     78      8 stop             31
```
