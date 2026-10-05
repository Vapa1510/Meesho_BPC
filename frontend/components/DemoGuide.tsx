'use client';

/**
 * The walkthrough the deck's QR codes land on.
 *
 * The four QR codes on slides 7 and 8 open only two addresses, /creator and
 * /creator/onboard, and the deck can no longer change. So both pages carry
 * this card: four stops that follow slides 7 and 8 in order, wherever the
 * judge arrived, plus a reset that puts the shared demo back to the deck's state.
 */
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

import { useBrands } from '@/components/BrandContext';
import { useCreators } from '@/components/CreatorContext';
import { api } from '@/lib/api';
import { DEMO_CREATOR_ID } from '@/lib/types';

const STEPS = [
  {
    n: 1,
    slide: 'Slide 7',
    title: 'Onboard Riya',
    what: 'Connect @riya.glows and answer 4 indirect questions.',
    href: '/creator/onboard',
  },
  {
    n: 2,
    slide: 'Slide 7',
    title: 'Her Creator DNA',
    what: 'Every value tagged fetched or asked. Correct it and the picks re-rank.',
    href: '/creator/profile',
  },
  {
    n: 3,
    slide: 'Slide 8',
    title: 'Fit Engine: her Top 8',
    what: '164 listings → 25 pass the gates → ranked, explained, with a content angle.',
    href: '/creator',
  },
  {
    n: 4,
    slide: 'Slide 8',
    title: 'Brand Match + feedback loop',
    what: 'Skip Ceramide Moisturiser as “Too expensive”: 76 → 73, and the brand sees why.',
    href: '/brand/product/P009',
  },
];

const HIDE_KEY = 'cfe.guide.hidden';

function readHidden(): boolean {
  try {
    return window.sessionStorage.getItem(HIDE_KEY) === '1';
  } catch {
    return false;
  }
}

function writeHidden(v: boolean) {
  try {
    if (v) window.sessionStorage.setItem(HIDE_KEY, '1');
    else window.sessionStorage.removeItem(HIDE_KEY);
  } catch {
    /* not remembered; harmless */
  }
}

export function DemoGuide() {
  const pathname = usePathname();
  const router = useRouter();
  const creators = useCreators();
  const brands = useBrands();
  const [hidden, setHidden] = useState(false);
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState<string | null>(null);

  useEffect(() => setHidden(readHidden()), []);

  const onRiya = creators.current?.creator_id === DEMO_CREATOR_ID;

  async function reset() {
    if (!window.confirm('Reset the demo? This clears every skip, offer and order made on this prototype and restores the numbers shown in the deck.')) return;
    setBusy(true);
    setNote(null);
    try {
      await api.resetDemo();
      await creators.refresh();
      creators.select(DEMO_CREATOR_ID);
      creators.invalidate();
      brands.invalidate();
      setNote('Reset done: back to the numbers in the deck.');
    } catch (e) {
      setNote(e instanceof Error ? e.message : 'Could not reset.');
    } finally {
      setBusy(false);
    }
  }

  if (hidden) {
    return (
      <div className="px-4 pt-4 sm:px-6">
        <button
          className="chip text-[12px] hover:border-[var(--signal)] hover:text-[var(--signal)]"
          onClick={() => {
            writeHidden(false);
            setHidden(false);
          }}
        >
          Show the 4-step walkthrough
        </button>
      </div>
    );
  }

  return (
    <section
      aria-label="Prototype walkthrough"
      className="mx-4 mt-4 rounded-[22px] border border-[#f3d3e2] bg-white p-4 shadow-[0_10px_30px_-18px_rgba(81,14,68,0.35)] sm:mx-6 sm:p-5"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[11px] font-bold uppercase tracking-[0.1em] text-[var(--signal)]">
            Meesho DICE S3 · Team Pro · live prototype
          </p>
          <h2 className="mt-0.5 text-[16px] font-bold leading-snug tracking-[-0.01em] text-[var(--plum)] sm:text-[17px]">
            Walk through slides 7 and 8 in four stops
          </h2>
          <p className="mt-0.5 text-[12px] leading-snug text-[var(--ink-3)]">
            Sample data, not Meesho data. Every number here is computed live by the engine.
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <button className="btn-quiet btn-sm" disabled={busy} onClick={() => void reset()}>
            {busy ? 'Resetting…' : 'Reset demo'}
          </button>
          <button
            className="px-1.5 text-[12px] text-[var(--ink-3)] hover:text-[var(--signal)]"
            onClick={() => {
              writeHidden(true);
              setHidden(true);
            }}
          >
            Hide
          </button>
        </div>
      </div>

      <ol className="mt-3 grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
        {STEPS.map((s) => {
          const here = pathname === s.href;
          return (
            <li key={s.n}>
              <Link
                href={s.href}
                onClick={() => {
                  if (!onRiya && s.n !== 1) creators.select(DEMO_CREATOR_ID);
                }}
                aria-current={here ? 'step' : undefined}
                className={`flex h-full gap-3 rounded-2xl border px-3 py-2.5 transition-colors ${
                  here
                    ? 'border-[var(--signal)] bg-[var(--signal-wash)]'
                    : 'border-[var(--line)] hover:border-[var(--signal)]'
                }`}
              >
                <span
                  className={`mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[12px] font-bold ${
                    here ? 'bg-[var(--signal)] text-white' : 'bg-[#f3e9ef] text-[var(--plum)]'
                  }`}
                >
                  {s.n}
                </span>
                <span className="min-w-0">
                  <span className="flex flex-wrap items-baseline gap-x-2">
                    <span className="text-[13px] font-semibold text-[var(--ink)]">{s.title}</span>
                    <span className="text-[10.5px] font-semibold uppercase tracking-wide text-[var(--ink-3)]">{s.slide}</span>
                  </span>
                  <span className="mt-0.5 block text-[12px] leading-snug text-[var(--ink-2)]">{s.what}</span>
                  {here && <span className="mt-1 block text-[11px] font-semibold text-[var(--signal)]">You are here</span>}
                </span>
              </Link>
            </li>
          );
        })}
      </ol>
      {!onRiya && creators.current && pathname.startsWith('/creator') && (
        <p className="mt-3 text-[12px] text-[var(--ink-2)]">
          You are viewing {creators.current.name}.{' '}
          <button
            className="font-semibold text-[var(--signal)]"
            onClick={() => {
              creators.select(DEMO_CREATOR_ID);
              router.refresh();
            }}
          >
            Switch to Riya, the deck&apos;s creator
          </button>
        </p>
      )}
      {note && <p className="mt-3 text-[12px] font-medium text-[var(--plum)]">{note}</p>}
    </section>
  );
}
