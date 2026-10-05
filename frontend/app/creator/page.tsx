'use client';

/**
 * Creator · Discover. Two of the deck's QR codes open this page (slide 7
 * "Creator DNA Profile" and slide 8 "Brand Match + Feedback Loop"), so it
 * leads with the walkthrough and Riya's Creator DNA, then her ranked picks.
 * Every promote / save / skip (with reason) re-ranks the slate immediately,
 * and the page says exactly what moved.
 */
import Link from 'next/link';
import { useCallback, useEffect, useRef, useState } from 'react';

import { ErrorState, Loading, PageHeader } from '@/components/AppShell';
import { useCreators } from '@/components/CreatorContext';
import { DemoGuide } from '@/components/DemoGuide';
import { DnaSummary } from '@/components/DnaSummary';
import { ProductCard } from '@/components/ProductCard';
import { ProductDrawer } from '@/components/ProductDrawer';
import { Toast } from '@/components/ui';
import { api, fmt } from '@/lib/api';
import type { RecommendationsResponse } from '@/lib/types';
import { REASON_LABEL, TOP_K_LABEL } from '@/lib/types';

type Snapshot = Map<string, { title: string; score: number; rank: number }>;

function snapshot(d: RecommendationsResponse): Snapshot {
  return new Map(d.recommendations.map((r) => [r.product_id, { title: r.title, score: r.fit_score, rank: r.rank }]));
}

/** What one tap changed, in plain words, for the "it re-ranked" banner.
 *  `leftScores` holds the new score of anything that dropped out of the list. */
