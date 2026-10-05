"""Demo data.

The catalogue is deliberately wider than the demo needs so Stage 1 has
something to reject: out-of-stock items, unserviceable pincodes, products below
the quality bar, a non-compliant listing, and prices far outside the band.

Creator C12345 (Aditi Sharma) and the five hero products carry the exact
figures used in the deck, so the running app and the slides agree.
"""
from __future__ import annotations

import os as _os
import random as _random

from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import SessionLocal, init_db
from .engine.retrieval import product_vector
from .models import Creator, Interaction, Product

CREATORS = [
    dict(
        creator_id="C12345",
        name="Aditi Sharma",
        tier_label="Growth Creator",
        followers=28_000,
        niche="Skincare",
        sub_niches=["serum", "routine", "brightening", "acne", "affordable"],
        bio="skincare and affordable routines",
        audience_age_min=18,
        audience_age_max=24,
        audience_tiers=["T1", "T2"],
        price_min=200,
        price_max=700,
        goal="revenue",
        intent_trend=78,
        intent_commerce=86,
        intent_brand=54,
        engagement_rate=0.061,
    ),
    dict(
        creator_id="C002",
        name="Ritika Verma",
        tier_label="Growth Creator",
        followers=48_000,
        niche="Makeup",
        sub_niches=["lips", "eyes", "tint", "everyday"],
        bio="everyday makeup on a budget",
        audience_age_min=18,
        audience_age_max=28,
        audience_tiers=["T1", "T2", "T3"],
        price_min=150,
        price_max=600,
        goal="reach",
        intent_trend=88,
        intent_commerce=64,
        intent_brand=48,
        engagement_rate=0.052,
    ),
    dict(
        creator_id="C003",
        name="Neha Pillai",
        tier_label="Established Creator",
        followers=220_000,
        niche="Haircare",
        sub_niches=["serum", "frizz", "oil", "premium"],
        bio="haircare science and premium routines",
        audience_age_min=18,
        audience_age_max=34,
        audience_tiers=["T1", "T2"],
        price_min=400,
        price_max=1500,
        goal="brand",
        intent_trend=62,
        intent_commerce=58,
        intent_brand=84,
        engagement_rate=0.038,
    ),
    dict(
        creator_id="C004", name="Simran Kaur", tier_label="Growth Creator", followers=36000,
        niche="Skincare", sub_niches=['sunscreen', 'moisturiser', 'acne', 'routine'], bio="dermat-approved routines for oily skin",
        audience_age_min=18, audience_age_max=26, audience_tiers=['T1', 'T2'],
        price_min=250, price_max=900, goal="revenue",
        intent_trend=64, intent_commerce=84, intent_brand=52, engagement_rate=0.057,
    ),
    dict(
        creator_id="C005", name="Ananya Rao", tier_label="Established Creator", followers=310000,
        niche="Skincare", sub_niches=['serum', 'premium', 'brightening', 'anti-ageing'], bio="clinical skincare, premium picks",
        audience_age_min=22, audience_age_max=36, audience_tiers=['T1'],
        price_min=700, price_max=2500, goal="brand",
        intent_trend=58, intent_commerce=60, intent_brand=86, engagement_rate=0.034,
    ),
    dict(
        creator_id="C006", name="Pooja Nair", tier_label="Emerging Creator", followers=6200,
        niche="Makeup", sub_niches=['lips', 'kajal', 'affordable', 'everyday'], bio="college-budget makeup under 300",
        audience_age_min=17, audience_age_max=23, audience_tiers=['T2', 'T3'],
        price_min=60, price_max=300, goal="reach",
        intent_trend=86, intent_commerce=66, intent_brand=40, engagement_rate=0.071,
    ),
    dict(
        creator_id="C007", name="Meera Joshi", tier_label="Growth Creator", followers=54000,
        niche="Makeup", sub_niches=['base', 'party', 'glow', 'eyes'], bio="party and festive glam",
        audience_age_min=20, audience_age_max=30, audience_tiers=['T1', 'T2'],
        price_min=300, price_max=1200, goal="reach",
        intent_trend=84, intent_commerce=62, intent_brand=58, engagement_rate=0.049,
    ),
    dict(
        creator_id="C008", name="Kavya Reddy", tier_label="Growth Creator", followers=41000,
        niche="Haircare", sub_niches=['oil', 'shampoo', 'routine', 'affordable'], bio="desi hair growth routines",
        audience_age_min=19, audience_age_max=32, audience_tiers=['T2', 'T3'],
        price_min=120, price_max=600, goal="revenue",
        intent_trend=66, intent_commerce=82, intent_brand=48, engagement_rate=0.058,
    ),
    dict(
        creator_id="C009", name="Isha Malhotra", tier_label="Emerging Creator", followers=9800,
        niche="Haircare", sub_niches=['frizz', 'serum', 'styling'], bio="curly and frizzy hair care",
        audience_age_min=18, audience_age_max=27, audience_tiers=['T1', 'T2'],
        price_min=200, price_max=800, goal="revenue",
        intent_trend=72, intent_commerce=78, intent_brand=50, engagement_rate=0.066,
    ),
    dict(
        creator_id="C010", name="Tanvi Desai", tier_label="Growth Creator", followers=67000,
        niche="Personal Care", sub_niches=['body', 'fragrance', 'grooming', 'winter'], bio="everyday self-care and body care",
        audience_age_min=20, audience_age_max=34, audience_tiers=['T1', 'T2', 'T3'],
        price_min=100, price_max=700, goal="revenue",
        intent_trend=62, intent_commerce=80, intent_brand=54, engagement_rate=0.046,
    ),
    dict(
        creator_id="C011", name="Aarav Mehta", tier_label="Growth Creator", followers=33000,
        niche="Personal Care", sub_niches=['grooming', 'fragrance', 'deodorant'], bio="men's grooming basics",
        audience_age_min=18, audience_age_max=30, audience_tiers=['T1', 'T2'],
        price_min=150, price_max=900, goal="reach",
        intent_trend=80, intent_commerce=66, intent_brand=52, engagement_rate=0.05,
    ),
    dict(
        creator_id="C012", name="Zoya Khan", tier_label="Established Creator", followers=180000,
        niche="Makeup", sub_niches=['lips', 'base', 'premium', 'trending'], bio="trend-led makeup reviews",
        audience_age_min=18, audience_age_max=30, audience_tiers=['T1', 'T2'],
        price_min=400, price_max=1800, goal="reach",
        intent_trend=90, intent_commerce=58, intent_brand=60, engagement_rate=0.041,
    ),
]

