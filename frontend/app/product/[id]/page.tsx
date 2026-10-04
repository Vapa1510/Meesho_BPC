'use client';

/**
 * Screen 4 — Why this product + Feedback.
 *
 * This is the screen the whole pitch rests on: the creator sees the score, the
 * signals behind it, the caveats, and a content angle — then accepts or rejects
 * it with a reason that changes the next ranking.
 */
import { useParams, useRouter } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';

import { ConfidencePill, SignalBars, TrendPill, fitColor } from '@/components/Fit';
import { ProductThumb } from '@/components/ProductArt';
import { ErrorNote, Loading, Shell } from '@/components/Shell';
import { api, session } from '@/lib/api';
import { REJECTION_REASONS, type Recommendation } from '@/lib/types';

export default function ProductPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const productId = params.id;

  const [rec, setRec] = useState<Recommendation | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [rejecting, setRejecting] = useState(false);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<{ message: string; notes: string[] } | null>(null);

  const load = useCallback(async () => {
    const creatorId = session.get();
    if (!creatorId) {
      router.replace('/');
      return;
    }
    setError(null);
    try {
      const [scored] = await api.rankProducts(creatorId, [productId]);
      setRec(scored);
      // Opening the detail is a click, and clicks are part of the loop.
      void api.feedback({
        creator_id: creatorId,
        product_id: productId,
        action: 'click',
        served_score: scored.fit_score,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not score this product.');
    }
  }, [productId, router]);

  useEffect(() => {
    void load();
  }, [load]);

  async function send(action: 'promote' | 'save' | 'skip', reason?: string) {
    const creatorId = session.get();
    if (!creatorId || !rec) return;
    setBusy(true);
    try {
      const response = await api.feedback({
        creator_id: creatorId,
        product_id: productId,
        action,
        reason: reason ?? null,
        served_score: rec.fit_score,
      });
      setResult({ message: response.message, notes: response.learning_notes });
      setRejecting(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save your feedback.');
    } finally {
      setBusy(false);
    }
  }

  if (error) {
    return (
      <Shell title="Why this product?" onBack={() => router.back()}>
        <ErrorNote message={error} onRetry={load} />
      </Shell>
    );
  }
  if (!rec) {
    return (
      <Shell title="Why this product?" onBack={() => router.back()}>
        <Loading label="Scoring this product" />
      </Shell>
    );
  }

  if (result) {
    return (
      <Shell title="Feedback" onBack={() => router.push('/recommendations')}>
        <div className="space-y-4 py-6 text-center">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-[#E4F7EA]">
            <svg width="28" height="28" viewBox="0 0 24 24" aria-hidden="true">
              <path
                d="M4 12.5l5 5L20 6.5"
                fill="none"
                stroke="#19B364"
                strokeWidth="3.4"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
          <p className="text-[15px] font-bold text-plum-deep">{result.message}</p>
          {result.notes.length > 0 && (
            <div className="card space-y-1 p-3 text-left">
              <p className="text-[11px] font-bold text-plum">What changed for you</p>
              {result.notes.map((note) => (
                <p key={note} className="text-[12px] leading-snug text-sub">
                  · {note}
                </p>
              ))}
            </div>
          )}
          <button className="btn" onClick={() => router.push('/recommendations')}>
            Back to my Top 5
          </button>
        </div>
      </Shell>
    );
  }

  return (
    <Shell
      title="Why this product?"
      onBack={() => router.back()}
      footer={
        rejecting ? (
          <div className="space-y-2">
            <p className="label">Tell us why it is not a fit</p>
            <div className="flex flex-wrap gap-1.5">
              {REJECTION_REASONS.map((reason) => (
                <button
                  key={reason.value}
                  disabled={busy}
                  onClick={() => void send('skip', reason.value)}
                  className="chip-outline active:bg-pink-pale"
                >
                  {reason.label}
                </button>
              ))}
            </div>
            <button
              className="w-full text-[12px] text-mute underline underline-offset-2"
              onClick={() => setRejecting(false)}
            >
              Cancel
            </button>
          </div>
        ) : (
          <div className="flex gap-2">
            <button
              className="btn flex-[1.3] text-[13px]"
              disabled={busy}
              onClick={() => void send('promote')}
            >
              PROMOTE
            </button>
            <button
              className="btn-outline flex-[0.8] text-[13px]"
              disabled={busy}
              onClick={() => void send('save')}
            >
              SAVE
            </button>
            <button
              className="btn-outline flex-1 border-[#F3B5C8] text-[12px] text-[#B0103F]"
              disabled={busy}
              onClick={() => setRejecting(true)}
            >
              NOT A FIT
            </button>
          </div>
        )
      }
    >
      <div className="space-y-4 pb-2">
        <header className="flex items-center gap-3">
          <ProductThumb artKey={rec.art_key} size={44} />
          <div className="min-w-0 flex-1">
            <h1 className="truncate text-[15px] font-bold text-plum-deep">{rec.title}</h1>
            <p className="text-[13px] font-bold text-[#7A0A3A]">
              ₹{rec.price} <span className="font-medium text-mute">· {rec.category}</span>
            </p>
          </div>
          <div
            className="flex h-14 w-14 shrink-0 flex-col items-center justify-center rounded-xl font-extrabold leading-none text-white"
            style={{ background: fitColor(rec.fit_score) }}
          >
            <span className="text-[23px]">{rec.fit_score}</span>
            <span className="mt-0.5 text-[9px] font-bold tracking-wide">FIT</span>
          </div>
        </header>

        <div className="flex flex-wrap items-center gap-2">
          <TrendPill stage={rec.trend_stage} score={rec.trend_score} />
          <ConfidencePill level={rec.confidence} />
        </div>

        <section className="space-y-1.5">
          <h2 className="label">Why this product?</h2>
          <ul className="space-y-1">
            {rec.reasons.map((reason) => (
              <li key={reason} className="flex items-start gap-2 text-[12.5px] leading-snug">
                <span className="mt-[3px] flex h-3.5 w-3.5 shrink-0 items-center justify-center rounded-full bg-[#19B364]">
                  <svg width="9" height="9" viewBox="0 0 24 24" aria-hidden="true">
                    <path
                      d="M4 12.5l5 5L20 6.5"
                      fill="none"
                      stroke="#fff"
                      strokeWidth="3.6"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </span>
                {reason}
              </li>
            ))}
          </ul>
        </section>

        {rec.caveats.length > 0 && (
          <section className="space-y-1.5">
            <h2 className="label">Worth knowing</h2>
            <ul className="space-y-1">
              {rec.caveats.map((caveat) => (
                <li key={caveat} className="flex items-start gap-2 text-[12.5px] leading-snug text-sub">
                  <span className="mt-[3px] flex h-3.5 w-3.5 shrink-0 items-center justify-center rounded-full bg-[#F0A21C] text-[9px] font-bold text-white">
                    !
                  </span>
                  {caveat}
                </li>
              ))}
            </ul>
          </section>
        )}

        <section className="space-y-1.5">
          <h2 className="label">Reason codes</h2>
          <div className="flex flex-wrap gap-1.5">
            {rec.reason_codes.map((code) => (
              <span
                key={code}
                className="chip bg-[#E4F7EA] font-mono text-[11px] font-bold text-[#0B6B38]"
              >
                {code}
              </span>
            ))}
          </div>
        </section>

        <section className="space-y-2">
          <h2 className="label">Fit signals</h2>
          <SignalBars signals={rec.signals} />
          <p className="text-[10.5px] leading-snug text-mute">
            Score = Σ (signal × weight) × price fit. Base {rec.base_score.toFixed(1)} ×{' '}
            {rec.price_fit.toFixed(2)}
            {rec.learning_multiplier !== 1 && ` × ${rec.learning_multiplier.toFixed(2)} learned`} ={' '}
            <b className="text-navy">{rec.fit_score}</b>
          </p>
          {rec.notes.map((note) => (
            <p key={note} className="text-[10.5px] text-mute">
              · {note}
            </p>
          ))}
        </section>

        <section className="rounded-xl border border-[#F5CFE2] bg-[#FFF1F7] p-3">
          <p className="text-[11px] font-medium text-mute">Suggested content angle</p>
          <p className="text-[13.5px] font-bold leading-snug text-[#7A0A3A]">
            {rec.content_angle}
          </p>
        </section>
      </div>
    </Shell>
  );
}
