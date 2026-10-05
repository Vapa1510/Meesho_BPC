'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useRef, useState, type ReactNode } from 'react';

import { useBrands } from '@/components/BrandContext';
import { useCreators } from '@/components/CreatorContext';
import { DEMO_CREATOR_ID, INTENT_LABEL } from '@/lib/types';
import { Avatar } from '@/components/ui';
import { api, apiWake, fmt } from '@/lib/api';

type Role = 'creator' | 'brand' | 'lab';

const ROLES: { id: Role; label: string; short: string; href: string; tag?: string }[] = [
  { id: 'creator', label: 'Creator', short: 'Creator', href: '/creator' },
  // The brand view is the same engine seen from the product side: a Phase 2
  // extension, not the core of the pitch.
  { id: 'brand', label: 'Brand view', short: 'Brand', href: '/brand', tag: 'extension' },
  { id: 'lab', label: 'Engine lab', short: 'Lab', href: '/lab/pipeline' },
];

const NAV: Record<Role, { href: string; label: string; exact?: boolean }[]> = {
  creator: [
    { href: '/creator', label: 'Discover', exact: true },
    { href: '/creator/catalogue', label: 'Catalogue' },
    { href: '/creator/offers', label: 'Offers' },
    { href: '/creator/profile', label: 'Profile' },
    { href: '/creator/onboard', label: 'Onboarding' },
  ],
  brand: [
    { href: '/brand', label: 'Dashboard', exact: true },
    { href: '/brand/new', label: 'List a product' },
    { href: '/brand/offers', label: 'Offers sent' },
  ],
  lab: [
    { href: '/lab/pipeline', label: 'Pipeline' },
    { href: '/lab/metrics', label: 'Trust metrics' },
    { href: '/lab/pilot', label: 'Pilot test' },
    { href: '/lab/simulate', label: 'Simulation' },
  ],
};

function roleOf(pathname: string): Role | null {
  if (pathname.startsWith('/creator')) return 'creator';
  if (pathname.startsWith('/brand')) return 'brand';
  if (pathname.startsWith('/lab')) return 'lab';
  return null;
}

function useOutsideClose(open: boolean, close: () => void) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) close();
    };
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && close();
    document.addEventListener('mousedown', onClick);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onClick);
      document.removeEventListener('keydown', onKey);
    };
  }, [open, close]);
  return ref;
}