# ----------------------------------------------------------------- the five
# hero products from the deck, then the rest of the catalogue
PRODUCTS = [
    dict(
        product_id="P001",
        title="Vitamin C Serum",
        category="Skincare",
        sub_category="serum",
        price=499,
        description="Brightening vitamin C serum for even skin tone, 30 ml.",
        tags=["brightening", "serum", "routine", "daily-use", "beginner-friendly", "affordable"],
        art_key="serum",
        rating=4.4,
        review_count=2_300,
        seller_rating=4.6,
        return_rate=0.05,
        orders_30d=18_400,
        conversion_rate=0.048,
        nmv_30d=9_181_600,
        trend_score=0.70,
        trend_stage="rising",
        creator_saturation=0.22,
        target_age_min=18,
        target_age_max=26,
        target_tiers=["T1", "T2"],
    ),
    dict(
        product_id="P002",
        title="Acne Patch Pack",
        category="Skincare",
        sub_category="acne",
        price=399,
        description="Hydrocolloid acne patches, 36 count, overnight wear.",
        tags=["acne", "overnight", "beginner-friendly", "affordable", "routine"],
        art_key="patch",
        rating=4.3,
        review_count=620,
        seller_rating=4.4,
        return_rate=0.06,
        orders_30d=11_200,
        conversion_rate=0.036,
        nmv_30d=4_468_800,
        trend_score=0.60,
        trend_stage="rising",
        creator_saturation=0.28,
        target_age_min=18,
        target_age_max=25,
        target_tiers=["T1", "T2"],
    ),
    dict(
        product_id="P003",
        title="Viral Lip Tint",
        category="Makeup",
        sub_category="lips",
        price=299,
        description="Long-wear lip and cheek tint, 8 shades.",
        tags=["lips", "tint", "affordable", "trending", "everyday"],
        art_key="tint",
        rating=4.2,
        review_count=3_900,
        seller_rating=4.3,
        return_rate=0.07,
        orders_30d=26_500,
        conversion_rate=0.049,
        nmv_30d=7_923_500,
        trend_score=0.78,
        trend_stage="peak",
        creator_saturation=0.46,
        target_age_min=18,
        target_age_max=24,
        target_tiers=["T1", "T2", "T3"],
    ),
    dict(
        product_id="P004",
        title="Budget Kajal",
        category="Makeup",
        sub_category="kajal",
        price=149,
        description="Smudge-proof kajal, 12-hour wear.",
        tags=["kajal", "eyes", "everyday", "affordable"],
        art_key="kajal",
        rating=4.1,
        review_count=8_600,
        seller_rating=4.2,
        return_rate=0.07,
        orders_30d=41_000,
        conversion_rate=0.043,
        nmv_30d=6_109_000,
        trend_score=0.58,
        trend_stage="peak",
        creator_saturation=0.52,
        target_age_min=18,
        target_age_max=30,
        target_tiers=["T1", "T2", "T3"],
    ),
    dict(
        product_id="P005",
        title="Premium Hair Serum",
        category="Haircare",
        sub_category="serum",
        price=899,
        description="Anti-frizz hair serum with argan oil, 100 ml.",
        tags=["serum", "frizz", "premium", "routine"],
        art_key="hair",
        rating=4.5,
        review_count=1_100,
        seller_rating=4.7,
        return_rate=0.04,
        orders_30d=6_300,
        conversion_rate=0.046,
        nmv_30d=5_663_700,
        trend_score=0.68,
        trend_stage="rising",
        creator_saturation=0.31,
        target_age_min=20,
        target_age_max=34,
        target_tiers=["T1", "T2"],
    ),
    # ------------------------------------------------ rest of the catalogue
    dict(
        product_id="P006", title="Niacinamide Serum", category="Skincare",
        sub_category="serum", price=449,
        description="10% niacinamide serum for oil control and pores.",
        tags=["serum", "acne", "oil-control", "routine", "affordable"], art_key="serum",
        rating=4.3, review_count=1_900, seller_rating=4.5, return_rate=0.06,
        orders_30d=9_800, conversion_rate=0.043, nmv_30d=4_398_200,
        trend_score=0.66, trend_stage="rising", creator_saturation=0.34,
        target_age_min=18, target_age_max=28, target_tiers=["T1", "T2"],
    ),
    dict(
        product_id="P007", title="Daily Sunscreen SPF 50", category="Skincare",
        sub_category="sunscreen", price=349,
        description="Lightweight no-white-cast sunscreen, SPF 50 PA++++.",
        tags=["sunscreen", "daily-use", "routine", "beginner-friendly"], art_key="serum",
        rating=4.4, review_count=5_200, seller_rating=4.5, return_rate=0.04,
        orders_30d=22_000, conversion_rate=0.046, nmv_30d=7_678_000,
        trend_score=0.63, trend_stage="peak", creator_saturation=0.58,
        target_age_min=18, target_age_max=34, target_tiers=["T1", "T2", "T3"],
    ),
    dict(
        product_id="P008", title="Gentle Foaming Cleanser", category="Skincare",
        sub_category="cleanser", price=279,
        description="pH-balanced foaming face wash for daily use.",
        tags=["cleanser", "daily-use", "routine", "affordable"], art_key="serum",
        rating=4.2, review_count=3_100, seller_rating=4.3, return_rate=0.06,
        orders_30d=15_400, conversion_rate=0.039, nmv_30d=4_296_600,
        trend_score=0.44, trend_stage="saturating", creator_saturation=0.55,
        target_age_min=18, target_age_max=34, target_tiers=["T1", "T2", "T3"],
    ),
    dict(
        product_id="P009", title="Ceramide Moisturiser", category="Skincare",
        sub_category="moisturiser", price=599,
        description="Barrier-repair moisturiser with ceramides, 50 g.",
        tags=["moisturiser", "barrier", "routine", "winter"], art_key="patch",
        rating=4.5, review_count=980, seller_rating=4.6, return_rate=0.05,
        orders_30d=5_600, conversion_rate=0.040, nmv_30d=3_354_400,
        trend_score=0.59, trend_stage="rising", creator_saturation=0.24,
        target_age_min=20, target_age_max=34, target_tiers=["T1", "T2"],
    ),
    dict(
        product_id="P010", title="Under-Eye Gel", category="Skincare",
        sub_category="eyes", price=329,
        description="Caffeine under-eye gel for puffiness, 15 ml.",
        tags=["eyes", "routine", "affordable", "beginner-friendly"], art_key="serum",
        rating=4.0, review_count=740, seller_rating=4.1, return_rate=0.10,
        orders_30d=3_900, conversion_rate=0.031, nmv_30d=1_283_100,
        trend_score=0.48, trend_stage="rising", creator_saturation=0.19,
        target_age_min=18, target_age_max=30, target_tiers=["T1", "T2", "T3"],
    ),
    dict(
        product_id="P011", title="Matte Liquid Lipstick", category="Makeup",
        sub_category="lips", price=349,
        description="Transfer-proof matte liquid lipstick, 10 shades.",
        tags=["lips", "matte", "everyday", "affordable"], art_key="tint",
        rating=4.1, review_count=6_200, seller_rating=4.2, return_rate=0.08,
        orders_30d=28_000, conversion_rate=0.041, nmv_30d=9_772_000,
        trend_score=0.52, trend_stage="peak", creator_saturation=0.64,
        target_age_min=18, target_age_max=30, target_tiers=["T1", "T2", "T3"],
    ),
    dict(
        product_id="P012", title="Blurring Compact", category="Makeup",
        sub_category="base", price=429,
        description="Oil-control compact powder with SPF 15.",
        tags=["base", "compact", "everyday"], art_key="patch",
        rating=4.0, review_count=2_400, seller_rating=4.1, return_rate=0.09,
        orders_30d=12_800, conversion_rate=0.034, nmv_30d=5_491_200,
        trend_score=0.38, trend_stage="saturating", creator_saturation=0.60,
        target_age_min=20, target_age_max=38, target_tiers=["T1", "T2", "T3"],
    ),
    dict(
        product_id="P013", title="Cream Blush Stick", category="Makeup",
        sub_category="base", price=379,
        description="Blendable cream blush stick, dewy finish.",
        tags=["base", "blush", "trending", "everyday"], art_key="kajal",
        rating=4.3, review_count=1_600, seller_rating=4.4, return_rate=0.06,
        orders_30d=9_100, conversion_rate=0.047, nmv_30d=3_448_900,
        trend_score=0.79, trend_stage="rising", creator_saturation=0.26,
        target_age_min=18, target_age_max=28, target_tiers=["T1", "T2"],
    ),
    dict(
        product_id="P014", title="Anti-Dandruff Shampoo", category="Haircare",
        sub_category="shampoo", price=399,
        description="Zinc pyrithione shampoo for flaky scalp, 340 ml.",
        tags=["shampoo", "scalp", "routine"], art_key="hair",
        rating=4.2, review_count=4_100, seller_rating=4.3, return_rate=0.07,
        orders_30d=14_200, conversion_rate=0.040, nmv_30d=5_665_800,
        trend_score=0.47, trend_stage="peak", creator_saturation=0.49,
        target_age_min=20, target_age_max=45, target_tiers=["T1", "T2", "T3"],
    ),
    dict(
        product_id="P015", title="Rosemary Hair Oil", category="Haircare",
        sub_category="oil", price=329,
        description="Cold-pressed rosemary and castor hair oil, 200 ml.",
        tags=["oil", "growth", "routine", "affordable", "trending"], art_key="hair",
        rating=4.3, review_count=2_900, seller_rating=4.4, return_rate=0.06,
        orders_30d=17_600, conversion_rate=0.049, nmv_30d=5_790_400,
        trend_score=0.81, trend_stage="rising", creator_saturation=0.33,
        target_age_min=18, target_age_max=34, target_tiers=["T1", "T2", "T3"],
    ),
    dict(
        product_id="P016", title="Heat Protectant Spray", category="Haircare",
        sub_category="styling", price=549,
        description="Thermal protection spray up to 220C, 150 ml.",
        tags=["styling", "frizz", "premium"], art_key="hair",
        rating=4.1, review_count=620, seller_rating=4.2, return_rate=0.08,
        orders_30d=2_800, conversion_rate=0.029, nmv_30d=1_537_200,
        trend_score=0.43, trend_stage="rising", creator_saturation=0.21,
        target_age_min=20, target_age_max=36, target_tiers=["T1", "T2"],
    ),
    dict(
        product_id="P017", title="Body Lotion with Urea", category="Personal Care",
        sub_category="body", price=299,
        description="Intensive body lotion for dry skin, 400 ml.",
        tags=["body", "winter", "routine", "affordable"], art_key="patch",
        rating=4.2, review_count=3_400, seller_rating=4.3, return_rate=0.05,
        orders_30d=13_900, conversion_rate=0.042, nmv_30d=4_156_100,
        trend_score=0.51, trend_stage="rising", creator_saturation=0.37,
        target_age_min=20, target_age_max=45, target_tiers=["T1", "T2", "T3"],
    ),
    dict(
        product_id="P018", title="Roll-On Deodorant", category="Personal Care",
        sub_category="fragrance", price=199,
        description="48-hour roll-on deodorant, alcohol free.",
        tags=["body", "daily-use", "affordable"], art_key="kajal",
        rating=4.0, review_count=5_800, seller_rating=4.1, return_rate=0.07,
        orders_30d=31_000, conversion_rate=0.035, nmv_30d=6_169_000,
        trend_score=0.33, trend_stage="saturating", creator_saturation=0.58,
        target_age_min=18, target_age_max=45, target_tiers=["T1", "T2", "T3"],
    ),
    # ----- products Stage 1 should reject, so the filters are visible -----
    dict(
        product_id="P019", title="Luxury Retinol Ampoule", category="Skincare",
        sub_category="serum", price=2_499,
        description="High-strength retinol ampoule set, 7 x 2 ml.",
        tags=["serum", "retinol", "premium"], art_key="serum",
        rating=4.6, review_count=410, seller_rating=4.7, return_rate=0.04,
        orders_30d=900, conversion_rate=0.027, nmv_30d=2_249_100,
        trend_score=0.55, trend_stage="rising", creator_saturation=0.14,
        target_age_min=28, target_age_max=45, target_tiers=["T1"],
    ),
    dict(
        product_id="P020", title="Clay Face Mask", category="Skincare",
        sub_category="mask", price=259,
        description="Kaolin clay mask for oily skin, 100 g.",
        tags=["mask", "oil-control", "affordable"], art_key="patch",
        rating=3.2, review_count=880, seller_rating=3.4, return_rate=0.18,
        orders_30d=2_100, conversion_rate=0.021, nmv_30d=543_900,
        trend_score=0.29, trend_stage="declining", creator_saturation=0.41,
        target_age_min=18, target_age_max=34, target_tiers=["T1", "T2", "T3"],
    ),
    dict(
        product_id="P021", title="Glow Highlighter Palette", category="Makeup",
        sub_category="base", price=459,
        description="Four-shade baked highlighter palette.",
        tags=["base", "glow", "party"], art_key="tint",
        rating=4.1, review_count=1_200, seller_rating=4.2, return_rate=0.08,
        orders_30d=5_400, conversion_rate=0.033, nmv_30d=2_478_600,
        trend_score=0.46, trend_stage="peak", creator_saturation=0.52,
        target_age_min=18, target_age_max=30, target_tiers=["T1", "T2"],
        in_stock=False,
    ),
    dict(
        product_id="P022", title="Keratin Smoothing Mask", category="Haircare",
        sub_category="mask", price=649,
        description="Salon-style keratin hair mask, 200 g.",
        tags=["mask", "frizz", "premium", "routine"], art_key="hair",
        rating=4.4, review_count=760, seller_rating=4.5, return_rate=0.06,
        orders_30d=3_200, conversion_rate=0.036, nmv_30d=2_076_800,
        trend_score=0.54, trend_stage="rising", creator_saturation=0.27,
        target_age_min=22, target_age_max=40, target_tiers=["T1", "T2"],
        serviceable=False,
    ),
    dict(
        product_id="P023", title="Skin Lightening Cream", category="Skincare",
        sub_category="cream", price=329,
        description="Listing withheld pending claim review.",
        tags=["cream", "brightening"], art_key="patch",
        rating=3.9, review_count=2_100, seller_rating=3.8, return_rate=0.14,
        orders_30d=7_400, conversion_rate=0.030, nmv_30d=2_434_600,
        trend_score=0.36, trend_stage="declining", creator_saturation=0.44,
        target_age_min=20, target_age_max=40, target_tiers=["T2", "T3"],
        policy_compliant=False,
    ),
    dict(
        product_id="P024", title="Mini Lip Balm Duo", category="Personal Care",
        sub_category="lips", price=99,
        description="Two tinted lip balms, SPF 15.",
        tags=["lips", "affordable", "everyday"], art_key="kajal",
        rating=4.0, review_count=4_300, seller_rating=4.1, return_rate=0.08,
        orders_30d=24_000, conversion_rate=0.036, nmv_30d=2_376_000,
        trend_score=0.40, trend_stage="saturating", creator_saturation=0.50,
        target_age_min=18, target_age_max=34, target_tiers=["T1", "T2", "T3"],
    ),
]

