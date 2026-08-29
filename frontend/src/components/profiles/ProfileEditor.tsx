import { InfoCircleOutlined } from "@ant-design/icons";
import { Alert, Flex, Form, Input, Modal, Slider, Tooltip, Typography } from "antd";
import { useEffect, useState } from "react";

import type { WeightProfile, WeightProfileInput } from "../../types/profile";
import { METRIC_INFO, metricSummary, redundantlyWeighted } from "./metricInfo";

const { Text } = Typography;

interface Props {
  open: boolean;
  metrics: string[];
  profile: WeightProfile | null;
  onSave: (payload: WeightProfileInput, isNew: boolean) => Promise<void>;
  onCancel: () => void;
}

interface FormValues {
  name: string;
  label: string;
  description: string;
  weights: Record<string, number>;
}

function blankWeights(metrics: string[]): Record<string, number> {
  return Object.fromEntries(metrics.map((m) => [m, 0]));
}

export function ProfileEditor({
  open,
  metrics,
  profile,
  onSave,
  onCancel,
}: Props) {
  const isNew = profile === null;
  const [form] = Form.useForm<FormValues>();
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  // The modal stays mounted across openings, so reload the fields each time.
  useEffect(() => {
    if (!open) return;
    setError(null);
    form.setFieldsValue({
      name: profile?.name ?? "",
      label: profile?.label ?? "",
      description: profile?.description ?? "",
      weights: profile
        ? { ...blankWeights(metrics), ...profile.weights }
        : blankWeights(metrics),
    });
  }, [open, profile, metrics, form]);

  const weights = Form.useWatch("weights", form) ?? {};
  const total = Object.values(weights).reduce((a: number, b) => a + (b ?? 0), 0);
  const doubleCounted = redundantlyWeighted(weights);

  async function submit() {
    const values = await form.validateFields();
    setError(null);
    setSaving(true);
    try {
      await onSave(
        { ...values, name: isNew ? values.name : profile.name },
        isNew,
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal
      open={open}
      title={isNew ? "New profile" : `Edit ${profile?.label ?? ""}`}
      onOk={() => void submit()}
      onCancel={onCancel}
      okText="Save"
      okButtonProps={{ loading: saving, disabled: total <= 0 }}
      width={680}
    >
      <Form form={form} layout="vertical" requiredMark={false}>
        {isNew && (
          <Form.Item
            name="name"
            label={
              <>
                Name&nbsp;
                <Text type="secondary">(lowercase, underscores)</Text>
              </>
            }
            rules={[
              { required: true, message: "A name is required" },
              {
                pattern: /^[a-z][a-z0-9_]*$/,
                message: "Use lowercase letters, digits and underscores",
              },
            ]}
          >
            <Input placeholder="cargo_expansion" />
          </Form.Item>
        )}

        <Form.Item
          name="label"
          label="Label"
          rules={[{ required: true, message: "A label is required" }]}
        >
          <Input />
        </Form.Item>

        <Form.Item
          name="description"
          label={
            <>
              Description&nbsp;
              <Text type="secondary">
                — the agent reads this to decide when to use this profile
              </Text>
            </>
          }
        >
          <Input.TextArea rows={4} placeholder="Choose when the question is about…" />
        </Form.Item>

        <Text type="secondary" style={{ fontSize: 12 }}>
          Weights — normalized to 1.0 on save · current total {total.toFixed(2)}
        </Text>

        <div style={{ marginTop: 8 }}>
          {metrics.map((m) => (
            <Flex key={m} align="center" gap={12}>
              <Flex
                vertical
                style={{ width: 200, flexShrink: 0, lineHeight: 1.3 }}
              >
                <Flex align="center" gap={6}>
                  <Text style={{ fontSize: 13 }} ellipsis title={m}>
                    {m}
                  </Text>
                  <Tooltip title={metricSummary(m) ?? m}>
                    <InfoCircleOutlined
                      style={{ fontSize: 12, color: "#8c8c8c", cursor: "help" }}
                    />
                  </Tooltip>
                </Flex>
                {METRIC_INFO[m] && (
                  <Text type="secondary" style={{ fontSize: 11 }} ellipsis>
                    {METRIC_INFO[m].label}
                  </Text>
                )}
              </Flex>
              <Form.Item name={["weights", m]} style={{ flex: 1, marginBottom: 8 }}>
                <Slider min={0} max={1} step={0.05} tooltip={{ open: false }} />
              </Form.Item>
              <Text
                style={{
                  fontFamily: "ui-monospace, monospace",
                  fontSize: 12,
                  width: 34,
                  textAlign: "right",
                }}
              >
                {(weights[m] ?? 0).toFixed(2)}
              </Text>
            </Flex>
          ))}
        </div>

        {doubleCounted.map(([a, b]) => (
          <Alert
            key={`${a}-${b}`}
            type="warning"
            showIcon
            style={{ marginTop: 12 }}
            message={`${a} and ${b} rank airports identically`}
            description={`One is the other divided by a fixed ceiling, and scoring works on percentile rank — so weighting both puts ${(
              (weights[a] ?? 0) + (weights[b] ?? 0)
            ).toFixed(2)} on a single signal rather than blending two. Weight one of them.`}
          />
        ))}

        {error && <Alert type="error" showIcon message={error} />}
      </Form>
    </Modal>
  );
}
