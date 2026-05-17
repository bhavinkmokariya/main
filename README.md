# Layer 4 — Webhook Management POC
## Complete Code Documentation
### Owner: Bhavin | Sprint 1 + 2 | FastAPI · MySQL · MongoDB

---

## Table of Contents

1. How to Run Independently (No Teammates Needed)
2. File Structure
3. What Each File Does
4. Seed Scripts Explained
5. MySQL Models Explained
6. Pydantic Schemas Explained
7. All 20 API Endpoints — Request / Response / Logic
8. MongoDB Collections Explained
9. Webhook Ingestion Flow (Step by Step)
10. Alembic Migration Commands
11. Testing with Postman / curl
12. How to Merge Into the Real Project

---

## 1. How to Run Independently

You need **zero** code from other team members to run and test everything.

### Step 1 — Install dependencies

```
pip install fastapi uvicorn sqlalchemy pymysql pymongo httpx python-dotenv bson
```

### Step 2 — Create `.env` file

```
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=yourpassword
MYSQL_DB=acme_db
MONGO_URI=mongodb://localhost:27017
MONGO_DB_NAME=webhook_logs
```

### Step 3 — Seed the parent database

Run this ONCE. It creates users, organizations, and projects tables with test data so your Layer 4 code has parent records to reference.

```
python seed_parent_db.py
```

This will print IDs like:
```
USER_ID    = 1
ORG_ID     = 1
PROJECT_ID = 1
ORG_DB     = acme_db
```

### Step 4 — Test MongoDB

```
python mongo_setup.py
```

This inserts a document into both collections, reads them back, and deletes them. If it prints "✅ MongoDB is working correctly!" you're good.

### Step 5 — Start the standalone test app

```
python standalone_test_app.py
```

Open `http://localhost:8000/docs` — you'll see all 20 endpoints in Swagger UI.

**Important:** For every protected endpoint, add this header in Postman / Swagger:
```
X-User-Id: 1
```
This replaces the real JWT for testing purposes.

---

## 2. File Structure

```
webhook_layer4/
│
├── seed_parent_db.py          ← Creates parent tables + test data
├── standalone_test_app.py     ← Self-contained FastAPI app (run this to test)
├── mongo_setup.py             ← MongoDB client + index setup + test script
│
├── models.py                  ← SQLAlchemy models (copy to real project)
├── schemas.py                 ← Pydantic request/response schemas
├── sources_service_routes.py  ← Sources service layer + FastAPI routes
├── destinations_service_routes.py ← Destinations service + routes
├── connections_service_routes.py  ← Connections service + routes
├── webhook_ingestion_routes.py    ← Public /ingest/{token} endpoint
└── webhook_logs_routes.py         ← Log read endpoints (MongoDB reads)
```

In your real project, these map to:
```
app/modules/sources/          → service.py, routes.py, models.py, schemas.py
app/modules/destinations/     → same pattern
app/modules/connections/      → same pattern
app/modules/webhook_ingestion/→ routes.py (+ request_parser, source_resolver, mongo_writer)
app/modules/webhook_logs/     → routes.py, service.py
```

---

## 3. What Each File Does

| File | What It Does |
|---|---|
| `seed_parent_db.py` | Creates `main_auth_db` and `acme_db`, populates users / organizations / projects so your layer has parent data |
| `standalone_test_app.py` | Complete working FastAPI app — all 20 endpoints, MySQL + MongoDB wired up, fake auth header. Run this to test everything. |
| `mongo_setup.py` | `connect_mongo()` and `get_mongo_db()` for your real project + a test script that verifies both collections |
| `models.py` | SQLAlchemy ORM classes for `sources`, `destinations`, `connections` |
| `schemas.py` | Pydantic models for every request body and response shape |
| `sources_service_routes.py` | 6 Source endpoints — create, list, get, update, delete, toggle |
| `destinations_service_routes.py` | 6 Destination endpoints — same pattern, auth value always masked |
| `connections_service_routes.py` | 6 Connection endpoints — validates cross-project ownership, returns nested objects |
| `webhook_ingestion_routes.py` | The single public endpoint — parses request, writes MongoDB, delivers to destinations |
| `webhook_logs_routes.py` | 3 read-only log endpoints that query MongoDB |

