'use client';

/**
 * Engine lab · Trust metrics. The deck's trust and quality metrics (slide 9)
 * and scale gates (slide 12), measured live from what this prototype has
 * served, next to the deck's targets. Modelled impact numbers are shown as
 * targets, never as results.
 */
import { useCallback, useEffect, useState } from 'react';

import { ErrorState, Loading, PageHeader } from '@/components/AppShell';
import { useCreators } from '@/components/CreatorContext';
import { api, fmt } from '@/lib/api';
import type { Metrics, Trust, TrustMetric } from '@/lib/types';
import { NMV_NOTE } from '@/lib/types';

function show(m: TrustMetric): string {
  if (m.value === null) return '—';
  if (m.unit === 'share') return fmt.pct(m.value, 0);
  if (m.unit === 'ms') return `${m.value.toFixed(0)} ms`;
  return m.value.toFixed(1);
}

function Status({ ok }: { ok: boolean | null }) {
  if (ok === null) return <span className="text-[11.5px] text-[var(--ink-3)]">no data yet</span>;
  return ok ? (
    <span className="whitespace-nowrap rounded-full bg-[#e6f7ef] px-2 py-0.5 text-[11px] font-semibold text-[#0b6b43]">meets target</span>
  ) : (
    <span className="whitespace-nowrap rounded-full bg-[#fff3df] px-2 py-0.5 text-[11px] font-semibold text-[#8a5a00]">below target</span>
  );
}

const MODELLED = [
  ['NMV per active creator', '+11.5%', '2.6 → 2.9 promotions × 8 orders × ₹400 AOV: ₹8,320 → ₹9,280 a month'],
  ['Return rate on promoted items', '−13%', '6.0% → 5.2% from better fit (quality, listing and logistics still drive returns)'],
  ['Time to first order, new creators', '~41% faster', 'Starter-5 on day one from declared niche + intent: 8.5 → 5 days (midpoint)'],
  ['Catalogue search effort per selection', '−30%', 'Products browsed per successful selection: index 100 → 70'],
  ['Recommendation adoption', '+20–30%', 'Creators promoting ≥ 1 recommended pick ÷ creators shown picks'],
  ['Product-mix diversity', '+15–20%', 'Distinct category × price-band × niche combinations promoted'],
];

