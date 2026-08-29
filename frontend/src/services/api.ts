import type { ChatMessage, ChatResponse, Conversation } from "../types/chat";
import type { WeightProfile, WeightProfileInput } from "../types/profile";

const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!response.ok) {
    const body = await response.text();
    let detail = body;
    try {
      detail = JSON.parse(body).detail ?? body;
    } catch {
      /* plain text body */
    }
    throw new Error(`${response.status}: ${detail}`);
  }
  return response.status === 204 ? (undefined as T) : response.json();
}

export const api = {
  health: () => request<Record<string, unknown>>("/health"),

  listConversations: () => request<Conversation[]>("/api/conversations"),
  createConversation: () =>
    request<Conversation>("/api/conversations", { method: "POST" }),
  renameConversation: (id: string, title: string) =>
    request<Conversation>(`/api/conversations/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ title }),
    }),
  deleteConversation: (id: string) =>
    request<void>(`/api/conversations/${id}`, { method: "DELETE" }),
  getMessages: (id: string) =>
    request<ChatMessage[]>(`/api/conversations/${id}/messages`),

  sendMessage: (conversationId: string, message: string) =>
    request<ChatResponse>("/api/chat", {
      method: "POST",
      body: JSON.stringify({ conversation_id: conversationId, message }),
    }),

  listMetrics: () => request<string[]>("/api/metrics"),
  listProfiles: () => request<WeightProfile[]>("/api/profiles"),
  createProfile: (payload: WeightProfileInput) =>
    request<WeightProfile>("/api/profiles", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateProfile: (name: string, payload: Omit<WeightProfileInput, "name">) =>
    request<WeightProfile>(`/api/profiles/${name}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  deleteProfile: (name: string) =>
    request<void>(`/api/profiles/${name}`, { method: "DELETE" }),
};
