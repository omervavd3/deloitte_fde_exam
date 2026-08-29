import { SendOutlined } from "@ant-design/icons";
import { Button, Flex, Input, Tag, Tooltip } from "antd";
import { useState } from "react";

interface Props {
  onSend: (text: string) => void;
  disabled: boolean;
}

const EXAMPLES = [
  "Which airports in New England are strong candidates for terminal expansion?",
  "What is the percentage of long haul flights out of Anchorage airport?",
  "What is the unmet flight demand in SFO airport and why?",
  "Rank Midwest airports for cargo handling capacity.",
  "Compare LAX and Santa Ana airport congestion levels.",
];

export function ChatInput({ onSend, disabled }: Props) {
  const [text, setText] = useState("");

  function submit(value: string) {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setText("");
  }

  return (
    <div
      style={{
        borderTop: "1px solid #f0f0f0",
        background: "#fff",
        padding: "12px 20px",
      }}
    >
      <Flex gap={6} wrap style={{ marginBottom: 10 }}>
        {EXAMPLES.map((e) => (
          <Tooltip key={e} title={e}>
            <Tag
              style={{ cursor: disabled ? "default" : "pointer", margin: 0 }}
              onClick={() => submit(e)}
            >
              {e.length > 46 ? `${e.slice(0, 46)}…` : e}
            </Tag>
          </Tooltip>
        ))}
      </Flex>

      <Input.Search
        value={text}
        onChange={(e) => setText(e.target.value)}
        onSearch={submit}
        placeholder="Ask about airport investment opportunities…"
        disabled={disabled}
        size="large"
        enterButton={
          <Button
            type="primary"
            size="large"
            icon={<SendOutlined />}
            disabled={disabled || !text.trim()}
          >
            Send
          </Button>
        }
      />
    </div>
  );
}
