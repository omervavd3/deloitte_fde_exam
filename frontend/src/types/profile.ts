/** One weightable metric, as served by GET /api/metrics. */
export interface MetricInfo {
  metric: string;
  label: string;
  formula: string;
  means: string;
  needs_segment: boolean;
}

/** The metric vocabulary. Fetched rather than held here: the backend defines
 * what a metric is and narrates from the same text, so a second copy in the UI
 * could only ever drift out of agreement with the answers. */
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
