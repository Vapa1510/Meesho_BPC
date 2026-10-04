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
export const imgSrc = (path: string): string =>
  /^(https?:|data:)/.test(path) ? path : `${BASE}${path}`;

export class ApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${BASE}${path}`, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
      cache: 'no-store',
    });
  } catch {
    throw new ApiError(
      `No response from the API at ${BASE}. Start the backend with ` +
        '"uvicorn app.main:app --port 8000".',
      0,
    );
  }
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

  recommendations: (id: string, topK = 5) =>
    request<RecommendationsResponse>(`/recommendations/${id}?category=bpc&top_k=${topK}`),

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
  }) => request<FeedbackResponse>('/feedback', { method: 'POST', body: JSON.stringify(payload) }),

  updateCreator: (
    id: string,
    payload: Partial<{ goal: Goal; price_min: number; price_max: number; avoid_categories: string[] }>,
  ) => request<Creator>(`/creator/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),

  metrics: () => request<Metrics>('/analytics/metrics'),

  /* ---------------------------------------------------------- brand side */
  brands: () => request<BrandSummary[]>('/brands'),
  brand: (name: string) => request<BrandOverview>(`/brands/${encodeURIComponent(name)}`),
  createProduct: (payload: NewProduct) =>
    request<Product>('/products', { method: 'POST', body: JSON.stringify(payload) }),
  productMatches: (id: string) => request<ProductMatches>(`/product/${id}/matches`),
  sendPitch: (payload: { product_id: string; creator_id: string; message?: string }) =>
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

  runSimulation: (creatorId: string, rounds = 8, topK = 5) =>
    request<SimRun>('/simulation/run', {
      method: 'POST',
      body: JSON.stringify({ creator_id: creatorId, rounds, top_k: topK }),
    }),

  simHistory: (creatorId: string) => request<SimHistory>(`/simulation/history/${creatorId}`),
  ablation: (creatorId: string) => request<Ablation>(`/simulation/ablation/${creatorId}`),
  discovered: (creatorId: string) => request<Discovered>(`/simulation/discovered/${creatorId}`),
  resetCreator: (creatorId: string) =>
    request<{ status: string }>(`/simulation/reset/${creatorId}`, { method: 'POST' }),
};

const KEY = 'cfe.creator_id';
const BRAND_KEY = 'cfe.brand';

export const brandSession = {
  get: (): string | null =>
    typeof window === 'undefined' ? null : window.localStorage.getItem(BRAND_KEY),
  set: (name: string) => window.localStorage.setItem(BRAND_KEY, name),
};

export const session = {
  get: (): string | null =>
    typeof window === 'undefined' ? null : window.localStorage.getItem(KEY),
  set: (id: string) => window.localStorage.setItem(KEY, id),
};

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
