'use client';

/** A creator's Creator DNA at a glance, each value tagged with its source (slide 7). */
import Link from 'next/link';

import type { Creator } from '@/lib/types';

export function SourceTag({ source }: { source?: string | null }) {
  if (!source) return null;
  const tone = source.startsWith('Asked')
    ? 'bg-[var(--signal-wash)] text-[var(--signal)]'
    : source.startsWith('Corrected')
      ? 'bg-[#fff3df] text-[#8a5a00]'
      : source.startsWith('Default')
        ? 'bg-[#f1eef2] text-[var(--ink-3)]'
        : 'bg-[#efe6f6] text-[var(--plum)]';
  return (
    <span className={`inline-block whitespace-nowrap rounded-full px-2 py-px text-[10px] font-semibold ${tone}`}>
      {source}
    </span>
  );
}

const INTENT_ROWS = [
  { key: 'trend', label: 'Trend', color: '#F28C1C' },
  { key: 'commerce', label: 'Commerce', color: '#E8195F' },
  { key: 'brand', label: 'Brand', color: '#7B4FE0' },
] as const;

export function DnaSummary({ creator, full = false }: { creator: Creator; full?: boolean }) {
  const src = creator.dna_sources ?? {};
  const shares = Object.entries(creator.niche_shares ?? {}).filter(([k]) => k !== 'Other');
  const positioning = Object.entries(creator.positioning ?? {}).sort((a, b) => b[1] - a[1]);
  const rows: { k: string; v: string; s?: string }[] = [
    {
      k: 'Niche',
      v: shares.length ? shares.map(([n, v]) => `${n} ${Math.round(v * 100)}%`).join(' · ') : creator.niche,
      s: src.niche,
    },
    {
      k: 'Price',
      v: `${creator.preferred_price ? `~₹${creator.preferred_price} preferred · ` : ''}₹${creator.price_min}–₹${creator.price_max}`,
      s: src.price,
    },
    {
      k: 'Audience',
      v: `${creator.audience_age_min}–${creator.audience_age_max} · ${creator.audience_tiers.map((t) => t.replace('T', 'Tier ')).join('/')}`,
      s: src.audience,
    },
  ];
  if (creator.content_formats?.length) rows.push({ k: 'Content', v: creator.content_formats.join(' · '), s: src.content });
  if (positioning.length)
    rows.push({
      k: 'Positioning',
      v: positioning.map(([p, v]) => `${p[0].toUpperCase()}${p.slice(1)} ${v.toFixed(2).replace(/^0/, '')}`).join(' · '),
      s: src.positioning,
    });

  return (
    <section className={`mx-4 rounded-[22px] border border-[var(--line)] bg-white p-4 sm:mx-6 ${full ? '' : 'mt-3'}`}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="text-[14px] font-bold text-[var(--plum)]">Creator DNA</h2>
          <span className="rounded-full bg-[var(--plum)] px-2.5 py-0.5 text-[11px] font-semibold text-white">
            {creator.cell}
          </span>
          <span className="text-[11.5px] text-[var(--ink-3)]">
            {creator.tier_label} · {(creator.followers / 1000).toFixed(1).replace('.0', '')}K followers
          </span>
        </div>
        {!full && (
          <Link href="/creator/profile" className="text-[12.5px] font-semibold text-[var(--signal)]">
            Open full Creator DNA →
          </Link>
        )}
      </div>

      <div className="mt-3 grid gap-4 md:grid-cols-[minmax(0,260px)_1fr]">
        <div>
          <div className="mb-1.5 flex items-center justify-between">
            <span className="text-[11.5px] font-semibold text-[var(--ink-3)]">Intent</span>
            <SourceTag source={src.intent} />
          </div>
          {INTENT_ROWS.map((r) => {
            const v = creator.intent_scores[r.key];
            const primary = creator.primary_intent?.toLowerCase().startsWith(r.key);
            return (
              <div key={r.key} className="mb-1 flex items-center gap-2 text-[12px]">
                <span className="w-[68px] font-medium">{r.label}</span>
                <span className="h-[7px] flex-1 overflow-hidden rounded-full bg-[#f6ebf1]">
                  <span className="block h-full rounded-full" style={{ width: `${v}%`, background: r.color }} />
                </span>
                <span className="w-[34px] text-right font-semibold">{(v / 100).toFixed(2)}</span>
                <span className="w-[48px] text-right text-[10px] font-semibold text-[var(--signal)]">{primary ? 'Primary' : ''}</span>
              </div>
            );
          })}
          {creator.intent_separation != null && (
            <p className="mt-1 text-[10.5px] text-[var(--ink-3)]">
              Separation {creator.intent_separation.toFixed(2)}
              {creator.intent_separation >= 0.25 ? ': clear, no follow-up needed' : ': close call'}
            </p>
          )}
        </div>
        <dl className="grid gap-x-5 gap-y-2 sm:grid-cols-2">
          {rows.map((r) => (
            <div key={r.k} className="min-w-0 border-b border-[var(--line)] pb-1.5">
              <dt className="flex items-center justify-between gap-2 text-[11px] font-semibold text-[var(--ink-3)]">
                {r.k}
                <SourceTag source={r.s} />
              </dt>
              <dd className="mt-0.5 text-[12.5px] font-semibold text-[var(--ink)]">{r.v}</dd>
            </div>
          ))}
        </dl>
      </div>
      {creator.dna_sources && (
        <p className="mt-2 text-[11px] text-[var(--ink-3)]">
          Saved only after consent. Promotes, saves and skips re-rank the picks but never rewrite this DNA; only{' '}
          {creator.name.split(' ')[0]} can correct it, on the Profile page.
        </p>
      )}
    </section>
  );
}
