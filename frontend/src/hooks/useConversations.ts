import { useCallback, useEffect, useState } from "react";

import { api } from "../services/api";
import type { Conversation } from "../types/chat";

export function useConversations() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      setConversations(await api.listConversations());
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  const create = useCallback(async () => {
    const conversation = await api.createConversation();
    setConversations((prev) => [conversation, ...prev]);
    setActiveId(conversation.id);
    return conversation;
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { conversations, activeId, setActiveId, create, refresh, error };
}