export default function MetricsPage() {
  const { revision } = useCreators();
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [trust, setTrust] = useState<Trust | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [m, t] = await Promise.all([api.metrics(), api.trust()]);
      setMetrics(m);
      setTrust(t);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load metrics.');
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load, revision]);

  if (error) return <ErrorState message={error} onRetry={load} />;
  if (!metrics || !trust) return <Loading label="Loading metrics" />;

  const reasons = Object.entries(metrics.rejection_reasons).sort((a, b) => b[1] - a[1]);
  const maxReason = Math.max(1, ...reasons.map(([, count]) => count));

  return (
    <>
      <PageHeader
        title="Trust metrics"
        description="How the engine would be judged before it scales: the deck's trust, quality and reliability metrics, measured live on this prototype's sample data and shown next to the deck's targets."
        actions={
          <button className="btn-quiet btn-sm" onClick={load}>
            Refresh
          </button>
        }
      />

      <div className="space-y-5 px-4 py-6 sm:px-6">
        <section className="panel">
          <div className="panel-head">
            <div>
              <h2 className="panel-title">Trust & quality (slides 9 and 12)</h2>
              <p className="panel-note">
                {trust.picks_shown} picks shown across {trust.slates_served} slates so far. {trust.note}
              </p>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="dt min-w-[720px]">
              <thead>
                <tr>
                  <th>Metric</th>
                  <th>Formula</th>
                  <th className="num">Now</th>
                  <th>Target</th>
                  <th>Status</th>
                  <th>Evidence</th>
                </tr>
              </thead>
              <tbody>
                {trust.metrics.map((m) => (
                  <tr key={m.metric}>
                    <td className="text-[12.5px] font-semibold">{m.metric}</td>
                    <td className="text-[12px] text-[var(--ink-2)]">{m.formula}</td>
                    <td className="mono num text-[13px] font-semibold">{show(m)}</td>
                    <td className="text-[12px]">{m.target}</td>
                    <td><Status ok={m.ok} /></td>
                    <td className="text-[11.5px] text-[var(--ink-3)]">{m.evidence}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="px-4 pb-4 pt-3 text-[11.5px] leading-relaxed text-[var(--ink-3)]">
            Precision@5 comes only from synthetic creators in the Simulation tab, whose hidden preferences deliberately
            drift from what they declared: it checks the mechanism, it is not creator performance. Mix diversity is tracked,
            not enforced (a roadmap item). Availability (&gt;99%) needs an uptime monitor and is measured in the pilot.
          </p>
        </section>

        <section className="panel">
          <div className="panel-head">
            <div>
              <h2 className="panel-title">Modelled targets (team hypotheses, not results)</h2>
              <p className="panel-note">
                Projections from the deck. Nothing here has been observed; the 12-week pilot reports test minus control.
              </p>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="dt min-w-[620px]">
              <thead>
                <tr>
                  <th>Target</th>
                  <th className="num">Modelled</th>
                  <th>How it is built</th>
                </tr>
              </thead>
              <tbody>
                {MODELLED.map(([k, v, how]) => (
                  <tr key={k}>
                    <td className="text-[12.5px] font-semibold">{k}</td>
                    <td className="mono num text-[13px] font-semibold">{v}</td>
                    <td className="text-[12px] text-[var(--ink-2)]">{how}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="px-4 pb-4 pt-3 text-[11.5px] leading-relaxed text-[var(--ink-3)]">
            <b>Funnel ≠ NMV case.</b> The funnel uplift (+25% clicks, +39% add-to-cart, +33% orders per 1,000 product views)
            describes product-page conversion. The +11.5% NMV case does not use it: it holds orders per promotion at 8 and AOV
            at ₹400 and counts only +0.30 promotions per creator a month, so any conversion gain would be upside. {NMV_NOTE}
          </p>
        </section>

        <div className="grid gap-5 lg:grid-cols-2">
          <section className="panel self-start">
            <div className="panel-head">
              <div>
                <h2 className="panel-title">Live counters (sample data)</h2>
                <p className="panel-note">From the interaction and feedback tables as they stand now.</p>
              </div>
            </div>
            <table className="dt">
              <tbody>
                {[
                  ['Click-through rate', fmt.pct(metrics.ctr)],
                  ['Conversion of clicks', fmt.pct(metrics.conversion_rate)],
                  ['Recommendation acceptance (promote + save ÷ decided)', fmt.pct(metrics.recommendation_acceptance)],
                  ['NMV per creator (sample)', fmt.rupees(metrics.nmv_per_creator)],
                  ...Object.entries(metrics.volumes).map(([k, v]) => [k.replace(/_/g, ' '), typeof v === 'number' ? fmt.int(v) : String(v)]),
                ].map(([k, v]) => (
                  <tr key={k}>
                    <td className="text-[12.5px] first-letter:uppercase">{k}</td>
                    <td className="mono num text-[12.5px] font-semibold">{v}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          <section className="panel self-start">
            <div className="panel-head">
              <div>
                <h2 className="panel-title">Why creators skipped</h2>
                <p className="panel-note">Each reason moves a different lever in the ranker for that creator, and the brand sees it.</p>
              </div>
            </div>
            {reasons.length === 0 ? (
              <p className="px-4 py-4 text-[12.5px] text-[var(--ink-3)]">No skips yet.</p>
            ) : (
              <div className="space-y-2.5 px-4 py-4">
                {reasons.map(([reason, count]) => (
                  <div key={reason} className="flex items-center gap-3">
                    <span className="w-[150px] shrink-0 text-[12.5px] capitalize">{reason.replace(/_/g, ' ')}</span>
                    <span className="meter h-[9px] flex-1">
                      <i style={{ width: `${(count / maxReason) * 100}%`, background: 'var(--plum)' }} />
                    </span>
                    <span className="mono w-[34px] shrink-0 text-right text-[12.5px] font-semibold">{count}</span>
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>
      </div>
    </>
  );
}
