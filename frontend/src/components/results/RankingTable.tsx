import { Table, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";

import type { AirportScore } from "../../types/chat";

const { Text } = Typography;

interface Props {
  scores: AirportScore[];
}

const columns: ColumnsType<AirportScore> = [
  { title: "#", dataIndex: "rank", key: "rank", width: 56 },
  {
    title: "Airport",
    key: "airport",
    render: (_, s) => (
      <>
        <Text strong>{s.iata}</Text> <Text type="secondary">{s.name}</Text>
      </>
    ),
  },
  {
    title: "Score",
    dataIndex: "score",
    key: "score",
    width: 96,
    align: "right",
    render: (score: number) => score.toFixed(1),
  },
];

export function RankingTable({ scores }: Props) {
  if (scores.length === 0) return null;

  return (
    <Table
      rowKey="iata"
      size="small"
      columns={columns}
      dataSource={scores}
      pagination={false}
      scroll={{ x: true }}
      style={{ marginTop: 12 }}
    />
  );
}
