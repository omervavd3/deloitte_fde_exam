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
