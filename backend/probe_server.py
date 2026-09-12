from app.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    conn.execute(text("SELECT 1"))
print("db_ok")
