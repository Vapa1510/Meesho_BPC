'use client';

/**
 * Creator · Onboarding. A phone-style flow that builds a Creator DNA from a
 * connected profile plus a few indirect questions. It never asks a creator
 * whether they are trend-, commerce- or brand-led: it asks what they enjoy,
 * what they would do, and what they would show their followers.
 *
 * ?handle=riya.glows&step=q2&demo=1 opens a step with demo answers (for screenshots).
 */
import { useRouter } from 'next/navigation';
import { useEffect, useMemo, useState, type ReactNode } from 'react';

import { PageHeader } from '@/components/AppShell';
import { useCreators } from '@/components/CreatorContext';
import { api, imgSrc } from '@/lib/api';
import type { DNA, FetchedProfile, OnboardingAnswers } from '@/lib/types';
import { TOP_K_BY_SCALE } from '@/lib/types';

type Step = 'connect' | 'q1' | 'q2' | 'q3' | 'q4' | 'q5' | 'q6' | 'q7' | 'dna';
const HANDLES = [
  { id: 'riya.glows', name: 'Riya Kapoor', note: 'Varanasi · 25K followers' },
  { id: 'naina.starts', name: 'Naina Verma', note: 'Gaya · 6.2K followers' },
  { id: 'zara.luxe', name: 'Zara Khan', note: 'Lucknow · 210K followers' },
];
const DEMO: OnboardingAnswers = {
  q1: ['skincare_routine', 'product_review', 'makeup_tutorial'],
  q2: 'definitely',
  q3: ['sells', 'niche', 'audience', 'trending'],
  q4: ['P003', 'P007', 'P001'],
};
const SIGNAL_OF: Record<string, string> = {
  q1: 'Content signal', q2: 'Intent', q3: 'Intent', q4: 'Product + Price signals',
  q5: 'Intent (follow-up)', q6: 'Audience', q7: 'Exclusions',
};
const INTENT_COLOR: Record<string, string> = { trend: '#F28C1C', commerce: '#E8195F', brand: '#7B4FE0' };
const INTENT_NAME: Record<string, string> = { trend: 'Trend', commerce: 'Commerce', brand: 'Brand' };

/* ------------------------------------------------------------ tiny icons */
function Ico({ k, size = 22, color = 'currentColor' }: { k: string; size?: number; color?: string }) {
  const p: Record<string, ReactNode> = {
    routine: <><rect x="8" y="9" width="8" height="12" rx="2" /><rect x="10" y="5" width="4" height="4" rx="1" /></>,
    tutorial: <><path d="M5 19 L15 9" /><path d="M15 9 l3 -3 l2 2 l-3 3 z" /></>,
    tips: <><path d="M6 4 v16" /><path d="M6 6 h10 M6 10 h8 M6 14 h10 M6 18 h6" /></>,
    review: <path d="M12 4 l2.4 5 5.4 .6 -4 3.7 1.1 5.3 -4.9 -2.8 -4.9 2.8 1.1 -5.3 -4 -3.7 5.4 -.6z" />,
    grwm: <><ellipse cx="12" cy="10" rx="6" ry="7" /><path d="M12 17 v4 M9 21 h6" /></>,
    reel: <><rect x="4" y="5" width="16" height="14" rx="3" /><path d="M10 9 l5 3 -5 3z" /></>,
  };
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      {p[k] ?? <circle cx="12" cy="12" r="6" />}
    </svg>
  );
}

function Phone({ children, step, total, label }: { children: ReactNode; step: number; total: number; label: string }) {
  return (
    <div id="phone" className="mx-auto w-[372px] rounded-[44px] bg-[#1f1a22] p-[10px] shadow-[0_24px_60px_-20px_rgba(81,14,68,0.45)]">
      <div className="relative flex h-[740px] flex-col overflow-hidden rounded-[36px] bg-white">
        <div className="flex items-center justify-between px-6 pt-3 text-[11px] font-semibold text-[var(--ink)]">
          <span>9:41</span>
          <span className="h-[22px] w-[96px] rounded-full bg-[#1f1a22]" />
          <span>5G ▮</span>
        </div>
        <div className="px-5 pb-2 pt-3">
          <div className="flex items-center justify-between">
            <span className="text-[15px] font-extrabold tracking-[-0.02em] text-[var(--plum)]">meesho</span>
            <span className="text-[11px] text-[var(--ink-3)]">{label}</span>
          </div>
          {total > 0 && (
            <div className="mt-2 h-[5px] overflow-hidden rounded-full bg-[#f6ebf1]">
              <div className="h-full rounded-full bg-[var(--signal)]" style={{ width: `${(100 * step) / total}%` }} />
            </div>
          )}
        </div>
        <div className="flex min-h-0 flex-1 flex-col px-5 pb-5">{children}</div>
      </div>
    </div>
  );
}

