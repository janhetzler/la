"""
Telemetry: Arize Phoenix + zentraler LLM Client für janhet.
"""
import os

# MUSS vor allen anderen Imports stehen
os.environ["PHOENIX_COLLECTOR_ENDPOINT"] = "http://127.0.0.1:6006/v1/traces"
os.environ["PHOENIX_CLIENT_HEADERS"] = "api_key=not-needed"
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "sk-cos-local-dev")

from langchain_openai import ChatOpenAI

LITELLM_URL = os.getenv("LITELLM_URL", "http://127.0.0.1:4000")
LITELLM_KEY = os.getenv("LITELLM_KEY", "sk-cos-local-dev")
PHOENIX_HOST = os.getenv("PHOENIX_HOST", "http://127.0.0.1:6006")

def init_phoenix():
    """Phoenix Tracing initialisieren."""
    try:
        from phoenix.otel import register
        tracer_provider = register(
            project_name="chief-of-staff",
            endpoint=f"{PHOENIX_HOST}/v1/traces",
            set_global_tracer_provider=True,
        )
        from openinference.instrumentation.langchain import LangChainInstrumentor
        LangChainInstrumentor().instrument(tracer_provider=tracer_provider)
        print(f"Phoenix Tracing aktiv → {PHOENIX_HOST}")
        return tracer_provider
    except Exception as e:
        print(f"Phoenix init: {e}")
        return None

def get_agent_llm(model: str = "granite-tiny", temperature: float = 0.0) -> ChatOpenAI:
    """Zentraler LLM Client — alle Agenten nutzen diese Funktion."""
    return ChatOpenAI(
        base_url=f"{LITELLM_URL}/v1",
        api_key=LITELLM_KEY,
        model=model,
        temperature=temperature,
    )
