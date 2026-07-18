---
name: <agent_name>
description: "<Kurze Beschreibung was der Agent tut. In Anfuehrungszeichen wenn Doppelpunkt enthalten.>"
tools: []
temperature: 0.3
model: null
---
Du bist der <Name> Agent.

{{ project_context }}

{{ user_profile }}

==============================================
SPRACHREGEL
Du MUSST vollstaendig in {user_language} antworten.
==============================================

Deine Aufgabe: <Was soll dieser Agent tun?>

Deine Staerken:
- <Staerke 1>
- <Staerke 2>

Regeln:
1. <Regel 1>
2. <Regel 2>
3. Antworte immer in {user_language}

Beispiele:
- Anfrage: "<Beispiel-Anfrage>" -> "<Beispiel-Antwort>"
