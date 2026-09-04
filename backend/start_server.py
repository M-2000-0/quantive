"""Launch Quantive backend server as a detached process."""
import subprocess
import sys
import os
import time

py = sys.executable
port = 8000
log_path = os.path.join(os.path.dirname(__file__), "server.log")

print(f"Starting Quantive on http://127.0.0.1:{port} ...")

proc = subprocess.Popen(
    [py, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
    cwd=os.path.dirname(os.path.abspath(__file__)),
    stdout=open(log_path, "w", encoding="utf-8", errors="replace"),
    stderr=subprocess.STDOUT,
    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
)

print(f"Server PID: {proc.pid}")
print(f"Logs: {log_path}")

# Wait for server to be ready
for i in range(45):
    time.sleep(1)
    if proc.poll() is not None:
        print(f"Server exited with code {proc.returncode}")
        try:
            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                print(f.read()[-2000:])
        except Exception as e:
            print(f"Could not read log: {e}")
        sys.exit(1)
    try:
        import urllib.request
        urllib.request.urlopen(f"http://127.0.0.1:{port}/login", timeout=2)
        print("✅ Server is ready!")
        print(f"   Dashboard: http://127.0.0.1:{port}/dashboard")
        print(f"   API Docs:  http://127.0.0.1:{port}/docs")
        sys.exit(0)
    except Exception:
        pass

print("⚠️  Server is starting but not yet responding to HTTP. Check server.log")
