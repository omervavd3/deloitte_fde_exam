export type Intent = "rank" | "compare" | "metric" | "explain" | "out_of_scope";

export interface AirportScore {
  iata: string;
  name: string;
  score: number;
  rank: number;
  metrics: Record<string, number>;
}

export interface WeightsUsed {
  profile: string;
  weights: Record<string, number>;
  overridden: boolean;
}

export interface LiveStatus {
  iata: string;
  delay_reason?: string | null;
  aircraft_in_area?: number | null;
}

export interface ChatResponse {
  conversation_id: string;
  message: string;
  intent: Intent;
  scores: AirportScore[];
  breakdown: Record<string, Record<string, number>>;
  weights_used?: WeightsUsed | null;
  live_conditions: LiveStatus[];
  assumptions: string[];
  warnings: string[];
  provenance: Record<string, unknown>;
}

export interface Conversation {
  id: string;
  title: string;
  created_at?: string;
  updated_at?: string;
}

export interface ChatMessage {
  role: "user" | "assistant" | "error";
  content: string;
  turn?: ChatResponse;
}
