from pydantic import BaseModel, Field
from typing import Optional


class ProductCreate(BaseModel):
    name: str
    category: str
    price: float = Field(gt=0)
    description: Optional[str] = None
    stock: int = Field(ge=0, default=0)


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = Field(default=None, gt=0)
    description: Optional[str] = None
    stock: Optional[int] = Field(default=None, ge=0)


class ProductResponse(BaseModel):
    productId: str
    name: str
    category: str
    price: float
    description: Optional[str]
    stock: int
    createdAt: str
    updatedAt: str


class PaginatedProductsResponse(BaseModel):
    items: list[ProductResponse]
    count: int
    next_cursor: Optional[str] = None
