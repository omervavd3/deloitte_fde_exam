import { Collapse, Flex, Tag, Typography } from "antd";

import { ACCENT } from "../../theme";
import type { MethodNote, ReasoningStep } from "../../types/chat";

const { Text } = Typography;

interface Props {
  reasoning?: ReasoningStep[];
  methodNotes?: MethodNote[];
}

/** The agent's decision chain and the caveats on reading its ranking.
 *
 * Both halves arrive from the server already written — nothing here composes
 * prose, so what is shown is what actually ran.
 */
export function HowComputed({ reasoning = [], methodNotes = [] }: Props) {
  if (reasoning.length === 0 && methodNotes.length === 0) return null;

  return (
    <Collapse
      ghost
      size="small"
      style={{ marginTop: 12, marginLeft: -12 }}
      items={[
        {
          key: "how",
          label: (
            <Text type="secondary" style={{ fontSize: 12 }}>
              How this was produced — {reasoning.length} decisions,{" "}
              {methodNotes.length} caveats
            </Text>
          ),
          children: (
            <Flex vertical gap={16}>
              {reasoning.length > 0 && <Trace steps={reasoning} />}
              {methodNotes.length > 0 && <Caveats notes={methodNotes} />}
            </Flex>
          ),
        },
      ]}
    />
  );
}

function Trace({ steps }: { steps: ReasoningStep[] }) {
  return (
    <div>
      <Text type="secondary" style={{ fontSize: 12 }}>
        Decisions taken before any number was computed
      </Text>

      <Flex vertical gap={8} style={{ marginTop: 8 }}>
        {steps.map((s, i) => (
          <Flex key={s.step} gap={10} align="flex-start">
            <span
              style={{
                flex: "0 0 18px",
                height: 18,
                borderRadius: 9,
                background: ACCENT,
                color: "#fff",
                fontSize: 11,
                lineHeight: "18px",
                textAlign: "center",
              }}
            >
              {i + 1}
            </span>
            <Text style={{ fontSize: 12 }}>
              <Text strong style={{ fontSize: 12 }}>
                {s.step}
              </Text>{" "}
              <Text type="secondary" style={{ fontSize: 12 }}>
                {s.detail}
              </Text>
            </Text>
          </Flex>
        ))}
      </Flex>
    </div>
  );
}

function Caveats({ notes }: { notes: MethodNote[] }) {
  return (
    <div>
      <Text type="secondary" style={{ fontSize: 12 }}>
        How to read the scores
      </Text>

      <Flex vertical gap={8} style={{ marginTop: 8 }}>
        {notes.map((n, i) => (
          <Flex key={`${n.topic}-${i}`} gap={10} align="flex-start">
            <Tag
              bordered={false}
              style={{ flex: "0 0 auto", fontSize: 11, marginInlineEnd: 0 }}
            >
              {n.topic}
            </Tag>
            <Text type="secondary" style={{ fontSize: 12 }}>
              {n.detail}
            </Text>
          </Flex>
        ))}
      </Flex>
    </div>
  );
}
