'use client';

/**
 * Simulation.
 *
 * A simulated creator carries a latent preference profile the engine never
 * sees, and which deliberately disagrees with what they said at signup. Each
 * round the engine serves a slate, the creator reacts according to the latent
 * profile, and the reaction is written back. Ranking quality is then measured
 * against that latent profile — the only real ground truth available.
 */
import { useCallback, useEffect, useState } from 'react';

import { EmptyState, ErrorState, Loading, PageHeader } from '@/components/AppShell';
import { useCreators } from '@/components/CreatorContext';
import { CompareBars, LineChart } from '@/components/Viz';
import { api, fmt } from '@/lib/api';
import { SERIES, type Ablation, type Discovered, type SimHistory, type SimRun } from '@/lib/types';

const ACTION_STYLE: Record<string, string> = {
  promote: 'bg-[#e7f6ee] text-[#0b6b43] border-[#c6e4d3]',
  save: 'bg-[#eef3fd] text-[#1a4fa0] border-[#c9d9f5]',
  skip: 'bg-[var(--canvas)] text-[var(--ink-2)] border-[var(--line)]',
};

export default function SimulatePage() {
  const { current, creators, select, refresh, invalidate, loading } = useCreators();

  const [history, setHistory] = useState<SimHistory | null>(null);
  const [ablation, setAblation] = useState<Ablation | null>(null);
  const [discovered, setDiscovered] = useState<Discovered | null>(null);
  const [lastRun, setLastRun] = useState<SimRun | null>(null);
  const [rounds, setRounds] = useState(8);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadState = useCallback(async () => {
    if (!current) return;
    setError(null);
    try {
      const h = await api.simHistory(current.creator_id);
      setHistory(h);
      if (h.rounds_run > 0) {
        const [a, d] = await Promise.all([
          api.ablation(current.creator_id),
          api.discovered(current.creator_id),
        ]);
        setAblation(a);
        setDiscovered(d);
      } else {
        setAblation(null);
        setDiscovered(null);
        setLastRun(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load simulation state.');
    }
  }, [current]);

  useEffect(() => {
    void loadState();
  }, [loadState]);

  async function generate() {
    setBusy('generate');
    setError(null);
    try {
      const [created] = await api.generateCreators(1);
      await refresh();
      select(created.creator_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not generate a creator.');
    } finally {
      setBusy(null);
    }
  }

  async function run() {
    if (!current) return;
    setBusy('run');
    setError(null);
    try {
      const result = await api.runSimulation(current.creator_id, rounds);
      setLastRun(result);
      await loadState();
      invalidate();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'The simulation did not complete.');
    } finally {
      setBusy(null);
    }
  }

  async function reset() {
    if (!current) return;
    setBusy('reset');
    try {
      await api.resetCreator(current.creator_id);
      setLastRun(null);
      await loadState();
      invalidate();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not reset this creator.');
    } finally {
      setBusy(null);
    }
  }

  if (loading || !current) return <Loading label="Loading creators" />;

  const snapshots = history?.snapshots ?? [];
  const hasRun = snapshots.length > 0;

  return (
    <>
      <PageHeader
        title="Simulation"
        description="Generate a creator with hidden preferences that differ from what they declared, then run rounds and watch how much of the real preference the engine recovers."
        actions={
          <>
            <button className="btn-quiet btn-sm" onClick={generate} disabled={busy !== null}>
              {busy === 'generate' ? 'Generating…' : 'Generate creator'}
            </button>
            {hasRun && (
              <button className="btn-quiet btn-sm" onClick={reset} disabled={busy !== null}>
                Reset
              </button>
            )}
          </>
        }
      />

      {error && <ErrorState message={error} onRetry={loadState} />}

      <div className="space-y-5 px-6 py-6">
        {/* ------------------------------------------------- run control */}
        <section className="panel">
          <div className="panel-head">
            <div>
              <h2 className="panel-title">Run rounds for {current.name}</h2>
              <p className="panel-note">
                {history?.rounds_run
                  ? `${history.rounds_run} rounds already run · ${creators.length} creators in the system`
                  : `No rounds run yet for this creator`}
              </p>
            </div>
          </div>
          <div className="flex flex-wrap items-end gap-4 px-4 py-4">
            <label className="w-[220px]">
              <span className="field-label">Rounds to run: {rounds}</span>
              <input
                type="range"
                min={1}
                max={20}
                value={rounds}
                onChange={(event) => setRounds(Number(event.target.value))}
                className="w-full accent-[var(--signal)]"
              />
            </label>
            <button className="btn" onClick={run} disabled={busy !== null}>
              {busy === 'run' ? 'Running…' : `Run ${rounds} rounds`}
            </button>
            {lastRun && (
              <p className="max-w-[46ch] text-[12.5px] leading-relaxed text-[var(--ink-2)]">
                {lastRun.summary}
              </p>
            )}
          </div>
        </section>

        {!hasRun && (
          <EmptyState
            title="Nothing simulated yet"
            body="Each round serves this creator a slate, records what they do with it according to preferences the engine cannot see, and measures how close the ranking came. Use the control above to start."
          />
        )}

        {hasRun && (
          <div className="grid gap-5 xl:grid-cols-2">
            {/* ------------------------------------------ learning curve */}
            <section className="panel">
              <div className="panel-head">
                <div>
                  <h2 className="panel-title">Ranking quality by round</h2>
                  <p className="panel-note">Measured against the creator&rsquo;s latent preferences</p>
                </div>
              </div>
              <div className="px-4 py-4">
                <LineChart
                  xTitle="round"
                  xLabels={snapshots.map((s) => s.round)}
                  series={[
                    {
                      key: 'ndcg',
                      label: 'NDCG@5',
                      color: SERIES.primary,
                      points: snapshots.map((s) => s.ndcg_at_k),
                    },
                    {
                      key: 'capture',
                      label: 'Utility capture',
                      color: SERIES.secondary,
                      points: snapshots.map((s) => s.utility_capture),
                    },
                  ]}
                />
                <p className="mt-3 border-t border-[var(--line)] pt-3 text-[12px] leading-relaxed text-[var(--ink-2)]">
                  Two forces pull on this line at once: the engine learns, which
                  lifts it, while the catalogue is consumed, which drags it
                  down — a promoted product retires, so the best remaining
                  matches get weaker. Whichever wins, it is the ablation beside
                  this that isolates the feedback loop on its own.
                </p>
              </div>
            </section>

            {/* ----------------------------------------------- ablation */}
            {ablation && (
              <section className="panel">
                <div className="panel-head">
                  <div>
                    <h2 className="panel-title">What the feedback loop is worth</h2>
                    <p className="panel-note">
                      Same creator, same catalogue, scored with the loop on and off
                    </p>
                  </div>
                </div>
                <div className="px-4 py-4">
                  <CompareBars
                    max={1}
                    rows={[
                      {
                        label: 'NDCG@5',
                        a: ablation.with_learning.ndcg_at_k,
                        b: ablation.without_learning.ndcg_at_k,
                      },
                      {
                        label: 'Mean utility of what was served',
                        a: ablation.with_learning.mean_served_utility,
                        b: ablation.without_learning.mean_served_utility,
                      },
                      {
                        label: 'Utility capture',
                        a: ablation.with_learning.utility_capture,
                        b: ablation.without_learning.utility_capture,
                      },
                    ]}
                  />
                  <p className="mt-4 border-t border-[var(--line)] pt-3 text-[12.5px] leading-relaxed text-[var(--ink-2)]">
                    {ablation.verdict}
                  </p>
                </div>
              </section>
            )}

            {/* ------------------------------- stated vs learned vs true */}
            {discovered && (
              <section className="panel xl:col-span-2">
                <div className="panel-head">
                  <div>
                    <h2 className="panel-title">Stated, learned, and actually true</h2>
                    <p className="panel-note">
                      From {fmt.int(discovered.events_seen)} recorded actions. The engine
                      only ever sees the first two columns.
                    </p>
                  </div>
                </div>
                <div className="grid gap-5 px-4 py-4 lg:grid-cols-[minmax(0,1fr)_280px]">
                  <table className="dt">
                    <thead>
                      <tr>
                        <th>Category</th>
                        <th className="w-[96px] text-right">Declared</th>
                        <th className="w-[120px] text-right">Learned weight</th>
                        <th className="w-[160px] text-right">True affinity</th>
                      </tr>
                    </thead>
                    <tbody>
                      {discovered.categories.map((row) => (
                        <tr key={row.category}>
                          <td className="text-[12.5px] font-medium">{row.category}</td>
                          <td className="mono num text-[12.5px] text-[var(--ink-3)]">
                            {row.stated.toFixed(2)}
                          </td>
                          <td className="mono num text-[12.5px] font-semibold">
                            {row.learned_multiplier.toFixed(2)}
                          </td>
                          <td>
                            <div className="flex items-center justify-end gap-2.5">
                              <span className="meter h-[6px] w-[84px]">
                                <i
                                  style={{
                                    width: `${row.true_affinity * 100}%`,
                                    background: 'var(--plum)',
                                  }}
                                />
                              </span>
                              <span className="mono w-[30px] text-right text-[12.5px]">
                                {row.true_affinity.toFixed(2)}
                              </span>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>

                  <div className="space-y-3">
                    <div className="rounded-md border border-[var(--line)] bg-[var(--canvas)] px-3 py-2.5">
                      <p className="text-[11.5px] text-[var(--ink-3)]">Price band declared</p>
                      <p className="mono text-[13px] font-semibold">
                        ₹{discovered.stated_price_band[0]} – ₹{discovered.stated_price_band[1]}
                      </p>
                      <p className="mt-2 text-[11.5px] text-[var(--ink-3)]">
                        Price band actually tolerated
                      </p>
                      <p className="mono text-[13px] font-semibold">
                        ₹{discovered.true_price_band[0]} – ₹{discovered.true_price_band[1]}
                      </p>
                    </div>
                    {discovered.notes.length > 0 && (
                      <div>
                        <p className="mb-1 text-[12px] font-semibold">Adjustments in force</p>
                        <ul className="space-y-0.5">
                          {discovered.notes.map((note) => (
                            <li key={note} className="text-[12px] text-[var(--ink-2)]">
                              {note}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </div>
              </section>
            )}

            {/* ------------------------------------------- round detail */}
            {lastRun && (
              <section className="panel xl:col-span-2">
                <div className="panel-head">
                  <div>
                    <h2 className="panel-title">What happened in the last run</h2>
                    <p className="panel-note">
                      {lastRun.rounds.length} rounds · {fmt.rupees(lastRun.total_nmv)} simulated NMV
                    </p>
                  </div>
                </div>
                <div className="max-h-[420px] overflow-y-auto">
                  <table className="dt">
                    <thead className="sticky top-0 bg-white">
                      <tr>
                        <th className="w-[64px]">Round</th>
                        <th>Product served</th>
                        <th className="w-[60px] text-right">Fit</th>
                        <th className="w-[64px] text-right">True</th>
                        <th className="w-[200px]">Creator did</th>
                      </tr>
                    </thead>
                    <tbody>
                      {lastRun.rounds.flatMap((round) =>
                        round.served.map((item) => (
                          <tr key={`${round.round_number}-${item.product_id}`}>
                            <td className="mono text-[12px] text-[var(--ink-3)]">
                              {item.rank === 1 ? round.round_number : ''}
                            </td>
                            <td className="text-[12.5px]">
                              {item.title}
                              <span className="ml-2 text-[11.5px] text-[var(--ink-3)]">
                                {item.category} · {fmt.rupees(item.price)}
                              </span>
                            </td>
                            <td className="mono num text-[12.5px]">{item.fit_score}</td>
                            <td className="mono num text-[12.5px] text-[var(--ink-3)]">
                              {item.latent_utility.toFixed(2)}
                            </td>
                            <td>
                              <span
                                className={`inline-flex rounded border px-2 py-[3px] text-[11.5px] font-medium ${
                                  ACTION_STYLE[item.action]
                                }`}
                              >
                                {item.action}
                                {item.reason ? ` · ${item.reason.replace(/_/g, ' ')}` : ''}
                              </span>
                            </td>
                          </tr>
                        )),
                      )}
                    </tbody>
                  </table>
                </div>
              </section>
            )}
          </div>
        )}
      </div>
    </>
  );
}
