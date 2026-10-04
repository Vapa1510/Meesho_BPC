export type Goal = 'reach' | 'revenue' | 'brand';
export type Niche = 'Skincare' | 'Makeup' | 'Haircare' | 'Personal Care';
export type Action = 'impression' | 'click' | 'save' | 'promote' | 'skip';

export interface IntentScores {
  trend: number;
  commerce: number;
  brand: number;
}

export interface Creator {
  creator_id: string;
  name: string;
  tier_label: string;
  followers: number;
  niche: string;
  sub_niches: string[];
  bio: string;
  audience_label: string;
  audience_age_min: number;
  audience_age_max: number;
  audience_tiers: string[];
  price_min: number;
  price_max: number;
  goal: Goal;
  intent_scores: IntentScores;
  avoid_categories: string[];
  engagement_rate: number;
  scale?: string;
  cell?: string;
  primary_intent?: string;
  secondary_intent?: string | null;
  intent_separation?: number | null;
  preferred_price?: number | null;
  niche_shares?: Record<string, number> | null;
  content_formats?: string[] | null;
  positioning?: Record<string, number> | null;
  dna_sources?: Record<string, string> | null;
  questions_asked?: number | null;
}

export interface OnboardingAnswers {
  q1?: string[];
  q2?: string;
  q3?: string[];
  q4?: string[];
  q5?: string;
  q6?: string;
  q7?: string[];
}

export interface IntentSummary {
  scores: { trend: number; commerce: number; brand: number };
  primary: 'trend' | 'commerce' | 'brand';
  secondary: string | null;
  separation: number;
  needs_follow_up: boolean;
  threshold: number;
}

export interface DNA {
  scale: string;
  intent: IntentSummary;
  niche: string;
  niche_shares: Record<string, number>;
  content_formats: string[];
  preferred_price: number | null;
  price_min: number;
  price_max: number;
  positioning: Record<string, number>;
  audience_age_min: number;
  audience_age_max: number;
  audience_tiers: string[];
  avoid_categories: string[];
  sources: Record<string, string>;
  questions_asked: number;
}

export interface FetchedProfile {
  name: string;
  followers: number;
  city: string;
  audience: { age_min: number; age_max: number; tiers: string[] } | null;
  content_history: Record<string, number>;
  hashtags: string[];
  posts: number;
}

export interface Signal {
  name: string;
  label: string;
  score: number;
  weight: number;
  contribution: number;
}

export interface Recommendation {
  product_id: string;
  rank: number;
  fit_score: number;
  title: string;
  price: number;
  category: string;
  art_key: string;
  brand: string;
  image: string;
  rating: number;
  trend_stage: string;
  trend_score: number;
  reason_codes: string[];
  reasons: string[];
  caveats: string[];
  confidence: 'LOW' | 'MEDIUM' | 'HIGH';
  content_angle: string;
  signals: Signal[];
  price_fit: number;
  base_score: number;
  learning_multiplier: number;
  penalty_saturation?: number;
  penalty_returns?: number;
  cell?: string;
  notes: string[];
}

export interface PipelineStats {
  catalogue_size: number;
  eligible_count: number;
  candidate_count: number;
  pool_ratio: number;
  rejected_by_rule: Record<string, string[]>;
}

export interface RecommendationsResponse {
  creator_id: string;
  model_version: string;
  generated_at: string;
  recommendations: Recommendation[];
  pipeline: PipelineStats;
  learning_notes: string[];
}

export interface Product {
  product_id: string;
  title: string;
  category: string;
  sub_category: string;
  price: number;
  description: string;
  tags: string[];
  art_key: string;
  brand: string;
  image: string;
  is_new: boolean;
  rating: number;
  review_count: number;
  seller_rating: number;
  return_rate: number;
  orders_30d: number;
  conversion_rate: number;
  nmv_30d: number;
  trend_score: number;
  trend_stage: string;
  creator_saturation: number;
  in_stock: boolean;
}

export interface FeedbackResponse {
  status: string;
  event_id: number;
  learning_notes: string[];
  message: string;
}

/* ---------------------------------------------------------- simulation */
export interface ServedItem {
  rank: number;
  product_id: string;
  title: string;
  category: string;
  price: number;
  fit_score: number;
  action: 'promote' | 'save' | 'skip';
  reason: string | null;
  latent_utility: number;
}

export interface SimRound {
  round_number: number;
  served: ServedItem[];
  promotes: number;
  saves: number;
  skips: number;
  nmv: number;
  ndcg_at_k: number;
  precision_at_k: number;
  mean_served_utility: number;
  utility_capture: number;
}

export interface SimRun {
  creator_id: string;
  rounds: SimRound[];
  first: SimRound;
  last: SimRound;
  ndcg_improvement: number;
  utility_improvement: number;
  total_nmv: number;
  summary: string;
}

export interface SimHistory {
  creator_id: string;
  rounds_run: number;
  snapshots: {
    round: number;
    ndcg_at_k: number;
    precision_at_k: number;
    mean_served_utility: number;
    utility_capture: number;
    promotes: number;
    saves: number;
    skips: number;
    nmv: number;
  }[];
}

export interface AblationMetrics {
  ndcg_at_k: number;
  precision_at_k: number;
  mean_served_utility: number;
  best_possible_utility: number;
  utility_capture: number;
  k: number;
}

export interface Ablation {
  with_learning: AblationMetrics;
  without_learning: AblationMetrics;
  ndcg_delta: number;
  utility_delta: number;
  verdict: string;
}