# Hand-written products get named sellers so the brand side has portfolios to
# show. Fictional names throughout.
BRAND_BY_ID = {
    "P001": "Dewdrop Labs", "P006": "Dewdrop Labs", "P007": "Dewdrop Labs",
    "P008": "Dewdrop Labs", "P019": "Dewdrop Labs",
    "P002": "ClearSkin Co.", "P010": "ClearSkin Co.", "P020": "ClearSkin Co.",
    "P009": "ClearSkin Co.", "P023": "ClearSkin Co.",
    "P003": "Rosette", "P011": "Rosette", "P013": "Rosette",
    "P021": "Rosette", "P012": "Rosette",
    "P004": "Kohl & Co", "P024": "Kohl & Co",
    "P005": "Tresse", "P014": "Tresse", "P015": "Tresse",
    "P016": "Tresse", "P022": "Tresse",
    "P017": "Everyday Essentials", "P018": "Everyday Essentials",
}

# Prior history, matching the Interactions table on slide 06.
INTERACTIONS = [
    dict(creator_id="C12345", product_id="P001", impressions=1_200, clicks=96,
         saves=24, promotes=12, orders=3, nmv=1_497),
    dict(creator_id="C12345", product_id="P002", impressions=980, clicks=52,
         saves=10, promotes=4, orders=1, nmv=399),
    dict(creator_id="C002", product_id="P003", impressions=2_100, clicks=180,
         saves=40, promotes=18, orders=6, nmv=1_794),
]



