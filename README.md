# Creator × Product Fit Engine

> **v2.1, aligned with the DICE deck.** What changed from v2:
> - **Indirect onboarding** (`engine/onboarding.py`, `/creator/onboard`). Creators connect a profile and
>   answer a few indirect questions: 5–8 for Emerging, 3–5 for Growth, 0–2 taps for Established. The
>   engine never asks for a "goal". Q1 feeds the **Content** signal, Q2 + Q3 (and an adaptive Q5) feed
>   **Intent** as a weighted score, Q4 feeds the **Product + Price** signals (preferred price = median
>   pick, observed range = min–max of picks). Intent separation below 0.25 (an MVP heuristic) triggers Q5.
> - **Seven signals**: Brand fit (positioning overlap) joins audience, niche, intent, product, commerce
>   and trend.
> - **3×3 marking scheme**: weights come from the creator's cell, scale × primary intent,
>   `W(cell) = W_intent + Δ_scale`, each cell summing to 100.
> - **Penalties are visible**: crowding (4 / 8 / 12 points by scale) and return risk (0–10 points) are
>   subtracted, instead of being hidden inside the trend signal.
> - **Price comfort is part of Product fit** (0.6 × quality + 0.4 × price comfort), not a multiplier.
> - **Gates** match the deck: rating ≥ 3.8 (seller rating until a listing has 50 reviews), returns ≤
>   category median (once there is history), audience fit ≥ 0.5.
> - Tier label "Top" is now "Established"; Top-K is 5 / 8 / 4 by scale; content angles are styled by
>   intent (Trend hook / Proof angle / Identity story) and use the formats from Q1.

One recommendation engine with two sides, built from slides 06 and 07 of the Meesho DICE
Season 3 submission.

- **Creator side.** A ranked feed of products with pictures, fit scores and reasons. Promote, save or
  skip with a reason, and the feed re-ranks. Accept or decline offers from brands.
- **Brand side.** Pick a seller, open a product, and see which creators fit it, with a projection of
  reach, orders and NMV. Send an offer, list a new product, and read why creators skipped.
- **Engine lab.** The filter funnel, a creator simulation with hidden preferences, and ranking metrics.

```
Next.js (Poppins, DICE theme)  ──REST/JSON──▶  FastAPI  ──▶  SQLite / PostgreSQL + pgvector
  Creator   Discover · Catalogue · Offers · Profile     eligibility → retrieval → ranking
  Brand     Dashboard · Product · List · Offers sent    product-to-creator matching
  Lab       Pipeline · Simulation · Metrics             offers · imagery · closed loop
```

---

## Run it

