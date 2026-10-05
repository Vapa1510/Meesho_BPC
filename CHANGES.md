# Changes in this version (v3, deck-locked)

The deck is final, so every change makes the prototype match the deck, or makes it say plainly
where it cannot. The printed QR codes (`/creator`, `/creator/onboard`) are unchanged.

## Review findings (G01–G29)

| ID | Finding | Status | What changed |
| --- | --- | --- | --- |
| G01 | Fit Rewards not built | **Done** | `engine/rewards.py`: fit ≥ 80 only; starter bonus on first delivered fit-pick order; archetype rewards (Trend Scout / Commerce Builder / Brand Builder); paid on delivered orders net of returns. Offers can carry a sample, conversion bonus or early access, refused below fit 80. Rewards on cards, drawer, Profile. |
| G02 | Slide 8 QR codes open the wrong screens | **Worked around** (deck frozen) | Both QR pages carry a 4-stop walkthrough that follows slides 7–8; `/creator` shows Riya's Creator DNA first; first-time visitors land on Riya. |
| G03 | Three different Riyas | **Partly** | Riya is now seeded (C013) from her deck answers through the onboarding code, so slides 7, 8 and 18 reproduce exactly and live. A4's screens (Aditi's data) and slides 5–6 (illustrative) cannot change; explained in README. |
| G04 | Profile Save overwrote intent | **Fixed** | Frontend sends only changed fields; backend swaps intent scores instead of overwriting; sources say "Corrected on Profile". |
| G05 | Loop stopped at promote/save/skip | **Done** | `POST /orders` (delivered / returned / cancelled), NMV net of returns, delivered orders feed learning, rewards accrue. Periodic DNA refresh labelled Phase 2. |
| G06 | pgvector shown as in prototype | **Documented** | `/health`, Lab and README state: SQLite + deterministic retrieval in the MVP; pgvector is the production path. |
| G07 | Signals thinner than slide 6 | **Documented** | Each signal's formula shown in the drawer; README table "prototype vs at scale". |
| G08 | Consent pre-ticked | **Fixed** | Unticked by default; the button says "Tick consent to continue". |
| G09 | Precision@5 framing | **Done** | Labelled "simulated creators: a mechanism check"; simulations run on synthetic creators only. |
| G10 | Stale DB and bloat in zip | **Fixed** | Zip ships without `creator_fit.db`, `node_modules`, `.next`, build logs. Seeding is idempotent and adds anything missing. |
| G11 | API skipped two rules | **Fixed** | Skip without a reason → 422. Offers to an off-niche or gated creator → 422 with the reason. |
| G12 | Top-K told three stories | **Done in app** | One rule everywhere in the app and API (Starter-5 / Top 8 / Top 4, slide 7). |
| G13 | No "Not relevant" reason | **Done** | "Skip (with reason)" everywhere; wrong-pick rate = skips for a fit reason. |
| G14 | Question bounds | No change needed | 5–7 and 4–5 sit inside the slide's 5–8 and 3–5. |
| G15 | A3 equation omits learned adjustment | **Documented** | Full equation in README and the drawer's formula line. |
| G16 | Source labels overstated | **Fixed** | Labels say exactly what was used; hashtags now cross-check the niche and positioning (and fill in when nothing else exists). |
| G17 | README stale | **Fixed** | Rewritten to mirror the deck, with limitations. |
| G18 | Legacy pages deployed | **Fixed** | Removed `/recommendations`, `/profile`, `/pipeline`, `/product/[id]`, `/catalogue`, `/insights`, `/metrics`, `/simulate`. |
| G19 | Next.js advisory | **Fixed** | 14.2.15 → 14.2.35. |
| G20 | Fragile live demo | **Done** | Riya seeded; Reset demo; "waking the server" notice with automatic retries for reads. |
| G21 | "12 creators" vs 13 | Documented | 12 seeded + Riya. |
| G22–G29 | Deck facts (headline loss at 10K, ~85% derived, 4.7×, 4.6% margin, AOV FY26, unlinked refs, funnel vs NMV, unverified figures) | Deck frozen | Funnel ≠ NMV note in Lab → Trust metrics and README; evidence labels in README. Others are Q&A prep. |

