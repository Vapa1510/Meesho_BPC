'use client';

/**
 * Creator · Profile. Her Creator DNA with the source of every value (slide 7),
 * the place to correct it, and her Fit Rewards: what she has earned from
 * delivered fit-pick orders, net of returns (slides 4, 5, 12).
 */
import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';

import { ErrorState, Loading, PageHeader } from '@/components/AppShell';
import { useCreators } from '@/components/CreatorContext';
import { DemoGuide } from '@/components/DemoGuide';
import { DnaSummary } from '@/components/DnaSummary';
import { Chip, Toast } from '@/components/ui';
import { api, fmt } from '@/lib/api';
import type { Goal, Niche, Rewards } from '@/lib/types';
import { NMV_NOTE } from '@/lib/types';

const NICHES: Niche[] = ['Skincare', 'Makeup', 'Haircare', 'Personal Care'];
const GOALS: { id: Goal; label: string; note: string }[] = [
  { id: 'reach', label: 'Trend-led', note: 'Reach: rising products that spread' },
  { id: 'revenue', label: 'Commerce-led', note: 'Earnings: products that convert' },
  { id: 'brand', label: 'Brand-led', note: 'Identity: products that fit my positioning' },
];
const GOAL_OF_INTENT: Record<string, Goal> = { 'Trend-led': 'reach', 'Commerce-led': 'revenue', 'Brand-led': 'brand' };

function FitRewardsPanel({ creatorId, name, revision, onChange }: { creatorId: string; name: string; revision: number; onChange: () => void }) {
  const [data, setData] = useState<Rewards | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      setData(await api.rewards(creatorId));
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'Could not load Fit Rewards.');
    }
  }, [creatorId]);

  useEffect(() => {
    void load();
  }, [load, revision]);

  async function order(productId: string, status: 'delivered' | 'returned') {
    setBusy(true);
    setErr(null);
    try {
      await api.order({ creator_id: creatorId, product_id: productId, status });
      await load();
      onChange();
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'Could not record that order.');
    } finally {
      setBusy(false);
    }
  }

  if (!data) return <section className="panel p-6 text-[13px] text-[var(--ink-3)]">{err ?? 'Loading Fit Rewards…'}</section>;
  const a = data.archetype;
  return (
    <section className="panel p-5 sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h2 className="text-[15px] font-semibold">Fit Rewards</h2>
          <p className="text-[12.5px] text-[var(--ink-3)]">Rewards fit, not volume: only picks with a fit score of {data.fit_threshold}+ qualify.</p>
        </div>
        <span className="rounded-full bg-[#fff6e8] px-3 py-1 text-[12px] font-semibold text-[#7a4a00]">{a.name}</span>
      </div>
      <div className="mt-3 rounded-2xl bg-[var(--canvas)] p-3.5 text-[12.5px] text-[var(--ink-2)]">
        <p className="italic">“{a.quote}”</p>
        <p className="mt-1"><b>Needs:</b> {a.needs} · <b>Rewards:</b> {a.reward}</p>
      </div>

      <div className="mt-3 grid grid-cols-3 gap-2 text-center">
        {[
          [data.delivered_fit_orders, 'delivered fit-pick orders'],
          [data.returned_orders, 'returned'],
          [fmt.rupees(data.fit_nmv), 'NMV from fit picks'],
        ].map(([v, l]) => (
          <div key={String(l)} className="rounded-xl border border-[var(--line)] py-2.5">
            <p className="text-[18px] font-bold text-[var(--plum)]">{v}</p>
            <p className="text-[11px] text-[var(--ink-3)]">{l}</p>
          </div>
        ))}
      </div>
      {data.earned.length > 0 ? (
        <ul className="mt-3 space-y-1 text-[12.5px]">
          {data.earned.map((e) => (
            <li key={e.reward} className="flex justify-between gap-3 rounded-xl bg-[#fff6e8] px-3 py-1.5 text-[#7a4a00]">
              <span><b>{e.reward}</b> · {e.basis}</span>
              <span className="font-semibold">×{e.count}</span>
            </li>
          ))}
        </ul>
      ) : null}
      <p className="mt-3 text-[12.5px] text-[var(--ink-2)]">{data.next_step}</p>

      <h3 className="mb-2 mt-5 text-[13px] font-semibold">Promoted products: Click → Order → NMV → Fit Rewards</h3>
      {data.promoted.length === 0 ? (
        <p className="text-[12.5px] text-[var(--ink-3)]">
          Nothing promoted yet. <Link href="/creator" className="font-semibold text-[var(--signal)]">Promote a pick from {name}&apos;s feed</Link>, then
          record an order here to see the loop close.
        </p>
      ) : (
        <ul className="divide-y divide-[var(--line)] rounded-2xl border border-[var(--line)]">
          {data.promoted.map((p) => (
            <li key={p.product_id} className="flex flex-wrap items-center gap-x-3 gap-y-2 px-3.5 py-2.5 text-[12.5px]">
              <span className="min-w-[150px] flex-1">
                <b>{p.title}</b> · {fmt.rupees(p.price)}
                <span className={`ml-2 rounded-full px-2 py-px text-[10.5px] font-semibold ${p.fit_qualified ? 'bg-[#e6f7ef] text-[#0b6b43]' : 'bg-[#f1eef2] text-[var(--ink-3)]'}`}>
                  fit {p.fit_score}{p.fit_qualified ? ' · qualifies' : ' · below 80'}
                </span>
                <span className="block text-[11.5px] text-[var(--ink-3)]">{p.delivered} delivered · {p.returned} returned</span>
              </span>
              <span className="flex gap-1.5">
                <button className="btn-quiet btn-sm" disabled={busy} onClick={() => void order(p.product_id, 'delivered')}>
                  + Delivered order
                </button>
                <button className="btn-quiet btn-sm" disabled={busy || p.delivered <= p.returned} onClick={() => void order(p.product_id, 'returned')}>
                  Return
                </button>
              </span>
            </li>
          ))}
        </ul>
      )}
      {err && <p className="mt-2 text-[12px] text-[var(--signal)]">{err}</p>}
      <p className="mt-3 text-[11px] leading-snug text-[var(--ink-3)]">
        Demo orders: in production they arrive from Meesho&apos;s order service. {NMV_NOTE} Rewards pay on delivered orders, net
        of returns, and are mostly non-cash or brand-funded; amounts are set by the programme or the brand.
      </p>
    </section>
  );
}

