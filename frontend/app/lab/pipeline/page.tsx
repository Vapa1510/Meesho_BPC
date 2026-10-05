'use client';

/** Pipeline — what Stage 1 removed and why, measured rather than claimed. */
import { useCallback, useEffect, useState } from 'react';

import { ErrorState, Loading, PageHeader } from '@/components/AppShell';
import { useCreators } from '@/components/CreatorContext';
import { Funnel } from '@/components/Viz';
import { api, fmt } from '@/lib/api';
import type { RecommendationsResponse } from '@/lib/types';

const RULE_COPY: Record<string, string> = {
  category: 'Outside the requested category',
  price_range: 'Priced far outside what this audience pays',
  stock_serviceable: 'Out of stock or not serviceable',
  quality_threshold: 'Below the rating floor (3.8; seller rating for new listings)',
  return_rate: 'Returns above the category median',
  audience_fit: 'Built for a different audience (audience fit < 0.5)',
  policy_compliant: 'Listing not policy compliant',
  creator_excluded: 'In a category the creator excluded',
  already_promoted: 'Already promoted by this creator',
};

export default function PipelinePage() {
  const { current, loading, revision } = useCreators();
  const [data, setData] = useState<RecommendationsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!current) return;
    setError(null);
    setData(null);
    try {
      setData(await api.recommendations(current.creator_id));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load the pipeline.');
    }
  }, [current]);

  useEffect(() => {
    void load();
  }, [load, revision]);

  if (loading || !current) return <Loading label="Loading creators" />;

  return (
    <>
      <PageHeader
        title="Pipeline"
        description={`Every listing in the catalogue, filtered down to the slate ${current.name} actually sees. Stage 1 is hard, auditable rules; Stage 2 orders candidates by deterministic similarity; the ranker scores what survives with explainable weighted rules. MVP = explainable rules + deterministic retrieval; production = a learned retriever and ranker behind the same interface.`}
      />

      {error && <ErrorState message={error} onRetry={load} />}
      {!error && !data && <Loading label="Running the pipeline" />}

      {data && (
        <div className="grid gap-5 px-6 py-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
          <section className="panel self-start">
            <div className="panel-head">
              <h2 className="panel-title">Funnel</h2>
              <span className="mono text-[11.5px] text-[var(--ink-3)]">
                {fmt.pct(data.pipeline.pool_ratio, 0)} eligible
              </span>
            </div>
            <div className="px-4 py-4">
              <Funnel
                stages={[
                  {
                    label: 'Catalogue',
                    value: data.pipeline.catalogue_size,
                    note: 'Every BPC product in the store',
                  },
                  {
                    label: 'Stage 1 — eligible',
                    value: data.pipeline.eligible_count,
                    note: 'Passed every hard rule for this creator',
                  },
                  {
                    label: 'Stage 2 — candidates',
                    value: data.pipeline.candidate_count,
                    note:
                      data.pipeline.candidate_count === data.pipeline.eligible_count
                        ? 'Ordered by similarity. The candidate cap does not bind at this catalogue size — every eligible product reaches the ranker.'
                        : 'Retrieved by similarity, ordered for the ranker',
                  },
                  {
                    label: 'Served',
                    value: data.recommendations.length,
                    note: 'Scored, ranked and shown',
                  },
                ]}
              />
            </div>
          </section>

          <section className="panel self-start">
            <div className="panel-head">
              <div>
                <h2 className="panel-title">Removed by rule</h2>
                <p className="panel-note">
                  Stage 1 decisions are hard and auditable — a product either may
                  be shown to this creator or it may not.
                </p>
              </div>
            </div>
            <table className="dt">
              <thead>
                <tr>
                  <th>Rule</th>
                  <th className="w-[80px] text-right">Removed</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(data.pipeline.rejected_by_rule).length === 0 && (
                  <tr>
                    <td colSpan={2} className="text-[12.5px] text-[var(--ink-3)]">
                      Nothing was removed for this creator.
                    </td>
                  </tr>
                )}
                {Object.entries(data.pipeline.rejected_by_rule)
                  .sort((a, b) => b[1].length - a[1].length)
                  .map(([rule, ids]) => (
                    <tr key={rule}>
                      <td>
                        <span className="block text-[12.5px] font-medium">
                          {RULE_COPY[rule] ?? rule.replace(/_/g, ' ')}
                        </span>
                        <span className="mono block text-[11px] text-[var(--ink-3)]">
                          {rule}
                        </span>
                      </td>
                      <td className="mono num text-[13px] font-semibold">{ids.length}</td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </section>

          <section className="panel lg:col-span-2">
            <div className="panel-head">
              <h2 className="panel-title">How the slate was built</h2>
            </div>
            <ol className="divide-y divide-[var(--line)]">
              {[
                {
                  name: 'Stage 1 — eligibility',
                  body: 'Correct category, price window, in stock and serviceable, rating ≥ 3.8 (seller rating for new listings), returns at or below the category median, policy compliant, audience fit ≥ 0.5, not excluded and not already promoted. Cheap, hard, and logged by rule.',
                },
                {
                  name: 'Stage 2 — retrieval',
                  body: 'Orders the eligible pool into a candidate set (capped at 200) by blending a deterministic hashed text similarity with category match and momentum. This is the MVP: explainable and model-free. Production swaps in a learned encoder with a pgvector nearest-neighbour index; the interface stays the same.',
                },
                {
                  name: 'Ranking',
                  body: "Seven signals scored 0–100, weighted by this creator's cell in the 3×3 matrix (scale × primary intent), minus a crowding and a return-risk penalty, then any learned adjustment.",
                },
              ].map((step, index) => (
                <li key={step.name} className="flex gap-4 px-4 py-3.5">
                  <span className="mono mt-[2px] shrink-0 text-[12px] font-semibold text-[var(--signal)]">
                    {index + 1}
                  </span>
                  <div className="max-w-[80ch]">
                    <p className="text-[13px] font-semibold">{step.name}</p>
                    <p className="mt-0.5 text-[12.5px] leading-relaxed text-[var(--ink-2)]">
                      {step.body}
                    </p>
                  </div>
                </li>
              ))}
            </ol>
          </section>
        </div>
      )}
    </>
  );
}
