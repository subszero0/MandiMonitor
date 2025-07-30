# MandiMonitor Bot

A Telegram bot for monitoring product prices and deals.

## Features

- Price monitoring for e-commerce products
- Telegram integration for notifications
- Database storage for user preferences
- Admin interface for management

## Tech Stack

- Python 3.12+
- FastAPI
- SQLModel
- Docker
- Telegram Bot API

## Quick Start

1. Install dependencies:
   ```bash
   poetry install
   ```

2. Configure environment:
   ```bash
   cp .env.example .env
   # Add your configuration to .env
   ```

3. Run the application:
   ```bash
   poetry run python -m bot.main
   ```

4. Access admin interface:
   ```bash
   FLASK_APP=bot.admin_app flask run
   ```

## Docker Deployment

```bash
docker compose up --build
```

## Testing

```bash
poetry run pytest
```

## Monitoring & Back-ups

Set up nightly database backups with cron:

```bash
# cron
0 2 * * * /home/ubuntu/scripts/backup_db.sh
```

Health endpoint for uptime monitoring:
- GET `/health` returns `200 OK "ok"`
- No authentication required
- Lightweight (no database access)

## License

MIT License - see LICENSE file for details.

---

*For development documentation and detailed setup instructions, see private documentation.*