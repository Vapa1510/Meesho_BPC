'use client';

/**
 * Creator · Discover. The engine's top picks for the selected creator, as
 * cards with the product picture, the fit score and one reason. Acting on a
 * card (promote / save / skip with a reason) feeds the closed loop, and the
 * slate is re-ranked straight away.
 */
import { useCallback, useEffect, useState } from 'react';

import { ErrorState, Loading, PageHeader } from '@/components/AppShell';
import { useCreators } from '@/components/CreatorContext';
import { ProductCard } from '@/components/ProductCard';
import { ProductDrawer } from '@/components/ProductDrawer';
import { Toast } from '@/components/ui';
import { api, fmt } from '@/lib/api';
import type { RecommendationsResponse } from '@/lib/types';
import { INTENT_LABEL, TOP_K_BY_SCALE } from '@/lib/types';

export default function DiscoverPage() {
  const { current, loading, error: creatorsError, invalidate, revision } = useCreators();
  const [data, setData] = useState<RecommendationsResponse | null>(null);
  const [open, setOpen] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!current) return;
    setError(null);
    try {
      setData(await api.recommendations(current.creator_id, TOP_K_BY_SCALE[current.scale ?? 'Growth'] ?? 8));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load recommendations.');
    }
  }, [current]);

  useEffect(() => {
    setData(null);
    void load();
  }, [load, revision]);

  async function act(productId: string, score: number, action: 'promote' | 'save' | 'skip', reason?: string) {
    if (!current) return;
    setBusy(true);
    try {
      const res = await api.feedback({
        creator_id: current.creator_id,
        product_id: productId,
        action,
        reason: reason ?? null,
        served_score: score,
      });
      setToast(res.message);
      setOpen(null);
      invalidate();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not record that.');
    } finally {
      setBusy(false);
    }
  }

  if (creatorsError) return <ErrorState message={creatorsError} />;
  if (loading || !current) return <Loading label="Loading creators" />;

  const recs = data?.recommendations ?? [];
  const active = recs.find((r) => r.product_id === open) ?? null;

  return (
    <>
      <PageHeader
        title={`Picks for ${current.name.split(' ')[0]}`}
        description="Products ranked for this creator's Creator DNA: audience, niche, intent and price. Open one to see exactly where its score came from."
        actions={
          <button className="btn-quiet btn-sm" onClick={() => void load()} disabled={!data}>
            Refresh
          </button>
        }
      />

      <div className="flex flex-wrap items-center gap-2 px-6 pb-5 pt-3">
        <span className="chip">{current.niche}</span>
        <span className="chip">{current.cell ?? INTENT_LABEL[current.goal]}</span>
        <span className="chip">
          {current.preferred_price ? `~₹${current.preferred_price} · ` : ''}₹{current.price_min}–₹{current.price_max}
        </span>
        <span className="chip">
          audience {current.audience_age_min}–{current.audience_age_max}
        </span>
        {data && (
          <span className="ml-auto text-[12px] text-[var(--ink-3)]">
            {fmt.int(data.pipeline.catalogue_size)} products →{' '}
            <b className="text-[var(--ink-2)]">{fmt.int(data.pipeline.eligible_count)}</b> eligible →{' '}
            <b className="text-[var(--signal)]">top {recs.length}</b>
          </span>
        )}
      </div>

      {data && data.learning_notes.length > 0 && (
        <div className="mx-6 mb-5 flex flex-wrap items-center gap-2 rounded-2xl bg-[var(--signal-wash)] px-4 py-3">
          <span className="text-[12px] font-semibold text-[var(--signal)]">Learning from you</span>
          {data.learning_notes.map((n) => (
            <span key={n} className="rounded-full bg-white px-2.5 py-0.5 text-[11.5px] text-[var(--ink-2)]">
              {n}
            </span>
          ))}
        </div>
      )}

      {error && <ErrorState message={error} onRetry={load} />}
      {!error && !data && <Loading label="Finding your best fits" />}

      {data && (
        <div className="grid gap-5 px-6 pb-16 md:grid-cols-2 xl:grid-cols-3">
          {recs.map((rec, i) => (
            <ProductCard
              key={rec.product_id}
              rec={rec}
              hero={i === 0}
              badge={i === 0 ? 'Top pick' : `#${rec.rank}`}
              busy={busy}
              onOpen={() => setOpen(rec.product_id)}
              onAction={(a, reason) => void act(rec.product_id, rec.fit_score, a, reason)}
            />
          ))}
        </div>
      )}

      {active && (
        <ProductDrawer
          rec={active}
          forName={current.name.split(' ')[0]}
          busy={busy}
          onClose={() => setOpen(null)}
          onAction={(a, reason) => void act(active.product_id, active.fit_score, a, reason)}
        />
      )}
      <Toast message={toast} onDone={() => setToast(null)} />
    </>
  );
}
