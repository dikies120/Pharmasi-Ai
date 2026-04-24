from typing import Optional

from back.core.llm import LLM


class Chatbot:
    def __init__(self, user_id: Optional[str] = None):
        self.user_id = user_id or "user_1"
        self.llm = LLM()

    def _prepare_model(self) -> bool:
        print("[SYSTEM] Checking LLM model before chat...")
        self.llm.model_available = self.llm.debug_connection(verbose=True)
        return self.llm.model_available

    def run(self):
        if not self._prepare_model():
            print(
                f"[ERROR] Model '{self.llm.model}' tidak tersedia. "
                "Jalankan `ollama pull` atau ubah OLLAMA_MODEL di .env"
            )
            return

        print("\nPharma AI Chatbot Ready\n")
        print(f"[INFO] User ID: {self.user_id}")
        print("[INFO] Ketik 'exit' atau 'quit' untuk keluar")

        while True:
            try:
                question = input("\nAnda: ").strip()

                if not question:
                    continue

                if question.lower() in ["exit", "quit"]:
                    print("[SYSTEM] Keluar...")
                    break

                try:
                    answer = self.llm.generate(question).strip()
                except Exception as e:
                    print(f"[ERROR] LLM error: {e}")
                    continue

                if not answer:
                    print("Bot: [EMPTY RESPONSE]")
                    continue

                print("Bot:", answer)

            except KeyboardInterrupt:
                print("\n[SYSTEM] Interrupted")
                break
            except Exception as e:
                print(f"[ERROR] {e}")

        print("[SYSTEM] Closing...")


def main(user_id: Optional[str] = None):
    bot = Chatbot(user_id=user_id)
    bot.run()


if __name__ == "__main__":
    import sys

    user_id = sys.argv[1] if len(sys.argv) > 1 else None
    main(user_id=user_id)