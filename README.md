# TeleporterBot v2 (Core Backend + Bot)

This is a simplified implementation of the TeleporterBot v2 logistics system:

- **FastAPI backend** (orders, riders, warehouses, pricing, routing)
- **PostgreSQL + Redis** for persistence and caching
- **Telegram bot** for customer & rider interactions

The **admin dashboard UI** and **n8n workflows** described in the implementation plan are intentionally **not included** here, as requested.

## Quick start

```bash
cp .env.example .env
pip install -r requirements.txt

# Or via Docker
docker-compose up -d --build
```

API docs will be available at `http://localhost:8000/docs` and the bot will connect to Telegram once the `TELEGRAM_BOT_TOKEN` is configured.

