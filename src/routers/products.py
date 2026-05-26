import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Response

from src import database
from src.models import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    PaginatedProductsResponse,
)

router = APIRouter(tags=["products"])


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@router.get("/health", summary="Health check")
def health_check():
    """Returns API and table status."""
    return {"status": "ok", "table": database.TABLE_NAME}


# ---------------------------------------------------------------------------
# Product CRUD
# ---------------------------------------------------------------------------

@router.post(
    "/products",
    response_model=ProductResponse,
    status_code=201,
    summary="Create a product",
)
def create_product(payload: ProductCreate):
    """Create a new product and store it in DynamoDB."""
    now = _now_iso()
    item = {
        "productId": str(uuid.uuid4()),
        "name": payload.name,
        "category": payload.category,
        "price": payload.price,
        "description": payload.description,
        "stock": payload.stock,
        "createdAt": now,
        "updatedAt": now,
    }
    database.put_product(item)
    return ProductResponse(**item)


@router.get(
    "/products",
    response_model=PaginatedProductsResponse,
    summary="List all products (paginated)",
)
def list_products(
    limit: int = Query(default=20, ge=1, le=100),
    cursor: Optional[str] = Query(default=None),
):
    """
    Return a paginated list of products.
    Pass the returned `next_cursor` as `cursor` on the next request to get the next page.
    """
    items, next_cursor = database.list_products(limit=limit, last_key=cursor)
    products = [ProductResponse(**item) for item in items]
    return PaginatedProductsResponse(
        items=products,
        count=len(products),
        next_cursor=next_cursor,
    )


@router.get(
    "/products/category/{category}",
    response_model=list[ProductResponse],
    summary="List products by category",
)
def list_by_category(
    category: str,
    max_price: Optional[float] = Query(default=None, gt=0),
):
    """
    Query the CategoryPriceIndex GSI. Returns products in the given category,
    sorted by price ascending. Optionally filter with ?max_price=.
    """
    items = database.list_by_category(category=category, max_price=max_price)
    return [ProductResponse(**item) for item in items]


@router.get(
    "/products/{product_id}",
    response_model=ProductResponse,
    summary="Get a single product",
)
def get_product(product_id: str):
    """Fetch a product by its productId."""
    item = database.get_product(product_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Product '{product_id}' not found")
    return ProductResponse(**item)


@router.put(
    "/products/{product_id}",
    response_model=ProductResponse,
    summary="Update a product (partial)",
)
def update_product(product_id: str, payload: ProductUpdate):
    """Partially update a product. Only provided fields are updated."""
    updates = payload.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields provided for update")

    updates["updatedAt"] = _now_iso()
    item = database.update_product(product_id, updates)
    if not item:
        raise HTTPException(status_code=404, detail=f"Product '{product_id}' not found")
    return ProductResponse(**item)


@router.delete(
    "/products/{product_id}",
    status_code=204,
    summary="Delete a product",
)
def delete_product(product_id: str):
    """Delete a product. Returns 204 on success, 404 if not found."""
    deleted = database.delete_product(product_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Product '{product_id}' not found")
    return Response(status_code=204)
