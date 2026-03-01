# Database Transaction Issues - Fixed

## Problems Identified

### 1. Missing `await db.commit()` Calls
Multiple routers were missing explicit commit statements, relying only on the auto-commit in `get_db()` dependency. This caused data loss when:
- Exceptions occurred before reaching the dependency cleanup
- Sessions closed prematurely
- Docker container restarts happened mid-transaction

### 2. DATABASE_URL Mismatch
Your `.env` file has:
```
DATABASE_URL=postgresql+asyncpg://postgres:8Y6RUWb8Vne8Bx67@squadron123.ddns.net:5432/teleporter
```

But when running **inside Docker**, the API container must use the internal service name:
```
DATABASE_URL=postgresql+asyncpg://postgres:8Y6RUWb8Vne8Bx67@db:5432/teleporter
```

The `squadron123.ddns.net` URL is for **external access only** (from your local machine outside Docker).

## Files Fixed

### ✅ api/routers/orders.py
- Added `await db.commit()` after creating orders (line ~180)
- Added `await db.commit()` after status updates (line ~220)
- Added `await db.commit()` after OTP verification (line ~260)

### ✅ api/routers/riders.py
- Added `await db.commit()` after creating riders (line ~40)
- Added `await db.commit()` after location updates (line ~90)
- Added `await db.commit()` after status updates (line ~110)

### ✅ api/routers/payments.py
- Added `await db.commit()` after payment confirmation (line ~240)
- Added `await db.commit()` after COD collection (line ~320)

### ✅ api/routers/webhooks.py
- Added `await db.commit()` after warehouse intake (line ~70)
- Added `await db.commit()` after route optimization (line ~180)

### ✅ api/routers/users.py
Already had proper commits - no changes needed

### ✅ api/routers/admin.py
Read-only endpoints - no changes needed

### ✅ api/routers/warehouses.py
Read-only endpoints - no changes needed

## How to Fix DATABASE_URL

You have two options:

### Option 1: Use Environment Variable Override (Recommended)
Keep your `.env` file as-is for local development, but override in `docker-compose.yml`:

```yaml
api:
  environment:
    - DATABASE_URL=postgresql+asyncpg://postgres:8Y6RUWb8Vne8Bx67@db:5432/teleporter
```

### Option 2: Separate .env Files
- `.env.local` - for running outside Docker (uses squadron123.ddns.net)
- `.env.docker` - for running inside Docker (uses db:5432)

Update docker-compose.yml:
```yaml
api:
  env_file:
    - .env.docker
```

## Testing the Fix

1. **Restart all containers:**
```bash
docker-compose down
docker-compose up -d
```

2. **Check database connectivity:**
```bash
curl http://localhost:8000/health/db
```

Expected response:
```json
{
  "status": "ok",
  "database": "teleporter",
  "user": "postgres",
  "users_count": 0
}
```

3. **Test order creation:**
```bash
# Create a test user first
curl -X POST http://localhost:8000/api/users/ \
  -H "Content-Type: application/json" \
  -d '{
    "telegram_id": 123456789,
    "full_name": "Test User",
    "phone": "+919876543210"
  }'

# Create an order
curl -X POST http://localhost:8000/api/orders/ \
  -H "Content-Type: application/json" \
  -d '{
    "telegram_id": 123456789,
    "pickup_address": "Maninagar, Ahmedabad",
    "drop_address": "Satellite, Ahmedabad",
    "package_size": "SMALL",
    "description": "Test parcel"
  }'
```

4. **Verify data persists:**
```bash
# List orders
curl http://localhost:8000/api/orders/

# Check in database directly
docker exec -it teleporter-db-1 psql -U postgres -d teleporter -c "SELECT order_number, status FROM orders;"
```

## Root Cause Analysis

The `get_db()` dependency in `api/db/database.py` has this pattern:

```python
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()  # ← Only commits if no exception
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

**Problem:** If the session closes before reaching the auto-commit (due to container restart, network issue, or early return), changes are lost.

**Solution:** Explicit `await db.commit()` after each logical transaction ensures data is persisted immediately.

## Additional Recommendations

1. **Add connection pooling monitoring:**
```python
# In api/main.py
@app.get("/health/db-pool")
async def health_db_pool():
    return {
        "pool_size": engine.pool.size(),
        "checked_in": engine.pool.checkedin(),
        "checked_out": engine.pool.checkedout(),
        "overflow": engine.pool.overflow(),
    }
```

2. **Enable SQL query logging temporarily:**
```python
# In api/db/database.py
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=True,  # ← Enable to see all SQL queries
    pool_pre_ping=True,
)
```

3. **Add transaction retry logic for critical operations:**
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def create_order_with_retry(data, db):
    # Your order creation logic
    await db.commit()
```

## Verification Checklist

- [ ] All containers start successfully
- [ ] `/health/db` endpoint returns "ok"
- [ ] Can create users and they persist after container restart
- [ ] Can create orders and they persist after container restart
- [ ] Order status updates are reflected in database
- [ ] Rider location updates are saved
- [ ] Payment confirmations are recorded
- [ ] No "connection refused" errors in logs
- [ ] No "transaction already closed" errors in logs
