from typing import Optional, List, Dict
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
import models
import schemas

def get_products(
    db: Session,
    skip: int = 0,
    limit: int = 200,
    search: Optional[str] = None,
    category: Optional[str] = None,
    status_filter: Optional[str] = None  # 'all', 'low_stock', 'out_of_stock', 'in_stock', 'needs_restock'
) -> List[models.Product]:
    query = db.query(models.Product)

    if search:
        search_fmt = f"%{search.strip().lower()}%"
        query = query.filter(
            or_(
                func.lower(models.Product.name).like(search_fmt),
                func.lower(models.Product.sku).like(search_fmt),
                func.lower(models.Product.category).like(search_fmt)
            )
        )

    if category and category.lower() != "all":
        query = query.filter(func.lower(models.Product.category) == category.strip().lower())

    if status_filter == "out_of_stock":
        query = query.filter(models.Product.quantity <= 0)
    elif status_filter == "low_stock":
        query = query.filter(
            models.Product.quantity > 0,
            models.Product.quantity <= models.Product.min_threshold
        )
    elif status_filter == "needs_restock":  # low + out of stock (matches the alert bell / banner)
        query = query.filter(models.Product.quantity <= models.Product.min_threshold)
    elif status_filter == "in_stock":
        query = query.filter(models.Product.quantity > models.Product.min_threshold)

    return query.order_by(models.Product.name.asc()).offset(skip).limit(limit).all()


def get_product(db: Session, product_id: int) -> Optional[models.Product]:
    return db.query(models.Product).filter(models.Product.id == product_id).first()


def get_product_by_sku(db: Session, sku: str) -> Optional[models.Product]:
    return db.query(models.Product).filter(func.lower(models.Product.sku) == sku.strip().lower()).first()


def create_product(db: Session, product_in: schemas.ProductCreate) -> models.Product:
    # Check if SKU already exists
    existing = get_product_by_sku(db, product_in.sku)
    if existing:
        raise ValueError(f"Product with SKU '{product_in.sku}' already exists.")

    db_product = models.Product(
        sku=product_in.sku.strip().upper(),
        name=product_in.name.strip(),
        description=product_in.description.strip() if product_in.description else None,
        category=product_in.category.strip(),
        price=product_in.price,
        cost_price=product_in.cost_price,
        quantity=product_in.quantity,
        min_threshold=product_in.min_threshold,
        unit=product_in.unit.strip().lower()
    )
    db.add(db_product)
    db.commit()
    db.refresh(db_product)

    # If initial quantity > 0, record an initial stock movement
    if db_product.quantity > 0:
        movement = models.StockMovement(
            product_id=db_product.id,
            movement_type="IN",
            quantity_change=db_product.quantity,
            previous_quantity=0,
            new_quantity=db_product.quantity,
            reason="Initial stock registration"
        )
        db.add(movement)
        db.commit()

    return db_product


def update_product(db: Session, product_id: int, product_update: schemas.ProductUpdate) -> Optional[models.Product]:
    db_product = get_product(db, product_id)
    if not db_product:
        return None

    update_data = product_update.model_dump(exclude_unset=True)

    # Check for SKU collision if updating SKU
    if "sku" in update_data and update_data["sku"]:
        sku_val = update_data["sku"].strip().upper()
        existing = db.query(models.Product).filter(
            func.lower(models.Product.sku) == sku_val.lower(),
            models.Product.id != product_id
        ).first()
        if existing:
            raise ValueError(f"SKU '{sku_val}' is already used by another product.")
        update_data["sku"] = sku_val

    # If quantity is being directly updated via edit modal, log the delta
    if "quantity" in update_data and update_data["quantity"] is not None:
        new_qty = update_data["quantity"]
        prev_qty = db_product.quantity
        if new_qty != prev_qty:
            delta = new_qty - prev_qty
            movement = models.StockMovement(
                product_id=db_product.id,
                movement_type="ADJUSTMENT",
                quantity_change=delta,
                previous_quantity=prev_qty,
                new_quantity=new_qty,
                reason="Direct quantity update in product editor"
            )
            db.add(movement)

    for field, value in update_data.items():
        setattr(db_product, field, value)

    db.commit()
    db.refresh(db_product)
    return db_product