# --------------------------------------------------------------------------
# Filler catalogue
# --------------------------------------------------------------------------
# The 24 hand-written products above are all plausible matches, so on their own
# they would make Stage 1 look like it does nothing. Real BPC catalogues are
# mostly noise relative to any one creator: wrong price bracket, thin reviews,
# out of stock. This generator adds that noise deterministically, which is what
# makes the ~20-30% eligible pool in the deck an observed number here rather
# than a claimed one.
#
# Generated products are capped below the hand-written ones on rating, trend and
# saturation, so the curated catalogue stays the interesting part of the demo.

FILLER_COUNT = int(_os.getenv("FILLER_PRODUCTS", "140"))

_FILLER_SPECS = {
    "Skincare": [
        ("Toner", "toner", ["toner", "routine"]),
        ("Face Mist", "mist", ["mist", "daily-use"]),
        ("Sheet Mask", "mask", ["mask", "affordable"]),
        ("Exfoliating Peel", "peel", ["peel", "routine"]),
        ("Lip Sleeping Mask", "lips", ["lips", "overnight"]),
        ("Eye Cream", "eyes", ["eyes", "routine"]),
    ],
    "Makeup": [
        ("Mascara", "eyes", ["eyes", "everyday"]),
        ("Brow Pencil", "eyes", ["eyes", "everyday"]),
        ("Setting Spray", "base", ["base", "party"]),
        ("Concealer Stick", "base", ["base", "everyday"]),
        ("Nail Lacquer", "nails", ["nails", "affordable"]),
    ],
    "Haircare": [
        ("Conditioner", "conditioner", ["conditioner", "routine"]),
        ("Scalp Scrub", "scalp", ["scalp", "routine"]),
        ("Hair Mask", "mask", ["mask", "frizz"]),
        ("Dry Shampoo", "styling", ["styling", "everyday"]),
    ],
    "Personal Care": [
        ("Body Wash", "body", ["body", "daily-use"]),
        ("Hand Cream", "body", ["body", "winter"]),
        ("Face Razor", "grooming", ["grooming", "affordable"]),
        ("Perfume Mist", "fragrance", ["fragrance", "party"]),
    ],
}

