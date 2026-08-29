import { DeleteOutlined, EditOutlined, PlusOutlined } from "@ant-design/icons";
import {
  Alert,
  App,
  Button,
  Card,
  Col,
  Collapse,
  Flex,
  Popconfirm,
  Progress,
  Row,
  Tag,
  Tooltip,
  Typography,
} from "antd";
import { useState } from "react";

import { useProfiles } from "../../hooks/useProfiles";
import type { WeightProfile } from "../../types/profile";
import { METRIC_INFO, metricSummary } from "./metricInfo";
import { ProfileEditor } from "./ProfileEditor";

const { Title, Paragraph, Text } = Typography;

/** Explains what each weightable metric measures and why it would be weighted. */
function MetricGlossary({ metrics }: { metrics: string[] }) {
  const keys = metrics.length ? metrics : Object.keys(METRIC_INFO);

  return (
    <Collapse
      size="small"
      style={{ marginBottom: 20 }}
      items={[
        {
          key: "glossary",
          label: "What each metric means",
          children: (
            <>
              <Paragraph type="secondary" style={{ fontSize: 12 }}>
                Every metric is written so that higher means more investment
                need — scoring percentiles each one and rewards the high end.
              </Paragraph>
              <Row gutter={[16, 16]}>
                {keys.map((metric) => {
                  const info = METRIC_INFO[metric];
                  return (
                    <Col key={metric} xs={24} md={12} xl={8}>
                      <Flex vertical gap={2}>
                        <Flex align="center" gap={8} wrap>
                          <Text code style={{ fontSize: 12 }}>
                            {metric}
                          </Text>
                          {info?.needsSegment && (
                            <Tag style={{ marginInlineEnd: 0 }}>T-100 segment</Tag>
                          )}
                        </Flex>
                        {info ? (
                          <>
                            <Text strong style={{ fontSize: 13 }}>
                              {info.label}
                            </Text>
                            <Text type="secondary" style={{ fontSize: 12 }}>
                              {info.formula}
                            </Text>
                            <Text style={{ fontSize: 12 }}>{info.meaning}</Text>
                          </>
                        ) : (
                          <Text type="secondary" style={{ fontSize: 12 }}>
                            No description available for this metric.
                          </Text>
                        )}
                      </Flex>
                    </Col>
                  );
                })}
              </Row>
            </>
          ),
        },
      ]}
    />
  );
}

export function ProfileDashboard() {
  const { profiles, metrics, error, save, remove } = useProfiles();
  const [editing, setEditing] = useState<WeightProfile | null | undefined>(
    undefined,
  );
  const { message } = App.useApp();

  async function handleSave(payload: Parameters<typeof save>[0], isNew: boolean) {
    await save(payload, isNew);
    setEditing(undefined);
    message.success(isNew ? "Profile created" : "Profile updated");
  }

  async function handleRemove(name: string) {
    try {
      await remove(name);
      message.success("Profile deleted");
    } catch (e) {
      message.error((e as Error).message);
    }
  }

  return (
    <div style={{ padding: 24 }}>
      <Flex align="flex-start" gap={16} style={{ marginBottom: 20 }}>
        <div>
          <Title level={4} style={{ marginTop: 0, marginBottom: 4 }}>
            Weight profiles
          </Title>
          <Paragraph type="secondary" style={{ maxWidth: "60ch", marginBottom: 0 }}>
            Each profile is an investment thesis. The agent picks one by reading
            the descriptions below, then scoring is computed deterministically
            from the weights.
          </Paragraph>
        </div>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          style={{ marginLeft: "auto", flexShrink: 0 }}
          onClick={() => setEditing(null)}
        >
          New profile
        </Button>
      </Flex>

      {error && (
        <Alert type="error" showIcon message={error} style={{ marginBottom: 16 }} />
      )}

      <MetricGlossary metrics={metrics} />

      <ProfileEditor
        open={editing !== undefined}
        metrics={metrics}
        profile={editing ?? null}
        onSave={handleSave}
        onCancel={() => setEditing(undefined)}
      />

      <Row gutter={[16, 16]}>
        {profiles.map((p) => (
          <Col key={p.name} xs={24} md={12} xl={8}>
            <Card
              title={
                <Flex align="center" gap={8}>
                  <span>{p.label}</span>
                  {p.is_builtin && <Tag>built-in</Tag>}
                </Flex>
              }
              size="small"
              style={{ height: "100%" }}
              actions={[
                <Button
                  key="edit"
                  type="text"
                  icon={<EditOutlined />}
                  onClick={() => setEditing(p)}
                >
                  Edit
                </Button>,
                p.is_builtin ? (
                  <Text key="del" type="secondary">
                    —
                  </Text>
                ) : (
                  <Popconfirm
                    key="del"
                    title="Delete this profile?"
                    okText="Delete"
                    okButtonProps={{ danger: true }}
                    onConfirm={() => void handleRemove(p.name)}
                  >
                    <Button type="text" danger icon={<DeleteOutlined />}>
                      Delete
                    </Button>
                  </Popconfirm>
                ),
              ]}
            >
              <Text code type="secondary">
                {p.name}
              </Text>
              <Paragraph style={{ marginTop: 8, fontSize: 13 }}>
                {p.description}
              </Paragraph>

              <Flex vertical gap={4}>
                {Object.entries(p.weights)
                  .sort(([, a], [, b]) => b - a)
                  .map(([metric, w]) => (
                    <Flex key={metric} align="center" gap={8}>
                      <Tooltip title={metricSummary(metric) ?? metric}>
                        <Text
                          type="secondary"
                          ellipsis
                          style={{
                            fontSize: 12,
                            width: 160,
                            flexShrink: 0,
                            cursor: "help",
                          }}
                        >
                          {metric}
                        </Text>
                      </Tooltip>
                      <Progress
                        percent={w * 100}
                        showInfo={false}
                        size="small"
                        style={{ flex: 1, marginBottom: 0 }}
                      />
                      <Text
                        style={{
                          fontSize: 12,
                          fontFamily: "ui-monospace, monospace",
                          width: 34,
                          textAlign: "right",
                        }}
                      >
                        {w.toFixed(2)}
                      </Text>
                    </Flex>
                  ))}
              </Flex>
            </Card>
          </Col>
        ))}
      </Row>
    </div>
  );
}
