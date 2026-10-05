import type {
  Ablation,
  BrandOverview,
  BrandSummary,
  CreatorMatch,
  NewProduct,
  Pitch,
  ProductMatches,
  Action,
  Creator,
  Discovered,
  DNA,
  FetchedProfile,
  Pilot,
  Rewards,
  Trust,
  OrderRow,
  OnboardingAnswers,
  FeedbackResponse,
  Goal,
  Metrics,
  Niche,
  Product,
  Recommendation,
  RecommendationsResponse,
  SimHistory,
  SimRun,
} from './types';

export const BASE = process.env.NEXT_PUBLIC_API_BASE ?? 'http://localhost:8000';

/** Product images are served by the API unless a seller supplied a full URL. */
export const imgSrc = (path?: string | null): string => {
  if (!path) return '';
  return /^(https?:|data:)/.test(path) ? path : `${BASE}${path}`;
};

export class ApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
  }
}

/* ------------------------------------------------------------------ wake-up
 * The demo backend runs on a free host that sleeps when idle. The first
 * request after a nap can take up to a minute, or fail while it boots. Requests
 * retry quietly, and the shell shows a "waking up" note meanwhile. */
type WakeListener = (waking: boolean) => void;
const wakeListeners = new Set<WakeListener>();
let waking = false;
function setWaking(next: boolean) {
  if (waking === next) return;
  waking = next;
  wakeListeners.forEach((fn) => fn(next));
}
export const apiWake = {
  subscribe(fn: WakeListener) {
    wakeListeners.add(fn);
    return () => {
      wakeListeners.delete(fn);
    };
  },
  isWaking: () => waking,
};

const RETRY_DELAYS_MS = [1500, 3000, 5000, 8000, 10000, 12000, 15000, 15000];
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response | null = null;
  // Only reads are retried: repeating a POST could record a tap twice.
  const retries = !init?.method || init.method === 'GET' ? RETRY_DELAYS_MS.length : 0;
  const slow = setTimeout(() => setWaking(true), 4000);
  try {
    for (let attempt = 0; ; attempt++) {
      try {
        response = await fetch(`${BASE}${path}`, {
          ...init,
          headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
          cache: 'no-store',
        });
        if (![502, 503, 504].includes(response.status)) break;
      } catch {
        response = null;
      }
      if (attempt >= retries) break;
      setWaking(true);
      await sleep(RETRY_DELAYS_MS[attempt]);
    }
  } finally {
    clearTimeout(slow);
  }
  if (!response) {
    setWaking(false);
    throw new ApiError(
      `No response from the API at ${BASE}. If this is the hosted demo, the server may still be ` +
        'waking up: wait a few seconds and try again.',
      0,
    );
  }
  setWaking(false);
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const detail =
      typeof body.detail === 'string' ? body.detail : `Request failed (${response.status})`;
    throw new ApiError(detail, response.status);
  }
  return response.json() as Promise<T>;
}

