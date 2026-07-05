export type ChatRole = "user" | "assistant";

export type JsonObject = Record<string, unknown>;

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  toolUsed?: string;
  modelName?: string;
  responseTimeMs?: number;
  timestamp: number;
}