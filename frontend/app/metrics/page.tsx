'use client';

/** Metrics — the monitoring numbers, computed from live tables. */
import { useCallback, useEffect, useState } from 'react';

import { ErrorState, Loading, PageHeader } from '@/components/AppShell';
import { useCreators } from '@/components/CreatorContext';
import { api, fmt } from '@/lib/api';
import type { Metrics } from '@/lib/types';

export default function MetricsPage() {
  const { revision } = useCreators();
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      setMetrics(await api.metrics());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load metrics.');
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load, revision]);

  if (error) return <ErrorState message={error} onRetry={load} />;
  if (!metrics) return <Loading label="Loading metrics" />;

  const model = metrics.model_performance;
  const measured = model.ndcg_at_k !== null;

  const tiles = [
    { label: 'Click-through rate', value: fmt.pct(metrics.ctr) },
    { label: 'Conversion of clicks', value: fmt.pct(metrics.conversion_rate) },
    {
      label: 'Recommendation acceptance',
      value: fmt.pct(metrics.recommendation_acceptance),
    },
    { label: 'NMV per creator', value: fmt.rupees(metrics.nmv_per_creator) },
  ];

  const reasons = Object.entries(metrics.rejection_reasons).sort((a, b) => b[1] - a[1]);
  const maxReason = Math.max(1, ...reasons.map(([, count]) => count));

  return (
    <>
      <PageHeader
        title="Metrics"
        description="Computed from the interaction, feedback and evaluation tables as they stand right now."
        actions={
          <button className="btn-quiet btn-sm" onClick={load}>
            Refresh
          </button>
        }
      />

      <div className="space-y-5 p-7">
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {tiles.map((tile) => (
            <div key={tile.label} className="panel px-4 py-3.5">
              <p className="text-[12px] text-[var(--ink-3)]">{tile.label}</p>
              <p className="mono mt-1 text-[24px] font-bold leading-none">{tile.value}</p>
            </div>
          ))}
        </div>

        <div className="grid gap-5 lg:grid-cols-2">
          <section className="panel self-start">
            <div className="panel-head">
              <h2 className="panel-title">Ranking quality</h2>
            </div>
            <div className="px-4 py-4">
              {measured ? (
                <>
                  <table className="dt">
                    <tbody>
                      {[
                        ['NDCG@5', model.ndcg_at_k],
                        ['Precision@5', model.precision_at_k],
                        ['Utility capture', model.utility_capture],
                      ].map(([label, value]) => (
                        <tr key={label as string}>
                          <td className="text-[12.5px]">{label}</td>
                          <td className="mono num text-[13px] font-semibold">
                            {(value as number).toFixed(3)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <p className="mt-3 text-[12px] leading-relaxed text-[var(--ink-2)]">
                    Averaged across {model.creators_evaluated} simulated creator
                    {model.creators_evaluated === 1 ? '' : 's'}, measured against latent
                    preferences the engine never sees.
                  </p>
                </>
              ) : (
                <p className="text-[12.5px] leading-relaxed text-[var(--ink-2)]">
                  No ranking quality to report yet. These need ground truth, which only
                  exists once a simulation has run — so they are left empty rather than
                  filled with a number that would mean nothing. Run a simulation to
                  populate them.
                </p>
              )}
            </div>
          </section>

          <section className="panel self-start">
            <div className="panel-head">
              <h2 className="panel-title">Volumes</h2>
            </div>
            <table className="dt">
              <tbody>
                {Object.entries(metrics.volumes).map(([key, value]) => (
                  <tr key={key}>
                    <td className="text-[12.5px] capitalize">{key.replace(/_/g, ' ')}</td>
                    <td className="mono num text-[12.5px] font-semibold">
                      {typeof value === 'number' ? fmt.int(value) : String(value)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          {reasons.length > 0 && (
            <section className="panel lg:col-span-2">
              <div className="panel-head">
                <div>
                  <h2 className="panel-title">Why creators rejected recommendations</h2>
                  <p className="panel-note">
                    This is the training signal. Each reason moves a different lever in
                    the ranker for that creator.
                  </p>
                </div>
              </div>
              <div className="space-y-2.5 px-4 py-4">
                {reasons.map(([reason, count]) => (
                  <div key={reason} className="flex items-center gap-3">
                    <span className="w-[150px] shrink-0 text-[12.5px] capitalize">
                      {reason.replace(/_/g, ' ')}
                    </span>
                    <span className="meter h-[9px] flex-1">
                      <i
                        style={{
                          width: `${(count / maxReason) * 100}%`,
                          background: 'var(--plum)',
                        }}
                      />
                    </span>
                    <span className="mono w-[34px] shrink-0 text-right text-[12.5px] font-semibold">
                      {count}
                    </span>
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>
      </div>
    </>
  );
}