_BRANDS = ("Glow", "Pure", "Everyday", "Botanic", "Luxe", "Bare", "Nova",
           "Daily", "Bloom", "Urban", "Petal", "Core")
_ART = ("serum", "patch", "tint", "kajal", "hair")


def generate_filler(count: int = FILLER_COUNT, start_index: int = 100) -> list[dict]:
    """Deterministic filler so every run of the demo produces the same funnel."""
    rng = _random.Random(20260102)
    rows: list[dict] = []
    categories = list(_FILLER_SPECS)

    for i in range(count):
        category = rng.choice(categories)
        base_name, sub_category, tags = rng.choice(_FILLER_SPECS[category])
        brand = rng.choice(_BRANDS)

        # Log-uniform price across the full catalogue range: most products sit
        # outside any single creator's band, which is what Stage 1 is for.
        price = int(round(49 * (6999 / 49) ** rng.random() / 10) * 10) or 49

        rating = round(min(4.4, max(2.6, rng.gauss(3.95, 0.45))), 1)
        reviews = int(10 ** rng.uniform(0.7, 3.9))
        orders = int(10 ** rng.uniform(1.3, 4.3))
        conversion = round(min(0.055, max(0.008, rng.gauss(0.029, 0.010))), 3)

        rows.append(
            dict(
                product_id=f"P{start_index + i}",
                title=f"{brand} {base_name}",
                category=category,
                sub_category=sub_category,
                price=price,
                description=f"{brand} {base_name.lower()} for everyday {category.lower()}.",
                tags=tags,
                art_key=rng.choice(_ART),
                brand=f"{brand} Co.",
                rating=rating,
                review_count=reviews,
                seller_rating=round(min(4.6, max(2.8, rating + rng.gauss(0.05, 0.3))), 1),
                return_rate=round(min(0.22, max(0.03, rng.gauss(0.09, 0.04))), 2),
                orders_30d=orders,
                conversion_rate=conversion,
                nmv_30d=int(orders * price),
                trend_score=round(min(0.70, max(0.10, rng.gauss(0.40, 0.15))), 2),
                trend_stage=rng.choice(
                    ["early", "rising", "peak", "saturating", "saturating", "declining"]
                ),
                creator_saturation=round(min(0.85, max(0.30, rng.gauss(0.52, 0.14))), 2),
                target_age_min=rng.choice([18, 18, 20, 22, 25, 28]),
                target_age_max=rng.choice([28, 30, 34, 38, 45]),
                target_tiers=rng.choice(
                    [["T1"], ["T1", "T2"], ["T2", "T3"], ["T1", "T2", "T3"]]
                ),
                in_stock=rng.random() > 0.12,
                serviceable=rng.random() > 0.08,
                policy_compliant=rng.random() > 0.04,
            )
        )
    return rows


