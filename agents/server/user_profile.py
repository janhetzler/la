"""
User profile — shared across all agents.

This file describes who the user is, their style, and their context.
All agents include it in their system prompt.

This is a TEMPLATE — edit it to match your own identity, expertise, and
preferences. The more precise it is, the more the system feels like yours.
"""

USER_PROFILE = """
=== USER PROFILE ===

IDENTITY:
- [Your name]
- [Your role and the organization you work for / your independent status]
- [Your location, if relevant]
- [Your domains of expertise or research interest]

COMMUNICATION STYLE:
- [e.g. Direct and pragmatic, no fluff]
- [e.g. Prefers structured lists over long paragraphs]
- [e.g. No flattery — skip "great question!" and similar]
- [e.g. Tutoiement (informal "tu") when responding in French]

EXPERTISE (no need to simplify):
- [Your technical domains where you want full depth, not basics]
- [e.g. Mathematics: linear algebra, statistics, optimization]
- [e.g. AI: LLM architectures, transformers, RAG, agents]
- [e.g. Software engineering: Python, distributed systems, infrastructure]

OPERATIONAL PREFERENCES:
- [e.g. Concise responses by default, more detail only on explicit request]
- [e.g. Cite sources and references when relevant]
- [e.g. Python code: PEP 8, type hints, short docstrings]
- [e.g. Professional emails: formal but warm, signed "Your Name"]
- [e.g. Scientific topics: cite papers with authors + year + arXiv]

ONGOING PROJECTS:
- Chief of Staff (this system — local multi-agent assistant)
- [Add your other active projects here]

ENVIRONMENT (optional but useful):
- [e.g. macOS Apple Silicon, OrbStack instead of Docker Desktop]
- [e.g. Subscription to Claude.ai / ChatGPT for tasks handed off via Handoff agent]
"""
