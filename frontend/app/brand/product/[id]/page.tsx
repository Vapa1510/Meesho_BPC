'use client';

/**
 * Brand · Product. The same engine, seen from the product's side: which
 * creators fit it, why, what that could be worth, and what creators have
 * already said about it. Sending an offer reaches the creator's inbox.
 */
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';

import { ErrorState, Loading } from '@/components/AppShell';
import { useBrands } from '@/components/BrandContext';
import { SignalBars } from '@/components/ProductDrawer';
import { Avatar, FitRing, ProductImage, Star, StatusChip, Toast } from '@/components/ui';
import { api, fmt } from '@/lib/api';
import { INTENT_LABEL } from '@/lib/types';
import { REASON_LABEL, type CreatorMatch, type ProductMatches } from '@/lib/types';

function MatchRow({
  m,
  productTitle,
  brand,
  onSend,
  sending,
}: {
  m: CreatorMatch;
  productTitle: string;
  brand: string;
  onSend: (message: string) => void;
  sending: boolean;
}) {
  const [compose, setCompose] = useState(false);
  const [why, setWhy] = useState(false);
  const [message, setMessage] = useState(
    `Hi ${m.name.split(' ')[0]}, ${brand} would love for you to feature ${productTitle}. We think it suits your audience.`,
  );

  return (
    <li className="px-5 py-4">
      <div className="flex flex-wrap items-center gap-4">
        <Avatar name={m.name} seed={m.creator_id} size={44} />
        <div className="min-w-[170px] flex-1">
          <p className="text-[14px] font-semibold">{m.name}</p>
          <p className="text-[12px] text-[var(--ink-3)]">
            {m.niche} · {fmt.compact(m.followers)} followers · {INTENT_LABEL[m.goal] ?? m.goal}
          </p>
          {m.reasons[0] && <p className="mt-1 text-[12.5px] text-[var(--ink-2)]">✓ {m.reasons[0]}</p>}
        </div>

        <dl className="grid grid-cols-3 gap-5 text-center">
          {[
            ['Reach', fmt.compact(m.est_reach)],
            ['Orders', fmt.int(m.est_orders)],
            ['NMV', `₹${fmt.compact(m.est_nmv)}`],
          ].map(([k, v]) => (
            <div key={k}>
              <dt className="text-[10.5px] font-medium uppercase tracking-wide text-[var(--ink-3)]">{k}</dt>
              <dd className="text-[14px] font-semibold">{v}</dd>
            </div>
          ))}
        </dl>

        <FitRing score={m.fit_score} size={52} />

        <div className="flex w-[130px] flex-col items-stretch gap-1.5">
          {m.offer_status ? (
            <div className="text-center">
              <StatusChip status={m.offer_status} />
            </div>
          ) : (
            <button className="btn btn-sm" onClick={() => setCompose((c) => !c)}>
              Send offer
            </button>
          )}
          <button className="text-[11.5px] text-[var(--ink-3)] hover:text-[var(--signal)]" onClick={() => setWhy((w) => !w)}>
            {why ? 'Hide breakdown' : 'Why this score'}
          </button>
        </div>
      </div>

      {compose && !m.offer_status && (
        <div className="mt-3 rounded-xl bg-[var(--canvas)] p-3">
          <textarea
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            maxLength={400}
            rows={2}
            className="field !rounded-lg"
          />
          <div className="mt-2 flex justify-end gap-2">
            <button className="btn-quiet btn-sm" onClick={() => setCompose(false)}>
              Cancel
            </button>
            <button className="btn btn-sm" disabled={sending} onClick={() => onSend(message)}>
              Send to {m.name.split(' ')[0]}
            </button>
          </div>
        </div>
      )}

      {why && (
        <div className="mt-3 grid gap-5 rounded-xl bg-[var(--canvas)] p-4 md:grid-cols-2">
          <SignalBars signals={m.signals} />
          <ul className="space-y-1.5 text-[12.5px] text-[var(--ink-2)]">
            {m.reasons.map((r) => (
              <li key={r}>
                <span className="text-[var(--green)]">✓</span> {r}
              </li>
            ))}
            {m.caveats.map((c) => (
              <li key={c}>
                <span className="text-[var(--orange)]">!</span> {c}
              </li>
            ))}
          </ul>
        </div>
      )}
    </li>
  );
}

