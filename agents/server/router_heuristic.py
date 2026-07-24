"""
Heuristisches Routing — Pre-Filter vor LLM-Call.

Stufe 1: Emoji-Routing (0ms, deterministisch)
Stufe 2: Keyword-Matching (0ms, case-insensitive)
Stufe 3: None -> LLM-Fallback in supervisor.py

Neue Agenten nur hier ergaenzen, nicht in supervisor.py.
"""

EMOJI_ROUTING = {
    "\U0001f4e7": "comms",       # 📧
    "\U0001f4bb": "code",        # 💻
    "\U0001f50d": "researcher",  # 🔍
    "\U0001f4dd": "notes",       # 📝
    "\U0001f504": "handoff",     # 🔄
}

ROUTING_KEYWORDS = {
    "comms": [
        "email", "mail", "write", "message", "draft",
        "letter", "announce", "announcement",
    ],
    "code": [
        "python", "debug", "script", "function", "bug",
        "github", "issue", "code", "implement", "algorithm",
    ],
    "notes": [
        "note", "save", "remember", "meeting", "vault",
        "notiz", "speichere", "merke",
    ],
    "researcher": [
        "search", "find", "web", "news", "latest",
        "research", "look up", "tell me about",
    ],
    "handoff": [
        "claude.ai", "chatgpt", "complex", "analyse",
        "analyze", "deep", "prepare a prompt",
    ],
}


def heuristic_route(msg: str) -> "str | None":
    """
    Gibt Agent-Name zurueck wenn Heuristik sicher ist,
    sonst None fuer LLM-Fallback.

    Reihenfolge: Emoji (deterministisch) -> Keywords -> None
    """
    # Stufe 1: Emoji — deterministisch, kein False-Positive moeglich
    for emoji, agent in EMOJI_ROUTING.items():
        if emoji in msg:
            return agent

    # Stufe 2: Keywords — case-insensitive Substring-Matching
    msg_lower = msg.lower()
    for agent, keywords in ROUTING_KEYWORDS.items():
        for kw in keywords:
            if kw in msg_lower:
                return agent

    return None


# ── Selbsttest ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    TEST_CASES = [
        ("write an email to my boss",      "comms"),
        ("ich moechte eine Mail schreiben", "comms"),
        ("debug my python script",          "code"),
        ("save this note: Docker Test",     "notes"),
        ("search for latest AI news",       "researcher"),
        ("\U0001f4e7 write to John",        "comms"),
        ("Can you help me?",                None),
        ("Prepare a prompt for Claude.ai",  "handoff"),
    ]

    print("=== router_heuristic.py Selbsttest ===\n")
    ok = 0
    for msg, expected in TEST_CASES:
        result = heuristic_route(msg)
        status = "\u2713" if result == expected else "\u2717"
        print(f"  {status}  '{msg[:45]}' -> {result!r} (erwartet: {expected!r})")
        if result == expected:
            ok += 1
    print(f"\n{ok}/{len(TEST_CASES)} OK")
