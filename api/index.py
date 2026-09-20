"""Vercel serverless entrypoint — thin wrapper for auto-detection."""
import sys
import os

# Ensure backend/ is on the Python path
_backend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from app.vercel_app import app  # noqa: E402,F401
