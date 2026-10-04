'use client';

/**
 * Chart primitives.
 *
 * Deliberately small: one line chart, one funnel, one comparison bar. Each
 * carries a hover layer, direct labels, and a recessive grid. Series colour is
 * limited to the two validated hues in `SERIES`; everything measuring a single
 * quantity uses one hue stepped by magnitude instead.
 */
import { useId, useState } from 'react';

import { SERIES, scoreTone } from '@/lib/types';

/* ------------------------------------------------------------------ meter */
export function Meter({
  value,
  max = 100,
  tone,
  height = 6,
}: {
  value: number;
  max?: number;
  tone?: string;
  height?: number;
}) {
  const pct = Math.max(1.5, Math.min(100, (value / max) * 100));
  return (
    <span className="meter" style={{ height }} aria-hidden>
      <i style={{ width: `${pct}%`, background: tone ?? scoreTone(value) }} />
    </span>
  );
}

/* ------------------------------------------------------------ line chart */
export interface Series {
  key: string;
  label: string;
  color: string;
  points: number[];
}

export function LineChart({
  series,
  xLabels,
  xTitle,
  height = 190,
  yMax = 1,
}: {
  series: Series[];
  xLabels: (string | number)[];
  xTitle: string;
  height?: number;
  yMax?: number;
}) {
  const id = useId();
  const [hover, setHover] = useState<number | null>(null);

  const padL = 34;
  const padR = 12;
  const padT = 12;
  const padB = 28;
  const width = 560;
  const plotW = width - padL - padR;
  const plotH = height - padT - padB;

  const n = Math.max(1, xLabels.length - 1);
  const x = (index: number) => padL + (plotW * index) / n;
  const y = (value: number) => padT + plotH * (1 - Math.min(value, yMax) / yMax);

  const ticks = [0, 0.25, 0.5, 0.75, 1].map((t) => t * yMax);

  return (
    <figure className="m-0">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="w-full"
        role="img"
        aria-label={`${series.map((s) => s.label).join(' and ')} by ${xTitle}`}
        onMouseLeave={() => setHover(null)}
      >
        {/* recessive grid */}
        {ticks.map((tick) => (
          <g key={tick}>
            <line
              x1={padL}
              x2={width - padR}
              y1={y(tick)}
              y2={y(tick)}
              stroke="#ece7ee"
              strokeWidth="1"
            />
            <text
              x={padL - 7}
              y={y(tick) + 3.5}
              textAnchor="end"
              fontSize="10"
              fill="var(--ink-3)"
            >
              {tick.toFixed(2).replace(/0$/, '')}
            </text>
          </g>
        ))}

        {xLabels.map((label, index) =>
          index % Math.ceil(xLabels.length / 10) === 0 || index === xLabels.length - 1 ? (
            <text
              key={index}
              x={x(index)}
              y={height - 9}
              textAnchor="middle"
              fontSize="10"
              fill="var(--ink-3)"
            >
              {label}
            </text>
          ) : null,
        )}

        {series.map((s) => (
          <polyline
            key={s.key}
            fill="none"
            stroke={s.color}
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            points={s.points.map((value, index) => `${x(index)},${y(value)}`).join(' ')}
          />
        ))}

        {/* markers, with a surface ring so overlapping points stay readable */}
        {series.map((s) =>
          s.points.map((value, index) => (
            <circle
              key={`${s.key}-${index}`}
              cx={x(index)}
              cy={y(value)}
              r={hover === index ? 5 : 3.5}
              fill={s.color}
              stroke="#fff"
              strokeWidth="2"
            />
          )),
        )}

        {hover !== null && (
          <line
            x1={x(hover)}
            x2={x(hover)}
            y1={padT}
            y2={padT + plotH}
            stroke="var(--ink-3)"
            strokeWidth="1"
            strokeDasharray="3 3"
          />
        )}

        {/* hit targets wider than the marks */}
        {xLabels.map((_, index) => (
          <rect
            key={`hit-${index}`}
            x={x(index) - plotW / n / 2}
            y={padT}
            width={plotW / n}
            height={plotH}
            fill="transparent"
            onMouseEnter={() => setHover(index)}
          />
        ))}
      </svg>

      <figcaption className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-[11.5px] text-[var(--ink-2)]">
        {series.map((s) => (
          <span key={s.key} className="inline-flex items-center gap-1.5">
            <span
              className="inline-block h-[3px] w-[14px] rounded-full"
              style={{ background: s.color }}
              aria-hidden
            />
            {s.label}
            {hover !== null && (
              <span className="mono text-[var(--ink)]">{s.points[hover]?.toFixed(3)}</span>
            )}
          </span>
        ))}
        <span className="ml-auto text-[var(--ink-3)]">
          {hover !== null ? `${xTitle} ${xLabels[hover]}` : xTitle}
        </span>
      </figcaption>
      <span id={id} className="sr-only" />
    </figure>
  );
}

