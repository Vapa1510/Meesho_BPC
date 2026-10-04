'use client';

/** The brand (seller) counterpart of CreatorContext: which seller's workspace is open. */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';

import { api, brandSession } from '@/lib/api';
import type { BrandSummary } from '@/lib/types';

interface BrandStore {
  brands: BrandSummary[];
  current: BrandSummary | null;
  loading: boolean;
  error: string | null;
  select: (name: string) => void;
  refresh: () => Promise<void>;
  /** Bumped when an offer is sent or a product is listed. */
  revision: number;
  invalidate: () => void;
}

const Ctx = createContext<BrandStore | null>(null);

export function BrandProvider({ children }: { children: ReactNode }) {
  const [brands, setBrands] = useState<BrandSummary[]>([]);
  const [name, setName] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [revision, setRevision] = useState(0);

  const refresh = useCallback(async () => {
    setError(null);
    try {
      const list = await api.brands();
      setBrands(list);
      setName((existing) => {
        if (existing && list.some((b) => b.brand === existing)) return existing;
        const stored = brandSession.get();
        if (stored && list.some((b) => b.brand === stored)) return stored;
        return list[0]?.brand ?? null;
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load brands.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const select = useCallback((n: string) => {
    setName(n);
    brandSession.set(n);
  }, []);

  const value = useMemo<BrandStore>(
    () => ({
      brands,
      current: brands.find((b) => b.brand === name) ?? null,
      loading,
      error,
      select,
      refresh,
      revision,
      invalidate: () => setRevision((r) => r + 1),
    }),
    [brands, name, loading, error, select, refresh, revision],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useBrands(): BrandStore {
  const value = useContext(Ctx);
  if (!value) throw new Error('useBrands must be used inside BrandProvider');
  return value;
}