export interface Discovered {
  creator_id: string;
  events_seen: number;
  categories: {
    category: string;
    stated: number;
    learned_multiplier: number;
    true_affinity: number;
  }[];
  stated_price_band: [number, number];
  true_price_band: [number, number];
  price_sensitivity_learned: number;
  notes: string[];
}

export interface Metrics {
  ctr: number;
  conversion_rate: number;
  recommendation_acceptance: number;
  nmv_per_creator: number;
  model_performance: {
    ndcg_at_k: number | null;
    precision_at_k: number | null;
    utility_capture: number | null;
    creators_evaluated: number;
    status: string;
  };
  volumes: Record<string, number>;
  actions: Record<string, number>;
  rejection_reasons: Record<string, number>;
}

export const REJECTION_REASONS: { value: string; label: string }[] = [
  { value: 'too_expensive', label: 'Too expensive' },
  { value: 'not_my_niche', label: 'Not my niche' },
  { value: 'already_promoted', label: 'Already promoted' },
  { value: 'audience_wont_care', label: "Audience won't care" },
  { value: 'dont_trust_product', label: "Don't trust product" },
  { value: 'not_trending', label: 'Not trending' },
  { value: 'angle_unclear', label: 'Angle unclear' },
];

/**
 * Fit scores are magnitude on a single scale, not categories, so they get one
 * hue stepped light-to-dark rather than a four-colour band scheme. A
 * categorical set of four here failed CVD separation and, for the amber/clay
 * pair, failed even for normal vision — and it was encoding nothing the number
 * beside it did not already say.
 */
const SCORE_RAMP = ['#f3a3c0', '#ee6c9b', '#e8195f', '#c01165'] as const;

export function scoreTone(score: number): string {
  if (score >= 85) return SCORE_RAMP[3];
  if (score >= 78) return SCORE_RAMP[2];
  if (score >= 68) return SCORE_RAMP[1];
  return SCORE_RAMP[0];
}

/** Two series, validated for CVD separation (worst adjacent ΔE 18.0 protan). */
export const SERIES = {
  primary: '#e8195f',
  secondary: '#1f6fd0',
} as const;


/* ------------------------------------------------------------ brand side */
export interface CreatorMatch {
  creator_id: string;
  name: string;
  niche: string;
  tier_label: string;
  followers: number;
  goal: Goal;
  price_min: number;
  price_max: number;
  fit_score: number;
  eligible: boolean;
  blocked_by: string | null;
  signals: Signal[];
  reasons: string[];
  caveats: string[];
  est_reach: number;
  est_orders: number;
  est_nmv: number;
  offer_status: 'pending' | 'accepted' | 'declined' | null;
}

export interface ProductDiagnosis {
  creators_total: number;
  reachable: number;
  strong_matches: number;
  blockers: Record<string, number>;
  price_in_band: number;
  median_band_ceiling: number;
  weakest: string[];
  tips: string[];
}

export interface FeedbackSummary {
  promotes: number;
  saves: number;
  skips: number;
  skip_reasons: Record<string, number>;
  offers_sent: number;
  offers_accepted: number;
  offers_declined: number;
}

export interface ProductMatches {
  product: Product;
  matches: CreatorMatch[];
  diagnosis: ProductDiagnosis;
  feedback: FeedbackSummary;
}

export interface Pitch {
  id: number;
  product: Product;
  creator_id: string;
  creator_name: string;
  brand: string;
  message: string;
  fit_score: number;
  status: 'pending' | 'accepted' | 'declined';
  reason: string | null;
  created_at: string;
  responded_at: string | null;
}

export interface BrandSummary {
  brand: string;
  products: number;
  avg_rating: number;
  nmv_30d: number;
  offers_sent: number;
  offers_accepted: number;
  image: string;
}

export interface BrandOverview {
  brand: string;
  products: Product[];
  offers_sent: number;
  offers_pending: number;
  offers_accepted: number;
  offers_declined: number;
  acceptance_rate: number | null;
  nmv_30d: number;
}

export interface NewProduct {
  title: string;
  brand: string;
  category: Niche;
  sub_category: string;
  price: number;
  description: string;
  tags: string[];
  pack: string;
  target_age_min: number;
  target_age_max: number;
  target_tiers: string[];
  image_url: string | null;
}

export const PACKS: { value: string; label: string }[] = [
  { value: 'dropper', label: 'Serum dropper' },
  { value: 'tube', label: 'Tube' },
  { value: 'jar', label: 'Cream jar' },
  { value: 'lipstick', label: 'Lipstick' },
  { value: 'compact', label: 'Compact' },
  { value: 'palette', label: 'Palette' },
  { value: 'pencil', label: 'Pencil' },
  { value: 'pump', label: 'Pump bottle' },
  { value: 'oil', label: 'Oil bottle' },
  { value: 'spray', label: 'Spray' },
  { value: 'nail', label: 'Nail polish' },
  { value: 'patch', label: 'Patches' },
];

export const REASON_LABEL: Record<string, string> = Object.fromEntries(
  REJECTION_REASONS.map((r) => [r.value, r.label]),
);

export const INTENT_LABEL: Record<string, string> = {
  reach: 'Trend-led', revenue: 'Commerce-led', brand: 'Brand-led',
  trend: 'Trend-led', commerce: 'Commerce-led',
};
export const TOP_K_BY_SCALE: Record<string, number> = { Emerging: 5, Growth: 8, Established: 4 };
