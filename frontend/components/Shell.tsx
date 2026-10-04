'use client';

import { usePathname, useRouter } from 'next/navigation';
import type { ReactNode } from 'react';

const NAV = [
  { href: '/recommendations', label: 'Home', icon: 'home' },
  { href: '/catalogue', label: 'Browse', icon: 'grid' },
  { href: '/insights', label: 'Insights', icon: 'chart' },
  { href: '/profile', label: 'Profile', icon: 'user' },
];

function NavIcon({ name, active }: { name: string; active: boolean }) {
  const fill = active ? '#E8195F' : '#8E8AA3';
  const paths: Record<string, string> = {
    home: 'M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8z',
    grid: 'M3 3h8v8H3zm10 0h8v8h-8zM3 13h8v8H3zm10 0h8v8h-8z',
    chart: 'M4 11h4v9H4zm6-7h4v16h-4zm6 9h4v7h-4z',
    user: 'M12 12c2.2 0 4-1.8 4-4s-1.8-4-4-4-4 1.8-4 4 1.8 4 4 4zm0 2c-2.7 0-8 1.3-8 4v2h16v-2c0-2.7-5.3-4-8-4z',
  };
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" aria-hidden="true">
      <path d={paths[name]} fill={fill} />
    </svg>
  );
}

export function Shell({
  title,
  children,
  onBack,
  showNav = true,
  footer,
}: {
  title: string;
  children: ReactNode;
  onBack?: () => void;
  showNav?: boolean;
  footer?: ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();

  return (
    <main className="flex min-h-screen items-center justify-center p-4">
      <div className="phone">
        {/* status bar */}
        <div className="pointer-events-none absolute inset-x-0 top-0 z-10 flex items-center justify-between px-6 pt-2 text-[12px] font-semibold text-plum-deep">
          <span>9:41</span>
          <span className="absolute left-1/2 top-2 h-[10px] w-[70px] -translate-x-1/2 rounded-full bg-plum-deep" />
          <span className="relative inline-block h-[9px] w-[17px] rounded-[2px] border-[1.5px] border-plum-deep">
            <span className="absolute inset-[1px] right-[6px] rounded-[1px] bg-plum-deep" />
          </span>
        </div>

        <header className="app-bar">
          {onBack && (
            <button
              onClick={onBack}
              aria-label="Go back"
              className="absolute left-3 top-8 p-1"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true">
                <path
                  d="M15 5l-7 7 7 7"
                  fill="none"
                  stroke="#2A1450"
                  strokeWidth="3"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </button>
          )}
          {title}
        </header>

        <div className="scroll-area">{children}</div>

        {footer && <div className="shrink-0 border-t border-hair px-4 py-3">{footer}</div>}

        {showNav && (
          <nav className="nav-bar">
            {NAV.map((item) => (
              <button
                key={item.href}
                onClick={() => router.push(item.href)}
                aria-label={item.label}
                aria-current={pathname.startsWith(item.href) ? 'page' : undefined}
                className="px-3"
              >
                <NavIcon name={item.icon} active={pathname.startsWith(item.href)} />
              </button>
            ))}
          </nav>
        )}
      </div>
    </main>
  );
}

export function Loading({ label = 'Loading' }: { label?: string }) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-3 py-16 text-mute">
      <span className="h-7 w-7 animate-spin rounded-full border-2 border-pink border-t-transparent" />
      <p className="text-[13px]">{label}</p>
    </div>
  );
}

export function ErrorNote({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="card mt-6 space-y-3 border-[#F3B5C8] bg-[#FFF5F8] p-4">
      <p className="text-[13px] font-semibold text-plum">Something went wrong</p>
      <p className="text-[13px] leading-relaxed text-sub">{message}</p>
      {onRetry && (
        <button onClick={onRetry} className="btn-outline h-9 text-[13px]">
          Try again
        </button>
      )}
    </div>
  );
}