export const api = {
  health: () =>
    request<{ status: string; model_version: string; database: string; pgvector: boolean }>(
      '/health',
    ),

  listCreators: () => request<Creator[]>('/creators'),
  getCreator: (id: string) => request<Creator>(`/creator/${id}`),

  onboard: (payload: { handle: string; answers: OnboardingAnswers; consent: boolean; name?: string }) =>
    request<Creator>('/creator/onboard', { method: 'POST', body: JSON.stringify(payload) }),
  onboardingConnect: (handle: string) =>
    request<{ handle: string; fetched: FetchedProfile; scale: string; questions: string[] }>(
      `/onboarding/connect/${handle}`,
    ),
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  onboardingQuestions: () => request<Record<string, any>>('/onboarding/questions'),
  onboardingPreview: (payload: { handle: string; answers: OnboardingAnswers }) =>
    request<{ dna: DNA; fetched: FetchedProfile }>('/onboarding/preview', {
      method: 'POST',
      body: JSON.stringify({ ...payload, consent: true }),
    }),

  /** Top-K follows the creator's tier (5 / 8 / 4) unless topK is given. */
  recommendations: (id: string, opts: { topK?: number; mode?: 'personalised' | 'interleaved' | 'generic' } = {}) => {
    const q = new URLSearchParams({ category: 'bpc' });
    if (opts.topK) q.set('top_k', String(opts.topK));
    if (opts.mode && opts.mode !== 'personalised') q.set('mode', opts.mode);
    return request<RecommendationsResponse>(`/recommendations/${id}?${q.toString()}`);
  },

  rankProducts: (creatorId: string, productIds: string[]) =>
    request<Recommendation[]>('/rank-products', {
      method: 'POST',
      body: JSON.stringify({ creator_id: creatorId, product_ids: productIds }),
    }),

  products: (category?: string) =>
    request<Product[]>(`/products${category && category !== 'All' ? `?category=${category}` : ''}`),

  feedback: (payload: {
    creator_id: string;
    product_id: string;
    action: Action;
    reason?: string | null;
    served_score?: number | null;
    source?: string | null;
  }) => request<FeedbackResponse>('/feedback', { method: 'POST', body: JSON.stringify(payload) }),

  updateCreator: (
    id: string,
    payload: Partial<{ goal: Goal; price_min: number; price_max: number; avoid_categories: string[] }>,
  ) => request<Creator>(`/creator/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),

  metrics: () => request<Metrics>('/analytics/metrics'),
  trust: () => request<Trust>('/analytics/trust'),
  pilot: () => request<Pilot>('/analytics/pilot'),

  /* ------------------------------------------------- orders + Fit Rewards */
  rewards: (creatorId: string) => request<Rewards>(`/rewards/${creatorId}`),
  order: (payload: { creator_id: string; product_id: string; status: 'placed' | 'delivered' | 'returned' | 'cancelled' }) =>
    request<OrderRow>('/orders', { method: 'POST', body: JSON.stringify(payload) }),

  /* ----------------------------------------------------------------- demo */
  resetDemo: () => request<{ status: string; demo_creator_id: string }>('/demo/reset', { method: 'POST' }),

  /* ---------------------------------------------------------- brand side */
  brands: () => request<BrandSummary[]>('/brands'),
  brand: (name: string) => request<BrandOverview>(`/brands/${encodeURIComponent(name)}`),
  createProduct: (payload: NewProduct) =>
    request<Product>('/products', { method: 'POST', body: JSON.stringify(payload) }),
  productMatches: (id: string) => request<ProductMatches>(`/product/${id}/matches`),
  sendPitch: (payload: { product_id: string; creator_id: string; message?: string; incentive?: string | null }) =>
    request<Pitch>('/pitches', { method: 'POST', body: JSON.stringify(payload) }),
  pitches: (params: { creator_id?: string; brand?: string; product_id?: string }) => {
    const q = new URLSearchParams(
      Object.entries(params).filter(([, v]) => v) as [string, string][],
    ).toString();
    return request<Pitch[]>(`/pitches${q ? `?${q}` : ''}`);
  },
  respondPitch: (id: number, action: 'accept' | 'decline', reason?: string) =>
    request<Pitch>(`/pitches/${id}/respond`, {
      method: 'POST',
      body: JSON.stringify({ action, reason: reason ?? null }),
    }),

  /* ------------------------------------------------------- simulation */
  generateCreators: (count = 1, seed?: number) =>
    request<Creator[]>('/simulation/generate', {
      method: 'POST',
      body: JSON.stringify({ count, seed: seed ?? null }),
    }),

  runSimulation: (creatorId: string, rounds = 8, topK = 5, mode: 'personalised' | 'interleaved' = 'personalised') =>
    request<SimRun>('/simulation/run', {
      method: 'POST',
      body: JSON.stringify({ creator_id: creatorId, rounds, top_k: topK, mode }),
    }),

  simHistory: (creatorId: string) => request<SimHistory>(`/simulation/history/${creatorId}`),
  ablation: (creatorId: string) => request<Ablation>(`/simulation/ablation/${creatorId}`),
  discovered: (creatorId: string) => request<Discovered>(`/simulation/discovered/${creatorId}`),
  resetCreator: (creatorId: string) =>
    request<{ status: string }>(`/simulation/reset/${creatorId}`, { method: 'POST' }),
};

const KEY = 'cfe.creator_id';
const BRAND_KEY = 'cfe.brand';

/** Browser storage can be missing or blocked (private windows, previews). */
function store(key: string): { get: () => string | null; set: (v: string) => void; clear: () => void } {
  return {
    get: () => {
      try {
        return typeof window === 'undefined' ? null : window.localStorage.getItem(key);
      } catch {
        return null;
      }
    },
    set: (v: string) => {
      try {
        window.localStorage.setItem(key, v);
      } catch {
        /* the selection simply is not remembered */
      }
    },
    clear: () => {
      try {
        window.localStorage.removeItem(key);
      } catch {
        /* nothing to clear */
      }
    },
  };
}

export const brandSession = store(BRAND_KEY);
export const session = store(KEY);

export const fmt = {
  int: (n: number) => n.toLocaleString('en-IN'),
  rupees: (n: number) => `₹${Math.round(n).toLocaleString('en-IN')}`,
  compact: (n: number) =>
    n >= 10_000_000
      ? `${(n / 10_000_000).toFixed(1)}Cr`
      : n >= 100_000
        ? `${(n / 100_000).toFixed(1)}L`
        : n >= 1_000
          ? `${(n / 1_000).toFixed(1)}K`
          : String(n),
  pct: (n: number, digits = 1) => `${(n * 100).toFixed(digits)}%`,
};
