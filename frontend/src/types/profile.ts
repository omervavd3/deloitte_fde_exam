/** One weightable metric, as served by GET /api/metrics. */
export interface MetricInfo {
  metric: string;
  label: string;
  formula: string;
  means: string;
  needs_segment: boolean;
}

/** The metric vocabulary. Fetched rather than held here: the agent narrates
 * from the same text, so a copy in the UI could only drift out of agreement. */
export interface MetricCatalog {
  metrics: MetricInfo[];
  redundant_pairs: [string, string][];
}

export interface WeightProfile {
  name: string;
  label: string;
  description: string;
  weights: Record<string, number>;
  is_builtin: boolean;
  updated_at: string;
}

export interface WeightProfileInput {
  name: string;
  label: string;
  description: string;
  weights: Record<string, number>;
}
