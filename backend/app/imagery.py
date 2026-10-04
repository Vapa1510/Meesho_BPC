"""Product imagery.

There is no photo library behind a demo catalogue, so the API draws each
product: a clean studio-style render of the right *kind* of pack (dropper
bottle, tube, jar, lipstick, compact...) in a brand colour taken from the
product id, on a soft category-tinted backdrop.

These are illustrations, not photographs. A seller who has a real photo sets
`image_url` on the product and the API serves that instead — the frontend asks
`image_for()` for a URL and does not care which one it gets.
"""
from __future__ import annotations

import hashlib
from functools import lru_cache

# Accent colours, all from the deck's palette.
ACCENTS = ["#E8195F", "#7B4FE0", "#F28C1C", "#0E9F6E", "#1F6FD0", "#C01165", "#F5B921"]

# Backdrop tint per category (soft, so the pack is what the eye lands on).
BACKDROP = {
    "Skincare": ("#FFE9F1", "#FFD3E3"),
    "Makeup": ("#FFEFE0", "#FFD9BC"),
    "Haircare": ("#F0E9FF", "#DCCFFF"),
    "Personal Care": ("#E3F7EE", "#C5EBDA"),
}
DEFAULT_BACKDROP = ("#F6F1FA", "#E6DCF0")

# Title keywords decide the pack; art_key is only the fallback.
KEYWORDS: list[tuple[tuple[str, ...], str]] = [
    (("patch",), "patch"),
    (("palette", "highlighter"), "palette"),
    (("compact", "powder"), "compact"),
    (("nail", "lacquer"), "nail"),
    (("lipstick", "lip tint", "lip balm", "blush stick", "stick", "lip "), "lipstick"),
    (("kajal", "brow", "pencil", "mascara", "liner"), "pencil"),
    (("shampoo", "conditioner", "body wash", "lotion", "wash", "hair oil serum"), "pump"),
    (("spray", "mist", "perfume", "deodorant"), "spray"),
    ((" oil", "oil "), "oil"),
    (("serum", "ampoule", "gel", "toner"), "dropper"),
    (("moisturiser", "mask", "clay", "peel", "scrub", "lightening"), "jar"),
    (("sunscreen", "cream", "cleanser", "razor"), "tube"),
]
ART_FALLBACK = {"serum": "dropper", "patch": "patch", "tint": "lipstick", "kajal": "pencil", "hair": "pump"}


def pick_shape(title: str, art_key: str = "") -> str:
    if art_key.startswith("pack:") and art_key[5:] in PACKS:   # a seller chose the pack
        return art_key[5:]
    t = f" {title.lower()} "
    for words, shape in KEYWORDS:
        if any(w in t for w in words):
            return shape
    return ART_FALLBACK.get(art_key, "jar")


def accent_for(seed: str) -> str:
    h = int(hashlib.md5(seed.encode()).hexdigest()[:8], 16)
    return ACCENTS[h % len(ACCENTS)]


