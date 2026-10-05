# Application Walkthrough & Demo Guide

This guide walks through the core user journeys of the **Creator × Product Fit Engine (CFE)** across its three interfaces: Creator Workspace, Brand Matching, and the Engine Lab.

---

## The 3 Core Journeys

### Journey 1: The Creator Experience (Discover & Adaptive Learning)

#### 1. Indirect Onboarding (`/creator/onboard`)
* Navigate to `/creator/onboard` and connect a demo handle (e.g. `@riya.glows`).
* Notice that the engine **never asks the creator for their business metrics or target revenue**.
* Walk through the 4 indirect scenario taps:
  1. *Content Formats*: Tap topics the creator actively produces (Skincare routine, Product reviews, Tutorials).
  2. *Scenario Choice*: Choose what the creator prioritizes when a product is hot.
  3. *Priority Ranking*: Order what matters most to their audience.
  4. *Quick Product Picks*: Pick 3 everyday favorites to establish comfortable price points and brand aesthetics.
* **Consent & DNA Review**: View the synthesized Creator DNA showing Intent distribution (Trend, Commerce, Brand) and explicit provenance tags (`Fetched`, `Asked`, `Default`). Check consent and proceed to the feed.

#### 2. The Personalized Feed (`/creator`)
* Land on the creator's Discover feed (e.g. *Riya's Top 8* for a Growth Creator).
* **Hero Recommendation Card**: Inspect the #1 pick (e.g., *Daily Sunscreen SPF 50*):
  * **Fit Score badge** with color tone based on score strength.
  * **Top Drivers**: Explicit point contributions (e.g., `Audience +24.0 · Commerce +22.6 · Product +14.3`).
  * **Suggested Content Angle**: A creator-ready hook for social videos.
  * **Fit Rewards Callout**: Highlight that this pick qualifies for Fit Rewards (Fit Score ≥ 80).
* **Product Detail Drawer**: Click any card to open the slide-over drawer:
  * Check the **Stage 1 Verification Checklist** (Stock, Price window, Rating, Returns, Policy, Audience fit).
  * Review the mathematical score formula and signal breakdown bars.

#### 3. Closed-Loop Feedback & Instant Re-ranking
* On a recommendation (e.g., *Ceramide Moisturiser*), click **"Skip (with reason)"**.
* Select a structured reason chip: **"Too expensive"**.
* **Watch the Live Re-ranking Banner**:
  * The feed recalculates immediately without full page reload.
  * A banner appears showing the exact diff: the skipped item drops, related items adjust, and the explanation shows how the learning multiplier bounded the score adjustment.

#### 4. Fit Rewards & Real-Time Order Accounting (`/creator/profile`)
* Open `/creator/profile` and scroll down to the **Fit Rewards** panel.
* View the creator archetype (*Commerce Builder*) and the rules: rewards unlock on delivered orders with Fit Score ≥ 80.
* Click **`+ Delivered order`** on a promoted product: watch delivered orders increment and NMV increase.
* Click **`Return`**: observe how return orders automatically net off against NMV, demonstrating return-conscious accounting.

---

### Journey 2: The Brand Experience (Matching & Feedback Telemetry)

#### 1. Product-to-Creator Matching (`/brand/product/P009`)
* Switch to the **Brand Portal** and select any product.
* View reachable creator matches ranked by fit score.
* Inspect projected reach metrics: **Estimated Reach**, **Projected Orders**, and **Forecasted NMV**.
* Expand unreachable creators to see why they were blocked (e.g. *Outside creator niche*, *Price band mismatch*).

#### 2. Targeted Offers with Incentives
* Click **"Send offer"** on a matching creator.
* For fit-qualified creators (Fit Score ≥ 80), select an incentive chip:
  * `Brand-funded sample`
  * `Conversion bonus`
  * `Early access` (for early/rising trend stage products)
* Send the offer and check the Creator Offers inbox (`/creator/offers`) to see the incentive badge attached.

#### 3. Seller Feedback Intelligence
* Under **"What creators did with it"**, review real-time feedback summary:
  * Total views, promotes, saves, and skips.
  * Exact reasons given by creators when declining or skipping (e.g. *Too expensive*), providing sellers with market intelligence on their pricing and positioning.

---

### Journey 3: The Engine Lab (Inspection & Experimentation)

#### 1. Pipeline Drop-Off Funnel (`/lab/pipeline`)
* Open `/lab/pipeline` to inspect the 4 stages of the engine.
* View the Stage 1 drop-off breakdown across all 8 hard filters (Category, Price range, Stock, Quality floor, Return rate median, Policy compliance, Excluded categories, Audience fit floor).

#### 2. Team-Draft Interleaved Sandbox (`/lab/pilot`)
* Open `/lab/pilot` to explore pilot evaluation.
* View an interleaved feed blending personalized picks with generic discovery recommendations in a team-draft alternation.
* Toggle **"Reveal the source"** to unmask which items were personalized vs. generic.
* Review the live match-quality win rate tracking creator preference across both arms.

#### 3. Trust & Quality Telemetry (`/lab/metrics`)
* Review live ranking quality metrics:
  * **NDCG@5** and **Precision@5**
  * **Explanation Coverage** (percentage of served picks with human-readable rationale)
  * **Wrong-Pick Rate** (percentage of recommendations skipped for fit reasons)
  * **P95 Latency** monitoring response time under load.

---

## One-Click Demo Reset

At any point during testing or demonstrations, click **"Reset demo"** in the top navigation banner (or call `POST /demo/reset`) to immediately restore all creators, catalogue listings, feedback events, and order counters to their clean baseline state.
