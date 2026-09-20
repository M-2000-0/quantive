"""Pre-demo health check — verify everything works before a government presentation."""
import sys
sys.path.insert(0, r'C:\Users\HP\OneDrive\Desktop\Quantive\backend')

import warnings
warnings.filterwarnings('ignore')

checks = []

# 1. Backend imports
try:
    from app.main import app
    from app.security.csrf import CSRFMiddleware
    inner = app.app
    routes = [r.path for r in inner.routes]
    checks.append(("Backend imports", True, f"{len(routes)} routes"))
except Exception as e:
    checks.append(("Backend imports", False, str(e)))

# 2. Critical routes exist
try:
    critical = ["/api/health", "/api/auth/login", "/login", "/dashboard"]
    inner = app.app
    all_paths = [r.path for r in inner.routes]
    missing = [p for p in critical if not any(p in rp for rp in all_paths)]
    if missing:
        checks.append(("Critical routes", False, f"Missing: {missing}"))
    else:
        checks.append(("Critical routes", True, f"All {len(critical)} present"))
except Exception as e:
    checks.append(("Critical routes", False, str(e)))

# 3. Database connectivity
try:
    from app.database import engine
    from sqlalchemy import text
    with engine.begin() as conn:
        conn.execute(text("SELECT 1"))
    checks.append(("Database", True, "SQLite connected"))
except Exception as e:
    checks.append(("Database", False, str(e)))

# 4. AI model loads
try:
    from app.ai.inference import get_engine
    engine = get_engine()
    ok = engine._ensure_loaded()
    checks.append(("AI Model", ok, "SovereignGPT loaded" if ok else "Not found"))
except Exception as e:
    checks.append(("AI Model", False, str(e)))

# 5. Knowledge base
try:
    from app.ai.vector_store import get_count, list_sources
    count = get_count()
    sources = list_sources()
    checks.append(("Knowledge Base", True, f"{count} chunks, {len(sources)} sources"))
except Exception as e:
    checks.append(("Knowledge Base", False, str(e)))

# 6. Auth system
try:
    from app.security import hash_password, verify_password, create_access_token
    test_hash = hash_password("test123")
    assert verify_password("test123", test_hash)
    token = create_access_token({"sub": "test-user", "org_id": "test-org", "role": "analyst"})
    checks.append(("Auth System", True, "JWT + bcrypt working"))
except Exception as e:
    checks.append(("Auth System", False, str(e)))

# 7. Frontend builds
try:
    import subprocess
    result = subprocess.run(
        ["npx", "tsc", "--noEmit"],
        cwd=r"C:\Users\HP\OneDrive\Desktop\Quantive\frontend",
        capture_output=True, text=True, timeout=60
    )
    ts_errors = result.stdout.count("error TS") + result.stderr.count("error TS")
    checks.append(("Frontend TypeScript", ts_errors == 0, f"{ts_errors} errors"))
except Exception as e:
    checks.append(("Frontend TypeScript", False, str(e)))

# 8. Frontend tests
try:
    result = subprocess.run(
        ["npx", "vitest", "run", "--reporter=verbose"],
        cwd=r"C:\Users\HP\OneDrive\Desktop\Quantive\frontend",
        capture_output=True, text=True, timeout=120
    )
    passed = result.stdout.count("passed")
    checks.append(("Frontend Tests", passed > 0, f"{passed} tests passing"))
except Exception as e:
    checks.append(("Frontend Tests", False, str(e)))

# Report
print()
print("=" * 60)
print("  QUANTIVE DEMO READINESS CHECK")
print("=" * 60)
print()
all_pass = True
for name, ok, detail in checks:
    status = "PASS" if ok else "FAIL"
    icon = "+" if ok else "X"
    print(f"  [{icon}] {name}: {detail}")
    if not ok:
        all_pass = False
print()
print("=" * 60)
if all_pass:
    print("  ALL CHECKS PASSED — DEMO READY")
else:
    print("  SOME CHECKS FAILED — FIX BEFORE DEMO")
print("=" * 60)
