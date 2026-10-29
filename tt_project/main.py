import os
from contextlib import asynccontextmanager
from typing import Optional, List

from fastapi import FastAPI, Depends, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi import Request
from sqlalchemy.orm import Session

from database import engine, Base, get_db
import models
import schemas
import crud
from seed_data import seed_inventory

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

# Ensure static & templates directory exist
os.makedirs(os.path.join(STATIC_DIR, "css"), exist_ok=True)
os.makedirs(os.path.join(STATIC_DIR, "js"), exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables
    Base.metadata.create_all(bind=engine)
    # Seed sample inventory if database is empty
    seed_inventory()
    yield


app = FastAPI(
    title="Inventory and Stock Management System API",
    description="RESTful API for small business product catalog, real-time stock tracking, low-stock alerts, and inventory audit logs.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Static Files & Templates
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


# --- Dashboard Frontend Route ---

@app.get("/", response_class=HTMLResponse, summary="Inventory Dashboard UI")
def serve_dashboard(request: Request):
    """Serves the interactive Inventory and Stock Management dashboard."""
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"title": "StockMaster - Inventory & Stock Management"}
    )


# --- REST API: Products & Stock Management ---

@app.get("/api/products", response_model=List[schemas.ProductResponse], tags=["Products"])
def list_products(
    search: Optional[str] = Query(None, description="Search product by name, SKU, or category"),
    category: Optional[str] = Query(None, description="Filter products by specific category"),
    status: Optional[str] = Query("all", description="Status filter: all, in_stock, low_stock, out_of_stock, needs_restock"),
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """Retrieve all products with real-time stock levels, search, and category filtering."""
    return crud.get_products(db, skip=skip, limit=limit, search=search, category=category, status_filter=status)


@app.get("/api/products/{product_id}", response_model=schemas.ProductResponse, tags=["Products"])
def get_product_details(product_id: int, db: Session = Depends(get_db)):
    """Fetch details of a single product by its primary key ID."""
    prod = crud.get_product(db, product_id)
    if not prod:
        raise HTTPException(status_code=404, detail=f"Product with ID {product_id} not found.")
    return prod


@app.post("/api/products", response_model=schemas.ProductResponse, status_code=status.HTTP_201_CREATED, tags=["Products"])
def create_new_product(product_in: schemas.ProductCreate, db: Session = Depends(get_db)):
    """Add a new product to inventory. Automatically initializes stock movement tracking."""
    try:
        return crud.create_product(db, product_in)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.put("/api/products/{product_id}", response_model=schemas.ProductResponse, tags=["Products"])
def update_product_details(product_id: int, product_update: schemas.ProductUpdate, db: Session = Depends(get_db)):
    """Update details of an existing product (pricing, description, thresholds, etc.)."""
    try:
        updated = crud.update_product(db, product_id, product_update)
        if not updated:
            raise HTTPException(status_code=404, detail=f"Product with ID {product_id} not found.")
        return updated
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/products/{product_id}", status_code=status.HTTP_200_OK, tags=["Products"])
def delete_product(product_id: int, db: Session = Depends(get_db)):
    """Delete a product and its associated stock movement history."""
    success = crud.delete_product(db, product_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Product with ID {product_id} not found.")
    return {"message": f"Product {product_id} deleted successfully."}


@app.post("/api/products/{product_id}/adjust-stock", response_model=schemas.ProductResponse, tags=["Stock Control"])
def adjust_inventory_stock(product_id: int, adjustment: schemas.StockAdjustRequest, db: Session = Depends(get_db)):
    """
    Perform stock operations:
    - **IN**: Restock/Add inventory from supplier
    - **OUT**: Dispatch or sell items to customer
    - **ADJUSTMENT**: Set exact count during physical inventory audit
    """
    try:
        return crud.adjust_stock(db, product_id, adjustment)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# --- REST API: Dashboard, Low Stock Alerts, & Analytics ---

@app.get("/api/inventory/stats", response_model=schemas.DashboardStats, tags=["Analytics"])
def get_inventory_statistics(db: Session = Depends(get_db)):
    """Retrieve high-level inventory KPIs: total units, asset valuation, alert counts, and category metrics."""
    return crud.get_dashboard_stats(db)


@app.get("/api/inventory/low-stock", response_model=List[schemas.ProductResponse], tags=["Low Stock Alerts"])
def get_low_stock_alerts(db: Session = Depends(get_db)):
    """List all products where current stock level is below or equal to the minimum threshold."""
    return crud.get_low_stock_products(db)


@app.get("/api/inventory/movements", response_model=List[schemas.StockMovementResponse], tags=["Stock Control"])
def get_recent_stock_movements(limit: int = Query(30, ge=1, le=100), db: Session = Depends(get_db)):
    """Fetch the chronological audit trail of all inventory inflows, sales, and corrections."""
    return crud.get_recent_movements(db, limit=limit)


@app.get("/api/categories", response_model=List[str], tags=["Categories"])
def get_all_categories(db: Session = Depends(get_db)):
    """List all distinct product categories in inventory."""
    return crud.get_categories(db)


# Global Exception Handler for Clean JSON Errors
@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})
