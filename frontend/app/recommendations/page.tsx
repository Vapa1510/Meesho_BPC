'use client';

/** Screen 3 — Recommendations Dashboard. The personalised Top 5. */
import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';

import { FitBadge } from '@/components/Fit';
import { ProductThumb } from '@/components/ProductArt';
import { ErrorNote, Loading, Shell } from '@/components/Shell';
import { api, session } from '@/lib/api';
import type { Creator, RecommendationsResponse } from '@/lib/types';

export default function RecommendationsPage() {
  const router = useRouter();
  const [data, setData] = useState<RecommendationsResponse | null>(null);
  const [creator, setCreator] = useState<Creator | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showPipeline, setShowPipeline] = useState(false);

  const load = useCallback(async () => {
    const creatorId = session.get();
    if (!creatorId) {
      router.replace('/');
      return;
    }
    setError(null);
    try {
      const [profile, recommendations] = await Promise.all([
        api.getCreator(creatorId),
        api.recommendations(creatorId, 5),
      ]);
      setCreator(profile);
      setData(recommendations);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load recommendations.');
    }
  }, [router]);

  useEffect(() => {
    void load();
  }, [load]);

  if (error) {
    return (
      <Shell title="Recommendations">
        <ErrorNote message={error} onRetry={load} />
      </Shell>
    );
  }
  if (!data || !creator) {
    return (
      <Shell title="Recommendations">
        <Loading label="Scoring the catalogue" />
      </Shell>
    );
  }

  const { pipeline } = data;

  return (
    <Shell title="Recommendations">
      <div className="space-y-3 pb-2">
        <div>
          <h1 className="text-[16px] font-bold text-plum-deep">Your Top BPC Opportunities</h1>
          <p className="text-[11px] text-mute">
            Ranked for {creator.name.split(' ')[0]} · {data.model_version}
          </p>
        </div>

        {data.learning_notes.length > 0 && (
          <div className="rounded-lg border border-[#E3D8F6] bg-[#F4EEFB] p-2.5">
            <p className="text-[11px] font-bold text-[#3A2290]">Adjusted from your feedback</p>
            <ul className="mt-1 space-y-0.5">
              {data.learning_notes.map((note) => (
                <li key={note} className="text-[11px] leading-snug text-[#3A2290]">
                  · {note}
                </li>
              ))}
            </ul>
          </div>
        )}

        <ol className="space-y-2">
          {data.recommendations.map((rec) => (
            <li key={rec.product_id}>
              <button
                onClick={() => router.push(`/product/${rec.product_id}`)}
                className={`card flex w-full items-center gap-3 p-2.5 text-left transition active:scale-[0.99] ${
                  rec.rank === 1 ? 'border-[#F5B7CF] bg-[#FFF8FB]' : ''
                }`}
              >
                <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-[#EEE9F4] text-[11px] font-bold text-sub">
                  {rec.rank}
                </span>
                <ProductThumb artKey={rec.art_key} size={38} />
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-[13px] font-bold leading-tight text-plum-deep">
                    {rec.title}
                  </span>
                  <span className="block text-[12px] font-semibold text-[#7A0A3A]">
                    ₹{rec.price}
                  </span>
                  {/* A compact, *distinguishing* line. The top reason is
                      nearly always "audience fit", which reads as noise when
                      it is repeated down the whole list. */}
                  <span className="mt-0.5 block truncate text-[11px] text-mute">
                    {rec.category} · {rec.trend_stage} · {rec.confidence}
                  </span>
                </span>
                <FitBadge score={rec.fit_score} />
              </button>
            </li>
          ))}
        </ol>

        {/* The funnel, shown rather than claimed. */}
        <button
          onClick={() => setShowPipeline((open) => !open)}
          className="w-full rounded-lg border border-pink-line bg-pink-pale px-3 py-2 text-left"
          aria-expanded={showPipeline}
        >
          <span className="flex items-center justify-between text-[11px] font-bold text-plum">
            How these 5 were chosen
            <span className="text-[14px] leading-none">{showPipeline ? '−' : '+'}</span>
          </span>
          {showPipeline && (
            <span className="mt-2 block space-y-1 text-[11px] leading-relaxed text-sub">
              <span className="block">
                <b className="text-plum">{pipeline.catalogue_size}</b> products in the catalogue
              </span>
              <span className="block">
                → <b className="text-plum">{pipeline.eligible_count}</b> passed the Stage 1
                filters ({Math.round(pipeline.pool_ratio * 100)}% pool)
              </span>
              <span className="block">
                → <b className="text-plum">{pipeline.candidate_count}</b> retrieved as candidates
              </span>
              <span className="block">
                → <b className="text-plum">{data.recommendations.length}</b> ranked and served
              </span>
              <span className="mt-1 block border-t border-pink-line pt-1">
                Removed by rule:{' '}
                {Object.entries(pipeline.rejected_by_rule)
                  .map(([rule, ids]) => `${rule.replace(/_/g, ' ')} (${ids.length})`)
                  .join(', ') || 'none'}
              </span>
            </span>
          )}
        </button>
      </div>
    </Shell>
  );
}
