'use client';

/** Catalogue — score any product for the selected creator, including ones the
 *  ranker chose not to serve. The deck preset reproduces the slide's table. */
import { useCallback, useEffect, useMemo, useState } from 'react';

import { ErrorState, Loading, PageHeader } from '@/components/AppShell';
import { useCreators } from '@/components/CreatorContext';
import { Meter } from '@/components/Viz';
import { api, fmt } from '@/lib/api';
import { scoreTone, type Product, type Recommendation } from '@/lib/types';

const DECK_SET = ['P001', 'P002', 'P003', 'P004', 'P005'];
const CATEGORIES = ['All', 'Skincare', 'Makeup', 'Haircare', 'Personal Care'];

export default function CataloguePage() {
  const { current, loading, revision } = useCreators();
  const [catalogue, setCatalogue] = useState<Product[]>([]);
  const [scored, setScored] = useState<Recommendation[] | null>(null);
  const [category, setCategory] = useState('All');
  const [deckOnly, setDeckOnly] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .products()
      .then(setCatalogue)
      .catch((err) => setError(err instanceof Error ? err.message : 'Could not load products.'));
  }, []);

  const ids = useMemo(() => {
    if (deckOnly) return DECK_SET;
    return catalogue
      .filter((p) => category === 'All' || p.category === category)
      .slice(0, 60)
      .map((p) => p.product_id);
  }, [catalogue, category, deckOnly]);

  const load = useCallback(async () => {
    if (!current || ids.length === 0) return;
    setError(null);
    setScored(null);
    try {
      setScored(await api.rankProducts(current.creator_id, ids));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not score these products.');
    }
  }, [current, ids]);

  useEffect(() => {
    void load();
  }, [load, revision]);

  if (loading || !current) return <Loading label="Loading creators" />;

  return (
    <>
      <PageHeader
        title="Catalogue"
        description={`Score any product against ${current.name} directly, bypassing the two-stage pipeline. Useful for checking why something was not served.`}
      />

      {error && <ErrorState message={error} onRetry={load} />}

      <div className="space-y-4 p-7">
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() => setDeckOnly((on) => !on)}
            className={`chip transition-colors ${
              deckOnly
                ? 'border-[var(--signal)] bg-[var(--signal-wash)] text-[var(--signal)]'
                : 'hover:border-[var(--ink-3)]'
            }`}
          >
            Deck set
          </button>
          <span className="h-4 w-px bg-[var(--line-strong)]" />
          {CATEGORIES.map((option) => (
            <button
              key={option}
              onClick={() => {
                setDeckOnly(false);
                setCategory(option);
              }}
              className={`chip transition-colors ${
                !deckOnly && category === option
                  ? 'border-[var(--signal)] bg-[var(--signal-wash)] text-[var(--signal)]'
                  : 'hover:border-[var(--ink-3)]'
              }`}
            >
              {option}
            </button>
          ))}
          {deckOnly && (
            <p className="ml-2 text-[12px] text-[var(--ink-2)]">
              The five products from slide 06, scored live.
            </p>
          )}
        </div>

        {!scored && !error && <Loading label="Scoring" />}

        {scored && (
          <section className="panel">
            <div className="panel-head">
              <h2 className="panel-title">
                {scored.length} products scored for {current.name}
              </h2>
              <span className="mono text-[11.5px] text-[var(--ink-3)]">
                ₹{current.price_min}–₹{current.price_max} · {current.niche}
              </span>
            </div>
            <table className="dt">
              <thead>
                <tr>
                  <th className="w-[38px]">#</th>
                  <th className="w-[84px]">ID</th>
                  <th>Product</th>
                  <th className="w-[94px]">Category</th>
                  <th className="w-[76px] text-right">Price</th>
                  <th className="w-[72px] text-right">Price fit</th>
                  <th className="w-[130px] text-right">Fit</th>
                </tr>
              </thead>
              <tbody>
                {scored.map((rec) => (
                  <tr key={rec.product_id} className="hover:bg-[var(--canvas)]">
                    <td className="mono text-[12px] text-[var(--ink-3)]">{rec.rank}</td>
                    <td className="mono text-[12px] text-[var(--ink-3)]">{rec.product_id}</td>
                    <td>
                      <span className="block text-[12.5px] font-medium">{rec.title}</span>
                      {rec.caveats.length > 0 && (
                        <span className="mt-0.5 block text-[11.5px] text-[var(--ink-3)]">
                          {rec.caveats[0]}
                        </span>
                      )}
                    </td>
                    <td className="text-[12px] text-[var(--ink-2)]">{rec.category}</td>
                    <td className="mono num text-[12.5px]">{fmt.rupees(rec.price)}</td>
                    <td
                      className={`mono num text-[12.5px] ${
                        rec.price_fit < 1 ? 'text-[var(--signal)]' : 'text-[var(--ink-3)]'
                      }`}
                    >
                      {rec.price_fit.toFixed(2)}
                    </td>
                    <td>
                      <div className="flex items-center justify-end gap-2.5">
                        <Meter value={rec.fit_score} height={6} />
                        <span
                          className="mono w-[26px] text-right text-[14px] font-bold"
                          style={{ color: scoreTone(rec.fit_score) }}
                        >
                          {rec.fit_score}
                        </span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        )}
      </div>
    </>
  );
}
