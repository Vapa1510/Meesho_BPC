'use client';

/** Insights — the monitoring metrics from the deck, read live from the API. */
import { useCallback, useEffect, useState } from 'react';

import { ErrorNote, Loading, Shell } from '@/components/Shell';
import { api } from '@/lib/api';

interface Metrics {
  ctr: number;
  conversion_rate: number;
  recommendation_acceptance: number;
  nmv_per_creator: number;
  model_performance: { auc: number | null; ndcg: number | null; status: string };
  volumes: Record<string, number>;
  actions: Record<string, number>;
  rejection_reasons: Record<string, number>;
}

const PCT = (value: number) => `${(value * 100).toFixed(1)}%`;

export default function InsightsPage() {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      setMetrics((await api.metrics()) as unknown as Metrics);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load metrics.');
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (error) {
    return (
      <Shell title="Insights">
        <ErrorNote message={error} onRetry={load} />
      </Shell>
    );
  }
  if (!metrics) {
    return (
      <Shell title="Insights">
        <Loading label="Loading metrics" />
      </Shell>
    );
  }

  const tiles = [
    { label: 'CTR', value: PCT(metrics.ctr) },
    { label: 'Conversion', value: PCT(metrics.conversion_rate) },
    { label: 'Acceptance', value: PCT(metrics.recommendation_acceptance) },
    {
      label: 'NMV / creator',
      value: `₹${Math.round(metrics.nmv_per_creator).toLocaleString('en-IN')}`,
    },
  ];

  const reasons = Object.entries(metrics.rejection_reasons);
  const maxReason = Math.max(1, ...reasons.map(([, count]) => count));

  return (
    <Shell title="Insights">
      <div className="space-y-4 pb-2">
        <div>
          <h1 className="text-[15px] font-bold text-plum-deep">Monitoring</h1>
          <p className="text-[11px] text-mute">
            Computed from the live interaction and feedback tables.
          </p>
        </div>

        <div className="grid grid-cols-2 gap-2">
          {tiles.map((tile) => (
            <div key={tile.label} className="card p-3">
              <p className="text-[11px] text-mute">{tile.label}</p>
              <p className="text-[18px] font-bold leading-tight text-plum-deep">{tile.value}</p>
            </div>
          ))}
        </div>

        <section className="card space-y-1.5 p-3">
          <h2 className="text-[12px] font-bold text-plum">Model performance</h2>
          <p className="text-[12px] leading-snug text-sub">
            AUC and NDCG need a held-out set and a trained ranker. The MVP runs on
            weighted rules, so these are reported as{' '}
            <b className="text-navy">{metrics.model_performance.status.replace(/_/g, ' ')}</b>{' '}
            rather than filled in.
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="label">Volumes</h2>
          <dl className="card divide-y divide-[#F4EEF6] px-3 text-[12.5px]">
            {Object.entries(metrics.volumes).map(([key, value]) => (
              <div key={key} className="flex justify-between py-1.5">
                <dt className="capitalize text-mute">{key.replace(/_/g, ' ')}</dt>
                <dd className="font-semibold">{value.toLocaleString('en-IN')}</dd>
              </div>
            ))}
          </dl>
        </section>

        {reasons.length > 0 && (
          <section className="space-y-2">
            <h2 className="label">Why creators said no</h2>
            <ul className="space-y-1.5">
              {reasons
                .sort((a, b) => b[1] - a[1])
                .map(([reason, count]) => (
                  <li key={reason} className="flex items-center gap-2 text-[12px]">
                    <span className="w-[108px] shrink-0 capitalize text-navy">
                      {reason.replace(/_/g, ' ')}
                    </span>
                    <span className="bar">
                      <span
                        style={{ width: `${(count / maxReason) * 100}%`, background: '#E8195F' }}
                      />
                    </span>
                    <span className="w-[20px] text-right font-bold">{count}</span>
                  </li>
                ))}
            </ul>
            <p className="text-[10.5px] leading-snug text-mute">
              This is the training signal. Each rejection reason moves a different
              lever in the ranker for that creator.
            </p>
          </section>
        )}
      </div>
    </Shell>
  );
}
