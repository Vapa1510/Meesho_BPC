'use client';

/**
 * Every view in this console looks at the engine through one creator's eyes,
 * so the selected creator is app-wide state rather than a per-page concern.
 */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';

import { api, session } from '@/lib/api';
import type { Creator } from '@/lib/types';
import { DEMO_CREATOR_ID } from '@/lib/types';

interface CreatorStore {
  creators: Creator[];
  current: Creator | null;
  loading: boolean;
  error: string | null;
  select: (id: string) => void;
  refresh: () => Promise<void>;
  /** Bumped whenever feedback or a simulation changes learned state, so views
   *  that depend on it can re-fetch without each one polling. */
  revision: number;
  invalidate: () => void;
}

const Ctx = createContext<CreatorStore | null>(null);

export function CreatorProvider({ children }: { children: ReactNode }) {
  const [creators, setCreators] = useState<Creator[]>([]);
  const [currentId, setCurrentId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [revision, setRevision] = useState(0);

  const refresh = useCallback(async () => {
    setError(null);
    try {
      const list = await api.listCreators();
      setCreators(list);
      setCurrentId((existing) => {
        if (existing && list.some((c) => c.creator_id === existing)) return existing;
        const stored = session.get();
        if (stored && list.some((c) => c.creator_id === stored)) return stored;
        // Someone arriving from a QR code in the deck lands on Riya, the deck's persona.
        if (list.some((c) => c.creator_id === DEMO_CREATOR_ID)) return DEMO_CREATOR_ID;
        return list[0]?.creator_id ?? null;
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load creators.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const select = useCallback((id: string) => {
    setCurrentId(id);
    session.set(id);
  }, []);

  const value = useMemo<CreatorStore>(
    () => ({
      creators,
      current: creators.find((c) => c.creator_id === currentId) ?? null,
      loading,
      error,
      select,
      refresh,
      revision,
      invalidate: () => setRevision((r) => r + 1),
    }),
    [creators, currentId, loading, error, select, refresh, revision],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useCreators(): CreatorStore {
  const value = useContext(Ctx);
  if (!value) throw new Error('useCreators must be used inside CreatorProvider');
  return value;
}
