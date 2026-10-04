'use client';

/** Screen 2 — Creator Profile. Key details and the intent scores that set weights. */
import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';

import { ErrorNote, Loading, Shell } from '@/components/Shell';
import { api, session } from '@/lib/api';
import type { Creator } from '@/lib/types';

const INTENT_META = [
  { key: 'trend', label: 'Trend', color: '#FD8004' },
  { key: 'commerce', label: 'Commerce', color: '#E8195F' },
  { key: 'brand', label: 'Brand', color: '#7C4FE0' },
] as const;

export default function ProfilePage() {
  const router = useRouter();
  const [creator, setCreator] = useState<Creator | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const creatorId = session.get();
    if (!creatorId) {
      router.replace('/');
      return;
    }
    setError(null);
    try {
      setCreator(await api.getCreator(creatorId));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load your profile.');
    }
  }, [router]);

  useEffect(() => {
    void load();
  }, [load]);

  if (error) {
    return (
      <Shell title="Creator Profile">
        <ErrorNote message={error} onRetry={load} />
      </Shell>
    );
  }
  if (!creator) {
    return (
      <Shell title="Creator Profile">
        <Loading label="Loading your profile" />
      </Shell>
    );
  }

  return (
    <Shell
      title="Creator Profile"
      footer={
        <button className="btn" onClick={() => router.push('/recommendations')}>
          See my Top 5
        </button>
      }
    >
      <div className="space-y-4 pb-2">
        <header className="flex items-center gap-3">
          <div className="flex h-14 w-14 shrink-0 items-center justify-center overflow-hidden rounded-full bg-gradient-to-br from-[#F8C6DA] to-pink ring-2 ring-white">
            <svg viewBox="0 0 24 24" width="46" height="46" aria-hidden="true">
              <circle cx="12" cy="8.5" r="4.6" fill="#FFE4D2" />
              <path d="M3 24c0-6 4-9 9-9s9 3 9 9z" fill="#FFE4D2" />
              <path
                d="M6.6 8.5c0-4 2.4-6 5.4-6s5.4 2 5.4 6c-1-2.2-3-3.2-5.4-3.2S7.6 6.3 6.6 8.5z"
                fill="#3A1830"
              />
            </svg>
          </div>
          <div className="min-w-0">
            <h1 className="truncate text-[17px] font-bold text-plum-deep">{creator.name}</h1>
            <span className="chip mt-1 bg-pink-pale font-semibold text-[#7A0A3A]">
              {creator.tier_label}
            </span>
            <p className="mt-1 text-[13px] font-bold text-plum-deep">
              {creator.followers.toLocaleString('en-IN')}{' '}
              <span className="font-medium text-mute">followers</span>
            </p>
          </div>
        </header>

        <p className="text-[13px] font-semibold text-plum-mid">{creator.bio}</p>

        <dl className="card divide-y divide-[#F4EEF6] px-3 text-[13px]">
          {[
            ['Primary niche', creator.niche],
            ['Audience', creator.audience_label],
            ['Price band', `₹${creator.price_min}–₹${creator.price_max}`],
            ['Goal', creator.goal],
          ].map(([term, value]) => (
            <div key={term} className="flex justify-between py-2">
              <dt className="text-mute">{term}</dt>
              <dd className="font-semibold capitalize">{value}</dd>
            </div>
          ))}
        </dl>

        <section className="space-y-2">
          <h2 className="label">Creator intent scores</h2>
          <p className="text-[11px] leading-snug text-mute">
            These set how your Top 5 is weighted. A commerce-led creator and a
            trend-led creator see the same catalogue ranked differently.
          </p>
          <ul className="space-y-2 pt-1">
            {INTENT_META.map((meta) => {
              const value = creator.intent_scores[meta.key];
              return (
                <li key={meta.key} className="flex items-center gap-2 text-[13px]">
                  <span className="w-[76px] shrink-0 font-semibold">{meta.label}</span>
                  <span className="bar">
                    <span style={{ width: `${value}%`, background: meta.color }} />
                  </span>
                  <span className="w-[26px] shrink-0 text-right font-bold">{value}</span>
                </li>
              );
            })}
          </ul>
        </section>

        {creator.avoid_categories.length > 0 && (
          <section className="space-y-2">
            <h2 className="label">Excluded categories</h2>
            <div className="flex flex-wrap gap-2">
              {creator.avoid_categories.map((category) => (
                <span key={category} className="chip bg-[#F1EEF6] text-sub">
                  {category}
                </span>
              ))}
            </div>
          </section>
        )}

        <button
          className="w-full pt-2 text-[12px] font-medium text-mute underline underline-offset-2"
          onClick={() => {
            session.clear();
            router.push('/');
          }}
        >
          Start over with a different creator
        </button>
      </div>
    </Shell>
  );
}
