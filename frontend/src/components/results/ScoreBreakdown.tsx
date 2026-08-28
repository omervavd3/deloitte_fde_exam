import { Flex, Tooltip, Typography } from "antd";

import { SERIES_COLORS } from "../../theme";

const { Text } = Typography;

interface Props {
  breakdown: Record<string, Record<string, number>>;
}

export function ScoreBreakdown({ breakdown }: Props) {
  const entries = Object.entries(breakdown);
  if (entries.length === 0) return null;

  return (
    <div style={{ marginTop: 16 }}>
      <Text type="secondary" style={{ fontSize: 12 }}>
        Score composition
      </Text>

      <Flex vertical gap={12} style={{ marginTop: 8 }}>
        {entries.map(([iata, components]) => {
          const total = Object.values(components).reduce((a, b) => a + b, 0);
          const parts = Object.entries(components);

          return (
            <div key={iata}>
              <Flex justify="space-between" style={{ fontSize: 13 }}>
                <Text strong>{iata}</Text>
                <Text>{total.toFixed(1)}</Text>
              </Flex>

              <Flex
                style={{
                  height: 12,
                  borderRadius: 3,
                  overflow: "hidden",
                  margin: "4px 0",
                }}
              >
                {parts.map(([metric, points], i) => (
                  <Tooltip
                    key={metric}
                    title={`${metric}: ${points.toFixed(1)} pts`}
                  >
                    <div
                      style={{
                        width: total > 0 ? `${(points / total) * 100}%` : 0,
                        background: SERIES_COLORS[i % SERIES_COLORS.length],
                      }}
                    />
                  </Tooltip>
                ))}
              </Flex>

              <Flex gap={10} wrap style={{ fontSize: 11 }}>
                {parts.map(([metric, points], i) => (
                  <Text key={metric} type="secondary" style={{ fontSize: 11 }}>
                    <span
                      style={{
                        display: "inline-block",
                        width: 8,
                        height: 8,
                        borderRadius: 2,
                        marginRight: 4,
                        background: SERIES_COLORS[i % SERIES_COLORS.length],
                      }}
                    />
                    {metric} {points.toFixed(1)}
                  </Text>
                ))}
              </Flex>
            </div>
          );
        })}
      </Flex>
    </div>
  );
}