---

## 4. Seed Scripts Explained

### `seed_parent_db.py`

This script creates everything that your teammates would normally create. You need it to work independently.

**What it creates:**

```
main_auth_db
├── users                    → 2 rows (bhavin@acme.com, lead@acme.com)
├── organizations            → 1 row (Acme Corp, database_name=acme_db)
├── organization_members     → 2 rows
└── organization_join_requests (empty)

acme_db
├── projects                 → 1 row (Webhook POC, id=1)
└── project_members          → 1 row
```

**Key output to save:**
```
USER_ID    = 1   ← use this as X-User-Id header in Postman
PROJECT_ID = 1   ← use this in all /api/v1/projects/{project_id}/... URLs
```

**Re-running:** It's safe to run again — it checks for existing seed data and skips if present.

---

## 5. MySQL Models Explained

### `sources` table

| Column | Type | Purpose |
|---|---|---|
| id | BIGINT PK | Auto-increment primary key |
| project_id | BIGINT FK | Which project this source belongs to |
| source_name | VARCHAR(150) | Human name e.g. "Stripe Live" |
| **source_token** | VARCHAR(64) UNIQUE | **Auto-generated** on create using `secrets.token_urlsafe(32)`. This is what makes your ingestion URL work. Never changes after creation. |
| description | TEXT nullable | Optional notes |
| secret_key | VARCHAR(255) nullable | For HMAC verification later. Never logged. |
| is_active | TINYINT | 1 = active, 0 = paused |
| created_by | BIGINT FK → users | Who created it |
| created_at | TIMESTAMP | Auto-set on insert |

**Important:** The old `source_url TEXT` column is removed. The ingestion URL is built at runtime: `/ingest/{source_token}`.

### `destinations` table

| Column | Type | Purpose |
|---|---|---|
| id | BIGINT PK | Primary key |
| project_id | BIGINT FK | Project ownership |
| destination_name | VARCHAR(150) | Human name e.g. "Order Service" |
| destination_url | TEXT | Where events are delivered |
| destination_type | VARCHAR(50) | Always "http" for now |
| auth_header_key | VARCHAR(150) nullable | e.g. "Authorization" |
| **auth_header_value** | VARCHAR(255) nullable | e.g. "Bearer abc123". **Always returned as "****" in API responses.** |
| is_active | TINYINT | 1 = active, 0 = paused |
| created_by | BIGINT FK | Who created it |
| created_at | TIMESTAMP | Auto-set |

### `connections` table

| Column | Type | Purpose |
|---|---|---|
| id | BIGINT PK | Primary key |
| project_id | BIGINT FK | Project ownership |
| connection_name | VARCHAR(150) | Human name e.g. "Stripe to Order Service" |
| **source_id** | BIGINT FK → sources | **Replaces the old `source_identifier TEXT` column** |
| **destination_id** | BIGINT FK → destinations | **Replaces the old `destination_url TEXT` column** |
| is_active | TINYINT | 1 = active, 0 = paused |
| created_by | BIGINT FK | Who created it |
| created_at | TIMESTAMP | Auto-set |

---

## 6. Pydantic Schemas Explained

### Source schemas

- **`SourceCreate`** — request body when creating. Only `source_name` is required.
- **`SourceUpdate`** — request body for PATCH. All fields optional.
- **`SourceResponse`** — what every endpoint returns. Includes `ingestion_url` built at runtime. Never includes `secret_key`.
- **`SourceToggleResponse`** — `{ is_active, message }` from the toggle endpoint.
- **`PaginatedSources`** — `{ items, total, page, per_page }` from the list endpoint.

### Destination schemas

- **`DestinationCreate`** — `destination_name` and `destination_url` required. URL validated to start with http/https.
- **`DestinationResponse`** — always returns `auth_header_value` as `"****"` if set.

### Connection schemas

- **`ConnectionCreate`** — `connection_name`, `source_id`, `destination_id`.
- **`ConnectionResponse`** — includes `source` and `destination` as nested objects, not just IDs.
- **`NestedSource`** — `{ id, source_name }`.
- **`NestedDestination`** — `{ id, destination_name, destination_url }`.

