'use client';

/** Creator · Offers. Brand offers sent to this creator. Accepting or declining
 *  is ordinary feedback: it moves this creator's ranking like a card tap does. */
import { useCallback, useEffect, useState } from 'react';

import { ErrorState, Loading, PageHeader } from '@/components/AppShell';
import { useCreators } from '@/components/CreatorContext';
import { FitRing, ProductImage, StatusChip, Toast } from '@/components/ui';
import { api, fmt } from '@/lib/api';
import { REASON_LABEL, REJECTION_REASONS, type Pitch } from '@/lib/types';

function OfferCard({
  pitch,
  busy,
  onRespond,
}: {
  pitch: Pitch;
  busy: boolean;
  onRespond: (action: 'accept' | 'decline', reason?: string) => void;
}) {
  const [declining, setDeclining] = useState(false);
  const p = pitch.product;
  return (
    <article className="card flex flex-col sm:flex-row">
      <ProductImage src={p.image} alt={p.title} className="aspect-[4/3] w-full sm:aspect-auto sm:w-[220px]" />
      <div className="flex min-w-0 flex-1 flex-col p-5">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <p className="text-[12px] font-semibold text-[var(--signal)]">{pitch.brand}</p>
            <h3 className="text-[17px] font-semibold leading-snug">{p.title}</h3>
            <p className="mt-0.5 text-[13px] text-[var(--ink-2)]">
              {fmt.rupees(p.price)} · {p.category}
            </p>
          </div>
          <div className="text-center">
            <FitRing score={pitch.fit_score} size={54} label />
          </div>
        </div>

        <p className="mt-3 rounded-xl bg-[var(--canvas)] px-3.5 py-2.5 text-[13px] leading-relaxed text-[var(--ink-2)]">
          “{pitch.message}”
        </p>

        <div className="mt-auto pt-4">
          {declining ? (
            <div>
              <p className="mb-1.5 text-[12px] text-[var(--ink-3)]">Tell the brand why:</p>
              <div className="flex flex-wrap gap-1.5">
                {REJECTION_REASONS.map((r) => (
                  <button
                    key={r.value}
                    disabled={busy}
                    onClick={() => onRespond('decline', r.value)}
                    className="chip transition-colors hover:border-[var(--signal)] hover:text-[var(--signal)]"
                  >
                    {r.label}
                  </button>
                ))}
                <button onClick={() => setDeclining(false)} className="px-2 text-[12px] text-[var(--ink-3)]">
                  cancel
                </button>
              </div>
            </div>
          ) : (
            <div className="flex gap-2">
              <button className="btn" disabled={busy} onClick={() => onRespond('accept')}>
                Accept offer
              </button>
              <button className="btn-quiet" disabled={busy} onClick={() => setDeclining(true)}>
                Decline
              </button>
            </div>
          )}
        </div>
      </div>
    </article>
  );
}

export default function CreatorOffersPage() {
  const { current, loading, invalidate } = useCreators();
  const [pitches, setPitches] = useState<Pitch[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!current) return;
    setError(null);
    try {
      setPitches(await api.pitches({ creator_id: current.creator_id }));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not load offers.');
    }
  }, [current]);

  useEffect(() => {
    setPitches(null);
    void load();
  }, [load]);

  async function respond(p: Pitch, action: 'accept' | 'decline', reason?: string) {
    setBusy(true);
    try {
      await api.respondPitch(p.id, action, reason);
      setToast(
        action === 'accept'
          ? `Accepted. ${p.product.title} is now marked as promoted.`
          : 'Declined. The brand will see your reason.',
      );
      invalidate();
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not send your answer.');
    } finally {
      setBusy(false);
    }
  }

  if (loading || !current) return <Loading label="Loading creators" />;

  const pending = (pitches ?? []).filter((p) => p.status === 'pending');
  const past = (pitches ?? []).filter((p) => p.status !== 'pending');

  return (
    <>
      <PageHeader
        title="Offers from brands"
        description="Brands that match your niche and price band can send you a product directly. Your answer also teaches your recommendations."
      />
      {error && <ErrorState message={error} onRetry={load} />}
      {!pitches && !error && <Loading label="Loading offers" />}

      {pitches && (
        <div className="space-y-8 px-6 pb-16 pt-5">
          {pending.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-[var(--line-strong)] bg-white p-8 text-center">
              <p className="text-[15px] font-semibold text-[var(--plum)]">No offers waiting</p>
              <p className="mx-auto mt-1 max-w-[52ch] text-[13px] text-[var(--ink-2)]">
                Switch to the Brand workspace, open a product that fits {current.name.split(' ')[0]} and
                send an offer. It will show up here.
              </p>
            </div>
          ) : (
            <div className="grid gap-4 lg:grid-cols-2">
              {pending.map((p) => (
                <OfferCard
                  key={p.id}
                  pitch={p}
                  busy={busy}
                  onRespond={(a, r) => void respond(p, a, r)}
                />
              ))}
            </div>
          )}

          {past.length > 0 && (
            <section>
              <h2 className="mb-3 text-[14px] font-semibold">Answered</h2>
              <div className="panel divide-y divide-[var(--line)]">
                {past.map((p) => (
                  <div key={p.id} className="flex items-center gap-4 px-4 py-3">
                    <ProductImage src={p.product.image} alt={p.product.title} className="h-12 w-12 rounded-xl" />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-[13.5px] font-semibold">{p.product.title}</p>
                      <p className="text-[12px] text-[var(--ink-3)]">
                        {p.brand}
                        {p.reason && ` · declined: ${REASON_LABEL[p.reason] ?? p.reason}`}
                      </p>
                    </div>
                    <StatusChip status={p.status} />
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>
      )}
      <Toast message={toast} onDone={() => setToast(null)} />
    </>
  );
}
