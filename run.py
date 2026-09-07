#!/usr/bin/env python3
"""
Quantive — One-Command Desktop Launcher

Usage:
    python run.py                  # Start on port 8000
    python run.py --port 3000      # Start on port 3000
    python run.py --host 0.0.0.0   # Allow external connections
    python run.py --no-browser     # Don't auto-open browser

This starts the FastAPI backend which also serves the React frontend.
Everything runs from a single Python process.
"""

import argparse
import os
import sys
import threading
import time
import webbrowser
from pathlib import Path


def ensure_dependencies():
    """Install required packages if missing."""
    required = ["fastapi", "uvicorn", "sqlalchemy", "pydantic", "pydantic-settings"]
    missing = []
    for pkg in required:
        try:
            __import__(pkg.replace("-", "_"))
        except ImportError:
            # Map package names to pip names
            pip_names = {
                "pydantic_settings": "pydantic-settings",
            }
            missing.append(pip_names.get(pkg, pkg))

    if missing:
        print(f"[SETUP] Installing missing packages: {', '.join(missing)}")
        import subprocess
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--quiet"] + missing,
            stdout=subprocess.DEVNULL,
        )


def check_frontend():
    """Verify the frontend build exists."""
    dist = Path(__file__).parent / "frontend" / "dist"
    if not dist.is_dir():
        print("[BUILD] Frontend not built. Building now...")
        import subprocess
        frontend_dir = Path(__file__).parent / "frontend"
        subprocess.check_call(
            ["npm", "run", "build"],
            cwd=str(frontend_dir),
            stdout=subprocess.DEVNULL,
        )
        print("[BUILD] Frontend built successfully.")
    return dist


def open_browser(host: str, port: int, delay: float = 2.0):
    """Open the browser after a short delay."""
    time.sleep(delay)
    url = f"http://{'localhost' if host == '0.0.0.0' else host}:{port}"
    print(f"\n  Opening {url} in your browser...")
    webbrowser.open(url)


def main():
    parser = argparse.ArgumentParser(
        description="Quantive — Sovereign Financial Optimization Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on (default: 8000)")
    parser.add_argument("--no-browser", action="store_true", help="Don't auto-open browser")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    args = parser.parse_args()

    # Banner
    print()
    print("  ╔══════════════════════════════════════════╗")
    print("  ║         QUANTIVE  v2.1.0                 ║")
    print("  ║  Sovereign Financial Optimization        ║")
    print("  ╚══════════════════════════════════════════╝")
    print()

    # Ensure dependencies
    ensure_dependencies()

    # Check frontend
    check_frontend()

    # Set environment
    os.environ.setdefault("ENVIRONMENT", "development")

    # Add backend to path
    backend_dir = Path(__file__).parent / "backend"
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))

    # Open browser in background thread
    if not args.no_browser:
        threading.Thread(target=open_browser, args=(args.host, args.port), daemon=True).start()

    # Start the server
    print(f"  Starting Quantive on http://{args.host}:{args.port}")
    print(f"  Press Ctrl+C to stop\n")

    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
        access_log=False,
    )


if __name__ == "__main__":
    main()
