#!/usr/bin/env python3
"""
Quantive Desktop — Native Glassmorphism Launcher

Uses PyQt5 + OS-level Acrylic/Blur for true glass effects.
The web app renders inside a native glass window.

Requirements:
    pip install PyQt5

Usage:
    python desktop.py                  # Start on port 8000
    python desktop.py --port 3000      # Custom port
"""

import argparse
import os
import sys
import subprocess
import threading
import time
from pathlib import Path


def check_pyqt5():
    """Check if PyQt5 is installed, offer to install it."""
    try:
        from PyQt5.QtWidgets import QApplication
        return True
    except ImportError:
        print("[SETUP] PyQt5 not found. Installing...")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "PyQt5", "--quiet"],
            stdout=subprocess.DEVNULL,
        )
        return True


def start_backend(port: int):
    """Start the FastAPI backend in a background thread."""
    backend_dir = Path(__file__).parent / "backend"
    os.environ.setdefault("ENVIRONMENT", "development")

    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app",
         "--host", "127.0.0.1", "--port", str(port)],
        cwd=str(backend_dir),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return proc


def try_native_blur(window):
    """Attempt to apply native OS blur effect."""
    try:
        import ctypes
        from ctypes import wintypes

        if sys.platform == "win32":
            # Windows 10/11 Acrylic blur
            hwnd = int(window.winId())
            import ctypes.wintypes as wintypes

            # DWMWA_SYSTEMBACKDROP_TYPE = 38 (Windows 11)
            # DWMSBT_MAINWINDOW = 2 (Acrylic)
            try:
                DWMWA_SYSTEMBACKDROP_TYPE = 38
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, DWMWA_SYSTEMBACKDROP_TYPE,
                    ctypes.byref(ctypes.c_int(2)),
                    ctypes.sizeof(ctypes.c_int),
                )
            except Exception:
                # Fallback: DWMWA_BLURBEHIND = 2
                class DWM_BLURBEHIND(ctypes.Structure):
                    _fields_ = [
                        ("dwFlags", wintypes.DWORD),
                        ("fEnable", wintypes.BOOL),
                        ("hRgnBlur", wintypes.HANDLE),
                        ("fTransitionOnMaximized", wintypes.BOOL),
                    ]

                bb = DWM_BLURBEHIND()
                bb.dwFlags = 0x03  # DWMBB_ENABLE | DWMBB_BLURREGION
                bb.fEnable = True
                ctypes.windll.dwmapi.DwmEnableBlurBehindWindow(
                    hwnd, ctypes.byref(bb)
                )
            return True

        elif sys.platform == "darwin":
            # macOS vibrancy (requires objc)
            try:
                import objc
                from AppKit import NSVisualEffectView, NSWindow

                window.setAttribute(113, True)  # WA_TranslucentBackground
                return True
            except Exception:
                return False

    except Exception:
        return False


