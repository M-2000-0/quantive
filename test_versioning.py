import sys
sys.path.insert(0, r'C:\Users\HP\OneDrive\Desktop\Quantive\backend')
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

# Test health
r = client.get('/api/health')
status = r.status_code
body = r.json()
print(f'Health: {status} OK - {body["status"]}')

# Test v1 background optimize
r = client.post('/api/v1/optimize/background')
print(f'V1 optimize: {r.status_code} - {r.json()}')

# Get job status
job_id = r.json()['job_id']
r = client.get(f'/api/v1/jobs/{job_id}')
print(f'V1 job status: {r.status_code} - {r.json()}')

# Test root-level still works (backward compat)
r2 = client.get('/api/health')
status2 = r2.status_code
print(f'Root health: {status2} OK')

print('\\nAll versioning working!')