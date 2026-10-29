import sys
import subprocess
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)  # so requirements.txt, main:app and inventory.db resolve from any cwd
sys.path.insert(0, BASE_DIR)


def ensure_dependencies():
    """Verify essential packages and inform the user if any are missing."""
    required = ["fastapi", "uvicorn", "sqlalchemy", "pydantic", "jinja2"]
    missing = []
    for pkg in required:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)

    if missing:
        print(f"Missing required packages: {', '.join(missing)}")
        print("Installing dependencies from requirements.txt...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", os.path.join(BASE_DIR, "requirements.txt")])

def main():
    print("=" * 60)
    print("   StockMaster - Inventory and Stock Management System")
    print("=" * 60)
    
    ensure_dependencies()

    # Pre-seed the database if not present
    from seed_data import seed_inventory
    seed_inventory()

    import uvicorn
    host = "127.0.0.1"
    port = 8080
    
    print("\n[+] Server starting...")
    print(f"    • Web Dashboard:  http://{host}:{port}")
    print(f"    • Swagger Docs:   http://{host}:{port}/docs")
    print(f"    • ReDoc Docs:     http://{host}:{port}/redoc")
    print("\nPress Ctrl+C to stop the server.\n")

    uvicorn.run("main:app", host=host, port=port, reload=True)

if __name__ == "__main__":
    main()
