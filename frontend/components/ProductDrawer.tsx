'use client';

/** Side panel: everything the engine knows about one creator-product pair. */
import { useEffect, useState } from 'react';

import { SkipReasons } from '@/components/ProductCard';
import { FitRing, ProductImage, Star } from '@/components/ui';
import { fmt } from '@/lib/api';
import { SIGNAL_HELP, type Check, type Recommendation } from '@/lib/types';

export function SignalBars({ signals, explain = false }: { signals: Recommendation['signals']; explain?: boolean }) {
  return (
    <ul className="space-y-2.5">
      {signals.map((s) => (
        <li key={s.name}>
          <div className="flex items-baseline justify-between gap-3 text-[12.5px]">
            <span className="font-medium">{s.label.replace(' fit', '')}</span>
            <span className="whitespace-nowrap text-[var(--ink-3)]">
              <span className="font-semibold text-[var(--ink)]">{Math.round(s.score)}</span>
              <span className="mx-1.5">×</span>
              {s.weight.toFixed(2)}
              <span className="mx-1.5">=</span>
              <span className="font-semibold text-[var(--signal)]">+{s.contribution.toFixed(1)}</span>
            </span>
          </div>
          <div className="mt-1 h-[7px] overflow-hidden rounded-full bg-[#f6ebf1]">
            <div
              className="h-full rounded-full"
              style={{
                width: `${Math.min(100, s.score)}%`,
                background: 'linear-gradient(90deg, #ff8fb4, #e8195f)',
                transition: 'width 450ms cubic-bezier(.22,1,.36,1)',
              }}
            />
          </div>
          {explain && SIGNAL_HELP[s.name] && (
            <p className="mt-1 text-[11px] leading-snug text-[var(--ink-3)]">{SIGNAL_HELP[s.name]}</p>
          )}
        </li>
      ))}
    </ul>
  );
}

export function Formula({ rec }: { rec: Recommendation }) {
  return (
    <p className="rounded-xl bg-[var(--canvas)] px-3.5 py-2.5 text-[12px] leading-relaxed text-[var(--ink-2)]">
      <b>{rec.base_score.toFixed(1)}</b> weighted total
      {(rec.penalty_saturation ?? 0) > 0 && <> − <b>{(rec.penalty_saturation ?? 0).toFixed(1)}</b> crowding</>}
      {(rec.penalty_returns ?? 0) > 0 && <> − <b>{(rec.penalty_returns ?? 0).toFixed(1)}</b> return risk</>}
      {rec.learning_multiplier !== 1 && (
        <>
          {' '}
          × <b>{rec.learning_multiplier.toFixed(2)}</b> learned from her feedback
        </>
      )}{' '}
      = <b className="text-[var(--signal)]">{rec.fit_score}</b>
      {rec.cell && <span className="block text-[11px] text-[var(--ink-3)]">Weights from her cell: {rec.cell}</span>}
    </p>
  );
}

