"""Vercel serverless entrypoint — thin wrapper for auto-detection."""
import sys
import os

# Ensure backend/ is on the Python path
_backend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from fastapi import FastAPI
from fastapi.responses import JSONResponse

# Top-level app required for Vercel Python runtime detection
# Define fallback first so static analysis finds it, then try to replace with full app
app = FastAPI(title="Quantive API (fallback)")

@app.get("/api/health")
def health():
    return JSONResponse({"status": "degraded", "error": "backend not loaded"})

@app.get("/api")
def api_root():
    return JSONResponse({"status": "degraded", "error": "backend not loaded"})

# Try to load the full backend — if successful, replace the fallback app
try:
    from app.vercel_app import app as backend_app  # noqa: E402
    app = backend_app
except Exception as _import_err:
    # Keep fallback app, update health to show error
    import logging
    logging.getLogger("quantive.vercel").warning("Backend load failed: %s", _import_err)
