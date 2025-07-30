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

## Deployment

### Local Development

```bash
# Start the full stack locally
docker compose up -d

# Or build and run in one command
docker compose up -d --build
```

### Production (GitHub Actions → AWS ECR → Lightsail)

The CI/CD pipeline automatically deploys on push to `main` branch.

**Required GitHub Secrets:**

```bash
AWS_ACCESS_KEY_ID      # AWS IAM user access key
AWS_SECRET_ACCESS_KEY  # AWS IAM user secret key  
AWS_REGION            # e.g., us-east-1
ECR_REPOSITORY        # ECR repository name
LIGHTSAIL_HOST        # Lightsail instance IP/hostname
LIGHTSAIL_USER        # SSH username (usually ubuntu)
LIGHTSAIL_KEY         # SSH private key for Lightsail access
```

**Stack includes:**
- Bot service (uvicorn on port 8000)
- Cloudflare tunnel (requires TUNNEL_TOKEN in .env)
- Cron backup service (nightly SQLite backups)

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