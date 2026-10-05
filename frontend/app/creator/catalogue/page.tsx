'use client';

/** Creator · Catalogue. Browse every product with its fit for the selected
 *  creator, including ones the ranker chose not to serve, and see why. */
import { useCallback, useEffect, useMemo, useState } from 'react';

import { ErrorState, Loading, PageHeader } from '@/components/AppShell';
import { useCreators } from '@/components/CreatorContext';
import { ProductDrawer } from '@/components/ProductDrawer';
import { Chip, FitRing, ProductImage, Star, Toast } from '@/components/ui';
import { api, fmt } from '@/lib/api';
import type { Product, Recommendation } from '@/lib/types';

const CATEGORIES = ['All', 'Skincare', 'Makeup', 'Haircare', 'Personal Care'];
const SORTS = [
  { id: 'fit', label: 'Best fit' },
  { id: 'price_asc', label: 'Price: low to high' },
  { id: 'trend', label: 'Trending' },
];
const PAGE = 24;

const BLOCKED: Record<string, string> = {
  price_range: 'Not in feed: outside her price window',
  stock_serviceable: 'Not in feed: out of stock',
  quality_threshold: 'Not in feed: below the rating bar',
  return_rate: 'Not in feed: returns above median',
  policy_compliant: 'Not in feed: policy or claims flag',
  creator_excluded: 'Not in feed: category she excluded',
  audience_fit: 'Not in feed: audience mismatch',
  already_promoted: 'Already promoted',
};

export default function CataloguePage() {
  const { current, loading, revision, invalidate } = useCreators();
  const [catalogue, setCatalogue] = useState<Product[]>([]);
  const [scored, setScored] = useState<Recommendation[] | null>(null);
  const [category, setCategory] = useState('All');
  const [sort, setSort] = useState('fit');
  const [query, setQuery] = useState('');
  const [shown, setShown] = useState(PAGE);
  const [open, setOpen] = useState<Recommendation | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => {
    api
      .products()
      .then(setCatalogue)
      .catch((e) => setError(e instanceof Error ? e.message : 'Could not load products.'));
  }, []);

  const load = useCallback(async () => {
    if (!current || catalogue.length === 0) return;
    setError(null);
    try {
      // Score everything (the endpoint takes any id list) so the sort is honest.
      setScored(await api.rankProducts(current.creator_id, catalogue.map((p) => p.product_id)));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not score these products.');
    }
  }, [current, catalogue]);

  useEffect(() => {
    setScored(null);
    void load();
  }, [load, revision]);

  useEffect(() => setShown(PAGE), [category, sort, query]);

  const rows = useMemo(() => {
    const list = (scored ?? []).filter(
      (r) =>
        (category === 'All' || r.category === category) &&
        (!query ||
          `${r.title} ${r.brand}`.toLowerCase().includes(query.toLowerCase())),
    );
    if (sort === 'price_asc') list.sort((a, b) => a.price - b.price);
    else if (sort === 'trend') list.sort((a, b) => b.trend_score - a.trend_score);
    // Best fit: what the feed could serve first, then the rest with the rule that blocks it.
    else list.sort((a, b) => Number(b.eligible) - Number(a.eligible) || b.fit_score - a.fit_score);
    return list;
  }, [scored, category, sort, query]);

  async function act(rec: Recommendation, action: 'promote' | 'save' | 'skip', reason?: string) {
    if (!current) return;
    setBusy(true);
    try {
      const res = await api.feedback({
        creator_id: current.creator_id,
        product_id: rec.product_id,
        action,
        reason: reason ?? null,
        served_score: rec.fit_score,
      });
      setToast(res.message);
      setOpen(null);
      invalidate();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not record that.');
    } finally {
      setBusy(false);
    }
  }

  if (loading || !current) return <Loading label="Loading creators" />;

  return (
    <>
      <PageHeader
        title="Catalogue"
        description={`Every listing, scored for ${current.name.split(' ')[0]}. Products that fail a hard check (price window, stock, rating, returns, claims, audience) are marked and never reach her feed.`}
      />

      <div className="flex flex-wrap items-center gap-2 px-4 pb-5 pt-4 sm:px-6">
        {CATEGORIES.map((c) => (
          <Chip key={c} active={category === c} onClick={() => setCategory(c)}>
            {c}
          </Chip>
        ))}
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search products or brands"
          className="field !w-full !rounded-full sm:ml-auto sm:!w-[240px]"
        />
        <select
          value={sort}
          onChange={(e) => setSort(e.target.value)}
          className="field !w-auto !rounded-full"
          aria-label="Sort"
        >
          {SORTS.map((s) => (
            <option key={s.id} value={s.id}>
              {s.label}
            </option>
          ))}
        </select>
      </div>

      {error && <ErrorState message={error} onRetry={load} />}
      {!scored && !error && <Loading label="Scoring the catalogue" />}

      {scored && (
        <>
          <p className="px-4 pb-3 text-[12px] text-[var(--ink-3)] sm:px-6">
            {fmt.int(rows.length)} products · {fmt.int(rows.filter((r) => r.eligible).length)} pass every check
          </p>
          <div className="grid grid-cols-2 gap-3 px-4 pb-6 sm:gap-4 sm:px-6 md:grid-cols-3 xl:grid-cols-4">
            {rows.slice(0, shown).map((r) => {
              const dim = !r.eligible;
              return (
                <button
                  key={r.product_id}
                  onClick={() => setOpen(r)}
                  className={`card card-hover flex flex-col text-left ${dim ? 'opacity-75' : ''}`}
                >
                  <div className="relative">
                    <ProductImage src={r.image} alt={r.title} className="aspect-square w-full" />
                    <span className="absolute right-2.5 top-2.5 flex rounded-full bg-white p-0.5 shadow">
                      <FitRing score={r.fit_score} size={42} />
                    </span>
                    {!r.eligible && r.blocked_by && (
                      <span className="absolute bottom-2.5 left-2.5 right-2.5 rounded-full bg-[var(--plum)]/90 px-2.5 py-0.5 text-center text-[10.5px] font-semibold text-white">
                        {BLOCKED[r.blocked_by] ?? 'Not in feed'}
                      </span>
                    )}
                  </div>
                  <div className="p-3.5">
                    <p className="truncate text-[11px] text-[var(--ink-3)]">{r.brand}</p>
                    <p className="truncate text-[13.5px] font-semibold">{r.title}</p>
                    <div className="mt-1 flex items-center gap-2 text-[12px]">
                      <b>{fmt.rupees(r.price)}</b>
                      <Star rating={r.rating} />
                    </div>
                    {r.caveats[0] && (
                      <p className="mt-1.5 line-clamp-2 text-[11.5px] leading-snug text-[var(--ink-3)]">
                        {r.caveats[0]}
                      </p>
                    )}
                  </div>
                </button>
              );
            })}
          </div>
          {shown < rows.length && (
            <div className="pb-16 text-center">
              <button className="btn-quiet" onClick={() => setShown((n) => n + PAGE)}>
                Show more
              </button>
            </div>
          )}
        </>
      )}

      {open && (
        <ProductDrawer
          rec={open}
          forName={current.name.split(' ')[0]}
          busy={busy}
          onClose={() => setOpen(null)}
          onAction={(a, reason) => void act(open, a, reason)}
        />
      )}
      <Toast message={toast} onDone={() => setToast(null)} />
    </>
  );
}