/* --------------------------------------------------------------- funnel */
export function Funnel({
  stages,
}: {
  stages: { label: string; value: number; note?: string }[];
}) {
  const top = Math.max(1, stages[0]?.value ?? 1);
  return (
    <ol className="space-y-2.5">
      {stages.map((stage, index) => {
        const pct = (stage.value / top) * 100;
        return (
          <li key={stage.label}>
            <div className="flex items-baseline justify-between gap-3">
              <span className="text-[12.5px] font-medium text-[var(--ink)]">
                {stage.label}
              </span>
              <span className="mono text-[12.5px] font-semibold">
                {stage.value.toLocaleString('en-IN')}
                <span className="ml-1.5 text-[11px] font-normal text-[var(--ink-3)]">
                  {pct.toFixed(0)}%
                </span>
              </span>
            </div>
            <div className="mt-1 h-[10px] w-full overflow-hidden rounded-[3px] bg-[#f0ebf2]">
              <div
                className="h-full rounded-[3px] transition-[width] duration-500"
                style={{
                  width: `${Math.max(1, pct)}%`,
                  // One hue, stepped darker as the funnel narrows: the stages
                  // are an ordered sequence, not four separate things.
                  background: ['#f3a9c4', '#ee7aa3', '#e8195f', '#a60f43'][
                    Math.min(index, 3)
                  ],
                }}
              />
            </div>
            {stage.note && (
              <p className="mt-1 text-[11.5px] text-[var(--ink-3)]">{stage.note}</p>
            )}
          </li>
        );
      })}
    </ol>
  );
}

/* ----------------------------------------------------------- comparison */
export function CompareBars({
  rows,
  format = (n: number) => n.toFixed(3),
  max,
}: {
  rows: { label: string; a: number; b: number }[];
  format?: (n: number) => string;
  max?: number;
}) {
  const ceiling = max ?? Math.max(...rows.flatMap((r) => [r.a, r.b]), 0.001);
  return (
    <div className="space-y-4">
      {rows.map((row) => (
        <div key={row.label}>
          <p className="mb-1.5 text-[12.5px] font-medium">{row.label}</p>
          {[
            { value: row.a, color: SERIES.primary, name: 'Loop on' },
            { value: row.b, color: SERIES.secondary, name: 'Loop off' },
          ].map((bar) => (
            <div key={bar.name} className="mb-1 flex items-center gap-2.5">
              <span className="w-[58px] shrink-0 text-[11.5px] text-[var(--ink-2)]">
                {bar.name}
              </span>
              <span className="meter h-[9px] flex-1">
                <i
                  style={{
                    width: `${Math.max(1.5, (bar.value / ceiling) * 100)}%`,
                    background: bar.color,
                  }}
                />
              </span>
              <span className="mono w-[52px] shrink-0 text-right text-[12px] font-semibold">
                {format(bar.value)}
              </span>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}
