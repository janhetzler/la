import sys, time, os
from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path

# Konfiguration aus Umgebungsvariablen
PROJECT_ROOT = Path(__file__).resolve().parent.parent
LA_ENV = os.getenv("LA_ENV", "sandbox")
for env_file in ["common.env"]:
    p = PROJECT_ROOT / "config" / LA_ENV / env_file
    if p.exists():
        load_dotenv(p, override=False)

LITELLM_URL = os.getenv("LITELLM_URL", "http://127.0.0.1:4000")
LITELLM_KEY = os.getenv("LITELLM_KEY", "sk-cos-local-dev")

client = OpenAI(
    base_url=f"{LITELLM_URL}/v1",
    api_key=LITELLM_KEY
)

def run_chat():
    print("=== Local Agent Terminal Chat ===")
    print("Tippe 'exit' zum Beenden.\n")
    messages = []

    while True:
        try:
            user_input = input("\033[1;34mDu:\033[0m ")
            if user_input.strip().lower() in ["exit", "quit"]:
                print("Chat beendet.")
                break
            if not user_input.strip():
                continue

            messages.append({"role": "user", "content": user_input})

            response = client.chat.completions.create(
                model="agent-local",
                messages=messages,
                stream=False,
                max_tokens=300
            )

            text = response.choices[0].message.content
            print(f"\033[1;32mAgent:\033[0m {text}\n")
            messages.append({"role": "assistant", "content": text})

        except KeyboardInterrupt:
            print("\nChat abgebrochen.")
            break
        except Exception as e:
            print(f"\033[1;31mFehler:\033[0m {e}\n")

if __name__ == "__main__":
    run_chat()
