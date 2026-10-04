'use client';

/** Brand · Offers sent. Every offer, its status, and the creator's reason if declined. */
import Link from 'next/link';
import { useEffect, useState } from 'react';

import { ErrorState, Loading, PageHeader } from '@/components/AppShell';
import { useBrands } from '@/components/BrandContext';
import { Avatar, FitRing, ProductImage, StatusChip } from '@/components/ui';
import { api, fmt } from '@/lib/api';
import { REASON_LABEL, type Pitch } from '@/lib/types';

export default function BrandOffersPage() {
  const { current, loading, revision } = useBrands();
  const [pitches, setPitches] = useState<Pitch[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!current) return;
    setPitches(null);
    api.pitches({ brand: current.brand }).then(setPitches).catch((e) => setError(e instanceof Error ? e.message : 'Could not load offers.'));
  }, [current, revision]);

  if (loading || !current) return <Loading label="Loading brands" />;

  return (
    <>
      <PageHeader
        title="Offers sent"
        description="Where each offer stands. When a creator declines, their reason tells you what to change."
      />
      {error && <ErrorState message={error} />}
      {!pitches && !error && <Loading label="Loading offers" />}
      {pitches && pitches.length === 0 && (
        <div className="mx-6 mt-5 rounded-2xl border border-dashed border-[var(--line-strong)] bg-white p-8 text-center">
          <p className="text-[15px] font-semibold text-[var(--plum)]">No offers yet</p>
          <p className="mt-1 text-[13px] text-[var(--ink-2)]">
            Open a product and send an offer to a creator who fits it.
          </p>
          <Link href="/brand" className="btn mt-4">
            Go to products
          </Link>
        </div>
      )}
      {pitches && pitches.length > 0 && (
        <div className="px-6 pb-16 pt-5">
          <div className="panel divide-y divide-[var(--line)]">
            {pitches.map((p) => (
              <div key={p.id} className="flex flex-wrap items-center gap-4 px-5 py-3.5">
                <ProductImage src={p.product.image} alt={p.product.title} className="h-14 w-14 rounded-xl" />
                <div className="min-w-[160px] flex-1">
                  <Link href={`/brand/product/${p.product.product_id}`} className="text-[14px] font-semibold hover:text-[var(--signal)]">
                    {p.product.title}
                  </Link>
                  <p className="text-[12px] text-[var(--ink-3)]">{fmt.rupees(p.product.price)}</p>
                </div>
                <div className="flex min-w-[170px] items-center gap-2.5">
                  <Avatar name={p.creator_name} seed={p.creator_id} size={30} />
                  <span className="text-[13px] font-medium">{p.creator_name}</span>
                </div>
                <FitRing score={p.fit_score} size={42} />
                <div className="w-[170px] text-right">
                  <StatusChip status={p.status} />
                  {p.reason && (
                    <p className="mt-1 text-[11.5px] text-[var(--ink-3)]">{REASON_LABEL[p.reason] ?? p.reason}</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </>
  );
}
