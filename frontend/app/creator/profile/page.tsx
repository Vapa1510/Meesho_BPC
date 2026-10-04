'use client';

/** Creator · Profile. The signals the engine reads, editable, plus onboarding
 *  for a brand-new creator. */
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

import { ErrorState, Loading, PageHeader } from '@/components/AppShell';
import { useCreators } from '@/components/CreatorContext';
import { Avatar, Chip, Toast } from '@/components/ui';
import { api, fmt } from '@/lib/api';
import type { Goal, Niche } from '@/lib/types';

const NICHES: Niche[] = ['Skincare', 'Makeup', 'Haircare', 'Personal Care'];
const GOALS: { id: Goal; label: string; note: string }[] = [
  { id: 'reach', label: 'Trend-led', note: 'Reach: rising products that spread' },
  { id: 'revenue', label: 'Commerce-led', note: 'Earnings: products that convert' },
  { id: 'brand', label: 'Brand-led', note: 'Identity: products that fit my positioning' },
];

function IntentBar({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div>
      <div className="flex justify-between text-[12px]">
        <span className="font-medium">{label}</span>
        <span className="text-[var(--ink-3)]">{value}</span>
      </div>
      <div className="mt-1 h-[7px] overflow-hidden rounded-full bg-[#f6ebf1]">
        <div className="h-full rounded-full" style={{ width: `${value}%`, background: color }} />
      </div>
    </div>
  );
}

export default function ProfilePage() {
  const { current, loading, error, refresh, invalidate } = useCreators();
  const router = useRouter();
  const [toast, setToast] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // edit
  const [goal, setGoal] = useState<Goal>('revenue');
  const [pmin, setPmin] = useState(200);
  const [pmax, setPmax] = useState(700);
  const [avoid, setAvoid] = useState<string[]>([]);

  useEffect(() => {
    if (!current) return;
    setGoal(current.goal);
    setPmin(current.price_min);
    setPmax(current.price_max);
    setAvoid(current.avoid_categories);
  }, [current]);

  async function save() {
    if (!current) return;
    setBusy(true);
    setErr(null);
    try {
      await api.updateCreator(current.creator_id, {
        goal,
        price_min: pmin,
        price_max: pmax,
        avoid_categories: avoid,
      });
      await refresh();
      invalidate();
      setToast('Profile updated. Your picks will re-rank.');
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'Could not save.');
    } finally {
      setBusy(false);
    }
  }

  if (error) return <ErrorState message={error} />;
  if (loading || !current) return <Loading label="Loading profile" />;

  return (
    <>
      <PageHeader
        title="Profile"
        description="The Creator DNA the engine reads, with where each value came from. Correct anything and the picks re-rank."
      />
      {err && <ErrorState message={err} />}

      <div className="grid gap-5 px-6 pb-16 pt-5 lg:grid-cols-[360px_1fr]">
        <section className="panel p-6">
          <div className="flex items-center gap-4">
            <Avatar name={current.name} seed={current.creator_id} size={64} />
            <div>
              <h2 className="text-[18px] font-bold tracking-[-0.02em] text-[var(--plum)]">{current.name}</h2>
              <p className="text-[12.5px] text-[var(--ink-3)]">
                {current.tier_label} · {fmt.compact(current.followers)} followers
              </p>
            </div>
          </div>
          <p className="mt-4 text-[13px] leading-relaxed text-[var(--ink-2)]">{current.bio}</p>
          <dl className="mt-5 space-y-2.5 text-[13px]">
            {[
              ['Niche', current.niche],
              ['Audience', current.audience_label],
              ['Price', `${current.preferred_price ? `~₹${current.preferred_price} · ` : ''}₹${current.price_min}–₹${current.price_max}`],
              ['Tier', current.scale ?? ''],
              ['Engagement', fmt.pct(current.engagement_rate)],
            ].map(([k, v]) => (
              <div key={k} className="flex justify-between border-b border-[var(--line)] pb-2">
                <dt className="text-[var(--ink-3)]">{k}</dt>
                <dd className="font-medium">{v}</dd>
              </div>
            ))}
          </dl>
          <h3 className="mb-3 mt-6 text-[12.5px] font-semibold">Intent scores</h3>
          <div className="space-y-3">
            <IntentBar label="Trend (reach)" value={current.intent_scores.trend} color="#7B4FE0" />
            <IntentBar label="Commerce (conversions)" value={current.intent_scores.commerce} color="#E8195F" />
            <IntentBar label="Brand (identity)" value={current.intent_scores.brand} color="#F28C1C" />
          </div>
          <p className="mt-3 text-[11.5px] leading-relaxed text-[var(--ink-3)]">
            The primary intent and the follower tier pick this creator&apos;s cell in the 3×3 matrix:{' '}
            <b className="text-[var(--plum)]">{current.cell}</b>. That cell sets how the seven fit signals are weighted.
          </p>
          {current.dna_sources && (
            <div className="mt-5">
              <h3 className="mb-2 text-[12.5px] font-semibold">Creator DNA sources</h3>
              <ul className="space-y-1.5 text-[12px]">
                {Object.entries(current.dna_sources).map(([k, v]) => (
                  <li key={k} className="flex justify-between gap-3 border-b border-[var(--line)] pb-1.5">
                    <span className="capitalize text-[var(--ink-3)]">{k}</span>
                    <span className="text-right font-medium">{v}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </section>

        <div className="space-y-5">
          <section className="panel p-6">
            <h2 className="text-[15px] font-semibold">Edit preferences</h2>
            <div className="mt-4 grid gap-5 md:grid-cols-2">
              <div>
                <span className="field-label">Primary intent (correct it if we got it wrong)</span>
                <div className="space-y-2">
                  {GOALS.map((g) => (
                    <button
                      key={g.id}
                      onClick={() => setGoal(g.id)}
                      className={`w-full rounded-xl border px-3.5 py-2.5 text-left transition-colors ${
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
              <div className="space-y-4">
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
                  <span className="field-label">Hide categories</span>
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
                <button className="btn" disabled={busy || pmin > pmax} onClick={() => void save()}>
                  Save changes
                </button>
              </div>
            </div>
          </section>

          <section className="panel p-6">
            <h2 className="text-[15px] font-semibold">Onboard a new creator</h2>
            <p className="mt-1 text-[12.5px] text-[var(--ink-3)]">
              Connect a profile and answer a few indirect questions: 5–8 for an emerging creator, 3–5 for a growth
              creator, and 0–2 taps for an established one. The engine never asks for a &ldquo;goal&rdquo; directly.
            </p>
            <button className="btn mt-4" onClick={() => router.push('/creator/onboard')}>
              Start onboarding
            </button>
          </section>
        </div>
      </div>
      <Toast message={toast} onDone={() => setToast(null)} />
    </>
  );
}
