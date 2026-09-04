import os
os.makedirs("docs/legal", exist_ok=True)
content = open("docs/legal/stock_discovery_template.txt", "r").read()
with open("docs/legal/stock_discovery_system.md", "w") as out:
    out.write(content)
print(f"Written {len(content)} chars")
