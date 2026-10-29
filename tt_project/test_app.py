from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base, get_db
from main import app
import models

from sqlalchemy.pool import StaticPool

# In-memory SQLite for testing with StaticPool so all connections share the DB
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

# Create fresh schema in-memory
Base.metadata.create_all(bind=test_engine)
client = TestClient(app)


def test_create_and_fetch_product():
    payload = {
        "sku": "TEST-KEY-001",
        "name": "Test Wireless Mouse",
        "description": "Ergonomic test mouse",
        "category": "Peripherals",
        "price": 25.00,
        "cost_price": 12.50,
        "quantity": 15,
        "min_threshold": 5,
        "unit": "pcs"
    }
    res = client.post("/api/products", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["sku"] == "TEST-KEY-001"
    assert data["quantity"] == 15
    assert data["is_low_stock"] is False
    assert data["total_value"] == 375.00
    prod_id = data["id"]

    # Fetch product by ID
    get_res = client.get(f"/api/products/{prod_id}")
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "Test Wireless Mouse"


def test_duplicate_sku_rejected():
    payload = {
        "sku": "TEST-KEY-001",  # Same SKU
        "name": "Another Mouse",
        "category": "Peripherals",
        "price": 20.00,
        "quantity": 5,
        "min_threshold": 2,
        "unit": "pcs"
    }
    res = client.post("/api/products", json=payload)
    assert res.status_code == 400
    assert "already exists" in res.json()["detail"]


def test_stock_adjust_in_and_out():
    # 1. Fetch created product
    res = client.get("/api/products?search=TEST-KEY-001")
    prod = res.json()[0]
    prod_id = prod["id"]
    initial_qty = prod["quantity"]

    # 2. Restock (IN +10)
    adjust_in = {
        "movement_type": "IN",
        "quantity": 10,
        "reason": "Supplier delivery batch A"
    }
    res_in = client.post(f"/api/products/{prod_id}/adjust-stock", json=adjust_in)
    assert res_in.status_code == 200
    assert res_in.json()["quantity"] == initial_qty + 10

    # 3. Dispatch (OUT -5)
    adjust_out = {
        "movement_type": "OUT",
        "quantity": 5,
        "reason": "Customer sales order #99"
    }
    res_out = client.post(f"/api/products/{prod_id}/adjust-stock", json=adjust_out)
    assert res_out.status_code == 200
    assert res_out.json()["quantity"] == initial_qty + 10 - 5


def test_stock_adjust_out_insufficient_stock():
    res = client.get("/api/products?search=TEST-KEY-001")
    prod = res.json()[0]
    prod_id = prod["id"]

    # Try to deduct 9999 units
    excess_out = {
        "movement_type": "OUT",
        "quantity": 9999,
        "reason": "Invalid bulk order"
    }
    res = client.post(f"/api/products/{prod_id}/adjust-stock", json=excess_out)
    assert res.status_code == 400
    assert "available in stock" in res.json()["detail"]


def test_low_stock_detection_and_alerts():
    # Create product with low stock
    payload = {
        "sku": "ALERT-ITEM-01",
        "name": "Low Stock USB Cable",
        "category": "Cables",
        "price": 5.00,
        "cost_price": 2.00,
        "quantity": 3,
        "min_threshold": 10,  # 3 <= 10 -> Low Stock!
        "unit": "pcs"
    }
    client.post("/api/products", json=payload)

    alerts_res = client.get("/api/inventory/low-stock")
    assert alerts_res.status_code == 200
    alerts = alerts_res.json()
    assert any(item["sku"] == "ALERT-ITEM-01" for item in alerts)


def test_inventory_stats_endpoint():
    res = client.get("/api/inventory/stats")
    assert res.status_code == 200
    stats = res.json()
    assert stats["total_products"] >= 2
    assert stats["total_stock_units"] > 0
    assert stats["total_inventory_value"] > 0
    assert stats["low_stock_count"] >= 1
    assert len(stats["category_breakdown"]) >= 1


def test_recent_movements_logged():
    res = client.get("/api/inventory/movements?limit=10")
    assert res.status_code == 200
    movements = res.json()
    assert len(movements) >= 2
    assert any(m["movement_type"] in ["IN", "OUT"] for m in movements)


def test_movement_timestamps_are_utc_marked():
    movements = client.get("/api/inventory/movements?limit=5").json()
    assert movements and all(m["timestamp"].endswith("Z") for m in movements)


def test_needs_restock_filter_includes_out_of_stock():
    client.post("/api/products", json={"sku": "ZERO-ITEM-01", "name": "Zero Stock Item", "category": "Cables",
                                       "price": 1.0, "quantity": 0, "min_threshold": 5})
    low = {p["sku"] for p in client.get("/api/products?status=low_stock").json()}
    need = {p["sku"] for p in client.get("/api/products?status=needs_restock").json()}
    assert "ZERO-ITEM-01" not in low and "ZERO-ITEM-01" in need
    assert "ALERT-ITEM-01" in low and "ALERT-ITEM-01" in need


def test_product_name_with_apostrophe_roundtrips():
    res = client.post("/api/products", json={"sku": "APOS-001", "name": "Men's Shirt", "category": "Clothing",
                                             "price": 10.0, "quantity": 5})
    assert res.status_code == 201 and res.json()["name"] == "Men's Shirt"


if __name__ == "__main__":
    print("Running automated system verification tests...")
    test_create_and_fetch_product()
    print("[PASS] Product creation & retrieval passed")
    test_duplicate_sku_rejected()
    print("[PASS] Duplicate SKU prevention passed")
    test_stock_adjust_in_and_out()
    print("[PASS] Stock adjustment (IN & OUT) passed")
    test_stock_adjust_out_insufficient_stock()
    print("[PASS] Over-dispatch prevention passed")
    test_low_stock_detection_and_alerts()
    print("[PASS] Low stock alert detection passed")
    test_inventory_stats_endpoint()
    print("[PASS] KPI stats calculation passed")
    test_recent_movements_logged()
    print("[PASS] Audit trail logging passed")
    print("\nAll 7 test suites executed successfully! 100% PASS.")