export default function BrandProductPage() {
  const { id } = useParams<{ id: string }>();
  const { invalidate } = useBrands();
  const [data, setData] = useState<ProductMatches | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      setData(await api.productMatches(id));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not load this product.');
    }
  }, [id]);

  useEffect(() => {
    setData(null);
    void load();
  }, [load]);

  async function send(creatorId: string, name: string, message: string) {
    setSending(true);
    try {
      await api.sendPitch({ product_id: id, creator_id: creatorId, message });
      setToast(`Offer sent to ${name}. It is in their Offers inbox.`);
      invalidate();
      await load();
    } catch (e) {
      setToast(e instanceof Error ? e.message : 'Could not send the offer.');
    } finally {
      setSending(false);
    }
  }

  if (error) return <ErrorState message={error} onRetry={load} />;
  if (!data) return <Loading label="Matching creators to this product" />;

  const { product: p, diagnosis: d, feedback: f } = data;
  const reachable = data.matches.filter((m) => m.eligible);
  const blocked = data.matches.filter((m) => !m.eligible);
  const inNiche = blocked.filter((m) => m.blocked_by !== "outside this creator's niche");
  const offNiche = blocked.length - inNiche.length;
  const maxSkip = Math.max(1, ...Object.values(f.skip_reasons));

  return (
    <div className="px-6 pb-16 pt-6">
      <Link href="/brand" className="text-[12.5px] text-[var(--ink-3)] hover:text-[var(--signal)]">
        ← All products
      </Link>

      <section className="card mt-3 flex flex-col md:flex-row">
        <ProductImage src={p.image} alt={p.title} className="aspect-[4/3] w-full md:aspect-auto md:h-[300px] md:w-[300px]" />
        <div className="flex-1 p-6">
          <p className="text-[12.5px] font-semibold text-[var(--signal)]">{p.brand}</p>
          <h1 className="text-[26px] font-bold leading-tight tracking-[-0.025em] text-[var(--plum)]">{p.title}</h1>
          <div className="mt-2 flex flex-wrap items-center gap-2.5 text-[13px]">
            <b className="text-[16px]">{fmt.rupees(p.price)}</b>
            <Star rating={p.rating} />
            <span className="text-[var(--ink-3)]">({fmt.int(p.review_count)} reviews)</span>
            <span className="chip">{p.category}</span>
            <span className="chip">{p.trend_stage}</span>
            {p.is_new && <span className="chip border-[var(--signal)] text-[var(--signal)]">New listing</span>}
          </div>
          <p className="mt-3 max-w-[60ch] text-[13.5px] leading-relaxed text-[var(--ink-2)]">{p.description}</p>
          <div className="mt-4 flex flex-wrap gap-1.5">
            {p.tags.map((t) => (
              <span key={t} className="chip">{t}</span>
            ))}
          </div>
          <dl className="mt-5 flex flex-wrap gap-8 text-[13px]">
            {[
              ['Orders, 30 days', fmt.int(p.orders_30d)],
              ['Conversion', fmt.pct(p.conversion_rate)],
              ['Return rate', fmt.pct(p.return_rate, 0)],
              ['Creators using it', fmt.pct(p.creator_saturation, 0)],
            ].map(([k, v]) => (
              <div key={k}>
                <dt className="text-[11.5px] text-[var(--ink-3)]">{k}</dt>
                <dd className="text-[16px] font-bold text-[var(--plum)]">{v}</dd>
              </div>
            ))}
          </dl>
        </div>
      </section>

      <div className="mt-6 grid gap-5 lg:grid-cols-[1fr_340px]">
        <section className="panel">
          <div className="panel-head">
            <div>
              <h2 className="panel-title">Best-fit creators</h2>
              <p className="panel-note">
                Same seven signals the creator sees. Reach, orders and NMV are projections: followers × engagement
                × click share × this product&rsquo;s conversion rate.
              </p>
            </div>
          </div>
          {reachable.length === 0 ? (
            <p className="px-5 py-8 text-center text-[13px] text-[var(--ink-3)]">
              No creator can be offered this product yet. See the notes on the right.
            </p>
          ) : (
            <ul className="divide-y divide-[var(--line)]">
              {reachable.map((m) => (
                <MatchRow
                  key={m.creator_id}
                  m={m}
                  productTitle={p.title}
                  brand={p.brand}
                  sending={sending}
                  onSend={(msg) => void send(m.creator_id, m.name, msg)}
                />
              ))}
            </ul>
          )}

          {blocked.length > 0 && (
            <details className="border-t border-[var(--line)] px-5 py-3">
              <summary className="cursor-pointer text-[12.5px] font-medium text-[var(--ink-2)]">
                {blocked.length} creators not reachable
                {inNiche.length > 0 && ` (${inNiche.length} in your niche)`}
              </summary>
              <ul className="mt-3 space-y-2">
                {blocked.map((m) => (
                  <li key={m.creator_id} className="flex items-center gap-3 text-[12.5px]">
                    <Avatar name={m.name} seed={m.creator_id} size={26} />
                    <span className="w-[130px] truncate font-medium">{m.name}</span>
                    <span className="text-[var(--ink-3)]">{m.blocked_by}</span>
                  </li>
                ))}
              </ul>
            </details>
          )}
        </section>

        <div className="space-y-5 self-start">
          <section className="panel p-5">
            <h2 className="text-[14px] font-semibold">Reach</h2>
            <div className="mt-3 grid grid-cols-3 gap-2 text-center">
              {[
                [d.creators_total, 'in your niche'],
                [d.reachable, 'reachable'],
                [d.strong_matches, 'strong fits'],
              ].map(([n, l]) => (
                <div key={String(l)} className="rounded-xl bg-[var(--canvas)] py-2.5">
                  <p className="text-[20px] font-bold text-[var(--plum)]">{n}</p>
                  <p className="text-[11px] text-[var(--ink-3)]">{l}</p>
                </div>
              ))}
            </div>
            {offNiche > 0 && (
              <p className="mt-2 text-[11.5px] text-[var(--ink-3)]">
                {offNiche} other creators cover different categories and are not offered this product.
              </p>
            )}
            {Object.entries(d.blockers).length > 0 && (
              <ul className="mt-3 space-y-1 text-[12.5px] text-[var(--ink-2)]">
                {Object.entries(d.blockers).map(([k, v]) => (
                  <li key={k}>
                    <b>{v}</b> blocked: {k}
                  </li>
                ))}
              </ul>
            )}
            {d.tips.length > 0 && (
              <div className="mt-4 rounded-xl p-3.5" style={{ background: 'var(--grad)' }}>
                <p className="text-[11px] font-semibold uppercase tracking-wide text-[var(--plum)]/70">
                  To reach more creators
                </p>
                <ul className="mt-1.5 space-y-1.5 text-[12.5px] leading-snug text-[var(--plum)]">
                  {d.tips.map((t) => (
                    <li key={t}>• {t}</li>
                  ))}
                </ul>
              </div>
            )}
          </section>

          <section className="panel p-5">
            <h2 className="text-[14px] font-semibold">What creators did with it</h2>
            <div className="mt-3 grid grid-cols-3 gap-2 text-center">
              {[
                [f.promotes, 'promoted'],
                [f.saves, 'saved'],
                [f.skips, 'skipped'],
              ].map(([n, l]) => (
                <div key={String(l)} className="rounded-xl bg-[var(--canvas)] py-2.5">
                  <p className="text-[20px] font-bold text-[var(--plum)]">{n}</p>
                  <p className="text-[11px] text-[var(--ink-3)]">{l}</p>
                </div>
              ))}
            </div>
            {Object.keys(f.skip_reasons).length > 0 ? (
              <ul className="mt-4 space-y-2.5">
                {Object.entries(f.skip_reasons)
                  .sort((a, b) => b[1] - a[1])
                  .map(([reason, n]) => (
                    <li key={reason}>
                      <div className="flex justify-between text-[12px]">
                        <span>{REASON_LABEL[reason] ?? reason}</span>
                        <b>{n}</b>
                      </div>
                      <div className="mt-1 h-[6px] rounded-full bg-[#f6ebf1]">
                        <div
                          className="h-full rounded-full bg-[var(--signal)]"
                          style={{ width: `${(n / maxSkip) * 100}%` }}
                        />
                      </div>
                    </li>
                  ))}
              </ul>
            ) : (
              <p className="mt-3 text-[12px] leading-relaxed text-[var(--ink-3)]">
                Nothing yet. Skip reasons from creators will show up here, so you know what to fix.
              </p>
            )}
            {f.offers_sent > 0 && (
              <p className="mt-4 border-t border-[var(--line)] pt-3 text-[12px] text-[var(--ink-2)]">
                Offers: <b>{f.offers_sent}</b> sent · <b>{f.offers_accepted}</b> accepted ·{' '}
                <b>{f.offers_declined}</b> declined
              </p>
            )}
          </section>
        </div>
      </div>
      <Toast message={toast} onDone={() => setToast(null)} />
    </div>
  );
}