Two terminals. No database to install.

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --port 8000     # seeds itself on first start
```

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:3000>. API reference at <http://localhost:8000/docs>.

```bash
cd backend && pytest -q        # 41 tests
```

If you ran an earlier version, delete `backend/creator_fit.db` once so the new creators and
sellers are seeded. (New columns are added to an old file automatically, but seed data is not.)

---

## The five-minute demo

1. **Landing** → *Creator*. Aditi's **Discover** feed shows the top pick large, with the picture, the
   fit score, two reasons and a content angle. Click any card to open the full breakdown: six
   signals, each with its score, weight and what it added.
2. **Skip** something with a reason (say *Too expensive*). The feed re-ranks, and the banner says
   what it learned.
3. Switch to **Brand** and pick *Dewdrop Labs*. Open **Vitamin C Serum**. The same six signals now
   rank *creators*: Aditi and Simran score 91, Ananya 76. Nine creators in other categories are
   listed as not offered this product, on purpose.
4. **Send offer** to Aditi. Go back to *Creator → Offers*: it is in her inbox with its fit score.
   Decline it with a reason.
5. Back on the brand's product page, **What creators did with it** now shows the reason. That is
   the feedback a brand never normally gets.
6. **List a product** shows a live image preview. List it and the matching runs straight away.
7. **Engine lab → Simulation** generates a creator whose true taste differs from what they declared,
   runs rounds, and shows how much the engine recovers.

---

## Product images

There is no photo library behind a demo catalogue, so `app/imagery.py` draws each product as a clean
studio-style render of the right kind of pack (dropper bottle, tube, jar, lipstick, compact,
palette, pencil, pump, oil bottle, spray, nail polish, patches) in a brand colour taken from the
product id. These are illustrations, not photographs.

A seller who has a real photo uploads it when listing (or sets `image_url` on the product); the API
then serves that instead. The frontend asks for one URL per product and does not care which kind it
gets.

---

## The product side (`engine/matching.py`)

The creator side asks *which products fit this creator*. The brand side asks the transpose, *which
creators fit this product*, using the **same signals, the same price gate and the same learned
adjustments**. A brand and a creator never see two different scores for the same pair (a test
asserts it).

Three things are specific to the brand's seat:

- **Niche gate.** An unsolicited offer should not go to a creator who does not cover the product's
  category. Off-niche creators are listed, but as not offered. (The creator side does not apply this
  gate, so creators can still browse across categories on their own terms.)
- **Why a pair is blocked.** Stage 1 runs per creator and the rule that blocked the pair is kept:
  *price is outside this audience's band*, *creator has already promoted it*, and so on.
- **A projection.** `reach = followers × engagement`, `clicks = reach × 0.10 × (fit / 80)`,
  `orders = clicks × conversion`, `NMV = orders × price`. It is arithmetic on public inputs, not a
  forecast, and the screen labels it that way.

**Offers close the loop.** An offer lands in the creator's inbox. Accepting is recorded as a
*promote*; declining needs a reason and is recorded as a *skip with that reason*. It goes through the
same function as a tap on a card, so what the brand learns about its product and what the ranker
learns about the creator come from one set of events.

**New listings start cold.** No reviews, no orders, early trend. They are scored on the seller rating
until real data arrives, and the product page says so.

---

## The engine

### Two-stage pipeline (`backend/app/engine/`)

**Stage 1 — eligibility** (`eligibility.py`). Hard, cheap, auditable: category,
price window, stock and serviceability, rating floor, policy compliance,
creator exclusions, and anything the creator has already promoted. Every
rejection is logged by rule. ~34% survives on the seed catalogue.

**Stage 2 — retrieval** (`retrieval.py`). Orders the eligible pool by
similarity. With `USE_PGVECTOR=1` this is a vector nearest-neighbour query;
without it a deterministic hashed stand-in keeps the pipeline shape identical.
Swap `pseudo_embedding()` for a sentence-transformer and nothing else changes.

> At 164 products the candidate cap never binds, so Stage 2 orders rather than
> narrows. The console says so rather than implying it filtered something.

**Ranking** (`scoring.py`). Seven signals, each a pure 0–100 function of
`(creator, product)`: audience, niche, intent, product, commerce, trend and brand fit.

### Weights come from the creator's cell in a 3×3 matrix

```
fit_score = ( Σ W_i(cell) × s_i  −  λ_S(scale) × saturation  −  return_penalty ) × learned_adjustment
W(cell)   = W_intent + Δ_scale        (each cell sums to 100)
```

The primary intent sets the base weights (Commerce-led puts 25 on commerce fit, Trend-led 25 on trend
fit, Brand-led 15 on brand fit) and the scale moves a few points: thin history leans on proven
products, rich history leans on the creator's own signals. Scale never earns a higher score. Products
far outside what the audience pays are removed in Stage 1; inside the window, price comfort is part of
product fit. Every term appears in the console; a test asserts the contributions reconstruct the score.

### The closed loop (`learning.py`)

| Reason | Effect |
| --- | --- |
| Too expensive | Down-weights products above the creator's price midpoint **only** |
| Not my niche | Down-weights that category |
| Already promoted | Removes that product from the slate |
| Audience won't care | Down-weights the category and weak-audience matches |
| Don't trust product | Down-weights lower-rated products |
| Not trending | Down-weights flat-trend products |
| Angle unclear | No ranking change — a content issue, not a fit issue |

Adjustments decay (45-day half-life) and **saturate** rather than hitting a
hard cap, so the response is graded: `84 → 76 → 70 → 66 → 60 → 56` over
repeated skips. The first skip matters, the tenth barely moves it, and a run of
angry taps can never zero a category.

Two rules are eligibility decisions rather than scoring ones, because
down-weighting leaves a product competing for a slot it can never deserve:

- **Already promoted** removes the product.
- **A promote retires the product by itself.** Waiting to be told "already
  promoted" wastes a slot in every future slate, and asking a creator to reject
  something they just posted about is the wrong way round.

---

## Simulation and evaluation

This is what makes the metrics real rather than placeholders.

A simulated creator carries a **latent preference profile** (`simulation.py`)
that the engine never sees and that deliberately drifts from what they declared
at signup — a secondary category they never mentioned, a real price ceiling
below the stated one. Each round:

1. the engine serves a Top-K slate,
2. the creator reacts according to the latent profile,
3. **the rejection reason is derived from whichever latent term was actually
   violated**, so the learning loop is fed real signal rather than noise,
4. the reaction is written back through the normal feedback path.

`evaluation.py` then scores the ranking against that latent utility — the only
real ground truth available. The ablation reruns the same creator with the
feedback loop disabled, which isolates what the loop itself is worth.

**Why round-over-round quality can fall while the loop is clearly helping:**
round 1 is measured against the full catalogue, and by round 8 the creator has
promoted the best matches, which retire. Falling precision is catalogue
consumption, not a worse model. The ablation controls for it.

`latent_utility()` is the single definition of what a product is worth to a
creator *now*, read by both the simulator and the evaluator — so the metric can
never punish the engine for correctly declining to re-serve something.

---

## API

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/creator/{id}` | Profile and intent scores |
| `POST` | `/creator/onboard` | Create from the onboarding answers |
| `GET` | `/recommendations/{id}?category=bpc&top_k=5` | Top-K, scores, reasons, funnel stats |
| `POST` | `/rank-products` | Score an explicit candidate set |
| `GET` | `/product/{id}` | Product details and signals |
| `POST` | `/feedback` | Promote / save / skip with a reason |
| `GET` | `/analytics/metrics` | CTR, acceptance, NMV, ranking quality |
| `POST` | `/simulation/generate` | Create creators with hidden latent profiles |
| `POST` | `/simulation/run` | Run N rounds, measuring after each |
| `GET` | `/simulation/history/{id}` | The learning curve |
| `GET` | `/simulation/ablation/{id}` | Loop on versus loop off |
| `GET` | `/simulation/discovered/{id}` | Stated vs learned vs true |
| `POST` | `/simulation/reset/{id}` | Clear learned state for a clean demo |
| `GET` | `/brands` | Sellers, with portfolio and offer stats |
| `GET` | `/brands/{brand}` | One seller's products and offer funnel |
| `POST` | `/products` | List a new product (cold start) |
| `GET` | `/product/{id}/matches` | Creators ranked for a product, diagnosis, creator feedback |
| `GET` | `/product/{id}/image.svg` | The product picture (drawn, unless a photo was set) |
| `POST` | `/pitches` | A brand sends an offer to a creator |
| `GET` | `/pitches?creator_id=&brand=` | Offers, for either side |
| `POST` | `/pitches/{id}/respond` | Accept, or decline with a reason |