function Switcher<T>({
  items,
  currentKey,
  getKey,
  render,
  onSelect,
  trigger,
}: {
  items: T[];
  currentKey: string | null;
  getKey: (item: T) => string;
  render: (item: T) => ReactNode;
  onSelect: (key: string) => void;
  trigger: ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const ref = useOutsideClose(open, () => setOpen(false));
  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-haspopup="listbox"
        className="flex items-center gap-2.5 rounded-full border border-[var(--line-strong)] bg-white py-1.5 pl-1.5 pr-3.5
                   text-left transition-colors hover:border-[var(--signal)]"
      >
        {trigger}
        <svg width="10" height="10" viewBox="0 0 10 10" aria-hidden className="text-[var(--ink-3)]">
          <path d="M1 3l4 4 4-4" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
        </svg>
      </button>
      {open && (
        <div
          role="listbox"
          className="absolute right-0 top-full z-40 mt-2 max-h-[360px] w-[300px] overflow-y-auto rounded-2xl
                     border border-[var(--line)] bg-white p-1.5 shadow-[0_18px_40px_-12px_rgba(81,14,68,0.28)]"
        >
          {items.map((item) => {
            const key = getKey(item);
            return (
              <button
                key={key}
                role="option"
                aria-selected={key === currentKey}
                onClick={() => {
                  onSelect(key);
                  setOpen(false);
                }}
                className={`flex w-full items-center gap-3 rounded-xl px-2.5 py-2 text-left hover:bg-[var(--signal-wash)] ${
                  key === currentKey ? 'bg-[var(--signal-wash)]' : ''
                }`}
              >
                {render(item)}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

function AccountSwitcher({ role }: { role: Role }) {
  const creators = useCreators();
  const brands = useBrands();

  if (role === 'brand') {
    const b = brands.current;
    if (!b) return null;
    return (
      <Switcher
        items={brands.brands}
        currentKey={b.brand}
        getKey={(x) => x.brand}
        onSelect={brands.select}
        trigger={
          <>
            <Avatar name={b.brand} size={30} />
            <span className="leading-tight">
              <span className="block max-w-[150px] truncate text-[12.5px] font-semibold">{b.brand}</span>
              <span className="block text-[11px] text-[var(--ink-3)]">{b.products} products</span>
            </span>
          </>
        }
        render={(x) => (
          <>
            <Avatar name={x.brand} size={32} />
            <span className="min-w-0 flex-1">
              <span className="block truncate text-[13px] font-semibold">{x.brand}</span>
              <span className="block text-[11.5px] text-[var(--ink-3)]">
                {x.products} products · {fmt.compact(x.nmv_30d)} NMV
              </span>
            </span>
          </>
        )}
      />
    );
  }

  const c = creators.current;
  if (!c) return null;
  return (
    <Switcher
      items={creators.creators}
      currentKey={c.creator_id}
      getKey={(x) => x.creator_id}
      onSelect={creators.select}
      trigger={
        <>
          <Avatar name={c.name} seed={c.creator_id} size={30} />
          <span className="leading-tight">
            <span className="block max-w-[150px] truncate text-[12.5px] font-semibold">{c.name}</span>
            <span className="block text-[11px] text-[var(--ink-3)]">
              {c.niche} · {fmt.compact(c.followers)}
            </span>
          </span>
        </>
      }
      render={(x) => (
        <>
          <Avatar name={x.name} seed={x.creator_id} size={32} />
          <span className="min-w-0 flex-1">
            <span className="flex items-center gap-1.5">
              <span className="truncate text-[13px] font-semibold">{x.name}</span>
              {x.creator_id === DEMO_CREATOR_ID && (
                <span className="shrink-0 rounded-full bg-[var(--signal-wash)] px-1.5 py-px text-[9.5px] font-bold uppercase tracking-wide text-[var(--signal)]">
                  deck
                </span>
              )}
            </span>
            <span className="block text-[11.5px] text-[var(--ink-3)]">
              {x.niche} · {x.primary_intent ?? INTENT_LABEL[x.goal] ?? x.goal} · ₹{x.price_min}–{x.price_max}
            </span>
          </span>
        </>
      )}
    />
  );
}

function Health() {
  const [ok, setOk] = useState<boolean | null>(null);
  useEffect(() => {
    api.health().then(() => setOk(true)).catch(() => setOk(false));
  }, []);
  return (
    <span className="flex items-center gap-1.5 text-[11.5px] text-[var(--ink-3)]" title={ok === false ? 'API unreachable' : 'API live'}>
      <span
        className={`h-[7px] w-[7px] rounded-full ${
          ok === null ? 'bg-[var(--line-strong)]' : ok ? 'bg-[var(--green)]' : 'bg-[var(--signal)]'
        }`}
      />
      <span className="hidden sm:inline">{ok === false ? 'API unreachable' : ok ? 'API live' : 'Connecting'}</span>
    </span>
  );
}

/** Shown while the free-tier backend wakes up from idle (first visit after a pause). */
function WakingBanner() {
  const [waking, setWaking] = useState(false);
  useEffect(() => apiWake.subscribe(setWaking), []);
  if (!waking) return null;
  return (
    <div role="status" className="border-b border-[#f5dca0] bg-[#fff8e6] px-4 py-2 text-center text-[12.5px] text-[#7a5200] sm:px-6">
      Waking the demo server. Free hosting sleeps when idle, so the first load can take up to a minute; it is quick after that.
    </div>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const role = roleOf(pathname);

  return (
    <div className="min-h-screen">
      <div className="h-[4px] w-full" style={{ background: 'var(--grad)' }} />
      <header className="sticky top-0 z-30 border-b border-[var(--line)] bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-[1320px] flex-wrap items-center gap-x-4 gap-y-2 px-4 py-2.5 sm:px-6 md:h-[64px] md:flex-nowrap md:py-0">
          <Link href="/" className="flex shrink-0 items-center gap-2.5">
            <span
              className="flex h-9 w-9 items-center justify-center rounded-xl text-[17px] font-extrabold text-white"
              style={{ background: 'linear-gradient(135deg, #e8195f, #c01165)' }}
            >
              F
            </span>
            <span className="text-[15px] font-bold tracking-[-0.02em] text-[var(--plum)]">Fit Engine</span>
          </Link>

          <div className="order-2 ml-auto flex items-center gap-3 md:order-3 md:ml-0">
            <Health />
            {role && <AccountSwitcher role={role} />}
          </div>

          <nav
            aria-label="Workspace"
            className="order-3 flex w-full justify-center rounded-full border border-[var(--line)] bg-[var(--canvas)] p-1 md:order-2 md:mx-auto md:w-auto"
          >
            {ROLES.map((r) => (
              <Link
                key={r.id}
                href={r.href}
                aria-current={role === r.id ? 'page' : undefined}
                className={`flex flex-1 items-center justify-center gap-1.5 whitespace-nowrap rounded-full px-3 py-1.5 text-[13px] font-semibold transition-colors md:flex-none md:px-4 ${
                  role === r.id
                    ? 'bg-[var(--signal)] text-white'
                    : 'text-[var(--ink-2)] hover:text-[var(--signal)]'
                }`}
              >
                <span className="sm:hidden">{r.short}</span>
                <span className="hidden sm:inline">{r.label}</span>
                {r.tag && (
                  <span
                    className={`hidden rounded-full px-1.5 py-px text-[9.5px] font-semibold uppercase tracking-wide sm:inline ${
                      role === r.id ? 'bg-white/25 text-white' : 'bg-white text-[var(--ink-3)]'
                    }`}
                  >
                    {r.tag}
                  </span>
                )}
              </Link>
            ))}
          </nav>
        </div>

        {role && (
          <div className="mx-auto flex max-w-[1320px] gap-6 overflow-x-auto px-4 sm:px-6 [scrollbar-width:none]">
            {NAV[role].map((item) => {
              const active = item.exact ? pathname === item.href : pathname.startsWith(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  aria-current={active ? 'page' : undefined}
                  className="tab shrink-0 whitespace-nowrap"
                >
                  {item.label}
                </Link>
              );
            })}
          </div>
        )}
        <WakingBanner />
      </header>

      <main className="mx-auto max-w-[1320px]">{children}</main>
    </div>
  );
}

export function PageHeader({
  title,
  description,
  actions,
}: {
  title: string;
  description?: string;
  actions?: ReactNode;
}) {
  return (
    <header className="flex flex-wrap items-end justify-between gap-4 px-4 pb-2 pt-6 sm:px-6 sm:pt-8">
      <div className="max-w-[64ch]">
        <h1 className="text-[22px] font-bold leading-tight tracking-[-0.025em] text-[var(--plum)] sm:text-[26px]">
          {title}
        </h1>
        {description && (
          <p className="mt-1.5 text-[13.5px] leading-relaxed text-[var(--ink-2)]">{description}</p>
        )}
      </div>
      {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
    </header>
  );
}

export function Loading({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-3 px-6 py-16 text-[13px] text-[var(--ink-3)]">
      <span
        className="h-4 w-4 animate-spin rounded-full border-2 border-[var(--signal)] border-t-transparent"
        aria-hidden
      />
      {label}
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="mx-6 my-6 max-w-[70ch] rounded-2xl border border-[#f5c3d5] bg-[#fff6f9] p-5">
      <p className="text-[14px] font-semibold text-[var(--plum)]">That request did not complete</p>
      <p className="mt-1.5 text-[13px] leading-relaxed text-[var(--ink-2)]">{message}</p>
      {onRetry && (
        <button className="btn-quiet btn-sm mt-3" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  );
}

export function EmptyState({
  title,
  body,
  action,
}: {
  title: string;
  body: string;
  action?: ReactNode;
}) {
  return (
    <div className="mx-6 my-6 max-w-[70ch] rounded-2xl border border-dashed border-[var(--line-strong)] bg-white p-6">
      <p className="text-[14px] font-semibold">{title}</p>
      <p className="mt-1.5 text-[13px] leading-relaxed text-[var(--ink-2)]">{body}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
