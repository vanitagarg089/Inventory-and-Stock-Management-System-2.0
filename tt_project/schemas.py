from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, Field, ConfigDict

# --- Product Schemas ---

class ProductBase(BaseModel):
    sku: str = Field(..., min_length=2, max_length=50, description="Unique Stock Keeping Unit (e.g. ELEC-001)")
    name: str = Field(..., min_length=1, max_length=150, description="Product Name")
    description: Optional[str] = Field(None, description="Detailed product description")
    category: str = Field(..., min_length=1, max_length=100, description="Category (e.g. Electronics, Clothing)")
    price: float = Field(..., ge=0.0, description="Retail selling price per unit")
    cost_price: float = Field(default=0.0, ge=0.0, description="Wholesale/Cost price per unit")
    quantity: int = Field(default=0, ge=0, description="Current stock in inventory")
    min_threshold: int = Field(default=10, ge=0, description="Threshold quantity that triggers low stock warning")
    unit: str = Field(default="pcs", min_length=1, max_length=30, description="Unit of measurement (pcs, kg, box, etc.)")


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    sku: Optional[str] = Field(None, min_length=2, max_length=50)
    name: Optional[str] = Field(None, min_length=1, max_length=150)
    description: Optional[str] = None
    category: Optional[str] = Field(None, min_length=1, max_length=100)
    price: Optional[float] = Field(None, ge=0.0)
    cost_price: Optional[float] = Field(None, ge=0.0)
    quantity: Optional[int] = Field(None, ge=0)
    min_threshold: Optional[int] = Field(None, ge=0)
    unit: Optional[str] = Field(None, min_length=1, max_length=30)


class ProductResponse(ProductBase):
    id: int
    created_at: datetime
    updated_at: datetime
    is_low_stock: bool
    is_out_of_stock: bool
    total_value: float

    model_config = ConfigDict(from_attributes=True)


# --- Stock Movement / Audit Schemas ---

class StockAdjustRequest(BaseModel):
    movement_type: str = Field(..., pattern="^(IN|OUT|ADJUSTMENT)$", description="Type of movement: 'IN', 'OUT', or 'ADJUSTMENT'")
    quantity: int = Field(..., gt=0, description="Quantity to add, deduct, or set")
    reason: Optional[str] = Field(None, max_length=255, description="Reason for the adjustment (e.g., Supplier Restock, Customer Sale, Damaged Item, Inventory Audit)")


class StockMovementResponse(BaseModel):
    id: int
    product_id: int
    movement_type: str
    quantity_change: int
    previous_quantity: int
    new_quantity: int
    reason: Optional[str] = None
    timestamp: datetime
    product_name: Optional[str] = None
    product_sku: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# --- Dashboard Stats Schemas ---

class CategoryStat(BaseModel):
    category: str
    product_count: int
    total_quantity: int
    total_value: float


class DashboardStats(BaseModel):
    total_products: int
    total_stock_units: int
    total_inventory_value: float
    low_stock_count: int
    out_of_stock_count: int
    categories_count: int
    category_breakdown: List[CategoryStat]
