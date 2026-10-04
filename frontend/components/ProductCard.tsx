'use client';

import { useState } from 'react';

import { FitRing, ProductImage, Star } from '@/components/ui';
import { fmt } from '@/lib/api';
import { REJECTION_REASONS, type Recommendation } from '@/lib/types';

/** A recommendation as a card: the picture, the score, one reason, three actions. */
export function ProductCard({
  rec,
  badge,
  hero = false,
  busy,
  onOpen,
  onAction,
}: {
  rec: Recommendation;
  badge?: string;
  hero?: boolean;
  busy: boolean;
  onOpen: () => void;
  onAction: (action: 'promote' | 'save' | 'skip', reason?: string) => void;
}) {
  const [skipping, setSkipping] = useState(false);

  return (
    <article
      className={`card card-hover flex ${hero ? 'md:col-span-2 md:flex-row' : 'flex-col'}`}
    >
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
        <div className="mt-1.5 flex flex-wrap items-center gap-2 text-[12.5px]">
          <b>{fmt.rupees(rec.price)}</b>
          <Star rating={rec.rating} />
          <span className="text-[var(--ink-3)]">· {rec.trend_stage}</span>
        </div>

        <p className="mt-2.5 flex gap-2 text-[12.5px] leading-snug text-[var(--ink-2)]">
          <span className="text-[var(--green)]">✓</span>
          <span>{rec.reasons[0] ?? 'Strong overall fit'}</span>
        </p>
        {hero && rec.reasons[1] && (
          <p className="mt-1 flex gap-2 text-[12.5px] leading-snug text-[var(--ink-2)]">
            <span className="text-[var(--green)]">✓</span>
            <span>{rec.reasons[1]}</span>
          </p>
        )}
        {hero && (
          <div className="mt-4 rounded-2xl p-4" style={{ background: 'var(--grad)' }}>
            <p className="text-[11px] font-semibold uppercase tracking-wide text-[var(--plum)]/70">
              Suggested content angle
            </p>
            <p className="mt-1 text-[14px] font-semibold leading-snug text-[var(--plum)]">
              {rec.content_angle}
            </p>
          </div>
        )}
        {hero && (
          <div className="mt-4 grid grid-cols-3 gap-2">
            {rec.signals.slice(0, 3).map((sig) => (
              <div key={sig.name} className="rounded-xl bg-[var(--canvas)] px-3 py-2">
                <p className="text-[11px] text-[var(--ink-3)]">{sig.label.replace(' fit', '')}</p>
                <p className="text-[16px] font-bold text-[var(--plum)]">{Math.round(sig.score)}</p>
              </div>
            ))}
          </div>
        )}
        {rec.caveats[0] && (
          <p className="mt-1 flex gap-2 text-[12px] leading-snug text-[var(--ink-3)]">
            <span className="text-[var(--orange)]">!</span>
            <span>{rec.caveats[0]}</span>
          </p>
        )}

        <div className="mt-auto pt-4">
          {skipping ? (
            <div>
              <p className="mb-1.5 text-[11.5px] text-[var(--ink-3)]">Why not?</p>
              <div className="flex flex-wrap gap-1.5">
                {REJECTION_REASONS.map((r) => (
                  <button
                    key={r.value}
                    disabled={busy}
                    onClick={() => onAction('skip', r.value)}
                    className="chip text-[11.5px] transition-colors hover:border-[var(--signal)] hover:text-[var(--signal)]"
                  >
                    {r.label}
                  </button>
                ))}
                <button onClick={() => setSkipping(false)} className="px-2 text-[11.5px] text-[var(--ink-3)]">
                  cancel
                </button>
              </div>
            </div>
          ) : (
            <div className="flex gap-2">
              <button className="btn btn-sm flex-1" disabled={busy} onClick={() => onAction('promote')}>
                Promote
              </button>
              <button className="btn-quiet btn-sm" disabled={busy} onClick={() => onAction('save')}>
                Save
              </button>
              <button className="btn-quiet btn-sm" disabled={busy} onClick={() => setSkipping(true)}>
                Skip
              </button>
            </div>
          )}
        </div>
      </div>
    </article>
  );
}