---

## 7. All 20 API Endpoints

### Source Endpoints (6)

---

**POST `/api/v1/projects/{project_id}/sources`**

Creates a new webhook source. Automatically generates a unique token.

Request body:
```json
{
  "source_name": "Stripe Live",
  "description": "Receives payment events",
  "secret_key": "my-hmac-secret"
}
```

Response (201):
```json
{
  "id": 1,
  "project_id": 1,
  "source_name": "Stripe Live",
  "source_token": "abc123...",
  "ingestion_url": "/ingest/abc123...",
  "description": "Receives payment events",
  "is_active": 1,
  "created_by": 1,
  "created_at": "2025-01-01T00:00:00"
}
```

Logic:
1. Generate `source_token` with `secrets.token_urlsafe(32)`
2. Insert row into `sources`
3. Build `ingestion_url` from token and return

---

**GET `/api/v1/projects/{project_id}/sources`**

Returns paginated list of sources in the project.

Query params: `page` (default 1), `per_page` (default 20), `is_active` (optional 0 or 1)

Response (200):
```json
{
  "items": [ ... ],
  "total": 5,
  "page": 1,
  "per_page": 20
}
```

---

**GET `/api/v1/projects/{project_id}/sources/{source_id}`**

Returns full detail of one source. Returns 404 if not found or not in this project.

---

**PATCH `/api/v1/projects/{project_id}/sources/{source_id}`**

Updates `source_name`, `description`, or `secret_key`. The `source_token` and `ingestion_url` are NEVER changed — they are permanent.

Request body (all optional):
```json
{
  "source_name": "Stripe Production",
  "description": "Updated description"
}
```

---

**DELETE `/api/v1/projects/{project_id}/sources/{source_id}`**

Deletes a source. Blocks with 409 if any active connections use this source.

Response 409 (blocked):
```json
{
  "message": "Cannot delete source with active connections",
  "connections": ["Stripe to Order Service", "Stripe to Notifications"]
}
```

Response 200 (success):
```json
{ "message": "Source deleted successfully" }
```

Logic: Also deletes all orphaned (inactive) connections for this source.

---

**POST `/api/v1/projects/{project_id}/sources/{source_id}/toggle`**

Pauses or resumes a source. Toggle means: if active → pause, if paused → resume.

Response:
```json
{ "is_active": 0, "message": "Source paused." }
```

Important: When paused, the ingestion URL still returns 200 but marks the request as `rejected` in MongoDB.

---

### Destination Endpoints (6)

---

**POST `/api/v1/projects/{project_id}/destinations`**

Creates a destination. Auth value is masked in the response.

Request:
```json
{
  "destination_name": "Order Service",
  "destination_url": "https://myapp.com/webhooks",
  "auth_header_key": "Authorization",
  "auth_header_value": "Bearer secrettoken123"
}
```

Response (201): `auth_header_value` is returned as `"****"`.

---

**GET `/api/v1/projects/{project_id}/destinations`**

Paginated list. `auth_header_value` always masked.

---

**GET `/api/v1/projects/{project_id}/destinations/{destination_id}`**

Full detail. Auth value masked.

---

**PATCH `/api/v1/projects/{project_id}/destinations/{destination_id}`**

Updates any field. If `auth_header_value` is sent, it overwrites the old one.

---

**DELETE `/api/v1/projects/{project_id}/destinations/{destination_id}`**

Blocks with 409 if active connections use this destination. Same pattern as source delete.

---

**POST `/api/v1/projects/{project_id}/destinations/{destination_id}/toggle`**

Pause or resume. When paused, connections pointing to this destination are skipped during delivery.

---

### Connection Endpoints (6)

---

**POST `/api/v1/projects/{project_id}/connections`**

Links a source to a destination. Both must belong to this project.

Request:
```json
{
  "connection_name": "Stripe to Order Service",
  "source_id": 1,
  "destination_id": 1
}
```

Validations:
- `source_id` must belong to `project_id` → 400 if not
- `destination_id` must belong to `project_id` → 400 if not
- No duplicate connection for same source+destination pair → 409 if exists