def _mix(hex_a: str, hex_b: str, t: float) -> str:
    a = [int(hex_a[i : i + 2], 16) for i in (1, 3, 5)]
    b = [int(hex_b[i : i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02X}" for x, y in zip(a, b))


# --------------------------------------------------------------------- packs
# Every pack is drawn in a 400x400 box, centred, standing on y=330.
def _dropper(c, cl, cd):
    return f"""
<rect x="150" y="170" width="100" height="160" rx="26" fill="url(#glass)"/>
<rect x="150" y="170" width="100" height="160" rx="26" fill="{c}" opacity=".16"/>
<rect x="164" y="210" width="72" height="84" rx="10" fill="#fff"/>
<rect x="174" y="226" width="52" height="7" rx="3.5" fill="{c}"/>
<rect x="174" y="242" width="38" height="5" rx="2.5" fill="{cl}"/>
<rect x="174" y="254" width="44" height="5" rx="2.5" fill="{cl}"/>
<rect x="176" y="150" width="48" height="30" rx="6" fill="{cd}"/>
<path d="M184 150v-34a16 16 0 0 1 32 0v34z" fill="{c}"/>
<rect x="160" y="182" width="9" height="130" rx="4.5" fill="#fff" opacity=".45"/>"""


def _tube(c, cl, cd):
    return f"""
<path d="M150 150h100l-10 168a12 12 0 0 1-12 12h-56a12 12 0 0 1-12-12z" fill="{c}"/>
<path d="M150 150h100l-2 28H152z" fill="{cd}" opacity=".25"/>
<rect x="150" y="318" width="100" height="12" rx="3" fill="{cd}"/>
<rect x="172" y="104" width="56" height="48" rx="8" fill="#fff"/>
<rect x="172" y="104" width="56" height="12" rx="4" fill="{cl}"/>
<rect x="168" y="214" width="64" height="62" rx="9" fill="#fff" opacity=".92"/>
<rect x="178" y="228" width="44" height="7" rx="3.5" fill="{c}"/>
<rect x="178" y="243" width="30" height="5" rx="2.5" fill="{cl}"/>
<rect x="160" y="168" width="8" height="140" rx="4" fill="#fff" opacity=".35"/>"""


def _jar(c, cl, cd):
    return f"""
<rect x="112" y="226" width="176" height="104" rx="22" fill="#fff"/>
<rect x="112" y="226" width="176" height="104" rx="22" fill="{c}" opacity=".14"/>
<rect x="104" y="170" width="192" height="64" rx="18" fill="{c}"/>
<rect x="104" y="170" width="192" height="18" rx="9" fill="{cl}" opacity=".55"/>
<rect x="140" y="252" width="120" height="52" rx="10" fill="#fff"/>
<rect x="156" y="266" width="88" height="8" rx="4" fill="{c}"/>
<rect x="170" y="282" width="60" height="5" rx="2.5" fill="{cl}"/>
<rect x="122" y="238" width="8" height="78" rx="4" fill="#fff" opacity=".5"/>"""


def _lipstick(c, cl, cd):
    return f"""
<rect x="156" y="226" width="88" height="104" rx="12" fill="#2A1530"/>
<rect x="156" y="226" width="88" height="14" rx="6" fill="{c}"/>
<rect x="170" y="240" width="10" height="82" rx="5" fill="#fff" opacity=".18"/>
<rect x="168" y="190" width="64" height="44" rx="6" fill="#D9C7A3"/>
<path d="M172 190v-46c0-16 12-30 28-30s28 14 28 30v46z" fill="{c}"/>
<path d="M172 150c20-18 36-14 56 0v-6c0-16-12-30-28-30s-28 14-28 30z" fill="{cl}" opacity=".6"/>"""


def _compact(c, cl, cd):
    return f"""
<ellipse cx="200" cy="300" rx="124" ry="38" fill="{cd}"/>
<ellipse cx="200" cy="286" rx="124" ry="38" fill="{c}"/>
<ellipse cx="200" cy="286" rx="96" ry="28" fill="#fff" opacity=".9"/>
<ellipse cx="200" cy="286" rx="72" ry="20" fill="{cl}"/>
<path d="M92 270c0-70 50-112 108-112s108 42 108 112c-24 22-60 32-108 32s-84-10-108-32z" fill="{c}" opacity=".0"/>
<ellipse cx="200" cy="232" rx="104" ry="86" fill="{c}" transform="rotate(-8 200 232)" opacity=".92"/>
<ellipse cx="200" cy="232" rx="82" ry="66" fill="#fff" opacity=".88" transform="rotate(-8 200 232)"/>
<ellipse cx="180" cy="214" rx="26" ry="12" fill="#fff" transform="rotate(-24 180 214)" opacity=".9"/>"""


def _palette(c, cl, cd):
    pans = []
    cols = [c, cl, cd, _mix(c, "#F5B921", .5), _mix(c, "#FFFFFF", .75), _mix(c, "#510E44", .3)]
    for i, col in enumerate(cols):
        x = 126 + (i % 3) * 56
        y = 214 + (i // 3) * 56
        pans.append(f'<rect x="{x}" y="{y}" width="48" height="48" rx="10" fill="{col}"/>')
    return f"""
<rect x="108" y="150" width="184" height="180" rx="22" fill="{cd}" transform="rotate(-6 200 240)"/>
<rect x="108" y="170" width="184" height="160" rx="20" fill="#fff"/>
<rect x="108" y="170" width="184" height="30" rx="14" fill="{c}"/>
{''.join(pans)}"""


def _pencil(c, cl, cd):
    return f"""
<g transform="rotate(32 200 230)">
<rect x="176" y="86" width="48" height="204" rx="8" fill="{c}"/>
<rect x="176" y="86" width="48" height="40" rx="8" fill="{cd}"/>
<rect x="184" y="134" width="8" height="140" rx="4" fill="#fff" opacity=".35"/>
<rect x="196" y="150" width="20" height="60" rx="4" fill="#fff" opacity=".9"/>
<path d="M176 290h48l-24 54z" fill="#E6C9A8"/>
<path d="M190 322h20l-10 22z" fill="#2A1530"/>
</g>"""


def _pump(c, cl, cd):
    return f"""
<rect x="140" y="176" width="120" height="154" rx="28" fill="{c}"/>
<rect x="140" y="176" width="120" height="30" rx="14" fill="{cl}" opacity=".5"/>
<rect x="156" y="222" width="88" height="82" rx="12" fill="#fff"/>
<rect x="168" y="238" width="64" height="8" rx="4" fill="{c}"/>
<rect x="176" y="256" width="48" height="5" rx="2.5" fill="{cl}"/>
<rect x="176" y="268" width="40" height="5" rx="2.5" fill="{cl}"/>
<rect x="188" y="136" width="24" height="42" rx="5" fill="{cd}"/>
<path d="M170 122h58a14 14 0 0 1 14 14v6h-86v-6a14 14 0 0 1 14-14z" fill="{cd}"/>
<rect x="150" y="190" width="9" height="124" rx="4.5" fill="#fff" opacity=".3"/>"""


def _oil(c, cl, cd):
    return f"""
<path d="M176 140h48v32c30 14 44 40 44 76v66a16 16 0 0 1-16 16H148a16 16 0 0 1-16-16v-66c0-36 14-62 44-76z" fill="url(#glass)"/>
<path d="M176 140h48v32c30 14 44 40 44 76v66a16 16 0 0 1-16 16H148a16 16 0 0 1-16-16v-66c0-36 14-62 44-76z" fill="{c}" opacity=".5"/>
<rect x="152" y="238" width="96" height="70" rx="12" fill="#fff"/>
<rect x="166" y="254" width="68" height="8" rx="4" fill="{c}"/>
<rect x="176" y="272" width="48" height="5" rx="2.5" fill="{cl}"/>
<rect x="180" y="100" width="40" height="46" rx="8" fill="{cd}"/>
<rect x="142" y="196" width="9" height="116" rx="4.5" fill="#fff" opacity=".4"/>"""


def _spray(c, cl, cd):
    return f"""
<rect x="146" y="190" width="108" height="140" rx="24" fill="url(#glass)"/>
<rect x="146" y="190" width="108" height="140" rx="24" fill="{c}" opacity=".35"/>
<rect x="160" y="238" width="80" height="62" rx="10" fill="#fff"/>
<rect x="172" y="252" width="56" height="7" rx="3.5" fill="{c}"/>
<rect x="182" y="268" width="36" height="5" rx="2.5" fill="{cl}"/>
<rect x="180" y="160" width="40" height="34" rx="6" fill="{cd}"/>
<path d="M168 134h52a10 10 0 0 1 10 10v12h-72v-12a10 10 0 0 1 10-10z" fill="{c}"/>
<rect x="150" y="204" width="8" height="112" rx="4" fill="#fff" opacity=".4"/>
<circle cx="236" cy="124" r="4" fill="{cl}"/><circle cx="252" cy="112" r="3" fill="{cl}"/><circle cx="250" cy="130" r="3" fill="{cl}"/>"""


def _nail(c, cl, cd):
    return f"""
<rect x="146" y="206" width="108" height="124" rx="24" fill="{c}"/>
<rect x="146" y="206" width="108" height="26" rx="12" fill="{cl}" opacity=".45"/>
<rect x="160" y="248" width="80" height="48" rx="10" fill="#fff" opacity=".9"/>
<rect x="172" y="262" width="56" height="7" rx="3.5" fill="{c}"/>
<rect x="172" y="132" width="56" height="78" rx="12" fill="#2A1530"/>
<rect x="184" y="144" width="8" height="54" rx="4" fill="#fff" opacity=".2"/>"""


def _patch(c, cl, cd):
    dots = []
    for i in range(12):
        x = 150 + (i % 4) * 34
        y = 190 + (i // 4) * 40
        r = 12 if i % 3 else 9
        dots.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{c if i % 2 else cl}"/><circle cx="{x-3}" cy="{y-3}" r="{r*0.35:.1f}" fill="#fff" opacity=".7"/>')
    return f"""
<rect x="116" y="150" width="168" height="170" rx="26" fill="#fff"/>
<rect x="116" y="150" width="168" height="36" rx="16" fill="{c}"/>
{''.join(dots)}
<rect x="144" y="292" width="112" height="6" rx="3" fill="{cl}"/>"""


PACKS = {
    "dropper": _dropper, "tube": _tube, "jar": _jar, "lipstick": _lipstick, "compact": _compact,
    "palette": _palette, "pencil": _pencil, "pump": _pump, "oil": _oil, "spray": _spray,
    "nail": _nail, "patch": _patch,
}


@lru_cache(maxsize=512)
def _render(shape: str, accent: str, bg1: str, bg2: str) -> str:
    cl = _mix(accent, "#FFFFFF", 0.55)
    cd = _mix(accent, "#2A1530", 0.35)
    body = PACKS.get(shape, _jar)(accent, cl, cd)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400" width="400" height="400">
<defs>
<radialGradient id="bg" cx="50%" cy="38%" r="75%"><stop offset="0" stop-color="{bg1}"/><stop offset="1" stop-color="{bg2}"/></radialGradient>
<linearGradient id="glass" x1="0" x2="1"><stop offset="0" stop-color="#fff" stop-opacity=".95"/><stop offset=".5" stop-color="#fff" stop-opacity=".75"/><stop offset="1" stop-color="#fff" stop-opacity=".9"/></linearGradient>
<filter id="blur" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="7"/></filter>
</defs>
<rect width="400" height="400" fill="url(#bg)"/>
<circle cx="78" cy="84" r="46" fill="{accent}" opacity=".10"/>
<circle cx="330" cy="318" r="64" fill="{accent}" opacity=".10"/>
<circle cx="64" cy="318" r="16" fill="#fff" opacity=".6"/>
<ellipse cx="200" cy="338" rx="108" ry="12" fill="#2A1530" opacity=".22" filter="url(#blur)"/>
{body}
</svg>"""


def render_svg(
    title: str,
    category: str = "",
    art_key: str = "",
    seed: str = "",
) -> str:
    bg1, bg2 = BACKDROP.get(category, DEFAULT_BACKDROP)
    return _render(pick_shape(title, art_key), accent_for(seed or title), bg1, bg2)


def image_for(product) -> str:
    """URL the frontend should use for this product."""
    if product.image_url:
        return product.image_url
    return f"/product/{product.product_id}/image.svg"
