import { useCallback, useEffect, useState } from "react";

import { api } from "../services/api";
import type { ChatMessage } from "../types/chat";

export function useChat(conversationId: string | null) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [pending, setPending] = useState(false);

  // Rehydrate from persisted graph state when the thread changes.
  useEffect(() => {
    if (!conversationId) {
      setMessages([]);
      return;
    }
    let cancelled = false;
    api
      .getMessages(conversationId)
      .then((history) => {
        if (cancelled) return;
        setMessages(
          history
            .filter((m) => m.role === "user" || m.role === "assistant")
            .map((m) => ({ role: m.role, content: m.content, turn: m.turn })),
        );
      })
      .catch(() => setMessages([]));
    return () => {
      cancelled = true;
    };
  }, [conversationId]);

  const send = useCallback(
    async (text: string) => {
      if (!conversationId) return;
      setMessages((prev) => [...prev, { role: "user", content: text }]);
      setPending(true);
      try {
        const turn = await api.sendMessage(conversationId, text);
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: turn.message, turn },
        ]);
      } catch (e) {
        setMessages((prev) => [
          ...prev,
          { role: "error", content: (e as Error).message },
        ]);
      } finally {
        setPending(false);
      }
    },
    [conversationId],
  );

  return { messages, send, pending };
}
