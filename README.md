# Creator × Product Fit Engine

A two-sided intelligent recommendation engine built for Meesho Beauty & Personal Care (BPC) that connects high-affinity creators with high-converting products.

Traditional influencer commerce relies on volume blast: brands send blanket pitches, creators drown in uncurated catalogues, and buyers face misaligned recommendations that drive up return rates. 

The **Creator × Product Fit Engine (CFE)** replaces volume spam with explainable, high-precision matching:
1. **Filters first**: Enforces hard commercial and quality gates before any scoring begins.
2. **Scores 7 signals**: Evaluates audience overlap, niche affinity, intent alignment, product trust, commerce velocity, trend momentum, and brand positioning.
3. **Explains every pick**: Breaks down the exact mathematical formula and gives creators actionable creative content angles.
4. **Rewards fit over volume**: Fit Rewards unlock exclusively on high-fit products (Fit Score ≥ 80) and pay on delivered orders net of returns.
5. **Learns in closed loops**: Every promote, save, and skip (with reason) immediately recalibrates creator weights with exponential time decay.

---

## Live Application

* **Web Application:** [https://meesho-cfe.vercel.app](https://meesho-cfe.vercel.app)
* **REST API & Swagger Docs:** [https://meesho-bpc.onrender.com/docs](https://meesho-bpc.onrender.com/docs)
* **API Health & Metadata:** [https://meesho-bpc.onrender.com/health](https://meesho-bpc.onrender.com/health)

---

## Key Modules & Experience

### 1. The Creator Experience (`/creator`)
* **Indirect Onboarding (`/creator/onboard`)**: Derives rich Creator DNA (niche shares, content formats, positioning, and intent) through 4 quick indirect scenario questions and platform analytics, rather than asking creators dry business metrics.
* **Creator DNA & Provenance (`/creator/profile`)**: Inspects every attribute alongside its transparent source (`Fetched`, `Asked`, or `Corrected`). Includes affirmative data consent.
* **Curated Top-K Feed (`/creator`)**: Delivers scale-adjusted recommendations (Starter-5 for Emerging, Top 8 for Growth, Top 4 for Established) with explicit score cards, primary drivers, and creative content angles.
* **Explainable Product Drawer**: Deep-dive side panel breaking down signal contributions (`Score × Weight = Points`), Stage 1 rule check verifications, and applicable Fit Rewards.
* **Interactive Feedback & Live Re-ranking**: Promote, save, or skip (with mandatory structured reason). Rejections immediately re-rank remaining candidates with a visible diff banner showing exact score and rank movements.
* **Fit Rewards Dashboard**: Displays creator archetype (*Commerce Builder*, *Trend Scout*, *Brand Builder*) with live order tracking celebrating delivered orders while netting off returns.

### 2. The Brand Experience (`/brand`)
* **Brand Catalog & Listings (`/brand`)**: Comprehensive overview of brand products, 30-day orders, conversion rates, and active pitches.
* **Product-to-Creator Matching (`/brand/product/[id]`)**: Ranks reachable creators for any specific product, projecting potential Reach, Orders, and NMV.
* **Targeted Offers with Incentives (`/brand/offers`)**: Brands can pitch qualified creators (Fit Score ≥ 80) attaching brand-funded incentives (`Brand-funded sample`, `Conversion bonus`, `Early access`).
* **Creator Feedback Telemetry**: Surfaces real-time reasons why creators declined or skipped products (e.g. *Too expensive*, *Not my niche*), giving sellers actionable feedback to improve their listings.

### 3. The Engine Lab (`/lab`)
* **Pipeline Funnel (`/lab/pipeline`)**: Full visibility into the 4-stage engine funnel (Full Catalogue → Commercial Eligibility → Candidate Retrieval → Served Recommendations) with rule-by-rule drop-off counts.
* **Team-Draft Interleaving Sandbox (`/lab/pilot`)**: Compares personalized vs. generic baseline feeds in an interleaved slate with source-masking to measure true match-quality win rate.
* **Trust & Quality Telemetry (`/lab/metrics`)**: Live monitoring of ranking quality (NDCG@5, Precision@5), explanation coverage, wrong-pick rate, and P95 latency.
* **Mechanism Validation Simulator (`/lab/simulate`)**: Simulates engine learning over multiple rounds against synthetic creators with hidden latent preferences.

---

## The 7 Fit Signals & Scoring Formula

Candidate products are evaluated across seven core signals:

```
FitScore(c, p) = ( Σ [W_i(cell) · s_i(c, p)]  −  λ(scale) · saturation(p)  −  ReturnPenalty(p) ) × L(c, p)
```

Where:
* **`W(cell) = Base_Intent + Delta_Scale`**: Marking scheme dynamically tailored across a 3×3 matrix (Scale Tier × Primary Intent). All cell weights sum to 100%.
* **`λ(scale) · saturation`**: Dynamic crowding penalty protecting established creators from oversaturated viral items.
* **`ReturnPenalty`**: Deducts up to 10 points when product return rates exceed category medians.
* **`L(c, p)`**: Bounded adaptive multiplier (0.62–1.15) reflecting creator feedback, with a 45-day exponential half-life.

| Signal | Core Focus | What It Measures |
|---|---|---|
| **Audience** | Demographic fit | Age distribution recall/precision and city-tier overlap between creator audience and product target |
| **Niche** | Topical authority | Creator content vocabulary, category share, and tag intersections |
| **Intent** | Creator goals | Alignment with creator's primary drive (Trend / Reach, Commerce / Revenue, or Brand Identity) |
| **Product** | Quality & price comfort | Review ratings, seller track record, and comfort within the audience's price band |
| **Commerce** | Commercial viability | Order velocity, 30-day NMV performance, and marketplace conversion rate |
| **Trend** | Timeliness | Viral momentum and product lifecycle stage (Early, Rising, Peak, Saturated, Declining) |
| **Brand** | Positioning fit | Overlap across brand positioning vectors (budget, mid, premium, trendy, routine) |

---

## Quick Start (Run Locally)

### Prerequisites
* Python 3.10+
* Node.js 18+

### 1. Backend Setup
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --port 8000 --reload
```
The backend initializes SQLite (`creator_fit.db`) and automatically seeds demo creators and products on first boot. API docs will be live at `http://localhost:8000/docs`.

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser.

### 3. Run Backend Test Suite
```bash
cd backend
pytest -q
```
Runs the complete test suite verifying eligibility gates, scoring math, feedback adjustments, and reward accounting.

---

## Technical Stack

* **Frontend**: Next.js 14 (App Router), React 18, TypeScript, Tailwind CSS
* **Backend**: FastAPI, SQLAlchemy 2.0, Pydantic v2
* **Storage**: SQLite for instant zero-dependency execution (production schema ready for PostgreSQL + `pgvector`)
* **Procedural Pack Art Engine**: Deterministic SVG pack illustration engine rendering instant product imagery for BPC packaging without external CDN dependencies.
