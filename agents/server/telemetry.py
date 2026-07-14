"""
Arize Phoenix Telemetry — janhet
Initialisiert Phoenix zentral für alle Agenten.
Muss als erstes importiert werden in server.py.
"""
import os
import logging

logger = logging.getLogger(__name__)

PHOENIX_HOST = os.getenv("PHOENIX_HOST", "http://127.0.0.1:6006")
PHOENIX_ENABLED = os.getenv("PHOENIX_ENABLED", "true").lower() == "true"


def init_phoenix():
    """Phoenix Tracing initialisieren."""
    if not PHOENIX_ENABLED:
        logger.info("Phoenix Tracing deaktiviert (PHOENIX_ENABLED=false)")
        return

    try:
        from phoenix.otel import register
        from openinference.instrumentation.langchain import LangChainInstrumentor

        tracer_provider = register(
            project_name="chief-of-staff",
            endpoint=f"{PHOENIX_HOST}/v1/traces",
            set_global_tracer_provider=True,
        )
        LangChainInstrumentor().instrument(tracer_provider=tracer_provider)
        logger.info(f"Phoenix Tracing aktiv → {PHOENIX_HOST}")

    except ImportError:
        logger.warning("Phoenix nicht installiert — Tracing deaktiviert")
    except Exception as e:
        logger.warning(f"Phoenix Init fehlgeschlagen: {e} — weiter ohne Tracing")


def get_litellm_client():
    """
    Zentraler LLM Client — geroutet über LiteLLM Proxy Port 4000.
    Alle Agenten nutzen diesen statt direkter Modell-Calls.
    """
    from langchain_openai import ChatOpenAI
    import config

    return ChatOpenAI(
        base_url=f"{config.LITELLM_URL}/v1",
        api_key=config.LITELLM_KEY,
        model=config.DEFAULT_LLM,
        temperature=0,
    )
