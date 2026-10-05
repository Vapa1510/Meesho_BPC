'use client';

/** Small shared pieces: product image, fit ring, avatar, stars, toast. */
import { useEffect, useState, type ReactNode } from 'react';

import { apiWake, imgSrc } from '@/lib/api';
import { scoreTone } from '@/lib/types';

export function ProductImage({
  src,
  alt,
  className = '',
}: {
  src?: string | null;
  alt: string;
  className?: string;
}) {
  const [failed, setFailed] = useState(false);
  const [retryNonce, setRetryNonce] = useState(0);

  useEffect(() => {
    setFailed(false);
  }, [src]);

  useEffect(() => {
    return apiWake.subscribe((waking) => {
      if (!waking) {
        setFailed(false);
        setRetryNonce((n) => n + 1);
      }
    });
  }, []);

  if (!src || failed) {
    return (
      <div
        className={`flex items-center justify-center bg-[var(--signal-wash)] text-[12px] text-[var(--ink-3)] ${className}`}
      >
        no image
      </div>
    );
  }

  const url = imgSrc(src);
  if (!url) {
    return (
      <div
        className={`flex items-center justify-center bg-[var(--signal-wash)] text-[12px] text-[var(--ink-3)] ${className}`}
      >
        no image
      </div>
    );
  }

  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      key={`${url}-${retryNonce}`}
      src={url}
      alt={alt}
      loading="lazy"
      onError={() => setFailed(true)}
      className={`object-cover ${className}`}
    />
  );
}

/** Fit score as a ring: the one number the whole product is about. */
export function FitRing({
  score,
  size = 52,
  label = false,
}: {
  score: number;
  size?: number;
  label?: boolean;
}) {
  const stroke = Math.max(4, Math.round(size / 11));
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const tone = scoreTone(score);
  return (
    <div className="relative inline-flex shrink-0 flex-col items-center" style={{ width: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} aria-hidden>
        <circle cx={size / 2} cy={size / 2} r={r} fill="white" stroke="#f3e6ee" strokeWidth={stroke} />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={tone}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${(c * Math.min(100, score)) / 100} ${c}`}
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
          style={{ transition: 'stroke-dasharray 500ms cubic-bezier(.22,1,.36,1)' }}
        />
      </svg>
      <span
        className="absolute left-0 top-0 flex items-center justify-center font-bold text-[var(--ink)]"
        style={{ width: size, height: size, fontSize: size * 0.34 }}
      >
        {score}
      </span>
      {label && <span className="mt-1 text-[10.5px] font-medium text-[var(--ink-3)]">fit</span>}
    </div>
  );
}

const AVATAR_TONES = [
  ['#E8195F', '#FF8FB4'],
  ['#7B4FE0', '#B79CFF'],
  ['#F28C1C', '#FFC879'],
  ['#0E9F6E', '#7DDDB8'],
  ['#1F6FD0', '#8DBBF5'],
  ['#C01165', '#F38BBE'],
];

export function Avatar({ name, seed, size = 40 }: { name: string; seed?: string; size?: number }) {
  const key = seed ?? name;
  const idx = [...key].reduce((a, ch) => a + ch.charCodeAt(0), 0) % AVATAR_TONES.length;
  const [a, b] = AVATAR_TONES[idx];
  const initials = name
    .replace(/[^A-Za-z ]/g, '')
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0])
    .join('')
    .toUpperCase();
  return (
    <span
      className="inline-flex shrink-0 items-center justify-center rounded-full font-semibold text-white"
      style={{
        width: size,
        height: size,
        fontSize: size * 0.38,
        background: `linear-gradient(135deg, ${a}, ${b})`,
      }}
      aria-hidden
    >
      {initials}
    </span>
  );
}

export function Star({ rating }: { rating: number }) {
  return (
    <span className="inline-flex items-center gap-1 text-[12px] font-semibold text-[var(--ink)]">
      <svg width="12" height="12" viewBox="0 0 20 20" aria-hidden>
        <path
          d="M10 1.5l2.6 5.5 6 .8-4.4 4.2 1.1 6L10 15.1 4.7 18l1.1-6L1.4 7.8l6-.8z"
          fill="#F5B921"
        />
      </svg>
      {rating.toFixed(1)}
    </span>
  );
}

const STATUS_TONE: Record<string, string> = {
  pending: 'bg-[#fff6e0] text-[#9a6200] border-[#f5dca0]',
  accepted: 'bg-[#e6f7ef] text-[#0b6b43] border-[#bfe5d2]',
  declined: 'bg-[#fdeaf1] text-[#b0124a] border-[#f5c3d5]',
};

export function StatusChip({ status }: { status: string }) {
  return (
    <span
      className={`inline-flex rounded-full border px-2.5 py-0.5 text-[11px] font-semibold capitalize ${
        STATUS_TONE[status] ?? 'border-[var(--line)] text-[var(--ink-2)]'
      }`}
    >
      {status}
    </span>
  );
}

export function Stat({
  label,
  value,
  note,
}: {
  label: string;
  value: ReactNode;
  note?: string;
}) {
  return (
    <div className="rounded-2xl border border-[var(--line)] bg-white px-4 py-3.5">
      <p className="text-[11.5px] font-medium text-[var(--ink-3)]">{label}</p>
      <p className="mt-0.5 text-[22px] font-bold leading-tight tracking-[-0.02em] text-[var(--plum)]">
        {value}
      </p>
      {note && <p className="mt-0.5 text-[11.5px] text-[var(--ink-3)]">{note}</p>}
    </div>
  );
}

export function Toast({ message, onDone }: { message: string | null; onDone: () => void }) {
  useEffect(() => {
    if (!message) return;
    const t = setTimeout(onDone, 3200);
    return () => clearTimeout(t);
  }, [message, onDone]);
  if (!message) return null;
  return (
    <div
      role="status"
      className="fixed bottom-6 left-1/2 z-50 -translate-x-1/2 rounded-full bg-[var(--plum)] px-5 py-2.5
                 text-[13px] font-medium text-white shadow-[0_12px_32px_-8px_rgba(81,14,68,0.5)]"
    >
      {message}
    </div>
  );
}

export function Chip({
  active,
  onClick,
  children,
}: {
  active?: boolean;
  onClick?: () => void;
  children: ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`chip transition-colors ${
        active
          ? 'border-[var(--signal)] bg-[var(--signal-wash)] text-[var(--signal)]'
          : 'hover:border-[var(--ink-3)]'
      }`}
    >
      {children}
    </button>
  );
}