export default function ProfilePage() {
  const { current, loading, error, refresh, invalidate, revision } = useCreators();
  const [toast, setToast] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [goal, setGoal] = useState<Goal>('revenue');
  const [pmin, setPmin] = useState(200);
  const [pmax, setPmax] = useState(700);
  const [avoid, setAvoid] = useState<string[]>([]);

  const currentGoal = current ? GOAL_OF_INTENT[current.primary_intent ?? ''] ?? current.goal : 'revenue';

  useEffect(() => {
    if (!current) return;
    setGoal(currentGoal);
    setPmin(current.price_min);
    setPmax(current.price_max);
    setAvoid(current.avoid_categories);
  }, [current, currentGoal]);

  const changed = current
    ? {
        goal: goal !== currentGoal,
        price: pmin !== current.price_min || pmax !== current.price_max,
        avoid: [...avoid].sort().join() !== [...current.avoid_categories].sort().join(),
      }
    : { goal: false, price: false, avoid: false };
  const dirty = changed.goal || changed.price || changed.avoid;

  async function save() {
    if (!current || !dirty) return;
    setBusy(true);
    setErr(null);
    try {
      // Send only what she changed, so saving never rewrites the rest of her DNA.
      await api.updateCreator(current.creator_id, {
        ...(changed.goal ? { goal } : {}),
        ...(changed.price ? { price_min: pmin, price_max: pmax } : {}),
        ...(changed.avoid ? { avoid_categories: avoid } : {}),
      });
      await refresh();
      invalidate();
      setToast('Saved. Her picks re-rank with the corrected DNA.');
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'Could not save.');
    } finally {
      setBusy(false);
    }
  }

  if (error) return <><DemoGuide /><ErrorState message={error} /></>;
  if (loading || !current) return <><DemoGuide /><Loading label="Loading profile" /></>;
  const first = current.name.split(' ')[0];

  return (
    <>
      <DemoGuide />
      <PageHeader
        title={`${first}'s Creator DNA`}
        description="What the engine knows about her, where each value came from, and what she can correct. Saved only after consent."
      />
      {err && <ErrorState message={err} />}
      <div className="pt-4">
        <DnaSummary creator={current} full />
      </div>

      <div className="grid gap-5 px-4 pb-16 pt-5 sm:px-6 lg:grid-cols-2">
        <section className="panel p-5 sm:p-6">
          <h2 className="text-[15px] font-semibold">Correct her DNA</h2>
          <p className="mt-1 text-[12.5px] text-[var(--ink-3)]">
            Only the fields she changes are saved. Correcting the intent makes it primary without discarding the scores the
            onboarding measured.
          </p>
          <div className="mt-4 space-y-5">
            <div>
              <span className="field-label">Primary intent</span>
              <div className="grid gap-2 sm:grid-cols-3">
                {GOALS.map((g) => (
                  <button
                    key={g.id}
                    onClick={() => setGoal(g.id)}
                    className={`rounded-xl border px-3.5 py-2.5 text-left transition-colors ${
                      goal === g.id
                        ? 'border-[var(--signal)] bg-[var(--signal-wash)]'
                        : 'border-[var(--line-strong)] hover:border-[var(--ink-3)]'
                    }`}
                  >
                    <span className="block text-[13px] font-semibold">{g.label}</span>
                    <span className="block text-[11.5px] text-[var(--ink-3)]">{g.note}</span>
                  </button>
                ))}
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <label>
                <span className="field-label">Price from (₹)</span>
                <input type="number" className="field" value={pmin} min={0} onChange={(e) => setPmin(+e.target.value)} />
              </label>
              <label>
                <span className="field-label">Price to (₹)</span>
                <input type="number" className="field" value={pmax} min={0} onChange={(e) => setPmax(+e.target.value)} />
              </label>
            </div>
            <div>
              <span className="field-label">Never show me</span>
              <div className="flex flex-wrap gap-1.5">
                {NICHES.map((n) => (
                  <Chip
                    key={n}
                    active={avoid.includes(n)}
                    onClick={() => setAvoid((a) => (a.includes(n) ? a.filter((x) => x !== n) : [...a, n]))}
                  >
                    {n}
                  </Chip>
                ))}
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <button className="btn" disabled={busy || !dirty || pmin > pmax} onClick={() => void save()}>
                Save changes
              </button>
              {!dirty && <span className="text-[12px] text-[var(--ink-3)]">Nothing changed yet.</span>}
              {pmin > pmax && <span className="text-[12px] text-[var(--signal)]">“From” must not exceed “to”.</span>}
            </div>
          </div>
        </section>

        <FitRewardsPanel creatorId={current.creator_id} name={first} revision={revision} onChange={invalidate} />
      </div>
      <Toast message={toast} onDone={() => setToast(null)} />
    </>
  );
}
