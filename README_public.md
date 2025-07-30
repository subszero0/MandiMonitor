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

## Docker Deployment

```bash
docker compose up --build
```

## Testing

```bash
poetry run pytest
```

## License

MIT License - see LICENSE file for details.

---

*For development documentation and detailed setup instructions, see private documentation.*