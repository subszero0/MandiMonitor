# MandiMonitor Bot 2.0

An intelligent Telegram bot for comprehensive e-commerce price monitoring and deal discovery, powered by Amazon PA-API 5.0.

## ✨ Features

### 🎯 Intelligent Price Monitoring
- **Smart Watch Creation**: AI-powered watch creation with intent detection and parameter optimization
- **Advanced Price Tracking**: 24-hour cached monitoring with comprehensive product data
- **Real-time Alerts**: 10-minute interval monitoring with intelligent quiet hours
- **Market Intelligence**: Price pattern analysis, deal quality scoring, and trend prediction

### 🧠 AI-Powered Search & Discovery
- **Category-Based Intelligence**: 20+ Indian marketplace categories with smart suggestions
- **Intent-Driven Search**: Understands user intent (deal hunting, comparison, feature search)
- **Personalized Results**: User history-based ranking and recommendations
- **Advanced Filtering**: Price, brand, rating, discount, availability, Prime eligibility

### 📊 Rich Product Data
- **Comprehensive Information**: Features, specifications, customer reviews, availability
- **Product Variations**: Automatic variant detection and comparison
- **Market Analysis**: Historical pricing, discount patterns, seasonal trends
- **Quality Scoring**: Multi-factor deal quality assessment (0-100 scale)

### 🚀 Enhanced User Experience
- **Intelligent Suggestions**: Smart parameter recommendations based on market data
- **Alternative Discovery**: Find similar products and better deals
- **Watch Optimization**: Performance analysis and parameter tuning for existing watches
- **Rich Carousels**: Beautiful product cards with detailed information

## 🛠️ Tech Stack

### Core Technologies
- **Python 3.12+** with type hints and async/await
- **FastAPI** for high-performance web services
- **SQLModel** for type-safe database operations
- **Amazon PA-API 5.0** for comprehensive product data
- **Telegram Bot API** for user interaction

### AI & Intelligence
- **Smart Search Engine** with intent analysis and personalization
- **Category Management** with Amazon browse node hierarchy
- **Machine Learning** for deal quality scoring and price prediction
- **Natural Language Processing** for query understanding

### Infrastructure
- **Docker** with multi-stage builds for production deployment
- **APScheduler** for background job processing
- **Redis** for advanced caching and rate limiting
- **SQLite/PostgreSQL** for data persistence
- **Playwright** for intelligent scraping fallback

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