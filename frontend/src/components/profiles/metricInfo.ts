/** Plain-English explanation of every scored metric.
 *
 * Mirrors `app.scoring.profiles.METRICS` and the formulas in
 * `app/data/metrics.py` / `app/data/sources/t100_segment.py`. Every metric
 * reads "higher means more investment need" — scoring percentiles each one and
 * rewards the high end.
 *
 * Metrics the backend reports but that are missing here still render, just
 * without a description, so adding a metric server-side never breaks the UI.
 */
export interface MetricInfo {
  /** Human-readable name shown beside the raw metric key. */
  label: string;
  /** One sentence on how it is computed. */
  formula: string;
  /** What a high value implies for investment. */
  meaning: string;
  /** True for metrics that need the optional T-100 Segment extract. */
  needsSegment?: boolean;
}

export const METRIC_INFO: Record<string, MetricInfo> = {
  pax_per_departure: {
    label: "Passengers per departure",
    formula: "Passengers ÷ departures performed.",
    meaning:
      "How full and how large the average departing aircraft is. High values mean each flight pushes more people through the terminal, so gates, security and baggage feel the strain before the airfield does.",
  },
  departures_per_runway: {
    label: "Departures per runway",
    formula: "Annual departures ÷ the airport's runway count.",
    meaning:
      "How hard each runway is worked. High values mean movements are concentrated on few runways — the classic airfield throughput constraint.",
  },
  operations_per_runway: {
    label: "Operations per runway",
    formula:
      "(Departures + arrivals) ÷ the number of runways at least 5,000 ft long.",
    meaning:
      "Airfield loading counted properly: arrivals use the same concrete departures do, and a 2,800 ft general-aviation strip cannot take a scheduled jet. Prefer this over departures per runway unless you need to match an older score.",
  },
  airfield_saturation: {
    label: "Airfield saturation",
    formula:
      "Operations per runway ÷ a planning ceiling of 240,000 operations per runway per year, clipped to 0–1.",
    meaning:
      "How close the airfield runs to its assumed practical capacity, with both directions and usable runways only. A value near 1.0 means the runways are at or beyond what they are assumed to sustain. This is capacity utilization averaged over a year, not measured congestion — peak-hour delay needs a data source this pipeline does not carry.",
  },
  enplanement_volume: {
    label: "Enplanement volume",
    formula: "Total annual boarding passengers (FAA enplanements).",
    meaning:
      "Raw passenger size. Not a constraint on its own, but it scales how much any given bottleneck costs, and it is what FAA hub tiers are derived from.",
  },
  freight_share: {
    label: "Freight share",
    formula:
      "Freight pounds ÷ (freight pounds + passengers × 200 lb), the assumed weight of a passenger plus bags.",
    meaning:
      "How cargo-oriented the airport is once passengers and freight are put on one scale. High values point to warehousing, ramp and logistics investment rather than terminal work.",
  },
  runway_pressure: {
    label: "Runway pressure",
    formula:
      "Departures per runway ÷ a planning ceiling of 120,000 departures per runway per year, clipped to 0–1.",
    meaning:
      "Departures per runway expressed against an assumed practical capacity. A value near 1.0 means the airfield is at or beyond what its runways are assumed to sustain. The ceiling is a planning heuristic, not a measured capacity.",
  },
  mail_share: {
    label: "Mail share",
    formula:
      "Mail pounds ÷ (mail + freight) pounds, left blank below 100,000 lb of combined cargo.",
    meaning:
      "How much of the airport's cargo is postal rather than general freight. High values are communities where air mail is the supply line — the Alaska bypass network, where Bethel moves 17M lb of mail a year. The volume floor stops a field with a few thousand pounds of mail and no freight from outranking a real mail hub on a 0.99 ratio.",
  },
  load_factor: {
    label: "Load factor",
    formula: "Passengers ÷ seats across every segment flown from the airport.",
    meaning:
      "How full aircraft leave. High values mean little slack left to absorb growth, so demand has to be met with more or larger flights rather than fuller ones.",
    needsSegment: true,
  },
  long_haul_share: {
    label: "Long-haul share",
    formula:
      "Share of departures on segments of 2,500 statute miles or more, weighted by departures performed.",
    meaning:
      "How much of the flying is long-distance. High values imply widebody gates, longer turns and heavier fuel and ground-handling demands.",
    needsSegment: true,
  },
  international_share: {
    label: "International share",
    formula:
      "Share of departures to non-US destinations, weighted by departures performed.",
    meaning:
      "How much of the traffic crosses a border. High values drive customs and border halls, international arrivals and sterile-corridor capacity.",
    needsSegment: true,
  },
  schedule_shortfall: {
    label: "Schedule shortfall",
    formula:
      "1 − completion rate, over segments that actually had scheduled service.",
    meaning:
      "The share of scheduled departures that did not fly — the closest public proxy for demand the airport could not serve. High values suggest constraint or reliability problems rather than raw size.",
    needsSegment: true,
  },
};

/** Compact one-liner for tooltips and slider hints. */
export function metricSummary(metric: string): string | null {
  const info = METRIC_INFO[metric];
  if (!info) return null;
  return `${info.label} — ${info.formula} ${info.meaning}`;
}

/** Mirrors `REDUNDANT_METRIC_PAIRS` in app/scoring/profiles.py.
 *
 * Each pair ranks airports identically, because one is the other divided by a
 * fixed ceiling. Scoring works on percentile rank, so weighting both does not
 * blend two signals — it puts the sum of both weights on one.
 */
export const REDUNDANT_METRIC_PAIRS: [string, string][] = [
  ["departures_per_runway", "runway_pressure"],
  ["operations_per_runway", "airfield_saturation"],
];

/** Pairs in `weights` that are both weighted, and so double-counted. */
export function redundantlyWeighted(
  weights: Record<string, number>,
): [string, string][] {
  return REDUNDANT_METRIC_PAIRS.filter(
    ([a, b]) => (weights[a] ?? 0) > 0 && (weights[b] ?? 0) > 0,
  );
}