Response (201): Full connection with nested source and destination objects.

---

**GET `/api/v1/projects/{project_id}/connections`**

List with nested source/destination. Optional filters: `source_id`, `is_active`.

Response item:
```json
{
  "id": 1,
  "connection_name": "Stripe to Order Service",
  "source": { "id": 1, "source_name": "Stripe Live" },
  "destination": { "id": 1, "destination_name": "Order Service", "destination_url": "https://..." },
  "is_active": 1
}
```

---

**GET `/api/v1/projects/{project_id}/connections/{connection_id}`**

Full detail with nested source and destination.

---

**PATCH `/api/v1/projects/{project_id}/connections/{connection_id}`**

Updates `connection_name` only. Source and destination cannot be changed — delete and recreate instead.

---

**DELETE `/api/v1/projects/{project_id}/connections/{connection_id}`**

Deletes the link only. Source and destination still exist.

---

**POST `/api/v1/projects/{project_id}/connections/{connection_id}/toggle`**

Pause or resume a connection.

---

### Public Ingestion Endpoint (1 — NO JWT)

---

**ANY `/ingest/{source_token}`**

The only public endpoint. No authentication required. Accepts all HTTP methods.

Request: Any HTTP method. Any body. Any content-type. Any headers.

Response (always 200 unless source_token not found):
```json
{
  "request_id": "64a1b2c3d4e5f6789abcdef0",
  "status": "received"
}
```

Response header: `X-Request-Id: 64a1b2c3d4e5f6789abcdef0`

Status values:
- `received` — source was active, event stored, delivery attempted
- `rejected` — source was paused, event stored but not delivered
- `no_connection` — source active but no connections configured

Only returns 404 if the `source_token` is completely unknown.

See Section 9 for the full step-by-step flow.

---

### Log Read Endpoints (3)

---

**GET `/api/v1/projects/{project_id}/requests`**

Paginated list of incoming webhook requests from MongoDB `raw_webhook_events`.

Query params: `page`, `per_page`, `source_id`, `status` (received/rejected/no_connection), `date_from`, `date_to`

Returns lightweight items (no headers or payload — those are in the detail endpoint):
```json
{
  "items": [
    {
      "id": "64a1b2c3...",
      "source_name": "Stripe Live",
      "request_method": "POST",
      "status": "received",
      "received_at": "2025-01-01T10:00:00"
    }
  ],
  "total": 42,
  "page": 1,
  "per_page": 20
}
```

---

**GET `/api/v1/projects/{project_id}/requests/{request_id}`**

Full detail of one webhook request. `request_id` is the MongoDB ObjectId string.

Returns everything — all headers, full payload, and all delivery attempts linked to this event:
```json
{
  "id": "64a1b2c3...",
  "source_name": "Stripe Live",
  "request_method": "POST",
  "sender_ip": "54.187.174.169",
  "headers": { "content-type": "application/json", ... },
  "payload": { "type": "payment_intent.succeeded", ... },
  "status": "received",
  "received_at": "...",
  "attempts": [
    {
      "destination_url": "https://myapp.com/webhooks",
      "status": "SUCCESS",
      "response_code": 200,
      "latency_ms": 245,
      "attempted_at": "..."
    }
  ]
}
```

---

**GET `/api/v1/projects/{project_id}/delivery-attempts`**

Paginated list of delivery attempts. Filter by `destination_id` or `status`.

Useful for seeing all attempts made to a specific destination.

---

## 8. MongoDB Collections Explained

### `raw_webhook_events`

One document per incoming webhook. Written BEFORE the 200 response is returned — this is the durability guarantee.

Key fields:
- `_id` — MongoDB ObjectId. This becomes the `request_id` returned to the caller.
- `source_id` — MySQL ID of the matching source (set from token lookup)
- `source_name` — Denormalized name (avoid joins when showing logs)
- `status` — `received` | `rejected` | `no_connection`
- `request_method` — GET, POST, PUT, etc.
- `sender_ip` — Extracted from X-Forwarded-For or client IP
- `headers` — All incoming headers as object
- `payload` — Parsed JSON object (or raw string if not JSON)

