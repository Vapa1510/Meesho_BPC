# Demo script and deployment checklist

## Before judging (5 minutes)

1. Open https://meesho-bpc.onrender.com/health. The free host sleeps after about 15 minutes idle;
   the first request wakes it (up to a minute). Do this again shortly before your slot.
2. Open https://meesho-cfe.vercel.app/creator on a phone and on a laptop. You should land on
   **Riya's Top 8** with the four-stop walkthrough at the top.
3. Press **Reset demo** so the numbers match the slides (Sunscreen 85, Vitamin C 83, Ceramide 76).
4. Scan each QR code in the exported PDF with two different phones.

Optional: point a free uptime monitor at `/health` every 10 minutes during the judging window so
the backend never sleeps.

## The 60–90 second path (follows slides 7 and 8)

| Time | Where | Do | Say |
| --- | --- | --- | --- |
| 0:00 | `/creator/onboard` (QR 1) | Start → tap Skincare routine, Product review, Makeup tutorial → Definitely → keep the ranking → pick Lip Tint ₹299, Sunscreen ₹349, Vitamin C ₹499 | "It never asks her goal. Four indirect questions, because Meesho already knows her tier, audience and content." |
| 0:25 | DNA screen | Point at Trend 0.10 / Commerce 0.68 / Brand 0.22 and the Fetched / Asked tags; tick consent; See my Top 8 | "Every value says where it came from, and nothing is saved without consent." |
| 0:40 | `/creator` (QR 2) | Top pick card: 85, three reasons, content angle, Fit Rewards line; open it | "164 listings, 25 pass the checks, Top 8 for a Growth creator. Here is why this one: Audience +24.0, Commerce +22.6, Product +14.3, and every check it passed." |
| 1:00 | Ceramide Moisturiser card | Skip (with reason) → Too expensive | "The list re-ranks at once: Ceramide 76 → 73." |
| 1:10 | Walkthrough stop 4 → `/brand/product/P009` | Show Riya at 73 and "Too expensive" under What creators did with it | "The brand sees the same score and, for the first time, why a creator passed." |
| 1:25 | Reset demo | | "Back to the deck's numbers." |

If asked "what does slide 8's Fit Engine QR open?": onboarding, with the Fit Engine one tap away in
the walkthrough. If asked about the A4 screens: they show seed creator Aditi Sharma's numbers (see
README, Notes for reviewers).

## Deploying without breaking the QR codes

The printed QR codes contain these exact addresses:
`https://meesho-cfe.vercel.app/creator` and `https://meesho-cfe.vercel.app/creator/onboard`.

1. **Same Vercel project.** Deploy `frontend/` to the project that owns `meesho-cfe.vercel.app`.
   `frontend/.vercel/project.json` is kept in this zip so `vercel --prod` from `frontend/` goes to
   that project. If Vercel deploys from GitHub, just push. Never create a new project or rename
   the domain.
2. **Same Render service.** `frontend/.env.production` points at `https://meesho-bpc.onrender.com`.
   Push the backend to the repo that service deploys from (or use the Render dashboard's manual
   deploy). It reseeds a fresh SQLite database on start, so Riya and the deck's numbers appear.
3. **Keep the two pages.** Do not move `frontend/app/creator/page.tsx` or
   `frontend/app/creator/onboard/page.tsx`.
4. **Check after deploying:** `/health` returns `"demo_creator_id": "C013"`; `/creator` shows
   Riya's Top 8; `/creator/onboard` shows the walkthrough; the PDF's QR codes open both.

Git: this zip includes the repository (`.git`) with the changes uncommitted, so you can review
them with `git status` / `git diff`, then commit and push to `Vapa1510/Meesho_BPC`.
