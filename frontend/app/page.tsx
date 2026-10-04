'use client';

import Link from 'next/link';

import { ProductImage } from '@/components/ui';

const SAMPLE = ['P001', 'P003', 'P015', 'P011'];

function Side({
  href,
  tone,
  kicker,
  title,
  points,
  cta,
}: {
  href: string;
  tone: string;
  kicker: string;
  title: string;
  points: string[];
  cta: string;
}) {
  return (
    <Link
      href={href}
      className="card card-hover group flex flex-col p-7"
      style={{ borderColor: tone }}
    >
      <p className="text-[12px] font-bold uppercase tracking-[0.08em]" style={{ color: tone }}>
        {kicker}
      </p>
      <h2 className="mt-1 text-[24px] font-bold leading-tight tracking-[-0.025em] text-[var(--plum)]">{title}</h2>
      <ul className="mt-4 space-y-2 text-[13.5px] text-[var(--ink-2)]">
        {points.map((p) => (
          <li key={p} className="flex gap-2.5">
            <span style={{ color: tone }}>●</span>
            {p}
          </li>
        ))}
      </ul>
      <span className="btn mt-6 self-start group-hover:bg-[#cf1454]">{cta}</span>
    </Link>
  );
}

export default function Landing() {
  return (
    <div className="px-6 pb-20 pt-10">
      <section className="overflow-hidden rounded-[28px] px-8 py-12 md:px-14" style={{ background: 'var(--grad)' }}>
        <div className="grid items-center gap-10 md:grid-cols-[1.2fr_1fr]">
          <div>
            <p className="text-[12.5px] font-bold uppercase tracking-[0.1em] text-[var(--signal)]">
              Creator × Product Fit Engine
            </p>
            <h1 className="mt-3 text-[40px] font-extrabold leading-[1.1] tracking-[-0.035em] text-[var(--plum)] md:text-[52px]">
              The right product
              <br />
              for the right creator.
            </h1>
            <p className="mt-4 max-w-[48ch] text-[15px] leading-relaxed text-[var(--plum)]/80">
              One engine, two sides. Creators see products that fit their audience and goals. Brands see
              the creators that fit their products, and what that match could earn.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-3">
            {SAMPLE.map((id, i) => (
              <div
                key={id}
                className="overflow-hidden rounded-2xl bg-white shadow-[0_14px_30px_-14px_rgba(81,14,68,0.4)]"
                style={{ transform: `translateY(${i % 2 ? 14 : -4}px) rotate(${i % 2 ? 2 : -2}deg)` }}
              >
                <ProductImage src={`/product/${id}/image.svg`} alt="" className="aspect-square w-full" />
              </div>
            ))}
          </div>
        </div>
      </section>

      <div className="mt-8 grid gap-5 md:grid-cols-2">
        <Side
          href="/creator"
          tone="#E8195F"
          kicker="I'm a creator"
          title="Find products worth promoting"
          points={[
            'A ranked feed with the picture, the fit score and the reasons',
            'Promote, save or skip, and the feed learns from it',
            'Accept or decline offers from brands',
          ]}
          cta="Open creator workspace"
        />
        <Side
          href="/brand"
          tone="#7B4FE0"
          kicker="I'm a brand"
          title="Find creators who fit your product"
          points={[
            'Every creator scored against your product, with a projection',
            'Send an offer; the creator answers in their inbox',
            'See why creators skip, so you know what to fix',
          ]}
          cta="Open brand workspace"
        />
      </div>

      <section className="mt-10 grid gap-4 md:grid-cols-3">
        {[
          ['1', 'Filter', 'Hard rules first: stock, price band, quality, niche, policy.'],
          ['2', 'Score', 'Seven signals weighted by the creator’s cell in a 3×3 matrix (scale × intent): audience, niche, intent, product, commerce, trend, brand.'],
          ['3', 'Learn', 'Every promote, skip and offer answer re-ranks the next list.'],
        ].map(([n, t, d]) => (
          <div key={n} className="rounded-2xl border border-[var(--line)] bg-white p-5">
            <span className="flex h-8 w-8 items-center justify-center rounded-full bg-[var(--signal-wash)] text-[13px] font-bold text-[var(--signal)]">
              {n}
            </span>
            <p className="mt-3 text-[15px] font-semibold">{t}</p>
            <p className="mt-1 text-[13px] leading-relaxed text-[var(--ink-2)]">{d}</p>
          </div>
        ))}
      </section>

      <p className="mt-8 text-center text-[12.5px] text-[var(--ink-3)]">
        Want to see inside? <Link className="font-semibold text-[var(--signal)]" href="/lab/pipeline">Open the engine lab</Link>:
        the filter funnel, a creator simulation, and ranking metrics.
      </p>
    </div>
  );
}
