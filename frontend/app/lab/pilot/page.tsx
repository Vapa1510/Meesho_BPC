'use client';

/**
 * Engine lab · Pilot test (slide 11). Weeks 3-4 measure today's generic
 * discovery as the baseline; weeks 5-6 interleave personalised and generic
 * picks in one feed with the source hidden, and score which feed's picks the
 * creator acts on (gate 1, match quality). This page runs that mechanism on
 * the prototype: the interleaved feed, pick-source logging, and the win rate.
 */
import { useCallback, useEffect, useState } from 'react';

import { ErrorState, Loading, PageHeader } from '@/components/AppShell';
import { useCreators } from '@/components/CreatorContext';
import { SkipReasons } from '@/components/ProductCard';
import { FitRing, Toast } from '@/components/ui';
import { api, fmt } from '@/lib/api';
import type { Pilot, PilotArm, RecommendationsResponse } from '@/lib/types';

function ArmTable({ title, arm, note }: { title: string; arm: PilotArm; note: string }) {
  const rows: [string, string, string][] = [
    ['Picks shown', fmt.int(arm.shown.personalised ?? 0), fmt.int(arm.shown.generic ?? 0)],
    ['Promotes + saves', fmt.int(arm.positive_actions.personalised ?? 0), fmt.int(arm.positive_actions.generic ?? 0)],
    [
      'Pick rate',
      arm.pick_rate.personalised == null ? '—' : fmt.pct(arm.pick_rate.personalised, 0),
      arm.pick_rate.generic == null ? '—' : fmt.pct(arm.pick_rate.generic, 0),
    ],
    ['Slates won', fmt.int(arm.personalised_wins), fmt.int(arm.generic_wins)],
  ];
  return (
    <section className="panel self-start">
      <div className="panel-head">
        <div>
          <h2 className="panel-title">{title}</h2>
          <p className="panel-note">{note}</p>
        </div>
      </div>
      <table className="dt">
        <thead>
          <tr>
            <th />
            <th className="num">Personalised</th>
            <th className="num">Generic</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(([k, a, b]) => (
            <tr key={k}>
              <td className="text-[12.5px]">{k}</td>
              <td className="mono num text-[12.5px] font-semibold">{a}</td>
              <td className="mono num text-[12.5px] font-semibold">{b}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="px-4 py-3 text-[12.5px]">
        Interleaving win rate:{' '}
        <b className="text-[var(--signal)]">{arm.win_rate == null ? 'no decided slates yet' : fmt.pct(arm.win_rate, 0)}</b>
        <span className="text-[var(--ink-3)]"> · {arm.slates} interleaved slates · {arm.ties} ties</span>
      </p>
    </section>
  );
}

export default function PilotPage() {
  const { current, loading, invalidate } = useCreators();
  const [slate, setSlate] = useState<RecommendationsResponse | null>(null);
  const [reveal, setReveal] = useState(false);
  const [pilot, setPilot] = useState<Pilot | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [skipping, setSkipping] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  const loadPilot = useCallback(async () => {
    try {
      setPilot(await api.pilot());
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not load the pilot metrics.');
    }
  }, []);

  useEffect(() => {
    void loadPilot();
  }, [loadPilot]);

  useEffect(() => {
    setSlate(null);
    setReveal(false);
  }, [current?.creator_id]);

  async function serve() {
    if (!current) return;
    setBusy('serve');
    setError(null);
    try {
      setSlate(await api.recommendations(current.creator_id, { mode: 'interleaved' }));
      setReveal(false);
      await loadPilot();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not serve a slate.');
    } finally {
      setBusy(null);
    }
  }

  async function act(productId: string, score: number, source: string, action: 'promote' | 'save' | 'skip', reason?: string) {
    if (!current) return;
    setBusy(productId);
    try {
      await api.feedback({ creator_id: current.creator_id, product_id: productId, action, reason, served_score: score, source });
      setToast(`Recorded. It counts for the ${source} feed.`);
      setSkipping(null);
      setSlate((s) => (s ? { ...s, recommendations: s.recommendations.filter((r) => r.product_id !== productId) } : s));
      invalidate();
      await loadPilot();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not record that.');
    } finally {
      setBusy(null);
    }
  }

  async function synthetic() {
    setBusy('synthetic');
    setError(null);
    try {
      const created = await api.generateCreators(5, 2026);
      for (const c of created) await api.runSimulation(c.creator_id, 4, 6, 'interleaved');
      await loadPilot();
      setToast('Ran 4 interleaved rounds for 5 synthetic creators.');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'The synthetic check did not complete.');
    } finally {
      setBusy(null);
    }
  }

  if (loading || !current) return <Loading label="Loading creators" />;
  const first = current.name.split(' ')[0];

  return (
    <>
      <PageHeader
        title="Pilot test: personalised vs generic"
        description="Slide 11, gate 1. Weeks 3–4 measure today's generic discovery as the baseline. Weeks 5–6 mix personalised and generic picks in one feed with the source hidden, log which feed every pick came from, and score which picks creators act on."
      />
      {error && <ErrorState message={error} />}

      <div className="space-y-5 px-4 py-6 sm:px-6">
        <section className="panel">
          <div className="panel-head">
            <div>
              <h2 className="panel-title">Interleaved feed for {current.name}</h2>
              <p className="panel-note">
                Team-draft interleaving: each round a coin decides which feed picks first. The creator sees one list; the
                source is logged per pick. Actions here are real feedback for {first} (use Reset demo on the Creator page to
                return to the deck&apos;s numbers).
              </p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-3 px-4 pt-4">
            <button className="btn btn-sm" disabled={busy !== null} onClick={() => void serve()}>
              {busy === 'serve' ? 'Serving…' : slate ? 'Serve a new slate' : 'Serve an interleaved slate'}
            </button>
            {slate && (
              <label className="flex items-center gap-2 text-[12.5px] text-[var(--ink-2)]">
                <input type="checkbox" checked={reveal} onChange={(e) => setReveal(e.target.checked)} className="accent-[#E8195F]" />
                Reveal the source (hidden from the creator)
              </label>
            )}
          </div>
          {slate ? (
            <ul className="divide-y divide-[var(--line)] px-4 py-2">
              {slate.recommendations.map((r) => (
                <li key={r.product_id} className="flex flex-wrap items-center gap-3 py-3">
                  <FitRing score={r.fit_score} size={40} />
                  <div className="min-w-[160px] flex-1">
                    <p className="text-[13.5px] font-semibold">{r.title}</p>
                    <p className="text-[12px] text-[var(--ink-3)]">
                      {fmt.rupees(r.price)} · {r.category}
                      {reveal && (
                        <span
                          className={`ml-2 rounded-full px-2 py-px text-[10.5px] font-semibold ${
                            r.source === 'personalised' ? 'bg-[var(--signal-wash)] text-[var(--signal)]' : 'bg-[#eef3fb] text-[#1f6fd0]'
                          }`}
                        >
                          {r.source}
                        </span>
                      )}
                    </p>
                  </div>
                  {skipping === r.product_id ? (
                    <div className="w-full">
                      <SkipReasons busy={busy !== null} onPick={(reason) => void act(r.product_id, r.fit_score, r.source, 'skip', reason)} onCancel={() => setSkipping(null)} />
                    </div>
                  ) : (
                    <div className="flex gap-1.5">
                      <button className="btn btn-sm" disabled={busy !== null} onClick={() => void act(r.product_id, r.fit_score, r.source, 'promote')}>
                        Promote
                      </button>
                      <button className="btn-quiet btn-sm" disabled={busy !== null} onClick={() => void act(r.product_id, r.fit_score, r.source, 'save')}>
                        Save
                      </button>
                      <button className="btn-quiet btn-sm" disabled={busy !== null} onClick={() => setSkipping(r.product_id)}>
                        Skip (with reason)
                      </button>
                    </div>
                  )}
                </li>
              ))}
            </ul>
          ) : (
            <p className="px-4 py-4 text-[12.5px] text-[var(--ink-3)]">No slate served yet.</p>
          )}
        </section>

        {pilot && (
          <div className="grid gap-5 lg:grid-cols-2">
            <ArmTable title="Real creators (this demo)" arm={pilot.real} note={pilot.gate} />
            <div className="space-y-3">
              <ArmTable title="Synthetic creators (mechanism check)" arm={pilot.synthetic} note={pilot.note} />
              <button className="btn-quiet btn-sm" disabled={busy !== null} onClick={() => void synthetic()}>
                {busy === 'synthetic' ? 'Running…' : 'Run a synthetic check: 5 creators × 4 interleaved rounds'}
              </button>
            </div>
          </div>
        )}

        <p className="text-[11.5px] leading-relaxed text-[var(--ink-3)]">
          Why interleaving: at 150–200 creators, a conventional A/B test on NMV is unlikely to detect +11.5% with confidence.
          Interleaving compares both feeds inside the same creator&apos;s session, so match quality can be read with far fewer
          creators. The pilot keeps a control group to Week 12 for the commerce read (orders and NMV, directional with
          confidence intervals).
        </p>
      </div>
      <Toast message={toast} onDone={() => setToast(null)} />
    </>
  );
}
