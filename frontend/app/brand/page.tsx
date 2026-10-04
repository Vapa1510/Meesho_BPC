'use client';

/** Brand · Dashboard. A seller's portfolio and how their offers are landing. */
import Link from 'next/link';
import { useEffect, useState } from 'react';

import { ErrorState, Loading, PageHeader } from '@/components/AppShell';
import { useBrands } from '@/components/BrandContext';
import { ProductImage, Star, Stat } from '@/components/ui';
import { api, fmt } from '@/lib/api';
import type { BrandOverview } from '@/lib/types';

export default function BrandDashboard() {
  const { current, loading, error, revision } = useBrands();
  const [data, setData] = useState<BrandOverview | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!current) return;
    setData(null);
    setErr(null);
    api.brand(current.brand).then(setData).catch((e) => setErr(e instanceof Error ? e.message : 'Could not load.'));
  }, [current, revision]);

  if (error) return <ErrorState message={error} />;
  if (loading || !current) return <Loading label="Loading brands" />;

  return (
    <>
      <PageHeader
        title={current.brand}
        description="Open a product to see which creators fit it, what they would earn you, and send an offer."
        actions={
          <Link href="/brand/new" className="btn">
            List a product
          </Link>
        }
      />
      {err && <ErrorState message={err} />}
      {!data && !err && <Loading label="Loading portfolio" />}

      {data && (
        <div className="space-y-6 px-6 pb-16 pt-5">
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <Stat label="Products" value={data.products.length} />
            <Stat label="NMV, last 30 days" value={`₹${fmt.compact(data.nmv_30d)}`} />
            <Stat
              label="Offers sent"
              value={data.offers_sent}
              note={data.offers_pending ? `${data.offers_pending} waiting for an answer` : undefined}
            />
            <Stat
              label="Acceptance rate"
              value={data.acceptance_rate === null ? '—' : fmt.pct(data.acceptance_rate, 0)}
              note={data.acceptance_rate === null ? 'No answers yet' : `${data.offers_accepted} accepted`}
            />
          </div>

          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {data.products.map((p) => (
              <Link
                key={p.product_id}
                href={`/brand/product/${p.product_id}`}
                className="card card-hover flex flex-col"
              >
                <div className="relative">
                  <ProductImage src={p.image} alt={p.title} className="aspect-square w-full" />
                  {p.is_new && (
                    <span className="absolute left-3 top-3 rounded-full bg-[var(--signal)] px-2.5 py-0.5 text-[11px] font-bold text-white">
                      New
                    </span>
                  )}
                </div>
                <div className="p-4">
                  <p className="truncate text-[14px] font-semibold">{p.title}</p>
                  <div className="mt-1 flex items-center gap-2 text-[12.5px]">
                    <b>{fmt.rupees(p.price)}</b>
                    <Star rating={p.rating} />
                    <span className="text-[var(--ink-3)]">· {p.trend_stage}</span>
                  </div>
                  <p className="mt-2 text-[11.5px] text-[var(--ink-3)]">
                    {fmt.int(p.orders_30d)} orders · {fmt.pct(p.conversion_rate)} conversion
                  </p>
                  <p className="mt-3 text-[12.5px] font-semibold text-[var(--signal)]">
                    See matching creators →
                  </p>
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}
    </>
  );
}
