/** Presentation helpers for the metric catalog.
 *
 * The descriptions themselves live in app/scoring/glossary.py and arrive over
 * GET /api/metrics - see `MetricCatalog`. Only the formatting is here.
 */
import type { MetricInfo } from "../../types/profile";

/** Compact one-liner for tooltips and slider hints. */
export function metricSummary(info: MetricInfo | undefined): string | null {
  if (!info) return null;
  return `${info.label} — ${info.formula} ${info.means}`;
}

/** Pairs the profile weights on both sides of, and so double-counts.
 *
 * Each pair ranks airports identically, because one is the other divided by a
 * fixed ceiling. Scoring works on percentile rank, so weighting both does not
 * blend two signals - it puts the sum of both weights on one.
 */
export function redundantlyWeighted(
  pairs: [string, string][],
  weights: Record<string, number>,
): [string, string][] {
  return pairs.filter(
    ([a, b]) => (weights[a] ?? 0) > 0 && (weights[b] ?? 0) > 0,
  );
}

/** Metric key -> its description, for lookups while rendering. */
export function byMetric(metrics: MetricInfo[]): Map<string, MetricInfo> {
  return new Map(metrics.map((info) => [info.metric, info]));
}