Indexes:
- `(source_id, received_at)` — for filtering by source and time
- `(project_id, received_at)` — for project-wide log views
- `(status)` — for filtering by outcome

### `delivery_attempts`

One document per delivery attempt to one destination.

Key fields:
- `event_id` — ObjectId reference to `raw_webhook_events._id`
- `status` — `SUCCESS` | `FAILED`
- `response_code` — HTTP status code from destination (null if network error)
- `latency_ms` — How long the HTTP call took
- `error_message` — Exception message if delivery failed (timeout, DNS, etc.)
- `destination_url` — The URL that was called (stored because destination URL might change)

Indexes:
- `(event_id)` — for finding all attempts for one event
- `(project_id, attempted_at)` — for project log views
- `(destination_id)` — for destination-side filtering

---

## 9. Webhook Ingestion Flow (Step by Step)

```
External Sender (Stripe, GitHub, etc.)
         |
         | HTTP POST /ingest/{source_token}
         ↓
[1] Look up Source by source_token in MySQL
    IF NOT FOUND → return 404

[2] Parse full request:
    - method, headers, raw body, content-type
    - query string, sender_ip, timestamp

[3] Write raw_webhook_events to MongoDB ← DURABILITY GUARANTEE
    status = "received" at this point
    (This happens BEFORE we return any response)

[4] Is source.is_active == 0?
    YES → update MongoDB status = "rejected"
        → return 200 { request_id, status: "rejected" }
    NO  → continue

[5] Find all active Connections WHERE source_id = X in MySQL

[6] No connections?
    YES → update MongoDB status = "no_connection"
        → return 200 { request_id, status: "no_connection" }
    NO  → continue

[7] For each Connection:
      Load destination from MySQL
      If destination.is_active == 0 → skip this destination

      HTTP POST to destination_url (10-second timeout)
      Add auth header if auth_header_key is set

      Write delivery_attempts document to MongoDB:
        status, response_code, latency_ms, error_message

[8] Return 200 OK
    Body: { request_id: "...", status: "received" }
    Header: X-Request-Id: <mongo_object_id>
```

**Why always return 200?**
The external sender (Stripe, GitHub, etc.) expects a 200 ACK quickly. If you return non-200, they may retry the same event. We acknowledge receipt immediately and handle delivery internally.

**Why write to MongoDB before returning?**
If the server crashes after the 200 but before writing to MongoDB, the event is lost. Writing first guarantees durability — if the document exists, the event was received.

---

## 10. Alembic Migration Commands

After your teammates set up Alembic, register your models in `alembic/env.py`:

```python
from app.modules.sources.models import Source
from app.modules.destinations.models import Destination
from app.modules.connections.models import Connection
```

Then run:

```bash
# Generate migration (detects your new tables)
alembic revision --autogenerate -m "add_sources_destinations_connections"

# Apply migration
alembic upgrade head

# Verify in MySQL
mysql -u root -p acme_db -e "DESCRIBE sources; DESCRIBE destinations; DESCRIBE connections;"
```

---

## 11. Testing with Postman / curl

### Setup

1. Base URL: `http://localhost:8000`
2. For protected endpoints add header: `X-User-Id: 1`
3. Content-Type: `application/json`

Use the IDs printed by `seed_parent_db.py` (PROJECT_ID=1, USER_ID=1).

### Full end-to-end test sequence

