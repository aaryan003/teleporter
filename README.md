# TeleporterBot v2 — Hub-and-Spoke Logistics Platform

> Telegram Bot-powered delivery management system with n8n automation, 
> warehouse hub model, route optimization, and AI-powered admin dashboard.

## 🏗️ Architecture

```
User → Telegram Bot → FastAPI → n8n Automation → Route Optimizer (OR-Tools)
                                    ↓
Admin Dashboard ← WebSocket ← PostgreSQL + Redis
```

**Key Innovation**: Hub-and-spoke model where parcels flow through a central warehouse,
enabling batched route optimization that reduces delivery costs by 15-30%.

## 🚀 Quick Start

```bash
# 1. Clone and configure
git clone <repo-url> && cd teleporter
cp .env.example .env
# Edit .env with your API keys

# 2. Launch the full stack
docker-compose up -d

# 3. Verify
docker-compose ps   # All 6 services should be running
```

### Access Points
| Service | URL |
|---------|-----|
| API Docs | http://localhost:8000/docs |
| n8n Dashboard | http://localhost:5678 |
| Admin Dashboard | http://localhost:3000 |
| Bot | Search your bot on Telegram |

## 📦 Tech Stack

| Layer | Technology |
|-------|-----------|
| Bot | aiogram 3.x (Python) |
| Backend | FastAPI + Pydantic + SQLAlchemy |
| Database | PostgreSQL 15 |
| Cache | Redis 7 |
| Automation | n8n |
| Route Optimization | Google OR-Tools |
| Maps | Google Maps API |
| Payments | Razorpay (test mode) |
| Dashboard | React 18 + Tailwind CSS |
| AI Insights | OpenAI GPT-4o-mini |
| Deployment | Docker Compose |

## 📐 System Design

### Parcel Lifecycle
```
ORDER_PLACED → PAYMENT_CONFIRMED → PICKUP_SCHEDULED 
→ PICKUP_RIDER_ASSIGNED → PICKED_UP → AT_WAREHOUSE 
→ ROUTE_OPTIMIZED → DELIVERY_RIDER_ASSIGNED → OUT_FOR_DELIVERY 
→ DELIVERED → COMPLETED
```

### Revenue Model (5 Streams)
1. **Base pricing**: Distance × Rate × Vehicle × Time factor
2. **Subscriptions**: Starter (₹99) / Business (₹499) / Enterprise (₹1,999)
3. **Smart batching discount**: 15% off for flexible timing
4. **Surge pricing**: Dynamic demand/supply ratio (30% to riders)
5. **Value-added services**: Priority, insurance, photo proof, returns

### n8n Automation Workflows
10 automated workflows handle order intake, payment processing, 
pickup scheduling, warehouse intake, route optimization, delivery 
tracking, return-trip pickups, daily analytics, rider health checks, 
and surge pricing updates.

## 🧪 Running Tests

```bash
# Install test dependencies
pip install pytest

# Run all tests
cd teleporter
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_pricing.py -v
python -m pytest tests/test_route_optimizer.py -v
python -m pytest tests/test_pickup_scheduler.py -v
```

## 📁 Project Structure

```
teleporter/
├── docker-compose.yml          # Full stack (6 services)
├── .env.example                # Environment template
├── api/                        # FastAPI backend
│   ├── main.py                 # App entry point
│   ├── models/                 # SQLAlchemy ORM models
│   ├── schemas/                # Pydantic request/response
│   ├── services/               # Business logic
│   │   ├── pricing.py          # 5-stream revenue engine
│   │   ├── route_optimizer.py  # OR-Tools VRP solver
│   │   ├── pickup_scheduler.py # Smart slot management
│   │   ├── maps.py             # Google Maps + caching
│   │   ├── otp.py              # Bcrypt OTP service
│   │   ├── ai_analytics.py     # OpenAI insights
│   │   └── notifications.py    # Telegram push
│   └── routers/                # API endpoints (7 routers)
├── bot/                        # Telegram bot (aiogram 3.x)
│   ├── handlers/user.py        # Booking flow
│   └── handlers/rider.py       # Task management
├── dashboard/                  # React admin dashboard
├── db/                         # Schema + seed data
├── n8n/workflows/              # Automation definitions
└── tests/                      # Pytest test suite
```

## 🔑 Environment Variables

See [.env.example](.env.example) for the full list. Key ones:
- `TELEGRAM_BOT_TOKEN` — From @BotFather
- `GOOGLE_MAPS_API_KEY` — Geocoding + Distance Matrix APIs
- `RAZORPAY_KEY_ID/SECRET` — Test mode keys
- `OPENAI_API_KEY` — For AI dashboard insights

## 📄 License

MIT
