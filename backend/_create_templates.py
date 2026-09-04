
import os
d = "app/templates/pages"

templates = {}
for fname in ["hybrid-workflow.html", "circuit-designer.html", "algorithm-marketplace.html", "error-correction.html", "quantum-simulator.html"]:
    path = os.path.join(d, fname)
    if not os.path.exists(path):
        print(f"Need to create: {fname}")
    else:
        print(f"Exists: {fname}")