DEMO_CREATOR_ID = "C013"          # Riya Kapoor, the deck's persona (slides 7, 8, 18)


def _wipe(db: Session) -> None:
    """Delete every row, children first, so a reset works on Postgres too."""
    from .models import (
        EvaluationSnapshot, FeedbackEvent, OrderEvent, Pitch, RecommendationLog, SimulatedProfile,
    )
    for model in (OrderEvent, Pitch, FeedbackEvent, RecommendationLog, EvaluationSnapshot,
                  SimulatedProfile, Interaction, Product, Creator):
        db.query(model).delete()
    db.commit()


def _seed_deck_creators(db: Session) -> int:
    """Riya, built from her deck answers through the onboarding code path."""
    from .engine import onboarding as ob

    added = 0
    products = {p.product_id: p for p in db.scalars(select(Product)).all()}
    for handle, answers in ob.DECK_ANSWERS.items():
        creator_id = ob.HANDLE_IDS[handle]
        if db.get(Creator, creator_id) is not None:
            continue
        fetched = ob.DEMO_PROFILES[handle]
        dna = ob.build_dna(answers, fetched, products)
        creator = Creator(creator_id=creator_id)
        ob.apply_dna(creator, dna, fetched, handle)
        db.add(creator)
        added += 1
    db.commit()
    return added