`model_performance` reports `no_simulation_run_yet` until there is ground truth
to measure against, rather than inventing a number.

### Reproducing the deck's table

The seed data carries the deck's figures, so scoring those five products
returns the deck's scores:

```bash
curl -X POST localhost:8000/rank-products -H 'Content-Type: application/json' \
  -d '{"creator_id":"C12345","product_ids":["P001","P002","P003","P004","P005"]}'
```

```
P001 Vitamin C Serum    ₹499  91    Beginner skincare routine under ₹500
P002 Acne Patch Pack    ₹399  85
P003 Viral Lip Tint     ₹299  84
P004 Budget Kajal       ₹149  71
P005 Premium Hair Serum ₹899  66
```

Those five scores are for Aditi (C12345); they all appear in **Creator → Catalogue**.

`GET /recommendations` ranks the whole catalogue, so its Top 5 is *not* these
five — it finds better matches for Aditi. That is the engine working; the
deck's table is a fixed illustration of five named products.

---

## Swapping in a learned model

The MVP ranker sits behind one function. Replace the body of `_rank()` in
`engine/pipeline.py`; its inputs and output shape are the contract the routers
and the console depend on. The training rows are already accumulating:
`recommendation_log` holds every served slate with its signals,
`feedback_events` holds what the creator did about it.

## PostgreSQL + pgvector

```bash
docker compose up -d
export DATABASE_URL=postgresql+psycopg://cfe:cfe@localhost:5432/creator_fit_db
export USE_PGVECTOR=1
cd backend && python -m app.seed && uvicorn app.main:app --port 8000
```

Only `config.py` reads the environment; no application code changes.

---

## Layout

```
backend/app/
  config.py  database.py  models.py  schemas.py  seed.py
  engine/
    eligibility.py   stage 1 — hard filters
    retrieval.py     stage 2 — candidate retrieval
    scoring.py       seven signals, 3×3 weights, penalties
    onboarding.py    indirect questions → Creator DNA
    reasons.py       reason codes, caveats, confidence, content angle
    learning.py      the closed loop
    simulation.py    latent creators and synthetic outcomes
    evaluation.py    NDCG, precision, ablation
    matching.py      product side: creators ranked for one product
    pipeline.py      orchestration — the only module the routers call
  imagery.py         product pictures
  routers/           creators, products, recommendations, feedback,
                     analytics, simulation, brands
  tests/             41 behavioural tests
frontend/
  app/               /  creator/*  brand/*  lab/*
  components/        shell, creator and brand context, cards, drawer, chart primitives
  lib/api.ts         typed client
```

## Notes on the demo data

- Creator `C12345` and products `P001`–`P005` carry the deck's exact figures.
- `P006`–`P024` are hand-written alternatives.
- ~140 further products are **generated deterministically** (seed `20260102`)
  to supply the noise a real catalogue has — wrong price bracket, thin reviews,
  out of stock. Without them Stage 1 would look like it does nothing. They are
  capped below the hand-written products on rating, trend and saturation. Set
  `FILLER_PRODUCTS=0` to turn them off.
- Interactions use orders × price (₹1,497 for 3 × ₹499). The NMV column in the
  slide 06 table is 10× this.

## A note on colour

The look follows the DICE deck: white space, one hot pink, deep plum for type, and the pastel
gradient used sparingly. Pink marks the thing to act on or a live value. Fit scores use one hue
stepped light-to-dark rather than a multi-colour band scheme, because a categorical set there
failed colour-vision separation and encoded nothing the number beside it did not already say.
The two chart series were validated for colour-vision separation (worst adjacent ΔE 18.0 under
protanopia). Type is Poppins; the app loads it from Google Fonts.
