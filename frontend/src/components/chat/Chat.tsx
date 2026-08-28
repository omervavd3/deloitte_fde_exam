import { Empty, Flex, Spin, Typography } from "antd";
import { useEffect, useRef } from "react";

import { useChat } from "../../hooks/useChat";
import { ChatInput } from "./ChatInput";
import { Message } from "./Message";

const { Text } = Typography;

interface Props {
  conversationId: string | null;
}

export function Chat({ conversationId }: Props) {
  const { messages, send, pending } = useChat(conversationId);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, pending]);

  if (!conversationId) {
    return (
      <Flex align="center" justify="center" style={{ height: "100%" }}>
        <Empty description="Select a conversation or start a new one." />
      </Flex>
    );
  }

  return (
    <div className="fill-column" style={{ height: "100%" }}>
      <div className="scroll-y" style={{ padding: 20 }}>
        <Flex vertical gap={16}>
          {messages.length === 0 && (
            <Text type="secondary">Ask a question to begin.</Text>
          )}
          {messages.map((m, i) => (
            <Message key={i} message={m} />
          ))}
          {pending && (
            <Flex gap={8} align="center">
              <Spin size="small" />
              <Text type="secondary">Thinking…</Text>
            </Flex>
          )}
          <div ref={endRef} />
        </Flex>
      </div>
      <ChatInput onSend={send} disabled={pending} />
    </div>
  );
}
