import { PlusOutlined } from "@ant-design/icons";
import { Button, Empty, Menu } from "antd";

import type { Conversation } from "../../types/chat";

interface Props {
  conversations: Conversation[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onCreate: () => void;
}

export function ConversationList({
  conversations,
  activeId,
  onSelect,
  onCreate,
}: Props) {
  return (
    <div style={{ padding: 12 }}>
      <Button
        type="primary"
        icon={<PlusOutlined />}
        block
        onClick={onCreate}
        style={{ marginBottom: 12 }}
      >
        New conversation
      </Button>

      {conversations.length === 0 ? (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description="No conversations yet"
        />
      ) : (
        <Menu
          mode="inline"
          selectedKeys={activeId ? [activeId] : []}
          onSelect={({ key }) => onSelect(key)}
          style={{ borderInlineEnd: "none" }}
          items={conversations.map((c) => ({
            key: c.id,
            label: c.title,
            title: c.id,
          }))}
        />
      )}
    </div>
  );
}