```bash
# 1. Create a source
curl -X POST http://localhost:8000/api/v1/projects/1/sources \
  -H "Content-Type: application/json" \
  -H "X-User-Id: 1" \
  -d '{"source_name": "Stripe Live", "description": "Test source"}'

# Note the source_token from the response, e.g. "abc123xyz"

# 2. Create a destination (use webhook.site for real testing)
curl -X POST http://localhost:8000/api/v1/projects/1/destinations \
  -H "Content-Type: application/json" \
  -H "X-User-Id: 1" \
  -d '{
    "destination_name": "webhook.site test",
    "destination_url": "https://webhook.site/YOUR-UUID-HERE"
  }'

# Note the destination id from the response, e.g. 1

# 3. Create a connection
curl -X POST http://localhost:8000/api/v1/projects/1/connections \
  -H "Content-Type: application/json" \
  -H "X-User-Id: 1" \
  -d '{"connection_name": "Stripe to webhook.site", "source_id": 1, "destination_id": 1}'

# 4. Send a test webhook (public, no auth header needed)
curl -X POST http://localhost:8000/ingest/abc123xyz \
  -H "Content-Type: application/json" \
  -d '{"type": "payment.received", "amount": 5000}'

# Should return: {"request_id": "64a...", "status": "received"}

# 5. View the log
curl http://localhost:8000/api/v1/projects/1/requests \
  -H "X-User-Id: 1"

# 6. View full detail with delivery attempt
curl http://localhost:8000/api/v1/projects/1/requests/64a... \
  -H "X-User-Id: 1"

# 7. Test paused source
curl -X POST http://localhost:8000/api/v1/projects/1/sources/1/toggle \
  -H "X-User-Id: 1"

curl -X POST http://localhost:8000/ingest/abc123xyz \
  -H "Content-Type: application/json" \
  -d '{"type": "test.paused"}'
# status should be "rejected"

# 8. Toggle source back on and toggle connection off
curl -X POST http://localhost:8000/api/v1/projects/1/sources/1/toggle \
  -H "X-User-Id: 1"

curl -X POST http://localhost:8000/api/v1/projects/1/connections/1/toggle \
  -H "X-User-Id: 1"

curl -X POST http://localhost:8000/ingest/abc123xyz \
  -H "Content-Type: application/json" \
  -d '{"type": "test.no_connection"}'
# status should be "no_connection"
```

### Testing DELETE validations

```bash
# Try to delete a source that has an active connection → should get 409
curl -X DELETE http://localhost:8000/api/v1/projects/1/sources/1 \
  -H "X-User-Id: 1"

# First delete the connection, then delete the source
curl -X DELETE http://localhost:8000/api/v1/projects/1/connections/1 \
  -H "X-User-Id: 1"

curl -X DELETE http://localhost:8000/api/v1/projects/1/sources/1 \
  -H "X-User-Id: 1"
```

---

## 12. How to Merge Into the Real Project

When the team is ready to integrate, here is exactly what to do.

### Step 1 — Copy models to the right files

```
models.py → split into:
  app/modules/sources/models.py      (Source class only)
  app/modules/destinations/models.py (Destination class only)
  app/modules/connections/models.py  (Connection class only)
```

Change the `Base` import at the top of each to use the shared project base:
```python
# Remove this line:
from sqlalchemy.orm import declarative_base
Base = declarative_base()

# Add this instead:
from app.database import Base
```

### Step 2 — Register models in Alembic

In `alembic/env.py`, add:
```python
from app.modules.sources.models import Source
from app.modules.destinations.models import Destination
from app.modules.connections.models import Connection
```

### Step 3 — Replace fake auth with real JWT

In `sources_service_routes.py`, `destinations_service_routes.py`, `connections_service_routes.py`:
```python
# Replace:
# current_user_id: int = Depends(get_current_user_id)  ← your fake version

# With the real auth module's dependency:
from app.modules.auth.dependencies import get_current_user
```

### Step 4 — Replace get_db

Replace the local `get_db` with the project's shared database dependency from `app.dependencies`.

### Step 5 — Wire up routes in main.py

```python
from app.modules.sources.routes import router as sources_router
from app.modules.destinations.routes import router as destinations_router
from app.modules.connections.routes import router as connections_router
from app.modules.webhook_ingestion.routes import router as ingestion_router
from app.modules.webhook_logs.routes import router as logs_router

app.include_router(sources_router)
app.include_router(destinations_router)
app.include_router(connections_router)
app.include_router(ingestion_router)
app.include_router(logs_router)
```

### Step 6 — MongoDB wiring

Add to `app/mongo.py` (or use the file from `mongo_setup.py`):
```python
from app.mongo import connect_mongo

@app.on_event("startup")
async def startup():
    connect_mongo()
```

---

*Layer 4 Module — Internal Document | Bhavin | Sprint 1 + 2*