function NextBtn({ children, onClick, disabled }: { children: ReactNode; onClick: () => void; disabled?: boolean }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="mt-auto w-full rounded-full bg-[var(--signal)] py-3 text-[14px] font-semibold text-white disabled:opacity-40"
    >
      {children}
    </button>
  );
}

function Q({ text, hint }: { text: string; hint?: string }) {
  return (
    <div className="mb-4 mt-1">
      <h2 className="text-[19px] font-bold leading-snug tracking-[-0.02em] text-[var(--plum)]">{text}</h2>
      {hint && <p className="mt-1 text-[12px] text-[var(--ink-3)]">{hint}</p>}
    </div>
  );
}

export default function OnboardPage() {
  const router = useRouter();
  const { refresh, select } = useCreators();
  const [handle, setHandle] = useState('riya.glows');
  const [fetched, setFetched] = useState<FetchedProfile | null>(null);
  const [scale, setScale] = useState('');
  const [planned, setPlanned] = useState<string[]>([]);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [bank, setBank] = useState<Record<string, any> | null>(null);
  const [answers, setAnswers] = useState<OnboardingAnswers>({});
  const [step, setStep] = useState<Step>('connect');
  const [dna, setDna] = useState<DNA | null>(null);
  const [consent, setConsent] = useState(true);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  // query params: handle, step, demo
  useEffect(() => {
    const q = new URLSearchParams(window.location.search);
    const h = q.get('handle');
    if (h) setHandle(h);
    if (q.get('demo')) setAnswers(DEMO);
    const s = q.get('step') as Step | null;
    if (s) setStep(s);
    void api.onboardingQuestions().then(setBank).catch(() => setErr('Could not load the questions.'));
  }, []);

  useEffect(() => {
    api.onboardingConnect(handle)
      .then((r) => { setFetched(r.fetched); setScale(r.scale); setPlanned(r.questions); })
      .catch(() => setErr('Could not connect this profile.'));
  }, [handle]);

  const flow = useMemo(() => {
    const f = [...planned];
    if (answers.q5 || (dna?.intent.needs_follow_up && f.includes('q3'))) {
      const at = f.indexOf('q4');
      if (!f.includes('q5')) f.splice(at === -1 ? f.length : at + 1, 0, 'q5');
    }
    return f;
  }, [planned, dna, answers.q5]);

  useEffect(() => {
    if (step === 'dna' || step === 'q5') {
      api.onboardingPreview({ handle, answers }).then((r) => setDna(r.dna)).catch(() => undefined);
    }
  }, [step, handle, answers]);

  async function advance() {
    const order: Step[] = ['connect', ...(flow as Step[]), 'dna'];
    const i = order.indexOf(step);
    let next = order[i + 1] ?? 'dna';
    if (next === 'dna' && !answers.q5 && planned.includes('q3')) {
      const r = await api.onboardingPreview({ handle, answers });
      setDna(r.dna);
      if (r.dna.intent.needs_follow_up) next = 'q5';
    }
    setStep(next);
  }

  async function finish() {
    setBusy(true);
    try {
      const c = await api.onboard({ handle, answers, consent });
      await refresh();
      select(c.creator_id);
      router.push('/creator');
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'Could not create the profile.');
    } finally {
      setBusy(false);
    }
  }

  const set = (patch: Partial<OnboardingAnswers>) => setAnswers((a) => ({ ...a, ...patch }));
  const toggle = (key: 'q1' | 'q4' | 'q7', id: string, max: number) =>
    setAnswers((a) => {
      const cur = (a[key] as string[] | undefined) ?? [];
      return { ...a, [key]: cur.includes(id) ? cur.filter((x) => x !== id) : cur.length >= max ? cur : [...cur, id] };
    });

  const qIndex = flow.indexOf(step as string);
  const qLabel = step === 'connect' ? 'Connect' : step === 'dna' ? 'Your Creator DNA' : `Question ${qIndex + 1} of ${flow.length}`;
  const total = flow.length + 1;
  const pos = step === 'connect' ? 0 : step === 'dna' ? total : qIndex + 1;

  /* ------------------------------------------------------------ screens */
  let screen: ReactNode = null;
  if (step === 'connect') {
    screen = (
      <>
        <Q text="Connect your creator profile" hint="We read what Meesho already knows, so we only ask what is missing." />
        <div className="space-y-2">
          {HANDLES.map((h) => (
            <button key={h.id} onClick={() => setHandle(h.id)}
              className={`flex w-full items-center justify-between rounded-2xl border px-3.5 py-2.5 text-left ${handle === h.id ? 'border-[var(--signal)] bg-[var(--signal-wash)]' : 'border-[var(--line-strong)]'}`}>
              <span><span className="block text-[13px] font-semibold">@{h.id}</span><span className="block text-[11px] text-[var(--ink-3)]">{h.note}</span></span>
              {handle === h.id && <span className="text-[11px] font-semibold text-[var(--signal)]">Connected</span>}
            </button>
          ))}
        </div>
        {fetched && (
          <div className="mt-4 rounded-2xl bg-[#faf6f9] p-3.5">
            <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-[var(--ink-3)]">Fetched automatically</p>
            <dl className="mt-2 space-y-1.5 text-[12px]">
              <div className="flex justify-between"><dt className="text-[var(--ink-3)]">Followers</dt><dd className="font-semibold">{(fetched.followers / 1000).toFixed(1).replace('.0', '')}K · {scale}</dd></div>
              <div className="flex justify-between"><dt className="text-[var(--ink-3)]">Audience</dt><dd className="font-semibold">{fetched.audience ? `${fetched.audience.age_min}–${fetched.audience.age_max} · ${fetched.audience.tiers.join('/')}` : 'not enough data yet'}</dd></div>
              <div className="flex justify-between"><dt className="text-[var(--ink-3)]">Content history</dt><dd className="font-semibold">{Object.keys(fetched.content_history).length ? Object.entries(fetched.content_history).map(([k, v]) => `${k} ${Math.round(v * 100)}%`).join(' · ') : `${fetched.posts} posts, too few`}</dd></div>
            </dl>
            <div className="mt-2 flex flex-wrap gap-1">{fetched.hashtags.map((t) => <span key={t} className="rounded-full bg-white px-2 py-0.5 text-[10.5px] text-[var(--ink-2)]">{t}</span>)}</div>
          </div>
        )}
        <div className="mt-3 rounded-xl bg-[var(--signal-wash)] px-3 py-2 text-[12px] text-[var(--plum)]">
          {planned.length ? <>Only <b>{planned.length} quick questions</b> left for {scale === 'Emerging' || scale === 'Established' ? 'an' : 'a'} {scale} creator.</> : <>No questions needed: confirm your auto-built profile.</>}
        </div>
        <NextBtn onClick={() => void advance()}>{planned.length ? 'Start' : 'Review my DNA'}</NextBtn>
      </>
    );
  } else if (step === 'q1' && bank) {
    const opts = Object.entries(bank.q1.options) as [string, { label: string; icon: string }][];
    screen = (
      <>
        <Q text="Which posts would you love to make?" hint="Tap up to 3. There are no wrong answers." />
        <div className="grid grid-cols-2 gap-2.5">
          {opts.map(([id, o]) => {
            const on = (answers.q1 ?? []).includes(id);
            return (
              <button key={id} onClick={() => toggle('q1', id, 3)}
                className={`relative flex h-[92px] flex-col items-center justify-center gap-1.5 rounded-2xl border text-[12px] font-semibold ${on ? 'border-[var(--signal)] bg-[var(--signal-wash)] text-[var(--plum)]' : 'border-[var(--line-strong)] text-[var(--ink-2)]'}`}>
                <Ico k={o.icon} color={on ? '#E8195F' : '#9a8ca3'} size={26} />
                {o.label}
                {on && <span className="absolute right-2 top-2 flex h-[18px] w-[18px] items-center justify-center rounded-full bg-[var(--signal)] text-[11px] text-white">✓</span>}
              </button>
            );
          })}
        </div>
        <NextBtn onClick={() => void advance()} disabled={!(answers.q1 ?? []).length}>Next</NextBtn>
      </>
    );
  } else if (step === 'q2' && bank) {
    const opts = Object.entries(bank.q2.options) as [string, { label: string }][];
    screen = (
      <>
        <Q text="A product sells well every week but isn’t trending anymore. Would you still promote it?" />
        <div className="mb-4 flex items-center gap-3 rounded-2xl bg-[#faf6f9] p-3">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={imgSrc('/product/P001/image.svg')} alt="" className="h-[78px] w-[78px] rounded-xl object-cover" />
          <div>
            <p className="text-[13px] font-semibold">Vitamin C Serum</p>
            <p className="text-[11.5px] text-[var(--ink-3)]">★ 4.4 · 120 orders / week</p>
            <span className="mt-1 inline-block rounded-full bg-[#fdeded] px-2 py-0.5 text-[10.5px] font-semibold text-[#d9343f]">Trend ↓</span>
          </div>
        </div>
        <div className="space-y-2.5">
          {opts.map(([id, o]) => (
            <button key={id} onClick={() => set({ q2: id })}
              className={`w-full rounded-full border py-3 text-[13.5px] font-semibold ${answers.q2 === id ? 'border-[var(--signal)] bg-[var(--signal)] text-white' : 'border-[var(--line-strong)] text-[var(--ink)]'}`}>
              {o.label}
            </button>
          ))}
        </div>
        <NextBtn onClick={() => void advance()} disabled={!answers.q2}>Next</NextBtn>
      </>
    );
  } else if (step === 'q3' && bank) {
    const labels = bank.q3.options as Record<string, { label: string }>;
    const order = answers.q3 ?? Object.keys(labels);
    const move = (i: number, d: number) => {
      const o = [...order];
      const j = i + d;
      if (j < 0 || j >= o.length) return;
      [o[i], o[j]] = [o[j], o[i]];
      set({ q3: o });
    };
    screen = (
      <>
        <Q text="What matters most when you pick a product?" hint="Drag to rank, most important first." />
        <div className="space-y-2.5">
          {order.map((id, i) => (
            <div key={id} className={`flex items-center gap-3 rounded-2xl border px-3 py-3 ${i === 0 ? 'border-[var(--signal)] bg-[var(--signal-wash)]' : 'border-[var(--line-strong)]'}`}>
              <span className={`flex h-[24px] w-[24px] items-center justify-center rounded-full text-[12px] font-bold text-white ${i === 0 ? 'bg-[var(--signal)]' : 'bg-[#b9a9b6]'}`}>{i + 1}</span>
              <span className="flex-1 text-[13.5px] font-semibold">{labels[id].label}</span>
              <button onClick={() => move(i, -1)} className="px-1 text-[var(--ink-3)]" aria-label="up">▲</button>
              <button onClick={() => move(i, 1)} className="px-1 text-[var(--ink-3)]" aria-label="down">▼</button>
            </div>
          ))}
        </div>
        <NextBtn onClick={() => { if (!answers.q3) set({ q3: order }); void advance(); }}>Next</NextBtn>
      </>
    );
  } else if (step === 'q4' && bank) {
    const prods = bank.q4.options as { product_id: string; title: string; price: number }[];
    screen = (
      <>
        <Q text="Pick 3 products you’d happily show your followers." hint={`${(answers.q4 ?? []).length} of 3 picked`} />
        <div className="grid grid-cols-2 gap-2.5">
          {prods.map((p) => {
            const on = (answers.q4 ?? []).includes(p.product_id);
            return (
              <button key={p.product_id} onClick={() => toggle('q4', p.product_id, 3)}
                className={`relative flex items-center gap-2 rounded-2xl border p-2 text-left ${on ? 'border-[var(--signal)] bg-[var(--signal-wash)]' : 'border-[var(--line-strong)]'}`}>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={imgSrc(`/product/${p.product_id}/image.svg`)} alt="" className="h-[64px] w-[52px] rounded-lg object-cover" />
                <span>
                  <span className="block text-[11px] leading-tight text-[var(--ink-2)]">{p.title}</span>
                  <span className={`block text-[13.5px] font-bold ${on ? 'text-[var(--signal)]' : 'text-[var(--ink)]'}`}>₹{p.price}</span>
                </span>
                {on && <span className="absolute right-1.5 top-1.5 flex h-[18px] w-[18px] items-center justify-center rounded-full bg-[var(--signal)] text-[11px] text-white">✓</span>}
              </button>
            );
          })}
        </div>
        <NextBtn onClick={() => void advance()} disabled={(answers.q4 ?? []).length !== 3}>Next</NextBtn>
      </>
    );
  } else if (step === 'q5' && bank) {
    const opts = Object.entries(bank.q5.options) as [string, { label: string }][];
    screen = (
      <>
        <Q text="Six months from now, which would make you proudest?" hint="One more, because your answers were a close call." />
        <div className="space-y-2.5">
          {opts.map(([id, o]) => (
            <button key={id} onClick={() => set({ q5: id })}
              className={`w-full rounded-2xl border px-4 py-3.5 text-left text-[13.5px] font-semibold ${answers.q5 === id ? 'border-[var(--signal)] bg-[var(--signal-wash)] text-[var(--plum)]' : 'border-[var(--line-strong)]'}`}>
              {o.label}
            </button>
          ))}
        </div>
        <NextBtn onClick={() => setStep('dna')} disabled={!answers.q5}>Next</NextBtn>
      </>
    );
  } else if (step === 'q6' || step === 'q7') {
    const isQ6 = step === 'q6';
    const opts: string[] = bank ? bank[step].options : [];
    screen = (
      <>
        <Q text={isQ6 ? 'Who asks you for product advice most?' : 'Any category you never want to see?'} hint={isQ6 ? 'We ask only because your audience data is still thin.' : 'Optional. You can change this any time.'} />
        <div className="grid grid-cols-2 gap-2.5">
          {opts.map((o) => {
            const on = isQ6 ? answers.q6 === o : (answers.q7 ?? []).includes(o);
            return (
              <button key={o} onClick={() => (isQ6 ? set({ q6: o }) : toggle('q7', o, 4))}
                className={`rounded-2xl border py-3.5 text-[13px] font-semibold ${on ? 'border-[var(--signal)] bg-[var(--signal-wash)] text-[var(--plum)]' : 'border-[var(--line-strong)]'}`}>
                {o}
              </button>
            );
          })}
        </div>
        <NextBtn onClick={() => void advance()} disabled={isQ6 && !answers.q6}>Next</NextBtn>
      </>
    );
  } else if (step === 'dna' && dna) {
    const sc = dna.intent.scores;
    const top = TOP_K_BY_SCALE[dna.scale] ?? 5;
    const rows: [string, string, string][] = [
      ['Niche', Object.entries(dna.niche_shares).filter(([k]) => k !== 'Other').map(([k, v]) => `${k} ${Math.round(v * 100)}%`).join(' · '), dna.sources.niche],
      ['Content', dna.content_formats.join(' · ') || '—', dna.sources.content],
      ['Price', `~₹${dna.preferred_price} preferred · ₹${dna.price_min}–${dna.price_max} range`, dna.sources.price],
      ['Audience', `${dna.audience_age_min}–${dna.audience_age_max} · ${dna.audience_tiers.join('/')}`, dna.sources.audience],
    ];
    screen = (
      <>
        <div className="mb-3 mt-1 flex items-center justify-between">
          <h2 className="text-[18px] font-bold tracking-[-0.02em] text-[var(--plum)]">Your Creator DNA</h2>
          <span className="whitespace-nowrap rounded-full bg-[var(--plum)] px-2.5 py-1 text-[10px] font-semibold text-white">{dna.scale} × {INTENT_NAME[dna.intent.primary]}-led</span>
        </div>
        <div className="rounded-2xl bg-[#faf6f9] p-3">
          {(['trend', 'commerce', 'brand'] as const).map((k) => (
            <div key={k} className="mb-1.5 flex items-center gap-2 text-[12px]">
              <span className="w-[68px] font-semibold">{INTENT_NAME[k]}</span>
              <span className="h-[8px] flex-1 overflow-hidden rounded-full bg-white">
                <span className="block h-full rounded-full" style={{ width: `${sc[k] * 100}%`, background: INTENT_COLOR[k] }} />
              </span>
              <span className="w-[30px] text-right font-semibold">{sc[k].toFixed(2)}</span>
              <span className="w-[62px] text-right text-[10px] font-semibold text-[var(--signal)]">{dna.intent.primary === k ? 'Primary' : dna.intent.secondary === k ? 'Secondary' : ''}</span>
            </div>
          ))}
          <p className="mt-1 text-[10.5px] text-[var(--ink-3)]">Intent separation {dna.intent.separation.toFixed(2)}{dna.intent.separation >= dna.intent.threshold ? ' · clear, no follow-up needed' : ' · close call, one follow-up asked'}</p>
        </div>
        <div className="mt-3 space-y-2">
          {rows.map(([k, v, s]) => (
            <div key={k} className="rounded-xl border border-[var(--line)] px-3 py-2">
              <div className="flex items-center justify-between"><span className="text-[11px] font-semibold text-[var(--ink-3)]">{k}</span>
                <span className={`rounded-full px-2 py-0.5 text-[9.5px] font-semibold ${/^Q|Q\d/.test(s) && !s.startsWith('Fetched') ? 'bg-[var(--signal-wash)] text-[var(--signal)]' : 'bg-[#efe6f6] text-[var(--plum)]'}`}>{s}</span></div>
              <p className="text-[12.5px] font-semibold">{v}</p>
            </div>
          ))}
        </div>
        <label className="mt-3 flex items-start gap-2 text-[11px] text-[var(--ink-2)]">
          <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} className="mt-0.5 accent-[#E8195F]" />
          I agree to Meesho using my profile and aggregated audience data to recommend products. I can edit this DNA any time.
        </label>
        <div className="mt-auto flex gap-2 pt-3">
          <button onClick={() => setStep('connect')} className="rounded-full border border-[var(--line-strong)] px-4 py-3 text-[13px] font-semibold">Edit</button>
          <button onClick={() => void finish()} disabled={!consent || busy} className="flex-1 rounded-full bg-[var(--signal)] py-3 text-[14px] font-semibold text-white disabled:opacity-40">
            See my Top {top}
          </button>
        </div>
      </>
    );
  } else {
    screen = <p className="mt-10 text-center text-[13px] text-[var(--ink-3)]">Loading…</p>;
  }

  const explain: Record<string, [string, string]> = {
    connect: ['Fetch first', 'Followers, audience analytics, content history and hashtags come from data Meesho already has. The tier decides how many questions are left.'],
    q1: ['Content signal', 'Formats she enjoys shape the content angle on every pick. Topics only fill in the niche when history is thin.'],
    q2: ['Intent', 'A scenario, not a label: would she promote a steady seller that is no longer trending?'],
    q3: ['Intent', 'What she ranks first says how she weighs proof, fit and buzz.'],
    q4: ['Product + Price signals', 'Her picks set a preferred price, an observed price range and her positioning.'],
    q5: ['Adaptive follow-up', 'Asked only when the top two intents are too close to call.'],
    q6: ['Audience', 'Asked only when analytics are missing.'],
    q7: ['Exclusions', 'Categories she never wants to see.'],
    dna: ['Creator DNA', 'Fetched and asked values, each tagged with its source. She confirms or edits it before her first picks.'],
  };

  return (
    <>
      <PageHeader title="Onboarding" description="A few indirect questions, and only the ones the data cannot answer." />
      {err && <p className="mx-6 rounded-xl bg-[var(--signal-wash)] px-4 py-3 text-[13px] text-[var(--plum)]">{err}</p>}
      <div className="grid gap-8 px-6 pb-16 pt-5 lg:grid-cols-[1fr_400px]">
        <section className="panel h-fit p-6">
          <p className="text-[11px] font-semibold uppercase tracking-[0.1em] text-[var(--signal)]">{step === 'connect' || step === 'dna' ? 'Step' : SIGNAL_OF[step]}</p>
          <h2 className="mt-1 text-[22px] font-bold tracking-[-0.02em] text-[var(--plum)]">{explain[step]?.[0]}</h2>
          <p className="mt-2 max-w-[520px] text-[14px] leading-relaxed text-[var(--ink-2)]">{explain[step]?.[1]}</p>
          <ol className="mt-6 space-y-2 text-[13px]">
            {(['connect', ...flow, 'dna'] as string[]).map((s, i) => (
              <li key={s} className={`flex items-center gap-3 ${s === step ? 'font-semibold text-[var(--plum)]' : 'text-[var(--ink-3)]'}`}>
                <span className={`flex h-[22px] w-[22px] items-center justify-center rounded-full text-[11px] ${s === step ? 'bg-[var(--signal)] text-white' : 'bg-[#f3e9ef]'}`}>{i + 1}</span>
                {s === 'connect' ? 'Connect profile' : s === 'dna' ? 'Confirm Creator DNA' : `${s.toUpperCase()} · ${SIGNAL_OF[s]}`}
              </li>
            ))}
          </ol>
        </section>
        <Phone step={pos} total={total} label={qLabel}>{screen}</Phone>
      </div>
    </>
  );
}