def create_glass_window(port: int):
    """Create the main glassmorphic desktop window."""
    from PyQt5.QtCore import Qt, QUrl, QTimer
    from PyQt5.QtGui import QColor, QFont, QPalette
    from PyQt5.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout,
        QHBoxLayout, QLabel, QPushButton, QStatusBar,
    )
    from PyQt5.QtWebEngineWidgets import QWebEngineView
    from PyQt5.QtWebEngineCore import QWebEngineSettings

    class GlassWindow(QMainWindow):
        def __init__(self, url: str):
            super().__init__()
            self.setWindowTitle("Quantive — Sovereign Financial Optimization")
            self.setMinimumSize(1200, 800)
            self.resize(1440, 900)

            # Dark background
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #0a0b0e;
                }
                QStatusBar {
                    background: rgba(16, 18, 22, 0.9);
                    color: #8590a0;
                    border-top: 1px solid rgba(255,255,255,0.05);
                    font-size: 11px;
                }
            """)

            # Central widget
            central = QWidget()
            central.setStyleSheet("background: transparent;")
            self.setCentralWidget(central)

            layout = QVBoxLayout(central)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)

            # Custom title bar
            titlebar = QWidget()
            titlebar.setFixedHeight(36)
            titlebar.setStyleSheet("""
                QWidget {
                    background: rgba(10, 11, 14, 0.85);
                    border-bottom: 1px solid rgba(255,255,255,0.05);
                }
            """)

            tb_layout = QHBoxLayout(titlebar)
            tb_layout.setContentsMargins(12, 0, 8, 0)

            # Logo
            logo = QLabel("Q")
            logo.setStyleSheet("""
                color: #c8a951;
                font-size: 14px;
                font-weight: 700;
                padding: 0 8px;
            """)
            tb_layout.addWidget(logo)

            # Title
            title = QLabel("QUANTIVE")
            title.setStyleSheet("""
                color: #8590a0;
                font-size: 11px;
                font-weight: 600;
                letter-spacing: 2px;
            """)
            tb_layout.addWidget(title)

            tb_layout.addStretch()

            # Window controls (custom)
            for color, hover in [("#515c6d", "#8590a0"), ("#515c6d", "#c8a951"), ("#515c6d", "#ef4444")]:
                btn = QPushButton("—" if hover == "#8590a0" else ("□" if hover == "#c8a951" else "×"))
                btn.setFixedSize(32, 28)
                btn.setCursor(Qt.PointingHandCursor)
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: transparent;
                        color: {color};
                        border: none;
                        font-size: 13px;
                        border-radius: 4px;
                    }}
                    QPushButton:hover {{
                        background: rgba(255,255,255,0.06);
                        color: {hover};
                    }}
                """)
                if hover == "#ef4444":
                    btn.clicked.connect(self.close)
                elif hover == "#c8a951":
                    btn.clicked.connect(self._toggle_maximize)
                else:
                    btn.clicked.connect(self.showMinimized)
                tb_layout.addWidget(btn)

            layout.addWidget(titlebar)

            # Web view
            self.web = QWebEngineView()
            self.web.setUrl(QUrl(url))
            self.web.setStyleSheet("background: #0a0b0e;")

            # Enable dark mode for web content
            settings = self.web.settings()
            settings.setAttribute(QWebEngineSettings.LocalStorageEnabled, True)
            settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
            settings.setAttribute(QWebEngineSettings.PluginsEnabled, True)

            layout.addWidget(self.web)

            # Status bar
            self.statusBar().showMessage(f"Connected to {url}")

            # Try native blur
            try_native_blur(self)

        def _toggle_maximize(self):
            if self.isMaximized():
                self.showNormal()
            else:
                self.showMaximized()

    # Create and show window
    window = GlassWindow(f"http://127.0.0.1:{port}")
    window.show()
    return window


def main():
    parser = argparse.ArgumentParser(description="Quantive Desktop — Native Glassmorphism")
    parser.add_argument("--port", type=int, default=8000, help="Port (default: 8000)")
    args = parser.parse_args()

    print()
    print("  ========================================")
    print("     QUANTIVE DESKTOP  v2.1.0")
    print("     Native Glassmorphism Edition")
    print("  ========================================")
    print()

    # Check dependencies
    check_pyqt5()

    # Check for QWebEngine
    try:
        from PyQt5.QtWebEngineWidgets import QWebEngineView
    except ImportError:
        print("[SETUP] PyQtWebEngine not found. Installing...")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "PyQtWebEngine", "--quiet"],
            stdout=subprocess.DEVNULL,
        )

    # Start backend
    print(f"  Starting backend on port {args.port}...")
    backend = start_backend(args.port)

    # Wait for backend to be ready
    import urllib.request
    for i in range(30):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{args.port}/api/health", timeout=1)
            break
        except Exception:
            time.sleep(0.5)
    else:
        print("  [WARN] Backend may not be ready yet")

    print("  Opening desktop window...")

    # Start Qt app
    app = QApplication(sys.argv)
    app.setApplicationName("Quantive")
    app.setOrganizationName("Quantive")

    # Dark palette
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(10, 11, 14))
    palette.setColor(QPalette.WindowText, QColor(232, 234, 237))
    palette.setColor(QPalette.Base, QColor(16, 18, 22))
    palette.setColor(QPalette.AlternateBase, QColor(22, 24, 30))
    palette.setColor(QPalette.Text, QColor(232, 234, 237))
    palette.setColor(QPalette.Button, QColor(22, 24, 30))
    palette.setColor(QPalette.ButtonText, QColor(232, 234, 237))
    palette.setColor(QPalette.Highlight, QColor(200, 169, 81))
    palette.setColor(QPalette.HighlightedText, QColor(10, 11, 14))
    app.setPalette(palette)

    window = create_glass_window(args.port)

    # Cleanup on exit
    def cleanup():
        backend.terminate()
        backend.wait()

    app.aboutToQuit.connect(cleanup)
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
