import {
  AppstoreOutlined,
  MessageOutlined,
  RiseOutlined,
} from "@ant-design/icons";
import { Layout, Menu, Space, Tag, Typography } from "antd";
import { useEffect, useState } from "react";

import { Chat } from "./components/chat/Chat";
import { ConversationList } from "./components/conversations/ConversationList";
import { ProfileDashboard } from "./components/profiles/ProfileDashboard";
import { useConversations } from "./hooks/useConversations";
import { api } from "./services/api";
import { ACCENT } from "./theme";

const { Header, Sider, Content } = Layout;
const { Text } = Typography;

type Tab = "chat" | "profiles";

export default function App() {
  const [tab, setTab] = useState<Tab>("chat");
  const { conversations, activeId, setActiveId, create, rename, remove } =
    useConversations();
  const [provenance, setProvenance] = useState<string>("");
  const [healthy, setHealthy] = useState<boolean | null>(null);

  useEffect(() => {
    api
      .health()
      .then((h) => {
        const p = h.provenance as {
          airports?: number;
          sources?: { as_of: string }[];
        };
        setProvenance(
          `${p.airports ?? "?"} airports · ${p.sources?.[0]?.as_of ?? "unknown"}`,
        );
        setHealthy(true);
      })
      .catch(() => {
        setProvenance("backend unreachable");
        setHealthy(false);
      });
  }, []);

  return (
    <Layout style={{ height: "100vh" }}>
      <Header
        style={{
          display: "flex",
          alignItems: "center",
          gap: 24,
          borderBottom: "1px solid #f0f0f0",
        }}
      >
        <Space size={8}>
          <RiseOutlined style={{ color: ACCENT, fontSize: 18 }} />
          <Text strong style={{ fontSize: 15, whiteSpace: "nowrap" }}>
            Airport Investment Intelligence
          </Text>
        </Space>

        <Menu
          mode="horizontal"
          selectedKeys={[tab]}
          onSelect={({ key }) => setTab(key as Tab)}
          style={{ flex: 1, minWidth: 0, borderBottom: "none" }}
          items={[
            { key: "chat", icon: <MessageOutlined />, label: "Chat" },
            {
              key: "profiles",
              icon: <AppstoreOutlined />,
              label: "Weight profiles",
            },
          ]}
        />

        <Tag
          color={healthy === false ? "error" : healthy ? "blue" : "default"}
          title="Data provenance"
          style={{ marginInlineEnd: 0 }}
        >
          {provenance || "checking…"}
        </Tag>
      </Header>

      {tab === "chat" ? (
        <Layout hasSider>
          <Sider
            width={264}
            theme="light"
            style={{ borderRight: "1px solid #f0f0f0", overflowY: "auto" }}
          >
            <ConversationList
              conversations={conversations}
              activeId={activeId}
              onSelect={setActiveId}
              onCreate={() => void create()}
              onRename={rename}
              onDelete={remove}
            />
          </Sider>
          <Content className="fill-column">
            <Chat conversationId={activeId} />
          </Content>
        </Layout>
      ) : (
        <Content style={{ overflowY: "auto" }}>
          <ProfileDashboard />
        </Content>
      )}
    </Layout>
  );
}
