'use client';

import { useState } from 'react';

import { FitRing, ProductImage, Star } from '@/components/ui';
import { fmt } from '@/lib/api';
import { REJECTION_REASONS, type Recommendation } from '@/lib/types';

/** Where the price sits against the creator's band, said plainly. */
export function PriceBandNote({ price, band }: { price: number; band?: [number, number] }) {
  if (!band) return null;
  const [lo, hi] = band;
  if (price >= lo && price <= hi) {
    return <span className="text-[var(--green)]" title={`Your band is ₹${lo}–₹${hi}`}>in your band</span>;
  }
  return (
    <span className="font-semibold text-[#b25d00]" title="Allowed by the price window, scored lower by price comfort">
      {price > hi ? 'above' : 'below'} your ₹{lo}–₹{hi} band
    </span>
  );
}

export function SkipReasons({
  busy,
  onPick,
  onCancel,
  prompt = 'Skip (with reason): why not this one?',
}: {
  busy: boolean;
  onPick: (reason: string) => void;
  onCancel?: () => void;
  prompt?: string;
}) {
  return (
    <div>
      <p className="mb-1.5 text-[11.5px] text-[var(--ink-3)]">{prompt}</p>
      <div className="flex flex-wrap gap-1.5">
        {REJECTION_REASONS.map((r) => (
          <button
            key={r.value}
            disabled={busy}
            onClick={() => onPick(r.value)}
            className="chip text-[11.5px] transition-colors hover:border-[var(--signal)] hover:text-[var(--signal)]"
          >
            {r.label}
          </button>
        ))}
        {onCancel && (
          <button onClick={onCancel} className="px-2 text-[11.5px] text-[var(--ink-3)]">
            cancel
          </button>
        )}
      </div>
    </div>
  );
}

/** A recommendation as a card: the picture, the score, why it fits, three actions. */
export function ProductCard({
  rec,
  badge,
  hero = false,
  busy,
  priceBand,
  onOpen,
  onAction,
}: {
  rec: Recommendation;
  badge?: string;
  hero?: boolean;
  busy: boolean;
  priceBand?: [number, number];
  onOpen: () => void;
  onAction: (action: 'promote' | 'save' | 'skip', reason?: string) => void;
}) {
  const [skipping, setSkipping] = useState(false);
  const drivers = rec.top_drivers ?? [];

  return (
    <article className={`card card-hover flex flex-col ${hero ? 'md:col-span-2 md:flex-row' : ''}`}>
      <button
        onClick={onOpen}
        aria-label={`Open ${rec.title}`}
        className={`relative block text-left ${hero ? 'md:w-1/2' : ''}`}
      >
        <ProductImage
          src={rec.image}
          alt={rec.title}
          className={`w-full ${hero ? 'aspect-[4/3] md:h-full md:aspect-auto' : 'aspect-[4/3]'}`}
        />
        {badge && (
          <span className="absolute left-3 top-3 rounded-full bg-[var(--signal)] px-3 py-1 text-[12px] font-bold text-white shadow">
            {badge}
          </span>
        )}
        <span className="absolute right-3 top-3 flex rounded-full bg-white p-0.5 shadow-md">
          <FitRing score={rec.fit_score} size={hero ? 58 : 48} />
        </span>
      </button>

      <div className={`flex min-w-0 flex-1 flex-col p-4 ${hero ? 'md:p-6' : ''}`}>
        <p className="text-[11.5px] font-medium text-[var(--ink-3)]">{rec.brand}</p>
        <button onClick={onOpen} className="text-left">
          <h3
            className={`font-semibold leading-snug tracking-[-0.01em] text-[var(--ink)] ${
              hero ? 'text-[20px]' : 'text-[15px]'
            }`}
          >
            {rec.title}
          </h3>
        </button>
        <div className="mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[12.5px]">
          <b>{fmt.rupees(rec.price)}</b>
          <span className="text-[11.5px]">
            <PriceBandNote price={rec.price} band={priceBand} />
          </span>
          <Star rating={rec.rating} />
          <span className="text-[var(--ink-3)]">· {rec.trend_stage}</span>
        </div>

        <p className="mt-3 text-[11px] font-semibold uppercase tracking-wide text-[var(--ink-3)]">Why this product?</p>
        <ul className="mt-1 space-y-1">
          {rec.reasons.slice(0, hero ? 3 : 2).map((r) => (
            <li key={r} className="flex gap-2 text-[12.5px] leading-snug text-[var(--ink-2)]">
              <span className="text-[var(--green)]">✓</span>
              <span>{r}</span>
            </li>
          ))}
        </ul>
        {drivers.length > 0 && (
          <p className="mt-1.5 text-[11.5px] leading-snug text-[var(--ink-3)]">
            Biggest drivers:{' '}
            {drivers.map((d, i) => (
              <span key={d.label}>
                {i > 0 && ' · '}
                <b className="text-[var(--ink-2)]">{d.label.replace(' fit', '')}</b> +{d.points.toFixed(1)}
              </span>
            ))}
          </p>
        )}

        {hero && (
          <div className="mt-4 rounded-2xl p-4" style={{ background: 'var(--grad)' }}>
            <p className="text-[11px] font-semibold uppercase tracking-wide text-[var(--plum)]/70">
              Suggested content angle
            </p>
            <p className="mt-1 text-[14px] font-semibold leading-snug text-[var(--plum)]">{rec.content_angle}</p>
          </div>
        )}
        {rec.caveats[0] && (
          <p className="mt-1.5 flex gap-2 text-[12px] leading-snug text-[var(--ink-3)]">
            <span className="text-[var(--orange)]">!</span>
            <span>{rec.caveats[0]}</span>
          </p>
        )}
        {rec.rewards?.length > 0 && (
          <p className="mt-2 rounded-xl bg-[#fff6e8] px-3 py-1.5 text-[11.5px] leading-snug text-[#7a4a00]">
            <b>Fit Rewards:</b> {rec.rewards.join(' · ').toLowerCase().replace(/^./, (c) => c.toUpperCase())}
          </p>
        )}

        <div className="mt-auto pt-4">
          {skipping ? (
            <SkipReasons busy={busy} onPick={(r) => onAction('skip', r)} onCancel={() => setSkipping(false)} />
          ) : (
            <div className="flex flex-wrap gap-2">
              <button className="btn btn-sm flex-1" disabled={busy} onClick={() => onAction('promote')}>
                Promote
              </button>
              <button className="btn-quiet btn-sm" disabled={busy} onClick={() => onAction('save')}>
                Save
              </button>
              <button className="btn-quiet btn-sm" disabled={busy} onClick={() => setSkipping(true)}>
                Skip (with reason)
              </button>
            </div>
          )}
        </div>
      </div>
    </article>
  );
}