def delete_product(db: Session, product_id: int) -> bool:
    db_product = get_product(db, product_id)
    if not db_product:
        return False
    db.delete(db_product)
    db.commit()
    return True


def adjust_stock(db: Session, product_id: int, req: schemas.StockAdjustRequest) -> models.Product:
    db_product = get_product(db, product_id)
    if not db_product:
        raise ValueError(f"Product with ID {product_id} not found.")

    prev_qty = db_product.quantity
    qty_val = req.quantity

    if req.movement_type == "IN":
        delta = qty_val
        new_qty = prev_qty + delta
    elif req.movement_type == "OUT":
        if prev_qty < qty_val:
            raise ValueError(f"Cannot dispatch {qty_val} units. Only {prev_qty} units available in stock.")
        delta = -qty_val
        new_qty = prev_qty - qty_val
    elif req.movement_type == "ADJUSTMENT":
        new_qty = qty_val
        delta = new_qty - prev_qty
    else:
        raise ValueError(f"Invalid movement type: {req.movement_type}")

    db_product.quantity = new_qty

    movement = models.StockMovement(
        product_id=db_product.id,
        movement_type=req.movement_type,
        quantity_change=delta,
        previous_quantity=prev_qty,
        new_quantity=new_qty,
        reason=req.reason or f"Stock {req.movement_type} adjustment"
    )
    db.add(movement)
    db.commit()
    db.refresh(db_product)
    return db_product


def get_low_stock_products(db: Session) -> List[models.Product]:
    return db.query(models.Product).filter(
        models.Product.quantity <= models.Product.min_threshold
    ).order_by(models.Product.quantity.asc()).all()


def get_categories(db: Session) -> List[str]:
    categories = db.query(models.Product.category).distinct().order_by(models.Product.category.asc()).all()
    return [c[0] for c in categories if c[0]]


def get_dashboard_stats(db: Session) -> schemas.DashboardStats:
    products = db.query(models.Product).all()

    total_products = len(products)
    total_stock_units = sum(p.quantity for p in products)
    total_inventory_value = round(sum(p.quantity * p.price for p in products), 2)
    low_stock_count = sum(1 for p in products if 0 < p.quantity <= p.min_threshold)
    out_of_stock_count = sum(1 for p in products if p.quantity <= 0)

    # Category breakdown
    cat_map: Dict[str, Dict] = {}
    for p in products:
        c = p.category
        if c not in cat_map:
            cat_map[c] = {"category": c, "product_count": 0, "total_quantity": 0, "total_value": 0.0}
        cat_map[c]["product_count"] += 1
        cat_map[c]["total_quantity"] += p.quantity
        cat_map[c]["total_value"] += round(p.quantity * p.price, 2)

    cat_stats = [
        schemas.CategoryStat(
            category=v["category"],
            product_count=v["product_count"],
            total_quantity=v["total_quantity"],
            total_value=round(v["total_value"], 2)
        )
        for v in cat_map.values()
    ]
    cat_stats.sort(key=lambda x: x.total_value, reverse=True)

    return schemas.DashboardStats(
        total_products=total_products,
        total_stock_units=total_stock_units,
        total_inventory_value=total_inventory_value,
        low_stock_count=low_stock_count,
        out_of_stock_count=out_of_stock_count,
        categories_count=len(cat_map),
        category_breakdown=cat_stats
    )


def get_recent_movements(db: Session, limit: int = 30) -> List[dict]:
    movements = db.query(
        models.StockMovement, models.Product.name, models.Product.sku
    ).join(
        models.Product, models.StockMovement.product_id == models.Product.id
    ).order_by(
        models.StockMovement.timestamp.desc()
    ).limit(limit).all()

    results = []
    for mov, prod_name, prod_sku in movements:
        results.append({
            "id": mov.id,
            "product_id": mov.product_id,
            "product_name": prod_name,
            "product_sku": prod_sku,
            "movement_type": mov.movement_type,
            "quantity_change": mov.quantity_change,
            "previous_quantity": mov.previous_quantity,
            "new_quantity": mov.new_quantity,
            "reason": mov.reason,
            "timestamp": mov.timestamp.isoformat() + "Z"  # stored as UTC; "Z" lets the browser convert to local time
        })
    return results