def seed(db: Session, *, force: bool = False, filler_count: int | None = None) -> dict[str, int]:
    """Load the demo data.

    Idempotent: anything missing (a creator or product added in a later version)
    is inserted, and nothing a demo created is overwritten. `force=True` wipes
    every table first, which is what POST /demo/reset uses to return the
    prototype to the exact state the deck shows.
    """
    if force:
        _wipe(db)

    existing_creators = {c for (c,) in db.execute(select(Creator.creator_id)).all()}
    existing_products = {p for (p,) in db.execute(select(Product.product_id)).all()}
    first_run = not existing_creators

    added_c = 0
    for row in CREATORS:
        if row["creator_id"] not in existing_creators:
            db.add(Creator(**row))
            added_c += 1

    catalogue = PRODUCTS + generate_filler(FILLER_COUNT if filler_count is None else filler_count)
    added_p = 0
    for row in catalogue:
        if row["product_id"] in existing_products:
            continue
        row = {**row, "brand": row.get("brand") or BRAND_BY_ID.get(row["product_id"], "Independent Seller")}
        product = Product(**row)
        product.embedding = product_vector(product)
        db.add(product)
        added_p += 1
    db.commit()

    added_i = 0
    if first_run:
        for row in INTERACTIONS:
            db.add(Interaction(**row))
            added_i += 1
        db.commit()

    added_c += _seed_deck_creators(db)
    return {"creators": added_c, "products": added_p, "interactions": added_i, "skipped": int(not (added_c or added_p))}


def main() -> None:
    init_db()
    with SessionLocal() as db:
        print(seed(db, force=True))


if __name__ == "__main__":
    main()
