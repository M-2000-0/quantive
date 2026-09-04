"""Simple SPA server that falls back to index.html for client-side routing."""
import http.server
import os
import sys

PORT = 4173
DIRECTORY = os.path.join(os.path.dirname(__file__), "dist")

class SPAHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_GET(self):
        # Try to serve the file directly
        path = self.translate_path(self.path)
        if os.path.isfile(path):
            return super().do_GET()
        # Fall back to index.html for SPA routing
        self.path = "/index.html"
        return super().do_GET()

    def log_message(self, format, *args):
        pass  # Suppress logs

if __name__ == "__main__":
    with http.server.HTTPServer(("0.0.0.0", PORT), SPAHandler) as httpd:
        print(f"SPA server running on http://localhost:{PORT}")
        sys.stdout.flush()
        httpd.serve_forever()
