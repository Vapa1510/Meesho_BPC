import type { Signal } from '@/lib/types';

/** Colour by score band, so a number reads before it is read. */
export function fitColor(score: number): string {
  if (score >= 85) return '#0FA85F';
  if (score >= 80) return '#26A9A0';
  if (score >= 70) return '#F0A21C';
  return '#E06A3B';
}

export function FitBadge({ score, size = 'md' }: { score: number; size?: 'sm' | 'md' | 'lg' }) {
  const dims = { sm: 32, md: 40, lg: 54 }[size];
  const font = { sm: 14, md: 17, lg: 23 }[size];
  return (
    <div
      className="flex shrink-0 flex-col items-center justify-center rounded-xl font-extrabold leading-none text-white"
      style={{ width: dims, height: dims, background: fitColor(score), fontSize: font }}
      aria-label={`Fit score ${score} out of 100`}
    >
      {score}
      <span className="mt-[1px] text-[9px] font-bold tracking-wide">FIT</span>
    </div>
  );
}

const SIGNAL_COLOR: Record<string, string> = {
  audience: '#1885FE',
  creator: '#8044DF',
  intent: '#E8195F',
  product: '#02A756',
  commerce: '#F39706',
  trend: '#FD8004',
};

export function SignalBars({ signals }: { signals: Signal[] }) {
  return (
    <ul className="space-y-2">
      {signals.map((signal) => (
        <li key={signal.name} className="flex items-center gap-2 text-[12px]">
          <span className="w-[74px] shrink-0 font-semibold text-navy">
            {signal.label.replace(' fit', '')}
          </span>
          <span className="bar">
            <span
              style={{
                width: `${Math.max(2, Math.min(100, signal.score))}%`,
                background: SIGNAL_COLOR[signal.name] ?? '#8E8AA3',
              }}
            />
          </span>
          <span className="w-[26px] shrink-0 text-right font-bold text-navy">
            {Math.round(signal.score)}
          </span>
          {/* The weight is what makes two creators rank the same product
              differently, so it is shown rather than hidden. */}
          <span className="w-[34px] shrink-0 text-right text-[10px] text-mute">
            ×{signal.weight.toFixed(2)}
          </span>
        </li>
      ))}
    </ul>
  );
}

export function ConfidencePill({ level }: { level: 'LOW' | 'MEDIUM' | 'HIGH' }) {
  const styles = {
    HIGH: 'bg-[#E4F7EA] text-[#0B6B38] border-[#B7E4C8]',
    MEDIUM: 'bg-[#FFF1D6] text-[#8A5A00] border-[#F5D79A]',
    LOW: 'bg-[#F1EEF6] text-[#5B5873] border-[#DDD7E8]',
  }[level];
  return <span className={`chip border font-bold ${styles}`}>{level}</span>;
}

export function TrendPill({ stage, score }: { stage: string; score: number }) {
  const rising = stage === 'rising' || stage === 'peak';
  return (
    <span
      className={`chip font-bold ${
        rising ? 'bg-[#E4F7EA] text-[#0B6B38]' : 'bg-[#F1EEF6] text-[#5B5873]'
      }`}
    >
      {stage.toUpperCase()} {rising ? '↑' : '·'} {score.toFixed(2)}
    </span>
  );
}
