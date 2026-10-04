"""Product Service — catalogue, metadata, availability."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..imagery import image_for
from ..models import Product
from ..schemas import ProductOut

router = APIRouter(tags=["products"])


def to_out(product: Product) -> ProductOut:
    return ProductOut(
        product_id=product.product_id,
        title=product.title,
        category=product.category,
        sub_category=product.sub_category,
        price=product.price,
        description=product.description,
        tags=product.tags or [],
        art_key=product.art_key,
        brand=product.brand or "",
        image=image_for(product),
        is_new=product.review_count == 0,
        rating=product.rating,
        review_count=product.review_count,
        seller_rating=product.seller_rating,
        return_rate=product.return_rate,
        orders_30d=product.orders_30d,
        conversion_rate=product.conversion_rate,
        nmv_30d=product.nmv_30d,
        trend_score=product.trend_score,
        trend_stage=product.trend_stage,
        creator_saturation=product.creator_saturation,
        in_stock=product.in_stock,
    )


@router.get("/products", response_model=list[ProductOut])
def list_products(
    category: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    stmt = select(Product)
    if category and category.lower() != "bpc":
        stmt = stmt.where(Product.category == category)
    return [to_out(p) for p in db.scalars(stmt).all()]


@router.get("/product/{product_id}", response_model=ProductOut)
def get_product(product_id: str, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail=f"product {product_id} not found")
    return to_out(product)
