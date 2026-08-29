import { Alert, Card, Divider, Flex, Tag, Typography } from "antd";

import { ACCENT } from "../../theme";
import type { ChatMessage } from "../../types/chat";
import { HowComputed } from "../results/HowComputed";
import { RankingTable } from "../results/RankingTable";
import { ScoreBreakdown } from "../results/ScoreBreakdown";

const { Text, Paragraph } = Typography;

interface Props {
  message: ChatMessage;
}

export function Message({ message }: Props) {
  if (message.role === "error") {
    return (
      <Alert type="error" showIcon message="Request failed" description={message.content} />
    );
  }

  if (message.role === "user") {
    return (
      <div
        className="pre-wrap"
        style={{
          alignSelf: "flex-end",
          maxWidth: 760,
          background: ACCENT,
          color: "#fff",
          borderRadius: 8,
          padding: "8px 12px",
        }}
      >
        {message.content}
      </div>
    );
  }

  const turn = message.turn;
  const hasNotes =
    !!turn && (turn.assumptions.length > 0 || turn.warnings.length > 0);

  return (
    <Card size="small" style={{ maxWidth: 860, alignSelf: "flex-start" }}>
      <Paragraph className="pre-wrap" style={{ marginBottom: 0 }}>
        {message.content}
      </Paragraph>

      {turn && turn.scores.length > 0 && <RankingTable scores={turn.scores} />}
      {turn && <ScoreBreakdown breakdown={turn.breakdown} />}
      {turn && (
        <HowComputed
          reasoning={turn.reasoning}
          methodNotes={turn.method_notes}
        />
      )}

      {turn && turn.live_conditions.length > 0 && (
        <Flex gap={6} wrap style={{ marginTop: 12 }}>
          {turn.live_conditions.map((c) => (
            <Tag key={c.iata} bordered color="blue">
              {c.iata}
              {c.delay_reason ? ` · ${c.delay_reason}` : ""}
              {c.aircraft_in_area != null
                ? ` · ${c.aircraft_in_area} aircraft`
                : ""}
            </Tag>
          ))}
        </Flex>
      )}

      {hasNotes && turn && (
        <>
          <Divider dashed style={{ margin: "12px 0 8px" }} />
          <Flex vertical gap={2} style={{ fontSize: 12 }}>
            {turn.weights_used && (
              <Text type="secondary">
                <Text strong style={{ fontSize: 12 }}>
                  Profile:
                </Text>{" "}
                {turn.weights_used.profile}
                {turn.weights_used.overridden && " (overridden)"}
              </Text>
            )}
            {turn.assumptions.map((a) => (
              <Text key={a} type="secondary">
                {a}
              </Text>
            ))}
            {turn.warnings.map((w) => (
              <Text key={w} type="danger">
                {w}
              </Text>
            ))}
          </Flex>
        </>
      )}
    </Card>
  );
}
