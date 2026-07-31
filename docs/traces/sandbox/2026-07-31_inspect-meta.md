# Meta-Agent Diagnose -- 2026-07-31

**Modell:** granite-350m-Q4_K_M
**Stack:** llama-server :8080 direkt (kein LiteLLM)
**Gesamtdauer:** 18.4s

---

## Test A -- Voller Prompt, default max_tokens

| max_tokens | default |
| Prompt-Laenge | 1399 Zeichen |
| prompt_tokens | 341 |
| completion_tokens | 6 |
| finish_reason | stop |
| Antwortlaenge | 14 Zeichen |
| Dauer | 4.1s |

**Rohe Antwort:**
```
What can I do?
```

---

## Test B -- Voller Prompt, max_tokens=512

| max_tokens | 512 |
| Prompt-Laenge | 1399 Zeichen |
| prompt_tokens | 341 |
| completion_tokens | 203 |
| finish_reason | stop |
| Antwortlaenge | 953 Zeichen |
| Dauer | 10.0s |

**Rohe Antwort:**
```
Certainly! Here's a response to your query, formatted as requested:

---

## What Can I Do?

### Researcher
- **Search Indexing**: Delivers information and data from indexed documents and the web.
- **Web Exploration**: Quickly accesses relevant information on the web.

### Comms
- **Email/Direct Message**: Sends and receives emails or messages.
- **Brief Reports**: Generates short reports summarizing key points.

### Notes
- **Personal Notes**: Stores and organizes personal notes and projects.
- **ChromaDB**: Stores personal projects, meetings, and other notes.

### Code
- **Programming, Algorithms, Debugging**: Engages in programming, algorithms, debugging, and GitHub issue management.
- **GitHub**: Access to GitHub for reviewing issues and contributing.

### Handoff
- **Rich Prompts**: Prepared rich prompts for Claude.ai or ChatGPT to complete tasks beyond my local model's capabilities.

---

Thank you for asking. What can I do for you?
```

---

## Test C -- Gekuerzter Prompt, max_tokens=512

| max_tokens | 512 |
| Prompt-Laenge | 228 Zeichen |
| prompt_tokens | 78 |
| completion_tokens | 69 |
| finish_reason | stop |
| Antwortlaenge | 337 Zeichen |
| Dauer | 4.2s |

**Rohe Antwort:**
```
I am a AI assistant designed to provide information, answer questions to the best of my ability. I can provide information on a wide range of topics including the human interface, coding, language, general knowledge, and more. I can assist with creating guides, answering queries, and even help with data analysis. What can I do for you?
```

---

## Zusammenfassung

| Test | max_tokens | prompt_tokens | completion_tokens | finish_reason | Antwortlaenge |
|------|-----------|--------------|------------------|---------------|--------------|
| A | None | 341 | 6 | stop | 14 |
| B | 512 | 341 | 203 | stop | 953 |
| C | 512 | 78 | 69 | stop | 337 |

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
Dauer:              4.1s
finish_reason:      stop
prompt_tokens:      341
completion_tokens:  6
Antwortlaenge:      14 Zeichen

Rohe Antwort:
What can I do?

=== TEST B -- Voller Prompt, max_tokens=512 ===
max_tokens:    512
Prompt-Laenge: 1399 Zeichen
Dauer:              10.0s
finish_reason:      stop
prompt_tokens:      341
completion_tokens:  203
Antwortlaenge:      953 Zeichen

Rohe Antwort:
Certainly! Here's a response to your query, formatted as requested:

---

## What Can I Do?

### Researcher
- **Search Indexing**: Delivers information and data from indexed documents and the web.
- **Web Exploration**: Quickly accesses relevant information on the web.

### Comms
- **Email/Direct Message**: Sends and receives emails or messages.
- **Brief Reports**: Generates short reports summarizing key points.

### Notes
- **Personal Notes**: Stores and organizes personal notes and projects.
- **ChromaDB**: Stores personal projects, meetings, and other notes.

### Code
- **Programming, Algorithms, Debugging**: Engages in programming, algorithms, debugging, and GitHub issue management.
- **GitHub**: Access to GitHub for reviewing issues and contributing.

### Handoff
- **Rich Prompts**: Prepared rich prompts for Claude.ai or ChatGPT to complete tasks beyond my local model's capabilities.

---

Thank you for asking. What can I do for you?

=== TEST C -- Gekuerzter Prompt, max_tokens=512 ===
max_tokens:    512
Prompt-Laenge: 228 Zeichen
Dauer:              4.2s
finish_reason:      stop
prompt_tokens:      78
completion_tokens:  69
Antwortlaenge:      337 Zeichen

Rohe Antwort:
I am a AI assistant designed to provide information, answer questions to the best of my ability. I can provide information on a wide range of topics including the human interface, coding, language, general knowledge, and more. I can assist with creating guides, answering queries, and even help with data analysis. What can I do for you?

=== ZUSAMMENFASSUNG ===
Test                                      max_tok  p_tok  c_tok finish          len
----------------------------------------------------------------------------------
A -- Voller Prompt, default max_tokens       None    341      6 stop             14
B -- Voller Prompt, max_tokens=512            512    341    203 stop            953
C -- Gekuerzter Prompt, max_tokens=512        512     78     69 stop            337
```
