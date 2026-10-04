/**
 * Inline SVG product art.
 *
 * Drawn rather than photographed so the repo has no binary assets and the demo
 * never shows a broken image. `art_key` comes straight from the API.
 */
const ART: Record<string, JSX.Element> = {
  serum: (
    <>
      <rect x="15" y="1" width="10" height="9" rx="4" fill="#2A1A30" />
      <rect x="13" y="9" width="14" height="5" rx="1.5" fill="#3B2A44" />
      <rect x="8" y="14" width="24" height="31" rx="6" fill="#F0920F" />
      <rect x="11.5" y="23" width="17" height="14" rx="2" fill="#fff" />
      <circle cx="20" cy="28" r="2.6" fill="#F28A1A" />
      <rect x="14" y="33" width="12" height="1.6" rx=".8" fill="#C9C5D6" />
    </>
  ),
  patch: (
    <>
      <ellipse cx="20" cy="33" rx="16" ry="9" fill="#0F9D9A" />
      <rect x="4" y="21" width="32" height="12" fill="#0F9D9A" />
      <ellipse cx="20" cy="21" rx="16" ry="9" fill="#19C2BE" />
      <ellipse cx="20" cy="21" rx="12" ry="6" fill="#E7FAF8" />
      <circle cx="15" cy="21" r="2.2" fill="#F5B7C8" />
      <circle cx="21" cy="19.5" r="2.2" fill="#F5B7C8" />
      <circle cx="25.5" cy="22" r="2.2" fill="#F5B7C8" />
    </>
  ),
  tint: (
    <>
      <rect x="16" y="2" width="9" height="13" rx="3" fill="#2A1A30" />
      <path d="M14 15h13l-1 5H15z" fill="#B3123F" />
      <rect x="12" y="20" width="17" height="25" rx="5" fill="#E8195F" />
      <rect x="15" y="27" width="11" height="9" rx="2" fill="#FDE9F3" />
    </>
  ),
  kajal: (
    <>
      <rect x="16" y="5" width="9" height="30" rx="2" fill="#2A1A30" />
      <rect x="16" y="10" width="9" height="4" fill="#E0B046" />
      <path d="M16 35h9l-4.5 9z" fill="#E9D3B4" />
      <path d="M19 40h3l-1.5 4z" fill="#2A1A30" />
    </>
  ),
  hair: (
    <>
      <rect x="17" y="1" width="8" height="5" rx="2" fill="#2A1A30" />
      <rect x="14" y="5" width="16" height="4" rx="1.5" fill="#3B2A44" />
      <rect x="9" y="9" width="23" height="36" rx="6" fill="#3A2540" />
      <rect x="12" y="20" width="17" height="16" rx="2" fill="#F3D9EA" />
      <rect x="15" y="25" width="11" height="2" rx="1" fill="#7C1067" />
      <rect x="15" y="30" width="8" height="1.6" rx=".8" fill="#B58AA8" />
    </>
  ),
};

export function ProductArt({ artKey, size = 40 }: { artKey: string; size?: number }) {
  return (
    <svg
      viewBox="0 0 40 48"
      width={size}
      height={size * 1.2}
      role="img"
      aria-hidden="true"
      className="shrink-0"
    >
      {ART[artKey] ?? ART.serum}
    </svg>
  );
}

export function ProductThumb({ artKey, size = 44 }: { artKey: string; size?: number }) {
  return (
    <div
      className="flex shrink-0 items-center justify-center rounded-lg bg-[#F8F2F6]"
      style={{ width: size, height: size * 1.15 }}
    >
      <ProductArt artKey={artKey} size={size * 0.78} />
    </div>
  );
}
