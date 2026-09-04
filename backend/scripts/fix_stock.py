
import os

path = os.path.join('docs', 'legal', 'stock_discovery_system.md')
os.makedirs(os.path.dirname(path), exist_ok=True)

# Read existing content up to the cut point
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

marker = '    UNIQUE(ticker, insider_name, transaction_date, shares)\n);\n'
idx = content.index(marker)
keep = content[:idx + len(marker)]

rest = open(os.path.join('..', '..', 'scripts', 'stock_rest.txt'), 'r', encoding='utf-8').read()

with open(path, 'w', encoding='utf-8') as f:
    f.write(keep + rest)

lines = open(path, 'r', encoding='utf-8').readlines()
print(f'Done: {len(lines)} lines')
