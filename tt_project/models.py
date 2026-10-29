from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

def _utcnow():
    """Naive UTC timestamp (SQLite-friendly) without the deprecated utcnow()."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(150), index=True, nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(100), index=True, nullable=False)
    price = Column(Float, nullable=False)  # Selling price
    cost_price = Column(Float, nullable=False, default=0.0)  # Purchase cost
    quantity = Column(Integer, nullable=False, default=0)
    min_threshold = Column(Integer, nullable=False, default=10)  # Low stock threshold
    unit = Column(String(30), nullable=False, default="pcs")
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    # Relationships
    movements = relationship("StockMovement", back_populates="product", cascade="all, delete-orphan", order_by="desc(StockMovement.timestamp)")

    @property
    def is_low_stock(self) -> bool:
        return self.quantity <= self.min_threshold

    @property
    def is_out_of_stock(self) -> bool:
        return self.quantity <= 0

    @property
    def total_value(self) -> float:
        return round(self.quantity * self.price, 2)


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    movement_type = Column(String(20), nullable=False)  # 'IN', 'OUT', 'ADJUSTMENT'
    quantity_change = Column(Integer, nullable=False)   # Positive for added, negative for removed
    previous_quantity = Column(Integer, nullable=False)
    new_quantity = Column(Integer, nullable=False)
    reason = Column(String(255), nullable=True)
    timestamp = Column(DateTime, default=_utcnow)

    # Relationships
    product = relationship("Product", back_populates="movements")
