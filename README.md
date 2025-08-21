# MandiMonitorBot

Telegram bot that hunts India-specific e-commerce deals and pings you when prices crash.

![CI/CD](https://github.com/subszero0/MandiMonitor/actions/workflows/ci-cd.yml/badge.svg)
![Dependency Scan](https://github.com/subszero0/MandiMonitor/actions/workflows/security-deps.yml/badge.svg)
![Lockfile Check](https://github.com/subszero0/MandiMonitor/actions/workflows/lockfile-check.yml/badge.svg)
![Branch Protection](https://img.shields.io/badge/Branch%20Protection-Enforced-brightgreen)
![Sentry](https://img.shields.io/badge/Sentry-Alerts_Enabled-purple)
![Responsible Disclosure](https://img.shields.io/badge/Responsible%20Disclosure-Welcome-brightgreen)
![License Audit](https://github.com/subszero0/MandiMonitor/actions/workflows/license-audit.yml/badge.svg)
[![SBOM](https://img.shields.io/badge/SBOM-Available-blue)](https://github.com/subszero0/MandiMonitor/actions)

## 🎯 Progress Status

**Phase 0 (Repository Setup)** ✅ **COMPLETED**
**Phase 1 (Hello-World Bot + Health)** ✅ **COMPLETED**  
**Phase 2 (Price Fetch System)** ✅ **COMPLETED**
**Phase 3 (Data Models & Migration)** ✅ **COMPLETED**
**Phase 4 (Watch Creation Flow)** ✅ **COMPLETED**
**Phase 5 (Scheduling System)** ✅ **COMPLETED**
**Phase 6 (Affiliate Links)** ✅ **COMPLETED**
**Phase 7 (Admin & Metrics)** ✅ **COMPLETED**
**Phase 8 (Monitoring & Backups)** ✅ **COMPLETED**
**Phase 9 (Docker & CI/CD)** ✅ **COMPLETED**
**Phase 10 (Beta Testing)** ✅ **COMPLETED**
**Phase 11 (Public Soft-Launch)** ✅ **COMPLETED**
**Security Audit Phase SA6 (CI/CD Pipeline Security)** ✅ **COMPLETED**
**Security Audit Phase SA7 (Monitoring & Incident Response)** ✅ **COMPLETED**
**Security Audit Phase SA8 (Compliance & Security Disclosure)** ✅ **COMPLETED**
**PA-API Phase 5 (Advanced Business Features)** ✅ **COMPLETED**
**PA-API Phase 6 (Technical Excellence)** ✅ **COMPLETED**

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- Poetry  
- Docker Desktop

### Local Development

1. **Install dependencies:**
   ```bash
   poetry install
   poetry run playwright install --with-deps
   ```

2. **Setup environment:**
   ```bash
   cp .env.example .env
   # Add your TELEGRAM_TOKEN to .env
   ```

3. **Run the bot:**
   ```bash
   poetry run python -m bot.main
   ```

4. **Test health endpoint:**
   ```bash
   curl http://localhost:8000/health
   ```

5. **Run admin interface:**
   ```bash
   FLASK_APP=bot.admin_app flask run
   ```

### Docker Deployment

```bash
# Local development
docker compose up --build

# Production deployment  
docker compose up -d
```

## 🏗️ Architecture

### Price Fetching Engine (Phase 2)
- **Smart Caching**: 24h SQLite cache for efficient price retrieval
- **Dual Sources**: Amazon PA-API with Playwright scraper fallback
- **Error Handling**: Quota limits, network failures, stale cache recovery
- **Testing**: 6/6 comprehensive unit tests with mocking

### Database Schema (Phase 3)
- **SQLModel Architecture**: Type-safe database models with relationships
- **User Management**: Telegram user tracking with watch associations
- **Watch System**: Price monitoring requests with filters and preferences
- **Price History**: Historical price tracking with source attribution
- **Click Analytics**: Affiliate link engagement monitoring
- **Database Bootstrap**: Automated table creation and migration support

### Watch Creation Flow (Phase 4)
- **Smart Parsing**: Regex-based extraction of brands, prices, discounts, and ASINs
- **Interactive UI**: Inline keyboards for missing brand and discount selection
- **User Flow**: Seamless watch creation with guided prompts and validation
- **Immediate Feedback**: Instant mini-carousel with current price and buy button
- **Database Integration**: Automatic user creation and watch persistence

### Scheduling System (Phase 5)
- **APScheduler Integration**: BackgroundScheduler singleton with timezone support
- **Daily Digest Jobs**: Scheduled 09:00 IST delivery of up to 5 deal cards per user
- **Real-time Monitoring**: 10-minute price polling with quiet hours (23:00-08:00 IST)
- **Job Management**: Automatic job registration on watch creation with unique IDs
- **Discount Filtering**: Smart deal selection based on min_discount and max_price
- **Error Resilience**: Idempotent jobs with watch/user validation

### Affiliate Deep Links (Phase 6)
- **Affiliate URL Builder**: `build_affiliate_url()` with configurable PAAPI_TAG support
- **Click Tracking**: Callback buttons log Click records before redirecting to Amazon
- **Telegram Integration**: `answer_callback_query(url=...)` for seamless redirects
- **Funnel Analytics**: Complete click-out logging with watch_id and ASIN tracking
- **URL Parameters**: Includes `linkCode=ogi&th=1&psc=1` for affiliate reliability
- **Cache Control**: `cache_time=0` for real-time click tracking

### Admin & Metrics (Phase 7)
- **Flask Admin Interface**: Secure `/admin` endpoint with HTTP Basic Authentication
- **Funnel Metrics**: Real-time counts for explorers, watch creators, live watches, and click-outs
- **CSV Export**: Streaming `/admin/prices.csv` download with memory-efficient generator
- **Authentication**: Configurable `ADMIN_USER`/`ADMIN_PASS` with WWW-Authenticate headers
- **Database Optimization**: Uses `func.count()` for efficient aggregation queries
- **JSON API**: Returns structured metrics for dashboard integration

### Monitoring & Back-ups (Phase 8)
- **Sentry Integration**: Conditional error reporting with `SENTRY_DSN` environment variable
- **Health Endpoint**: Lightweight `/health` endpoint for uptime monitoring (no auth, no DB)
- **Database Backups**: Automated nightly SQLite backups with date suffix and 30-day retention
- **Error Tracking**: Global Sentry activation across CLI, tests, and WSGI applications
- **Production Ready**: Health checks for UptimeRobot integration and monitoring
- **Cron Automation**: Shell script for automated database backup scheduling

### Docker & CI/CD (Phase 9)
- **Multi-stage Docker**: Optimized builder and runtime layers for production deployment
- **Container Orchestration**: Docker Compose stack with bot, Cloudflared tunnel, and cron services
- **GitHub Actions CI/CD**: End-to-end pipeline with testing, ECR push, and Lightsail deployment
- **Infrastructure as Code**: Automated container health checks and system cleanup
- **Secure Tunneling**: Cloudflared integration for secure external access without port exposure
- **Production Deployment**: One-command deployment with `docker compose up -d`

### CI/CD Pipeline Security (Phase SA6)
- **OIDC Authentication**: GitHub Actions authenticate to AWS using short-lived OIDC tokens instead of long-lived access keys
- **Hardened Workflow Permissions**: All workflows use least-privilege `read-all` default with minimal job-level overrides
- **Mandatory Code Review**: Branch protection rules require 1 approving review and passing security checks before merge
- **Automated Compliance**: Weekly validation ensures branch protection rules remain active
- **Permission Validation**: Custom workflow validates that all GitHub Actions use proper permission scopes
- **Evidence Collection**: Automated generation of security compliance reports and protection rule evidence

### Monitoring & Incident Response (Phase SA7)
- **Centralized Logging**: Structured JSON logs pushed to Grafana Cloud Loki with 14-day retention
- **PII Protection**: Automatic filtering of sensitive data from logs with user ID hashing
- **Sentry Integration**: Comprehensive error tracking with alert rules for spikes and critical issues
- **Real-time Alerting**: Multi-channel notifications via email, Slack, and PagerDuty for incident escalation
- **Performance Monitoring**: Response time tracking and health check failure detection
- **Incident Runbook**: Complete step-by-step procedures for detection, response, and post-mortem analysis
- **Component Tagging**: Logs organized by application component for rapid troubleshooting and correlation

### Compliance & Security Disclosure (Phase SA8)
- **Responsible Disclosure Policy**: Clear vulnerability reporting guidelines with defined response timelines
- **License Compatibility Audit**: Automated CI/CD validation ensuring all dependencies comply with MIT and Amazon Associates ToS
- **Security Contact**: Dedicated security@mandimonitor.app email with 3-business-day response commitment
- **Hall of Fame Recognition**: Public acknowledgment for security researchers contributing to project safety
- **Legal Compliance**: Weekly license audits preventing GPL/AGPL contamination and commercial license conflicts
- **Artifact Reporting**: 90-day retention of license compatibility reports for compliance verification

### Beta Testing (Phase 10)
- **Structured Testing Framework**: Comprehensive beta test plan with 5-friend private Telegram group
- **Feedback Collection System**: Daily feedback templates, mid-test surveys, and final evaluation forms
- **Issue Tracking Integration**: GitHub issue management with priority levels and beta-feedback labels
- **Success Criteria**: 90%+ command success rate, <2s response time, 7+ satisfaction score
- **Communication Templates**: Welcome messages, daily check-ins, and thank you recognition system

### Public Soft-Launch (Phase 11)
- **Multi-Channel Launch Strategy**: LinkedIn, Telegram, and GitHub repository announcements
- **Professional Domain Setup**: bot.mandimonitor.com with Cloudflare tunnel and SSL configuration
- **Real-time Launch Monitoring**: Comprehensive monitoring script with performance thresholds and alerting
- **Success Metrics Tracking**: User adoption, system performance, and community engagement measurements
- **Rollback Procedures**: Complete incident response plan with emergency contacts and communication strategy

### Components
- `bot/paapi_wrapper.py` - Amazon PA-API integration
- `bot/scraper.py` - Playwright web scraping fallback
- `bot/cache_service.py` - 24h cache with smart routing
- `bot/models.py` - SQLModel database schema (5 tables)
- `bot/db.py` - Database engine and initialization
- `bot/patterns.py` - Regex patterns for text parsing
- `bot/watch_parser.py` - Watch creation text parser
- `bot/watch_flow.py` - Complete watch creation flow
- `bot/ui_helpers.py` - Inline keyboard utilities
- `bot/carousel.py` - Product card builders
- `bot/scheduler.py` - APScheduler singleton with job management
- `bot/affiliate.py` - Affiliate URL generation with tracking parameters
- `bot/admin_app.py` - Flask admin interface with basic auth and CSV export
- `bot/monitoring.py` - Sentry error tracking and health monitoring
- `bot/revenue_optimization.py` - A/B testing and conversion tracking for affiliate optimization
- `bot/admin_analytics.py` - Business intelligence dashboard and user segmentation analysis
- `bot/admin.py` - Enhanced admin interface with real-time analytics and performance metrics
- `bot/log_config.py` - Structured logging configuration with PII filtering
- `scripts/backup_db.sh` - Automated database backup script
- `scripts/setup_oidc.sh` - GitHub OIDC provider and IAM role setup script
- `scripts/enforce_branch_protection.sh` - Branch protection rules automation script
- `infra/iam_oidc.tf` - Terraform configuration for GitHub OIDC authentication
- `infra/sentry/alerts.yml` - Sentry alert rules configuration for incident detection
- `docs/security/incident_runbook.md` - Comprehensive incident response procedures
- `docs/observability/MandiMonitor-Logs.json` - Grafana dashboard for centralized log visualization
- `Dockerfile` - Multi-stage production container image
- `docker-compose.yml` - Container orchestration stack with Loki logging driver
- `.github/workflows/ci-cd.yml` - End-to-end deployment pipeline with OIDC authentication
- `.github/workflows/validate-permissions.yml` - Workflow permissions validation
- `.github/workflows/branch-protection.yml` - Branch protection compliance monitoring
- `.github/workflows/sentry-alerts.yml` - Sentry alert configuration and smoke testing
- `.github/workflows/license-audit.yml` - License compatibility audit with MIT/Amazon Associates ToS validation
- `tests/test_price.py` - Price system unit tests
- `tests/test_models.py` - Database schema tests
- `tests/test_watch_parser.py` - Watch parsing tests
- `tests/test_scheduler.py` - Scheduler functionality tests
- `tests/test_affiliate.py` - Affiliate URL and click tracking tests
- `tests/test_admin.py` - Admin interface authentication and CSV tests
- `tests/test_health.py` - Health endpoint monitoring tests
- `tests/test_revenue_optimization.py` - Revenue optimization and A/B testing unit tests
- `tests/test_admin_analytics.py` - Business analytics and dashboard functionality tests
- `tests/integration/test_loki_push.py` - Loki integration and structured logging tests
- `docs/beta_test_plan.md` - Comprehensive beta testing strategy and framework
- `docs/beta_test_templates.md` - Communication templates and feedback collection tools
- `docs/launch_plan.md` - Public soft-launch strategy with monitoring and success criteria
- `docs/launch_checklist.md` - Pre-launch verification and execution checklist
- `scripts/launch_monitoring.py` - Real-time launch monitoring with performance thresholds

## 🧪 Testing

   ```bash
# Run all tests
poetry run pytest -v

# Run specific test module
poetry run pytest tests/test_price.py -v

# Code quality checks
poetry run ruff check .
poetry run black --check .
```

## 📊 Current Features

✅ **Telegram Bot** - `/start` and `/watch` commands with health monitoring
✅ **Price Fetching** - Amazon.in price retrieval with caching
✅ **Database Schema** - SQLModel with 5 tables (User, Watch, Price, Click, Cache)
✅ **Data Persistence** - SQLite database with automatic table creation
✅ **Watch Creation** - Interactive flow with text parsing and inline buttons
✅ **Smart UI** - Brand and discount selection with immediate feedback
✅ **Scheduling System** - APScheduler with daily digest and real-time monitoring
✅ **Job Management** - Automatic scheduling with timezone and quiet hours support
✅ **Affiliate Links** - Click tracking with redirect via callback buttons
✅ **Click Analytics** - Complete funnel measurement with database logging
✅ **Admin Interface** - Secure Flask admin with metrics and CSV export
✅ **Funnel Metrics** - Real-time analytics dashboard with authentication
✅ **Error Monitoring** - Sentry integration for production error tracking
✅ **Health Monitoring** - Lightweight `/health` endpoint for uptime checks
✅ **Database Backups** - Automated nightly backups with retention management
✅ **Container Deployment** - Multi-stage Docker with optimized runtime
✅ **CI/CD Pipeline** - Automated testing, building, and deployment to AWS
✅ **Secure Tunneling** - Cloudflared integration for production access
✅ **Web Health Endpoint** - HTTP `/health` for monitoring
✅ **Error Recovery** - Graceful fallback and stale cache handling
✅ **Advanced Caching** - Multi-tier intelligent caching with Redis and memory optimization
✅ **API Quota Management** - Circuit breaker pattern with request prioritization
✅ **Performance Monitoring** - Comprehensive system metrics and performance analytics
✅ **Technical Excellence** - Enhanced reliability, scalability, and observability

## 🛣️ Roadmap

✅ **Phase 5**: Scheduling system for daily/real-time monitoring
✅ **Phase 6**: Affiliate link integration with click tracking
✅ **Phase 7**: Admin panel with metrics and CSV export
✅ **Phase 8**: Monitoring, health checks, and database backups
✅ **Phase 9**: Docker containerization and CI/CD pipeline
✅ **Phase 10**: Beta testing with structured feedback collection
✅ **Phase 11**: Public soft-launch with monitoring and analytics

**🎯 Next: Post-MVP Enhancements** - Multi-marketplace support, advanced features

## 🚀 Deployment

### Production Stack
```bash
# Deploy with all services
docker compose up -d
```

The stack includes:
- **Bot Service**: Main application on port 8000
- **Cloudflared**: Secure tunnel for external access
- **Cron Service**: Automated nightly database backups

### GitHub Secrets Required
For automated CI/CD deployment, configure these GitHub repository secrets:

```env
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=us-east-1
ECR_REPOSITORY=mandi-monitor-bot
LIGHTSAIL_HOST=your-server.com
LIGHTSAIL_USER=ubuntu
# Example format - replace with your actual SSH private key
LIGHTSAIL_KEY=-----BEGIN_OPENSSH_PRIVATE_KEY-----
```

### Environment Variables
Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
# Edit .env with your tokens and settings
```

## 🔧 Operations

### Backup & Restore

The MandiMonitor bot includes automated encrypted database backups for data protection.

#### Creating Manual Backups

```bash
# Set the backup passphrase (32+ character random string recommended)
export DB_BACKUP_PASSPHRASE="your-secure-passphrase-here"

# Run the backup script
./scripts/backup_db.sh
```

This creates an encrypted backup file in the format: `backups/db_YYYYMMDD_HHMMSS.sql.gz.gpg`

#### Restoring from Backup

```bash
# Restore from an encrypted backup
gpg --decrypt backups/db_20250728_010000.sql.gz.gpg | gunzip > dealbot.db

# Alternatively, specify the passphrase in the command
echo "your-passphrase" | gpg --batch --passphrase-fd 0 --decrypt backups/db_20250728_010000.sql.gz.gpg | gunzip > dealbot.db
```

#### Automated Nightly Backups

Automated backups run nightly at 1:00 AM IST via GitHub Actions. The workflow:

1. SSHs into the Lightsail instance
2. Creates an encrypted backup using GPG symmetric encryption (AES-256)
3. Uploads the backup to the configured S3 bucket
4. Cleans up backups older than 30 days

**Required GitHub Secrets:**
- `DB_BACKUP_PASSPHRASE`: Encryption passphrase for backups
- `LIGHTSAIL_PRIVATE_KEY`: SSH private key for server access
- `LIGHTSAIL_HOST`: Server hostname/IP
- `BACKUP_BUCKET`: S3 bucket name for backup storage

#### Passphrase Rotation

For security, rotate the backup passphrase quarterly:

1. Generate a new 32+ character random passphrase
2. Update the `DB_BACKUP_PASSPHRASE` secret in GitHub and Lightsail
3. Test the new passphrase with a manual backup
4. Document the rotation date in your security logs

### Infrastructure Hardening

#### Rootless Docker Deployment

MandiMonitor runs with enterprise-grade container security:

```bash
# Deploy with rootless Docker (automatically configured in CI/CD)
./scripts/setup_rootless_docker.sh

# Verify rootless deployment
docker exec $(docker compose ps -q bot) id -u  # Should return 1000, not 0
```

#### Firewall Configuration

The system uses defense-in-depth network security:

```bash
# UFW firewall status (Lightsail instance)
sudo ufw status verbose
# Should show: 22/tcp (SSH) and 443/tcp (Cloudflare) only

# iptables outbound restrictions
sudo iptables -L OUTPUT -n
# Should show: HTTPS (443), DNS (53), NTP (123) allowed, others rejected
```

#### Security Testing

Automated security validation runs in CI/CD:

```bash
# Manual firewall smoke test (creates ephemeral Lightsail instance)
gh workflow run ssh-smoke.yml

# Container security integration tests
pytest tests/integration/test_compose_secure.py -v

# Cloudflare Tunnel ACL tests (requires configuration)
pytest tests/integration/test_tunnel_acl.py -v -m network
```

## 📊 Observability & Monitoring

MandiMonitor implements comprehensive observability with structured logging, real-time alerting, and incident response procedures:

### Centralized Logging
- **Grafana Cloud Loki**: Structured JSON logs with 14-day retention and LogQL queries
- **PII Protection**: Automatic filtering of sensitive data with user ID hashing for correlation
- **Component Tagging**: Logs organized by application component (core, telegram, pricing, etc.)
- **Search & Analysis**: Advanced log filtering and aggregation for rapid troubleshooting

### Error Tracking & Alerting
- **Sentry Integration**: Real-time error capture with stack traces and performance monitoring
- **Multi-Channel Alerts**: Email, Slack (#security-alerts), and PagerDuty escalation
- **Smart Thresholds**: Configurable alert sensitivity (>5 errors/min, >5s response time)
- **Security Events**: Dedicated monitoring for authentication failures and admin access

### Monitoring Dashboards
- **Log Analytics**: Import Grafana dashboard ID 13639 or use `docs/observability/MandiMonitor-Logs.json`
- **Error Trends**: Real-time visualization of error rates by component and severity
- **Performance Metrics**: Response time tracking and health check monitoring
- **Security Events**: Authentication failure tracking and suspicious activity detection

### Alert Rules
1. **New Error Events** - Immediate notification on first occurrence
2. **Error Spike Detection** - Alert when >5 errors/minute across any component
3. **High Response Time** - Warning when p95 response time >5 seconds
4. **Health Check Failures** - Critical alert on 3+ consecutive health check failures
5. **Authentication Failures** - Security alert on admin panel access issues
6. **Database Errors** - Critical alert on connection or integrity issues

### Incident Response
- **Automated Detection**: Sentry alerts trigger immediate notification workflows
- **Structured Response**: Step-by-step incident runbook with severity classification
- **Evidence Preservation**: Automatic log and database backup on security incidents
- **Post-Mortem Process**: Standardized analysis and improvement tracking procedures

### Access Monitoring Resources
- **Sentry Dashboard**: https://sentry.io/organizations/{org}/projects/mandimonitor/
- **Grafana Logs**: https://grafana.com/orgs/{org}/ (import MandiMonitor-Logs dashboard)
- **Incident Runbook**: [docs/security/incident_runbook.md](docs/security/incident_runbook.md)
- **Alert Configuration**: [infra/sentry/alerts.yml](infra/sentry/alerts.yml)

## 🛡️ Security & Responsible Disclosure

We take the safety of MandiMonitor users seriously. If you discover a vulnerability,
**please email security@mandimonitor.app** with steps to reproduce.
We commit to:

| Step | Timeline |
|------|----------|
| Acknowledge report | **≤ 3 business days** |
| Triage & reproduce | ≤ 7 business days |
| Fix or mitigation | ≤ 30 calendar days (severity-dependent) |
| Public disclosure | Coordinated with researcher |

### Reporting Guidelines

- **Scope**: Issues affecting MandiMonitor bot, admin interface, or infrastructure
- **Out of Scope**: Social engineering, physical attacks, third-party services
- **Contact**: security@mandimonitor.app (response within 3 business days)
- **Format**: Include steps to reproduce, impact assessment, and any proof-of-concept

### Recognition

- Hall-of-fame credits available for qualifying reports (opt-in)
- Public acknowledgment after coordinated disclosure
- We believe in collaborative security improvement

For security concerns or questions, please contact the maintainers via the security email above.

## 🔒 Security & Architecture

Comprehensive security documentation is available in the `docs/security/` directory:

- **[Architecture & Data Flow](docs/security/architecture.md)** - System overview, trust boundaries, and technology stack
- **[Asset Inventory](docs/security/assets.csv)** - Classification and rotation policies for sensitive assets
- **[Threat Model](docs/security/threat_model.md)** - STRIDE analysis and risk mitigation roadmap

### Supply Chain Security

- **SBOM Generation**: Software Bill of Materials automatically generated with every build ([Download latest SBOM ↗](https://github.com/subszero0/MandiMonitor/actions))
- **Dependency Scanning**: Automated CVE detection using pip-audit and Safety on every dependency change
- **Container Scanning**: Trivy scans for HIGH/CRITICAL vulnerabilities in Docker images
- **Lockfile Integrity**: Automated verification that poetry.lock matches pyproject.toml

### Infrastructure & Network Security

- **Container Hardening**: Read-only filesystems, capability drops, resource limits, and rootless execution
- **Zero-Trust Network Access**: Cloudflare Tunnel with JWT authentication and IP-based restrictions
- **Host-Level Hardening**: UFW firewall (ports 22, 443 only) with iptables outbound restrictions
- **SSH Security**: Key-only authentication, modern ciphers, fail2ban protection, no root access
- **Rootless Docker**: All containers run as non-privileged user (UID 1000) with namespace isolation
- **Automated Security Testing**: Ephemeral Lightsail instances test firewall rules and security configurations

### Privacy & Data Protection

The MandiMonitor bot is designed with **privacy-by-design principles**:

- **Minimal Data Collection**: Only Telegram user IDs are stored - no usernames, messages, or personal information
- **No Tracking**: We don't log message content, device information, or browsing behavior
- **Encrypted Backups**: All database backups are encrypted with GPG AES-256 encryption
- **User Control**: Simply stop using the bot to cease all data processing
- **Automated Privacy Monitoring**: CI/CD pipeline includes automated PII detection to prevent accidental data collection

**Data We Store:**
- Telegram user ID (numeric, pseudonymous identifier)
- Your watch preferences (keywords, price limits, discount thresholds)
- Historical price data for deals (public product information)
- Affiliate click timestamps (for revenue analytics)

**Data We DON'T Store:**
- Real names, usernames, or profile information
- Phone numbers or email addresses
- Message content or conversation history
- Location data or device information
- Payment or financial information

For detailed privacy information, see our [PII Audit Report](docs/security/pii_audit_2025-07-28.md).

For security concerns or responsible disclosure, please contact the maintainers via GitHub issues.

## 🔗 Links

- **Telegram Bot**: [@MandiMonitor_bot](https://t.me/MandiMonitor_bot)
- **GitHub**: [subszero0/MandiMonitor](https://github.com/subszero0/MandiMonitor)