export function Checks({ checks, eligible }: { checks: Check[]; eligible: boolean }) {
  return (
    <section>
      <h3 className="mb-2 text-[13px] font-semibold">
        {eligible ? 'Passed every eligibility check' : 'Not in the feed: an eligibility check failed'}
      </h3>
      <ul className="space-y-1.5">
        {checks.map((c) => (
          <li key={c.rule} className="flex items-start justify-between gap-3 text-[12.5px]">
            <span className="flex gap-2 text-[var(--ink-2)]">
              <span className={c.passed ? 'text-[var(--green)]' : 'text-[var(--signal)]'}>{c.passed ? '✓' : '✕'}</span>
              {c.label}
            </span>
            <span className="shrink-0 font-semibold text-[var(--ink)]">{c.value}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

export function ProductDrawer({
  rec,
  forName,
  busy,
  onClose,
  onAction,
}: {
  rec: Recommendation;
  forName: string;
  busy: boolean;
  onClose: () => void;
  onAction: (action: 'promote' | 'save' | 'skip', reason?: string) => void;
}) {
  const [skipping, setSkipping] = useState(false);

  useEffect(() => {
    setSkipping(false);
  }, [rec.product_id]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-40 flex justify-end">
      <button
        aria-label="Close"
        onClick={onClose}
        className="absolute inset-0 bg-[rgba(42,21,48,0.28)] backdrop-blur-[1px]"
      />
      <aside
        role="dialog"
        aria-label={rec.title}
        className="relative h-full w-full max-w-[500px] overflow-y-auto bg-white shadow-[-24px_0_60px_-20px_rgba(81,14,68,0.35)]"
      >
        <div className="relative">
          <ProductImage src={rec.image} alt={rec.title} className="aspect-[16/10] w-full" />
          <button
            onClick={onClose}
            aria-label="Close"
            className="absolute right-4 top-4 flex h-9 w-9 items-center justify-center rounded-full bg-white/90 text-[var(--ink)] shadow hover:text-[var(--signal)]"
          >
            ✕
          </button>
          <div className="absolute -bottom-7 right-5 flex rounded-full bg-white p-1 shadow-md">
            <FitRing score={rec.fit_score} size={64} />
          </div>
        </div>

        <div className="space-y-6 px-5 pb-8 pt-5 sm:px-6">
          <div className="pr-20">
            <p className="text-[12px] font-medium text-[var(--ink-3)]">{rec.brand}</p>
            <h2 className="text-[20px] font-bold leading-tight tracking-[-0.02em] text-[var(--plum)]">{rec.title}</h2>
            <div className="mt-2 flex flex-wrap items-center gap-2.5 text-[13px]">
              <b>{fmt.rupees(rec.price)}</b>
              <Star rating={rec.rating} />
              <span className="chip">{rec.category}</span>
              <span className="chip">{rec.trend_stage}</span>
            </div>
          </div>

          <div className="rounded-2xl p-4" style={{ background: 'var(--grad)' }}>
            <p className="text-[11.5px] font-semibold uppercase tracking-wide text-[var(--plum)]/70">
              Content angle for {forName}
            </p>
            <p className="mt-1 text-[14px] font-semibold leading-snug text-[var(--plum)]">{rec.content_angle}</p>
          </div>

          <section>
            <h3 className="mb-2 text-[13px] font-semibold">Why this product?</h3>
            {rec.top_drivers?.length > 0 && (
              <div className="mb-3 grid grid-cols-3 gap-2">
                {rec.top_drivers.map((d) => (
                  <div key={d.label} className="rounded-xl bg-[var(--canvas)] px-3 py-2">
                    <p className="text-[11px] text-[var(--ink-3)]">{d.label.replace(' fit', '')}</p>
                    <p className="text-[16px] font-bold text-[var(--plum)]">+{d.points.toFixed(1)}</p>
                    <p className="text-[10.5px] text-[var(--ink-3)]">
                      {Math.round(d.score)} × {d.weight.toFixed(2)}
                    </p>
                  </div>
                ))}
              </div>
            )}
            <ul className="space-y-1.5">
              {rec.reasons.map((r) => (
                <li key={r} className="flex gap-2 text-[13px] leading-relaxed text-[var(--ink-2)]">
                  <span className="mt-[2px] text-[var(--green)]">✓</span>
                  {r}
                </li>
              ))}
              {rec.caveats.map((c) => (
                <li key={c} className="flex gap-2 text-[13px] leading-relaxed text-[var(--ink-2)]">
                  <span className="mt-[2px] text-[var(--orange)]">!</span>
                  {c}
                </li>
              ))}
            </ul>
          </section>

          {rec.rewards?.length > 0 ? (
            <section className="rounded-2xl bg-[#fff6e8] p-4">
              <h3 className="text-[13px] font-semibold text-[#7a4a00]">Fit Rewards on this pick</h3>
              <ul className="mt-1.5 space-y-1 text-[12.5px] text-[#7a4a00]">
                {rec.rewards.map((r) => (
                  <li key={r}>• {r}</li>
                ))}
              </ul>
              <p className="mt-2 text-[11px] leading-snug text-[#8a6a3a]">
                Fit-qualified (fit 80+). Rewards pay on delivered orders, net of returns, and are mostly non-cash or
                brand-funded.
              </p>
            </section>
          ) : (
            <p className="text-[12px] text-[var(--ink-3)]">
              Fit Rewards start at a fit score of 80; this pick scores {rec.fit_score}.
            </p>
          )}

          <section className="space-y-3">
            <h3 className="text-[13px] font-semibold">How the score adds up: seven signals</h3>
            <SignalBars signals={rec.signals} explain />
            <Formula rec={rec} />
          </section>

          {rec.checks?.length > 0 && <Checks checks={rec.checks} eligible={rec.eligible} />}

          <section className="border-t border-[var(--line)] pt-5">
            <div className="flex flex-wrap gap-2">
              <button className="btn" disabled={busy || !rec.eligible} onClick={() => onAction('promote')}>
                Promote
              </button>
              <button className="btn-quiet" disabled={busy} onClick={() => onAction('save')}>
                Save
              </button>
              <button className="btn-quiet" disabled={busy} onClick={() => setSkipping((s) => !s)}>
                Skip (with reason)
              </button>
            </div>
            {skipping && (
              <div className="mt-3">
                <SkipReasons
                  busy={busy}
                  onPick={(r) => onAction('skip', r)}
                  prompt="Why? Each reason teaches the ranker something different, and the brand sees it."
                />
              </div>
            )}
          </section>
        </div>
      </aside>
    </div>
  );
}
