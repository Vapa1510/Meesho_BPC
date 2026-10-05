# Creator × Product Fit Engine

**Meesho DICE Challenge Season 3 · Business Track · Team Pro, IIT (BHU) Varanasi**
Growing Beauty & Personal Care through influencers.

From 1000s of BPC listings to a few worth promoting: the engine filters first, scores seven
signals weighted by the creator's cell, explains every pick, rewards fit (not volume) and learns
from every promote, save or skip (with reason).

- **Live prototype:** https://meesho-cfe.vercel.app (API: https://meesho-bpc.onrender.com, docs at `/docs`)
- **Sample data, not Meesho data.** 164 BPC listings, 13 creators. Every number on screen is computed live.

---

## The QR codes in the deck

The deck is final, so the prototype is built around the five QR codes exactly as printed.

| Slide | Label | Opens | What a judge sees |
| --- | --- | --- | --- |
| 4 | Survey responses | Google Drive folder | Survey data (outside this repo) |
| 7 | 1 · Indirect Onboarding Tool | `/creator/onboard` | Riya's onboarding, plus the 4-stop walkthrough |
| 7 | 2 · Creator DNA Profile | `/creator` | Riya's Creator DNA (every value tagged fetched or asked) above her Top 8 |
| 8 | 3 · Fit Engine (creator side) | `/creator/onboard` | The walkthrough's "Fit Engine: her Top 8" stop is one tap away |
| 8 | 4 · Brand Match + Feedback Loop | `/creator` | The walkthrough's "Brand Match + feedback loop" stop is one tap away |

Both landing pages carry a **four-stop walkthrough** that follows slides 7 and 8 in order:
onboard Riya → her Creator DNA → her Top 8 → Brand Match and the feedback loop. A first-time
visitor lands on **Riya Kapoor**, the deck's persona. **Reset demo** puts the shared deployment
back to the exact numbers on the slides.

**Keep the QR codes working:** deploy to the *same* Vercel project (the `frontend/.vercel` link
is kept for that) and the *same* Render service, and keep `app/creator/page.tsx` and
`app/creator/onboard/page.tsx` where they are. See [DEMO.md](DEMO.md).

---

## Run it

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --port 8000      # creates and seeds creator_fit.db on first start
```

```bash
cd frontend
npm install
npm run dev                           # http://localhost:3000
```

```bash
cd backend && pytest -q               # 69 tests, including the deck-number suite
```

`make reset` (or the **Reset demo** button, or `POST /demo/reset`) restores the deck state.

---

## What the deck says, and where it lives in the code

| Deck | Claim | Code |
| --- | --- | --- |
| Slides 2, 6, 16 | Filter first: stock, rating ≥ 3.8 (seller rating under 50 reviews), returns ≤ category median, policy/claims, price window, exclusions, audience fit ≥ 50 | `engine/eligibility.py` |
| Slides 4, 6, 16 | Seven signals: Audience, Niche, Intent, Product, Commerce, Trend, Brand | `engine/scoring.py` |
| Slides 6, 16 | 3×3 marking scheme, `W(cell) = W_intent + Δscale`, every cell sums to 100; crowding λ = 4 / 8 / 12 | `engine/scoring.py` (`BASE_WEIGHTS`, `SCALE_DELTA`, `SATURATION_LAMBDA`) |
| Slide 7 | Indirect onboarding: 5–8 / 3–5 / 0–2 questions by tier; Q2 + Q3 → intent (0.4 / 0.6); Q5 if separation < 0.25; consent before saving | `engine/onboarding.py`, `/creator/onboard` |
| Slide 7 | Top-K by tier: Starter-5 (Emerging), Top 8 (Growth), Top 4 (Established) | `engine/pipeline.py` (`TOP_K_BY_SCALE`) |
| Slides 7, 8 | Feedback re-ranks, bounded ×0.62 to ×1.15, 45-day half-life; never rewrites the DNA | `engine/learning.py` |
| Slide 8 | Riya: 164 → 25 eligible; #1 Daily Sunscreen SPF 50 = 85; brand sees the same scores; skip of Ceramide 76 → 73 | `tests/test_deck_numbers.py` |
| Slide 8 | Skip reasons and what each changes; decline = skip with a reason | `engine/learning.py`, `routers/feedback.py`, `routers/brands.py` |
| Slides 2, 4, 5, 12 | Fit Rewards: fit-qualified picks only (fit ≥ 80); brand-funded samples only at fit ≥ 80; starter bonus on the first delivered fit-pick order; archetype rewards; paid on delivered orders net of returns | `engine/rewards.py`, `routers/orders.py`, offers in `routers/brands.py` |
| Slide 5 | Click → Order → NMV → Fit Rewards → Learn | `POST /orders`, `GET /rewards/{id}` |
| Slide 11 | Baseline = generic discovery; weeks 5–6 interleaved test with source hidden; pick-source logging | `engine/baseline.py`, `?mode=interleaved`, `GET /analytics/pilot`, Lab → Pilot test |
| Slides 9, 12 | Trust metrics: explained picks, wrong picks, freshness, mix diversity, catalogue reach, fallback coverage, P95 latency, Precision@5 | `GET /analytics/trust`, Lab → Trust metrics |
| Slide 18 | Riya × Vitamin C Serum: 68.3 / 98.0 / 87.9 / 93.6 / 91.8 / 74.2 / 85.0 → 85.0 − 1.76 = 83 | `tests/test_deck_numbers.py` |
| Slide 17 | REST endpoints, creators / products / interactions tables | `routers/`, `models.py` |

`tests/test_deck_numbers.py` asserts every number above on the full 164-listing catalogue, so a
code change cannot silently move a number a judge can check.

---

## How a score is built

```
FitScore(c, p) = ( Σ_i W_i(cell) · s_i(c, p)  −  λ_S(scale) · saturation(p)  −  ReturnPenalty(p) ) × L(c, p)