## Your P0 / P1 / P2 list

| Priority | Item | Status |
| --- | --- | --- |
| P0 | Deck ↔ prototype identical | Riya, catalogue, price bands, weights, scores and Top-K reproduce slides 7, 8, 16, 18 exactly; pinned by `tests/test_deck_numbers.py`. |
| P0 | Top-K rule | Starter-5 / Top 8 / Top 4, API default and every screen. |
| P0 | Prototype URL | Same domains kept; production build verified; waking notice for cold starts. Re-check from an incognito window after deploying (DEMO.md). |
| P0 | QR codes | Kept as printed; both landing pages route to all four stops. |
| P0 | Clean build | `next build` passes; 69 backend tests pass on Python 3.11 (Render's) and 3.13; end-to-end browser run of the judges' path passes at phone size. |
| P0 | Feedback loop | Promote / Save / Skip (with reason) → instant re-rank with a "what changed" banner (Ceramide 76 → 73) → brand sees the reason. |
| P0 | Evidence labels | In the app (sample data, projection, simulated, team hypothesis) and README. |
| P0 | NMV language | One sentence, used wherever NMV appears. |
| P0 | Modelled impact | Lab → Trust metrics lists +11.5%, −13%, ~41%, −30% as modelled targets, not results. |
| P0 | One persona | Riya everywhere in the app (default creator, walkthrough, onboarding). The deck's A4 slide cannot change. |
| P0 | Price eligibility | Every pick passes the deck's price window; anything outside the band is labelled "above/below your band" and scored lower. A strict band would break slide 8 (164 → 25, Ceramide ₹599 "above her range"). Catalogue marks products the feed will never serve. |
| P0 | Seven signals | Audience, Niche, Intent, Product, Commerce, Trend, Brand, everywhere. |
| P0 | Weights | 63 weights match A3, every cell sums to 100 (tested). |
| P1 | Pilot design / baseline | Generic baseline feed, team-draft interleaving, pick-source logging, win rate (Lab → Pilot test). |
| P1 | Meesho integration | Landing page and README: plugs into Creator Club and its AI toolkit. |
| P1 | Audience data | Explained as attributed buyers + consented platform/API analytics (drawer, README). |
| P1 | Cold start | Starter-5 note for Emerging creators; new listings judged on seller rating. |
| P1 | Business impact bridge | Funnel ≠ NMV note. |
| P1 | Retrieval explanation | MVP = explainable rules + deterministic retrieval; production = learned. |
| P1 | Learning claim | "Feedback re-ranks immediately; DNA refresh is Phase 2." |
| P1 | Recommendation explanation | "Why this product?" with the 3 biggest contributions on every card and in the drawer. |
| P1 | Eligibility gate | Every check shown in the drawer (stock, rating, returns, claims, price window, exclusions, audience, already promoted). |
| P1 | Wrong-recommendation handling | "Skip (with reason)" everywhere; reason required. |
| P1 | Simulation | Labelled mechanism validation; synthetic creators only; kept out of brand lists and trust metrics. |
| P1 | Evaluation metrics | Lab → Trust metrics: explained picks, wrong picks, freshness, mix diversity, catalogue reach, fallback coverage, P95 latency, Precision@5 vs targets. |
| P2 | Brand side | Labelled "Brand view · extension (Phase 2)". |
| P2 | Product diversity | Tracked, not enforced (labelled). |
| P2 | pgvector | Not presented as powering the demo. |
| P2 | UI polish | Consistent terminology; legacy pages removed; top-pick card fixed on phones; responsive header. |
| P2 | README | Rewritten. |
| P2 | Demo flow | DEMO.md 60–90 s script + Reset demo. |
