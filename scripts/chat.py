import sys, time
from openai import OpenAI

client = OpenAI(
    base_url="http://127.0.0.1:8002/v1",
    api_key="sk-cos-local-dev"
)

def run_chat():
    print("=== Chief-of-Staff Terminal Chat ===")
    print("Tippe 'exit' zum Beenden, 'log' für Phoenix Traces.\n")
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