W(cell)  = W_intent + Δ_scale            each cell sums to 100
L(c, p)  = learned adjustment from her feedback, bounded 0.62 – 1.15, 45-day half-life
Scored only if every hard check passes, including AudienceFit ≥ 50
```

The appendix slide (A3) shows the equation without `L(c, p)`; slide 8 states its bounds.

| Signal | Computed as (prototype) | At scale |
| --- | --- | --- |
| Audience | 0.68 × age overlap (0.75 recall + 0.25 precision) + 0.32 × city-tier overlap | + language and interests from attributed buyers and consented platform/API analytics |
| Niche | 34 + 52 × (category share ÷ top share) + tag bonus (≤ 12) | same, from live content history |
| Intent | her intent scores × the product's trend / commerce / brand roles | + observed promotion behaviour |
| Product | 0.6 × quality (rating, reviews, seller rating, returns) + 0.4 × price comfort | same |
| Commerce | 0.46 × conversion + 0.30 × orders (30 d) + 0.24 × NMV (30 d) | + CTR and similar-creator performance |
| Trend | trend score × stage multiplier (seeded) | search and category momentum feeds |
| Brand | Σ min(her positioning share, product share) | + brand/value alignment, past collaborations |

**Price.** The *band* is what her audience usually pays (Riya: ₹299–499). The *price window* is
the hard gate: 45% below to 30% above the band (Riya: ₹164–649). Inside the window, price comfort
lowers Product fit for anything outside the band, and the card says "above your band". This is
how slide 8 gets 164 → 62 after the price window, and why Riya can skip the ₹599 Ceramide
Moisturiser "above her range".

---

## Architecture (honest version)

```
Next.js 14 (Vercel)  ──REST/JSON──▶  FastAPI (Render)  ──▶  SQLite (prototype) / PostgreSQL (production path)
```

| Piece | In the prototype | Proposed / production |
| --- | --- | --- |
| Web app | Next.js, responsive (works from a phone after a QR scan) | PWA |
| API | FastAPI: creator, product, recommendation, feedback, analytics, brand, orders, demo | API gateway with auth and rate limits |
| Database | **SQLite**, seeded on start; resets when the free host restarts | PostgreSQL (`docker-compose.yml`, `DATABASE_URL`) |
| Retrieval | **Deterministic hashed similarity** + category + momentum (explainable, no model download) | learned encoder + pgvector ANN index |
| Ranker | **Explainable weighted rules** (7 signals × 3×3 weights) + bounded feedback adjustments | learned ranker behind the same `_rank()` interface; training rows already logged |
| Cache | none | Redis |

`GET /health` says this in so many words. `USE_PGVECTOR=1` only reads stored vectors; it does not
run a pgvector query.

---

## Evidence labels

| Label | Meaning | Examples |
| --- | --- | --- |
| Sourced | external market data or Meesho disclosures | 4.12M creators (ISB × Hashfame), +141% content-commerce NMV (Q1 FY27) |
| Derived | arithmetic on sourced inputs | 2.72M non-metro creators, ~85% with no campaign (1 − 408K / 2.72M) |
| Sample data | the prototype's catalogue and creators | every product, rating, order count in the app |
| Projection | arithmetic on sample inputs, not a forecast | brand-side reach, orders, NMV |
| Simulated | synthetic creators with hidden preferences: mechanism checks | Precision@5, the synthetic interleaving win rate |
| Team hypothesis | modelled target, validated in the pilot | +11.5% NMV per creator, −13% returns, ~41% faster first order, −30% search effort |

**NMV** is net of cancellations, returns and undelivered orders; it is not revenue or profit.

**Funnel ≠ NMV case.** The funnel uplift (+25% clicks, +39% add-to-cart, +33% orders per 1,000
product views) describes product-page conversion. The +11.5% NMV case does not use it: it holds
orders per promotion at 8 and AOV at ₹400 and counts only +0.30 promotions per creator a month.

---

## Pilot (slide 11)

- **Weeks 3–4, baseline:** today's generic discovery (`mode=generic`: high-converting SKUs for everyone).
- **Weeks 5–6, interleaved test:** personalised and generic picks in one feed, team-draft order,
  source hidden from the creator, logged per pick (`recommendation_log.source`, `feedback_events.source`).
  Gate 1 reads the match-quality win rate (`GET /analytics/pilot`). Interleaving compares both
  feeds inside each creator's session, which is why 150–200 creators can read match quality when
  a conventional A/B test on NMV could not detect +11.5%.
- **Weeks 7–12:** A/B with holdout; NMV is directional, with confidence intervals.

The Lab's **Pilot test** page serves an interleaved slate, reveals the source on demand, and can run
a synthetic check (labelled as such).

---

## API

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/creator/{id}` · `/creators` | Profile, Creator DNA and sources (Riya first) |
| `POST` | `/creator/onboard` | Build the DNA from a connected profile + answers (consent required; same handle updates, never duplicates) |
| `PATCH` | `/creator/{id}` | The creator correcting intent, price or exclusions; only sent fields change |
| `GET` | `/recommendations/{id}?category=bpc[&mode=interleaved\|generic][&top_k=]` | Top-K (by tier by default) with drivers, checks, rewards, source |
| `POST` | `/rank-products` | Score any products; each says whether it would be served, and why not |
| `GET` | `/product/{id}` | Product details |
| `POST` | `/feedback` | Promote / save / skip (a skip needs a reason) |
| `GET` | `/product/{id}/matches` | Creators ranked for a product (brand view), projections, skip reasons |
| `POST` | `/pitches` · `/pitches/{id}/respond` | Offers, optional Fit Reward (fit ≥ 80), decline with a reason |
| `POST` | `/orders` | Attributed order event: delivered / returned / cancelled |
| `GET` | `/rewards/{id}` | Fit Rewards: archetype, earned, delivered fit-pick NMV |
| `GET` | `/analytics/trust` · `/analytics/pilot` · `/analytics/metrics` | Trust metrics vs targets, interleaving win rate, counters |
| `POST` | `/simulation/generate` · `/simulation/run` | Synthetic creators only (never the deck's creators) |
| `GET` · `POST` | `/demo` · `/demo/reset` | The walkthrough and the reset |

---

## Notes for reviewers: where a slide and the prototype differ

The deck could not be edited after submission. These are the places where a slide reads
differently from the running prototype, and why.

- **Slide 17 (A4) phone screens** label the profile "Riya", but the values shown (18–24, Tier 1/2,
  ₹200–700, intent 78/86/54, Top 5 of 90/85/84/83/82) are seed creator **Aditi Sharma (C12345)**,
  who is in the app with exactly those numbers. Riya's own DNA is the one on slides 7, 8 and 18.
- **Slides 5 and 6** show illustrative product lists (marked illustrative on the slides). The live
  Top 8 for Riya is Sunscreen 85, Vitamin C 83, Rosemary Hair Oil 83, Niacinamide 78, ….
- **Top-K:** slides 2, 4, 5, 11 and 17 say "Top 5"; the prototype follows slide 7's tier rule
  (Starter-5 / Top 8 / Top 4), as the pilot plan intends at scale.
- **Slide 8** says "12 creators": the sample data has 12 seeded creators plus Riya.
- **Slide 17** marks PostgreSQL + pgvector as in the prototype: the prototype runs SQLite with
  deterministic retrieval (see Architecture).
- **"Not relevant"** (slides 9, 12): the prototype uses "Skip (with reason)" throughout; wrong
  picks are skips for a fit reason (too expensive, not my niche, audience won't care, don't trust
  product, not trending).
- **Question depth:** within the slide's ranges; an Emerging creator gets 5–7 questions and a
  Growth creator 4–5.

---

## Layout

```
backend/app/
  engine/  eligibility · retrieval · scoring · onboarding · reasons · learning · rewards
           baseline (generic feed, fallback, interleaving) · pipeline · matching · simulation · evaluation
  routers/ creators · products · recommendations · feedback · brands · orders · analytics · simulation · demo
  seed.py  12 creators + Riya (built from her deck answers) + 164 listings
backend/tests/   69 tests; test_deck_numbers.py pins the slides
frontend/app/    /  creator/{,onboard,profile,catalogue,offers}  brand/*  lab/{pipeline,metrics,pilot,simulate}
frontend/components/DemoGuide.tsx   the walkthrough on the QR landing pages
```
