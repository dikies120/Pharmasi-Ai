import asyncio
from pathlib import Path
from typing import Optional

from back.core.agent import Agent
from back.pharma_mcp.client import MCPClient


class Chatbot:
    def __init__(self, user_id: Optional[str] = None):
        self.user_id = user_id or "user_1"
        self.agent = Agent(user_id=self.user_id)
        self.client = MCPClient()

        self.server_script = Path(__file__).resolve().parents[1] / "pharma_mcp" / "server.py"

    async def run(self):
        print("[SYSTEM] Connecting to MCP...")

        try:
            await self.client.connect(str(self.server_script))
        except Exception as e:
            print(f"[ERROR] Gagal connect MCP: {e}")
            return

        print("MCP Connected")

        try:
            tools = await self.client.list_tools()
            print("Tools tersedia:", tools)
        except Exception as e:
            print(f"[ERROR] Gagal ambil tools: {e}")
            tools = []

        print("\nPharma AI Agent Ready\n")
        print(f"[INFO] User ID: {self.user_id}")

        while True:
            try:
                question = input("\nAnda: ").strip()

                if not question:
                    continue

                if question.lower() in ["exit", "quit"]:
                    print("[SYSTEM] Keluar...")
                    break

                if question.lower() == "memory":
                    print("[INFO] Memory sekarang dikelola di MCP (server/tool)")
                    continue

                if question.lower() == "history":
                    print("[INFO] History tersimpan di Mongo melalui MCP")
                    continue

                decision = self.agent.decide(question)

                if not isinstance(decision, dict):
                    print("[ERROR] Decision invalid")
                    continue

                if "answer" in decision:
                    answer = str(decision["answer"])
                    print("Bot:", answer)
                    continue

                tool = decision.get("tool")
                arguments = decision.get("arguments", {}) or {}

                if not tool:
                    print("[ERROR] Tool kosong")
                    continue

                if tools and tool not in tools:
                    print(f"[ERROR] Tool '{tool}' tidak ada")
                    continue

                # 🔥 WAJIB: kirim user_id ke MCP
                arguments["user_id"] = self.user_id

                print(f"Tool: {tool}")
                print(f"[DEBUG] Args: {arguments}")

                try:
                    result = await self.client.call_tool(tool, arguments)
                except Exception as e:
                    print(f"[ERROR] Tool error: {e}")
                    continue

                print(f"[DEBUG] Tool result: {result}")

                try:
                    print("FINAL ANSWER CALLED")
                    final = self.agent.final_answer(question, result)
                except Exception as e:
                    print(f"[ERROR] Final error: {e}")
                    final = str(result)

                print("Bot:", final)

            except KeyboardInterrupt:
                print("\n[SYSTEM] Interrupted")
                break
            except Exception as e:
                print(f"[ERROR] {e}")

        print("[SYSTEM] Closing...")
        try:
            await self.client.close()
        except Exception:
            pass


async def main(user_id: Optional[str] = None):
    bot = Chatbot(user_id=user_id)
    await bot.run()


if __name__ == "__main__":
    import sys

    user_id = sys.argv[1] if len(sys.argv) > 1 else None
    asyncio.run(main(user_id=user_id))