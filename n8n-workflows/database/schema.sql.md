# Deprecated — see schemas/database-schema.sql

This file was a stale duplicate of the canonical schema and drifted badly
from the SQL the workflows actually execute (missing tables, renamed
columns, no `workflows` Postgres schema).

**The single source of truth is now [`schemas/database-schema.sql`](../schemas/database-schema.sql).**

```bash
psql -U quantive -d quantive -f schemas/database-schema.sql
```
