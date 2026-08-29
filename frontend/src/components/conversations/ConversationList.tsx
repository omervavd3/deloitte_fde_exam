import {
  DeleteOutlined,
  EditOutlined,
  MoreOutlined,
  PlusOutlined,
} from "@ant-design/icons";
import { App, Button, Dropdown, Empty, Input, Menu } from "antd";
import { useState } from "react";

import type { Conversation } from "../../types/chat";

interface Props {
  conversations: Conversation[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onCreate: () => void;
  onRename: (id: string, title: string) => Promise<unknown>;
  onDelete: (id: string) => Promise<unknown>;
}

export function ConversationList({
  conversations,
  activeId,
  onSelect,
  onCreate,
  onRename,
  onDelete,
}: Props) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const { message, modal } = App.useApp();

  async function commitRename(id: string) {
    const title = draft.trim();
    setEditingId(null);
    const previous = conversations.find((c) => c.id === id)?.title;
    if (!title || title === previous) return;
    try {
      await onRename(id, title);
    } catch (e) {
      message.error((e as Error).message);
    }
  }

  function confirmDelete(conversation: Conversation) {
    modal.confirm({
      title: "Delete this conversation?",
      content: `"${conversation.title}" and its message history will be removed.`,
      okText: "Delete",
      okButtonProps: { danger: true },
      onOk: async () => {
        try {
          await onDelete(conversation.id);
          message.success("Conversation deleted");
        } catch (e) {
          message.error((e as Error).message);
          throw e; // keep the modal open on failure
        }
      },
    });
  }

  function renderLabel(conversation: Conversation) {
    if (editingId === conversation.id) {
      return (
        <Input
          size="small"
          autoFocus
          value={draft}
          maxLength={200}
          onChange={(e) => setDraft(e.target.value)}
          onClick={(e) => e.stopPropagation()}
          onPressEnter={() => void commitRename(conversation.id)}
          onBlur={() => void commitRename(conversation.id)}
          onKeyDown={(e) => {
            if (e.key === "Escape") setEditingId(null);
          }}
        />
      );
    }

    return (
      <div
        style={{ display: "flex", alignItems: "center", gap: 4, minWidth: 0 }}
      >
        <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis" }}>
          {conversation.title}
        </span>
        <Dropdown
          trigger={["click"]}
          menu={{
            items: [
              { key: "rename", icon: <EditOutlined />, label: "Rename" },
              {
                key: "delete",
                icon: <DeleteOutlined />,
                label: "Delete",
                danger: true,
              },
            ],
            onClick: ({ key, domEvent }) => {
              domEvent.stopPropagation();
              if (key === "rename") {
                setDraft(conversation.title);
                setEditingId(conversation.id);
              } else {
                confirmDelete(conversation);
              }
            },
          }}
        >
          <Button
            type="text"
            size="small"
            icon={<MoreOutlined />}
            aria-label="Conversation actions"
            onClick={(e) => e.stopPropagation()}
          />
        </Dropdown>
      </div>
    );
  }

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
          onSelect={({ key }) => {
            if (key !== editingId) onSelect(key);
          }}
          style={{ borderInlineEnd: "none" }}
          items={conversations.map((c) => ({
            key: c.id,
            label: renderLabel(c),
            title: c.title,
          }))}
        />
      )}
    </div>
  );
}
