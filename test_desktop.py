import sys
print("Python OK")
try:
    from PyQt5.QtWidgets import QApplication
    print("PyQt5 OK")
except Exception as e:
    print(f"PyQt5 FAIL: {e}")
try:
    from PyQt5.QtWebEngineWidgets import QWebEngineView
    print("WebEngine OK")
except Exception as e:
    print(f"WebEngine FAIL: {e}")

app = QApplication(sys.argv)
print("App created OK")
from PyQt5.QtCore import QUrl
from PyQt5.QtWebEngineWidgets import QWebEngineView
w = QWebEngineView()
w.resize(1200, 800)
w.load(QUrl("http://127.0.0.1:8000"))
w.show()
print("Window shown!")
sys.exit(app.exec_())
