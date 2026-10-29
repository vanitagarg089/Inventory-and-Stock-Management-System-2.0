from database import engine, SessionLocal, Base
import models

def seed_inventory():
    """Initializes the database schema and populates rich sample products."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Check if data already exists
    if db.query(models.Product).count() > 0:
        print("Database already contains records. Skipping seed.")
        db.close()
        return

    sample_products = [
        # Electronics & Gadgets
        {
            "sku": "ELEC-LOGI-M185",
            "name": "Logitech M185 Wireless Mouse",
            "description": "Compact, reliable 2.4GHz wireless mouse with 1-year battery life.",
            "category": "Electronics",
            "price": 14.99,
            "cost_price": 8.50,
            "quantity": 42,
            "min_threshold": 15,
            "unit": "pcs"
        },
        {
            "sku": "ELEC-USBC-HUB7",
            "name": "Anker 7-in-1 USB-C Hub",
            "description": "4K HDMI, 100W Power Delivery, SD/TF Card Reader, 3x USB 3.0 ports.",
            "category": "Electronics",
            "price": 39.99,
            "cost_price": 22.00,
            "quantity": 6,  # LOW STOCK (<= 10)
            "min_threshold": 10,
            "unit": "pcs"
        },
        {
            "sku": "ELEC-HDMI-2M",
            "name": "High-Speed HDMI 2.1 Cable (2m)",
            "description": "8K@60Hz and 4K@120Hz braided ultra high-speed HDMI cord.",
            "category": "Electronics",
            "price": 9.49,
            "cost_price": 3.80,
            "quantity": 88,
            "min_threshold": 20,
            "unit": "pcs"
        },
        {
            "sku": "ELEC-MECH-KB87",
            "name": "Keychron TKL Mechanical Keyboard",
            "description": "Hot-swappable tactile brown switch RGB wireless mechanical keyboard.",
            "category": "Electronics",
            "price": 79.99,
            "cost_price": 48.00,
            "quantity": 0,  # OUT OF STOCK
            "min_threshold": 5,
            "unit": "pcs"
        },

        # Office & Stationery
        {
            "sku": "OFFC-A4-PAPER",
            "name": "HP Premium A4 Copy Paper (500 Sheets)",
            "description": "80gsm multipurpose high-white office printing paper ream.",
            "category": "Office Supplies",
            "price": 6.80,
            "cost_price": 4.10,
            "quantity": 115,
            "min_threshold": 30,
            "unit": "reams"
        },
        {
            "sku": "OFFC-GEL-PEN10",
            "name": "Pilot G2 0.7mm Gel Pens (Pack of 10)",
            "description": "Smooth writing refillable black ink gel rollerball pens.",
            "category": "Office Supplies",
            "price": 12.50,
            "cost_price": 7.00,
            "quantity": 3,  # LOW STOCK (<= 12)
            "min_threshold": 12,
            "unit": "boxes"
        },
        {
            "sku": "OFFC-NOTE-B5",
            "name": "Moleskine Hardcover Ruled Notebook",
            "description": "Acid-free ivory paper classic notebook with bookmark ribbon.",
            "category": "Office Supplies",
            "price": 18.00,
            "cost_price": 9.50,
            "quantity": 24,
            "min_threshold": 10,
            "unit": "pcs"
        },

        # Furniture & Ergonomics
        {
            "sku": "FURN-CHAIR-MESH",
            "name": "Ergonomic High-Back Mesh Chair",
            "description": "Breathable mesh back with adjustable lumbar support and 3D armrests.",
            "category": "Furniture",
            "price": 189.00,
            "cost_price": 110.00,
            "quantity": 2,  # LOW STOCK (<= 5)
            "min_threshold": 5,
            "unit": "pcs"
        },
        {
            "sku": "FURN-DESK-RISER",
            "name": "Dual-Monitor Standing Desk Converter",
            "description": "Pneumatic spring gas-assist height adjustable desktop riser.",
            "category": "Furniture",
            "price": 129.50,
            "cost_price": 75.00,
            "quantity": 11,
            "min_threshold": 6,
            "unit": "pcs"
        },

        # Hardware & Accessories
        {
            "sku": "HDWR-TOOL-64PC",
            "name": "Precision Electronics Screwdriver Kit (64-in-1)",
            "description": "Magnetic driver set with flexible shaft and 64 steel precision bits.",
            "category": "Hardware",
            "price": 24.99,
            "cost_price": 13.50,
            "quantity": 18,
            "min_threshold": 8,
            "unit": "sets"
        },
        {
            "sku": "HDWR-CABLE-TIE",
            "name": "Velcro Reusable Cable Ties (100 Pack)",
            "description": "Self-fastening durable wire organizer wraps for cable management.",
            "category": "Hardware",
            "price": 8.99,
            "cost_price": 3.20,
            "quantity": 0,  # OUT OF STOCK
            "min_threshold": 15,
            "unit": "packs"
        },
        {
            "sku": "HDWR-SURGE-6OUT",
            "name": "Belkin 6-Outlet Surge Protector Strip",
            "description": "Heavy-duty 2m power extension cord with 900 Joule surge protection.",
            "category": "Hardware",
            "price": 19.99,
            "cost_price": 10.00,
            "quantity": 4,  # LOW STOCK (<= 8)
            "min_threshold": 8,
            "unit": "pcs"
        }
    ]

    for p_data in sample_products:
        prod = models.Product(**p_data)
        db.add(prod)
        db.commit()
        db.refresh(prod)

        # Log initial movement
        if prod.quantity > 0:
            mov = models.StockMovement(
                product_id=prod.id,
                movement_type="IN",
                quantity_change=prod.quantity,
                previous_quantity=0,
                new_quantity=prod.quantity,
                reason="Initial seed inventory balance"
            )
            db.add(mov)

    db.commit()
    print(f"Successfully seeded {len(sample_products)} products into inventory.")
    db.close()

if __name__ == "__main__":
    seed_inventory()
