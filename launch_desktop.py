import subprocess, sys, time, urllib.request, os
from pathlib import Path

ROOT = Path(__file__).parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"

print("Starting backend...")
be = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
    cwd=str(BACKEND),
)

# Wait for backend
for _ in range(30):
    try:
        urllib.request.urlopen("http://127.0.0.1:8000/api/health", timeout=1)
        print("Backend ready!")
        break
    except Exception:
        time.sleep(0.5)
else:
    print("Backend may not be ready")

print("Starting Electron desktop app...")
electron = subprocess.Popen(
    [str(FRONTEND / "node_modules" / ".bin" / "electron.cmd"), "."],
    cwd=str(FRONTEND),
)

try:
    electron.wait()
except KeyboardInterrupt:
    pass
finally:
    electron.terminate()
    be.terminate()
    electron.wait()
    be.wait()