function diff(before: Snapshot, after: Snapshot, leftScores: Map<string, number>): string[] {
  const out: string[] = [];
  before.forEach((b, id) => {
    if (!after.has(id)) {
      const now = leftScores.get(id);
      out.push(`${b.title} ${now !== undefined ? `${b.score} → ${now}, ` : ''}dropped out of the list`);
    }
  });
  after.forEach((a, id) => {
    const b = before.get(id);
    if (!b) out.push(`${a.title} joined at #${a.rank}`);
    else if (b.score !== a.score) out.push(`${a.title} ${b.score} → ${a.score}${b.rank !== a.rank ? ` (#${b.rank} → #${a.rank})` : ''}`);
    else if (b.rank !== a.rank) out.push(`${a.title} #${b.rank} → #${a.rank}`);
  });
  return out;
}

export default function DiscoverPage() {
  const { current, loading, error: creatorsError, invalidate, revision } = useCreators();
  const [data, setData] = useState<RecommendationsResponse | null>(null);
  const [open, setOpen] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const [changes, setChanges] = useState<{ action: string; items: string[] } | null>(null);
  const before = useRef<{ snap: Snapshot; action: string } | null>(null);
  const bannerRef = useRef<HTMLDivElement>(null);

  // Bring the "what changed" banner into view: on a phone the tap usually
  // happens far down the list, where the banner would otherwise go unseen.
  useEffect(() => {
    if (changes) bannerRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }, [changes]);

  const load = useCallback(async () => {
    if (!current) return;
    setError(null);
    try {
      const next = await api.recommendations(current.creator_id);
      if (before.current) {
        const prev = before.current;
        before.current = null;
        const after = snapshot(next);
        const left = [...prev.snap.keys()].filter((id) => !after.has(id));
        const leftScores = new Map<string, number>();
        if (left.length) {
          try {
            for (const r of await api.rankProducts(current.creator_id, left)) leftScores.set(r.product_id, r.fit_score);
          } catch {
            /* the banner just omits the new score */
          }
        }
        setChanges({ action: prev.action, items: diff(prev.snap, after, leftScores) });
      }
      setData(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load recommendations.');
    }
  }, [current]);

  useEffect(() => {
    void load();
  }, [load, revision]);

  useEffect(() => {
    setData(null);
    setChanges(null);
  }, [current?.creator_id]);

  async function act(productId: string, score: number, source: string, action: 'promote' | 'save' | 'skip', reason?: string) {
    if (!current) return;
    setBusy(true);
    try {
      const title = data?.recommendations.find((r) => r.product_id === productId)?.title ?? 'that pick';
      if (data) {
        before.current = {
          snap: snapshot(data),
          action:
            action === 'skip'
              ? `You skipped ${title} (${REASON_LABEL[reason ?? ''] ?? reason})`
              : action === 'promote'
                ? `You promoted ${title}`
                : `You saved ${title}`,
        };
      }
      const res = await api.feedback({
        creator_id: current.creator_id,
        product_id: productId,
        action,
        reason: reason ?? null,
        served_score: score,
        source,
      });
      setToast(res.message);
      setOpen(null);
      invalidate();
    } catch (err) {
      before.current = null;
      setError(err instanceof Error ? err.message : 'Could not record that.');
    } finally {
      setBusy(false);
    }
  }

  if (creatorsError) return <><DemoGuide /><ErrorState message={creatorsError} /></>;
  if (loading || !current) return <><DemoGuide /><Loading label="Loading creators" /></>;

  const recs = data?.recommendations ?? [];
  const active = recs.find((r) => r.product_id === open) ?? null;
  const first = current.name.split(' ')[0];
  const scale = current.scale ?? 'Growth';
  const kLabel = TOP_K_LABEL[scale] ?? `Top ${recs.length}`;

  return (
    <>
      <DemoGuide />
      <PageHeader
        title={`${first}'s ${kLabel}`}
        description={`Ranked by the Fit Engine for ${first}'s Creator DNA. Open any pick for the full breakdown: the seven signals, the checks it passed and the Fit Rewards it can earn.`}
        actions={
          <button className="btn-quiet btn-sm" onClick={() => void load()} disabled={!data}>
            Refresh
          </button>
        }
      />

      <DnaSummary creator={current} />

      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 px-4 pb-4 pt-3 text-[12.5px] text-[var(--ink-3)] sm:px-6">
        {data ? (
          <>
            <span>
              <b className="text-[var(--ink-2)]">{fmt.int(data.pipeline.catalogue_size)}</b> listings →{' '}
              <b className="text-[var(--ink-2)]">{fmt.int(data.pipeline.eligible_count)}</b> pass the gates →{' '}
              <b className="text-[var(--signal)]">{kLabel}</b>
            </span>
            <Link href="/lab/pipeline" className="font-semibold text-[var(--signal)]">
              See what each gate removed →
            </Link>
          </>
        ) : (
          <span>Ranking the catalogue…</span>
        )}
      </div>

      {scale === 'Emerging' && (
        <p className="mx-4 mb-4 rounded-2xl bg-[#f3eefb] px-4 py-3 text-[12.5px] leading-relaxed text-[var(--plum)] sm:mx-6">
          <b>Starter-5 (cold start).</b> With little history, day-one picks come from the niche and intent {first} declared
          in onboarding. As she promotes, saves and skips, her own behaviour takes over from the declared signals.
        </p>
      )}

      {changes && (
        <div ref={bannerRef} role="status" className="mx-4 mb-4 scroll-mt-28 rounded-2xl border border-[#f3d3e2] bg-white px-4 py-3 sm:mx-6">
          <div className="flex items-start justify-between gap-3">
            <p className="text-[12.5px] font-semibold text-[var(--plum)]">
              {changes.action}. The list re-ranked straight away:
            </p>
            <button className="text-[12px] text-[var(--ink-3)] hover:text-[var(--signal)]" onClick={() => setChanges(null)}>
              Close
            </button>
          </div>
          {changes.items.length ? (
            <ul className="mt-1.5 flex flex-wrap gap-1.5">
              {changes.items.slice(0, 6).map((c) => (
                <li key={c} className="rounded-full bg-[var(--signal-wash)] px-2.5 py-0.5 text-[12px] text-[var(--ink)]">
                  {c}
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-1 text-[12px] text-[var(--ink-2)]">No score in this list moved; the signal is stored for the next ranking.</p>
          )}
          <p className="mt-2 text-[11.5px] leading-snug text-[var(--ink-3)]">
            Feedback re-ranks immediately within bounds (×0.62 to ×1.15, fading with a 45-day half-life). It never rewrites
            the Creator DNA; a periodic DNA refresh is Phase 2.{' '}
            {current.niche === 'Skincare' && (
              <Link href="/brand/product/P009" className="font-semibold text-[var(--signal)]">
                See what the brand sees →
              </Link>
            )}
          </p>
        </div>
      )}

      {data && data.learning_notes.length > 0 && (
        <div className="mx-4 mb-5 flex flex-wrap items-center gap-2 rounded-2xl bg-[var(--signal-wash)] px-4 py-3 sm:mx-6">
          <span className="text-[12px] font-semibold text-[var(--signal)]">Learning from {first}</span>
          {data.learning_notes.map((n) => (
            <span key={n} className="rounded-full bg-white px-2.5 py-0.5 text-[11.5px] text-[var(--ink-2)]">
              {n}
            </span>
          ))}
        </div>
      )}

      {error && <ErrorState message={error} onRetry={load} />}
      {!error && !data && <Loading label="Finding the best fits" />}

      {data && (
        <div className="grid gap-4 px-4 pb-16 sm:gap-5 sm:px-6 md:grid-cols-2 xl:grid-cols-3">
          {recs.map((rec, i) => (
            <ProductCard
              key={rec.product_id}
              rec={rec}
              hero={i === 0}
              badge={i === 0 ? 'Top pick' : `#${rec.rank}`}
              busy={busy}
              priceBand={[current.price_min, current.price_max]}
              onOpen={() => setOpen(rec.product_id)}
              onAction={(a, reason) => void act(rec.product_id, rec.fit_score, rec.source, a, reason)}
            />
          ))}
        </div>
      )}

      {active && (
        <ProductDrawer
          rec={active}
          forName={first}
          busy={busy}
          onClose={() => setOpen(null)}
          onAction={(a, reason) => void act(active.product_id, active.fit_score, active.source, a, reason)}
        />
      )}
      <Toast message={toast} onDone={() => setToast(null)} />
    </>
  );
}
