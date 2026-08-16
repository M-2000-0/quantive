# Quantive Backend

B2B SaaS platform for blockchain compliance and transaction risk monitoring.

## Architecture

```
┌─────────────┐     ┌──────────┐     ┌────────────┐
│   Clients   │────▶│  API     │────▶│ PostgreSQL │
│ (REST/WS)   │     │ (Express)│     │ (Prisma)   │
└─────────────┘     └────┬─────┘     └────────────┘
                         │                   
                    ┌────▼─────┐     ┌────────────┐
                    │  Redis   │────▶│  BullMQ    │
                    │ (Queue)  │     │ (Workers)  │
                    └──────────┘     └────┬───────┘
                                          │
                                   ┌──────▼──────┐
                                   │   MinIO/S3  │
                                   │  (Reports)  │
                                   └─────────────┘
```

## Tech Stack

- **Runtime**: Node.js + TypeScript
- **Framework**: Express.js
- **Database**: PostgreSQL 16 + Prisma ORM
- **Queue**: Redis + BullMQ
- **Storage**: S3-compatible (MinIO for dev)
- **Auth**: JWT + Refresh Tokens
- **Logging**: Pino with trace IDs

## Quick Start

```bash
# Install dependencies
npm install

# Start infrastructure
docker compose up -d

# Generate Prisma client
npm run db:generate

# Run migrations
npm run db:migrate

# Seed demo data
npm run db:seed

# Start dev server
npm run dev
```

## Environment Variables

Copy `.env.example` to `.env` and configure:

| Variable | Default | Description |
|---|---|---|
| `PORT` | 4000 | API server port |
| `DATABASE_URL` | postgresql://quantive:quantive@localhost:5432/quantive | PostgreSQL |
| `REDIS_URL` | redis://localhost:6379 | Redis connection |
| `JWT_SECRET` | - | JWT signing secret |
| `JWT_REFRESH_SECRET` | - | Refresh token secret |
| `S3_ENDPOINT` | http://localhost:9000 | S3-compatible endpoint |
| `ENCRYPTION_KEY` | - | 32-byte hex for AES-256 |

## API Endpoints

### Authentication
| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/auth/register` | Register organization |
| POST | `/api/v1/auth/login` | Login |
| POST | `/api/v1/auth/refresh` | Refresh tokens |
| POST | `/api/v1/auth/logout` | Logout |
| GET | `/api/v1/auth/me` | Current user |

### Transactions
| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/transactions` | List transactions |
| GET | `/api/v1/transactions/:id` | Get transaction |
| POST | `/api/v1/transactions/ingest` | Ingest single tx |
| POST | `/api/v1/transactions/ingest-batch` | Batch ingest (auto-queues >100) |

### Wallets
| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/transactions/wallets/list` | List wallets |
| GET | `/api/v1/transactions/wallets/:id` | Get wallet detail |
| PATCH | `/api/v1/transactions/wallets/:id/tags` | Update tags |

### Alerts
| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/alerts` | List alerts |
| GET | `/api/v1/alerts/:id` | Get alert |
| PATCH | `/api/v1/alerts/:id/status` | Acknowledge/dismiss |

### Cases
| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/cases` | List cases |
| GET | `/api/v1/cases/:id` | Get case with alerts + comments |
| POST | `/api/v1/cases` | Create case from alerts |
| PATCH | `/api/v1/cases/:id` | Update/assign/close case |
| POST | `/api/v1/cases/:id/comments` | Add comment |

### Reports
| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/reports` | List generated reports |
| POST | `/api/v1/reports/generate` | Generate report |

### Admin
| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/admin/dashboard` | Dashboard stats |
| GET | `/api/v1/admin/organization` | Org settings |
| GET/POST/PATCH | `/api/v1/admin/users` | User management |
| GET/POST | `/api/v1/admin/roles` | Role management |
| GET | `/api/v1/admin/audit-logs` | Audit trail |
| GET/POST/DELETE | `/api/v1/admin/webhooks` | Webhook endpoints |
| GET/POST | `/api/v1/admin/integrations` | Integrations |

## Event Flow

```
Blockchain ──▶ Ingestion API ──▶ Normalize ──▶ Risk Scoring (Rules)
                                                   │
                                           ┌───────▼───────┐
                                           │  Score < 0.5  │──▶ Store transaction
                                           │  Score ≥ 0.5  │──▶ Create Alert
                                           └───────┬───────┘
                                                   │
                                           ┌───────▼───────┐
                                           │  Analyst       │
                                           │  Reviews Alert │
                                           └───────┬───────┘
                                                   │
                                      ┌────────────┴────────────┐
                                      │ Dismiss    │ Create Case│
                                      └────────────┴─────┬──────┘
                                                          │
                                                  ┌──────▼──────┐
                                                  │ Investigate │
                                                  │ Close/Report│
                                                  └─────────────┘
```

## Security

- **JWT** access + refresh tokens with short expiry
- **bcrypt** (12 rounds) for password hashing
- **Helmet** security headers
- **Rate limiting** per IP
- **Multi-tenant** data isolation (org scoping on every query)
- **RBAC** permissions checked per endpoint
- **Input validation** via Zod schemas
- **Encryption at rest** for sensitive integration configs
- **Audit logs** for every state change
- **Trace IDs** end-to-end request tracking

## Key Design Decisions (MVP Scope)

- Rule-based risk scoring first; AI integration point reserved for future
- Maximum alert/case auto-linking but never auto-close without human review
- Each risk flag includes a reason code for explainability
- Queue-based processing for large batches and PDF generation
- Immutable audit log (append-only via Prisma)
