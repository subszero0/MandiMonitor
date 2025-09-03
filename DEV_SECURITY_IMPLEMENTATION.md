# 🛡️ MandiMonitor Dev Phase Security Implementation Guide
**Practical Security for Development (September 2025)**

---

## 🎯 EXECUTIVE SUMMARY

This guide provides **practical, actionable security implementations** specifically tailored for MandiMonitor's development phase. Unlike the comprehensive security guide, this focuses on realistic steps that balance security with development velocity.

### **Current Status (Dev Phase - September 2025)**
- ✅ **Already Completed:** Advanced audit framework, rate limiting, logging infrastructure
- 🔄 **High Priority:** Basic credential management, simple authentication
- 🟡 **Medium Priority:** Container basics, input validation
- 🟢 **Production Prep:** Advanced features (can wait)

### **Dev Phase Philosophy**
- **Security shouldn't slow development**
- **Start simple, scale to production**
- **Focus on prevention over detection**
- **Build security habits, not bureaucracy**

---

## 🔴 IMMEDIATE ACTIONS (2-3 Days)

### **1. Basic Credential Protection**

#### **Problem:** Exposed credentials in `.env` file
#### **Solution:** Simple environment variable management

**Implementation:**
```bash
# Create development-specific env files
cp .env .env.dev
cp .env .env.test

# Add to .gitignore (if not already)
echo ".env.local" >> .gitignore
echo ".env.dev" >> .gitignore
echo ".env.test" >> .gitignore
```

**Python Implementation:**
```python
# bot/config.py - Add environment handling
import os
from pathlib import Path

class DevConfig:
    """Development configuration with basic security."""

    def __init__(self):
        self.env = os.getenv('ENVIRONMENT', 'development')

        # Load environment-specific config
        if self.env == 'development':
            self._load_dev_config()
        elif self.env == 'test':
            self._load_test_config()
        else:
            self._load_prod_config()

    def _load_dev_config(self):
        """Load development config with basic protection."""
        env_file = Path('.env.dev')
        if env_file.exists():
            self._load_env_file(env_file)
        else:
            # Fallback to basic dev values
            self.telegram_token = "dev_token_placeholder"
            self.paapi_key = "dev_key_placeholder"

    def _load_env_file(self, file_path: Path):
        """Load environment file with basic validation."""
        with open(file_path) as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    if key in ['TELEGRAM_TOKEN', 'PAAPI_ACCESS_KEY']:
                        if len(value) < 10:  # Basic validation
                            raise ValueError(f"Invalid {key} length")
                    setattr(self, key.lower(), value)

# Usage
config = DevConfig()
```

#### **Success Criteria:**
- [x] `.env.dev` and `.env.test` files created
- [x] Basic environment variable validation implemented
- [x] No credentials committed to git

---

### **2. Simple Admin Authentication**

#### **Problem:** Hardcoded credentials in config
#### **Solution:** Basic environment-based authentication

**Implementation:**
```bash
# .env.dev
ADMIN_USER=dev_admin
ADMIN_PASS=dev_secure_pass_123!
ENVIRONMENT=development
```

**Python Implementation:**
```python
# bot/config.py - Update admin config
class DevConfig:
    def __init__(self):
        # ... existing code ...

        # Admin credentials from environment
        self.admin_user = os.getenv('ADMIN_USER', 'dev_admin')
        self.admin_pass = os.getenv('ADMIN_PASS', 'dev_secure_pass_123!')

        # Validate in dev mode
        if self.env == 'development':
            self._validate_dev_admin_creds()

    def _validate_dev_admin_creds(self):
        """Basic validation for dev admin credentials."""
        if len(self.admin_pass) < 12:
            print("WARNING: Admin password too short for dev")
        if self.admin_user == 'admin':
            print("WARNING: Using default admin username")

# Usage in Flask app
from flask import request, abort

def check_admin_auth():
    """Simple admin authentication for dev."""
    auth = request.authorization
    if not auth:
        return False

    config = DevConfig()
    return (auth.username == config.admin_user and
            auth.password == config.admin_pass)
```

#### **Success Criteria:**
- [x] Admin credentials loaded from environment variables
- [x] Basic validation warnings for weak credentials
- [x] Authentication works in development

---

## ✅ COMPLETED IMPLEMENTATIONS (3rd September 2025)

### **Environment Files Created:**
- ✅ `.env.dev` - Development environment with placeholder credentials
- ✅ `.env.test` - Test environment with placeholder credentials
- ✅ Updated `.gitignore` to exclude new env files

### **DevConfig Class Implemented:**
- ✅ Environment-specific configuration loading
- ✅ Basic credential validation (length checks)
- ✅ Warning system for placeholder values in dev/test
- ✅ Fallback mechanisms for missing files

### **Authentication System:**
- ✅ Simple admin authentication from environment variables
- ✅ Flask-compatible authentication functions
- ✅ Security event logging integration

### **Input Validation Framework:**
- ✅ Search query validation with sanitization
- ✅ ASIN format validation (10-character alphanumeric)
- ✅ Price range validation
- ✅ Telegram message sanitization

### **Enhanced Logging:**
- ✅ Structured logging setup for development
- ✅ Separate security event logging
- ✅ Authentication attempt logging
- ✅ Input validation failure logging

### **Integration Points:**
- ✅ Updated main config loading to use DevConfig in dev/test environments
- ✅ Created modular auth, validation, and logging modules
- ✅ Maintained backward compatibility with existing Settings class

---

## 🟡 WEEK 1 ACTIONS (5-7 Days)

### **3. Basic Input Validation**

#### **Problem:** Limited input validation framework
#### **Solution:** Simple validation decorators

**Implementation:**
```python
# bot/validation.py
import re
from typing import Optional
from functools import wraps

class DevInputValidator:
    """Simple input validation for development phase."""

    @staticmethod
    def validate_search_query(query: str) -> Optional[str]:
        """Validate search queries with dev-friendly rules."""
        if not query or len(query) > 200:
            return None

        # Basic sanitization for dev
        clean_query = re.sub(r'[<>"\';]', '', query)
        return clean_query.strip()

    @staticmethod
    def validate_asin(asin: str) -> Optional[str]:
        """Validate ASIN format."""
        if not asin:
            return None

        # ASIN format: 10 alphanumeric characters
        if not re.match(r'^[A-Z0-9]{10}$', asin.upper()):
            return None

        return asin.upper()

# Usage in handlers
from bot.validation import DevInputValidator

async def handle_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle search with basic validation."""
    query = update.message.text

    # Validate input
    clean_query = DevInputValidator.validate_search_query(query)
    if not clean_query:
        await update.message.reply_text("❌ Invalid search query")
        return

    # Proceed with search...
```

#### **Success Criteria:**
- [x] Basic input validation for search queries
- [x] ASIN format validation implemented
- [x] User-friendly error messages for invalid input

---

### **4. Development Logging Enhancement**

#### **Problem:** Basic logging setup
#### **Solution:** Structured logging for development

**Implementation:**
```python
# bot/logging_config.py
import logging
import sys
from pathlib import Path

def setup_dev_logging():
    """Setup logging for development environment."""

    # Create logs directory
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_dir / 'dev.log'),
            logging.FileHandler(log_dir / 'security.log', level=logging.WARNING)
        ]
    )

    # Security-specific logger
    security_logger = logging.getLogger('security')
    security_logger.setLevel(logging.WARNING)

    return logging.getLogger(__name__)

# Usage
logger = setup_dev_logging()

# Security logging
def log_security_event(event: str, details: dict = None):
    """Log security events in development."""
    security_logger = logging.getLogger('security')
    security_logger.warning(f"SECURITY: {event}", extra=details or {})
```

#### **Success Criteria:**
- [x] Structured logging configured
- [x] Security events logged separately
- [x] Log files created in `logs/` directory

---

## 🟢 OPTIONAL ENHANCEMENTS (Week 2+)

### **5. Basic Container Security (Optional)**

#### **Problem:** Root user in containers
#### **Solution:** Simple non-root setup

**Implementation:**
```dockerfile
# Dockerfile.dev (simplified for dev)
FROM python:3.12-slim

# Create non-root user (simple version)
RUN useradd --create-home --shell /bin/bash devuser

# Set working directory with proper permissions
WORKDIR /app
RUN chown devuser:devuser /app

# Copy requirements first
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application
COPY . .

# Switch to non-root user
USER devuser

EXPOSE 8000
CMD ["python", "-m", "bot.main"]
```

#### **Success Criteria:**
- [ ] Container runs as non-root user
- [ ] Basic permissions configured
- [ ] Development workflow unaffected

---

### **6. Code Security Scanning Integration**

#### **Problem:** No automated security scanning
#### **Solution:** Basic security checks in CI

**Implementation:**
```yaml
# .github/workflows/dev-security.yml
name: Dev Security Checks

on: [push, pull_request]

jobs:
  security:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'

      - name: Install security tools
        run: |
          pip install bandit safety

      - name: Run Bandit (basic security scan)
        run: |
          bandit -r bot/ -f txt -o bandit-report.txt || true

      - name: Check for secrets
        run: |
          # Simple grep for common secrets (dev-level)
          if grep -r "password\|token\|key" --exclude-dir=.git . | grep -v "placeholder\|example"; then
            echo "Potential secrets found - review manually"
          fi
```

#### **Success Criteria:**
- [ ] Basic security scanning integrated
- [ ] Bandit security scan running
- [ ] No critical secrets detected

---

## 📊 DEV PHASE SECURITY CHECKLIST

### **Week 1 Checklist:**
- [x] Environment-specific configuration implemented
- [x] Basic credential protection in place
- [x] Simple admin authentication working
- [x] Input validation for key functions
- [x] Development logging enhanced
- [ ] Basic security scanning integrated

### **Week 2 Checklist:**
- [ ] Container security basics implemented (optional)
- [ ] Code review security checklist created
- [ ] Development security documentation updated
- [ ] Team security awareness improved

### **Pre-Production Checklist:**
- [ ] All critical dev security issues addressed
- [ ] Production security requirements identified
- [ ] Security patterns established for scaling
- [ ] Security testing framework ready

---

## 🎯 SUCCESS METRICS FOR DEV PHASE

### **Realistic Dev Phase Goals:**
1. **Security Score:** 5.5/10 → 7.0/10 (achievable in 2 weeks)
2. **Zero Critical Vulnerabilities** in dev environment
3. **Basic Security Habits** established in development workflow
4. **Production Security Foundation** laid for future scaling
5. **Development Velocity Maintained** while improving security

### **Key Performance Indicators:**
- ✅ No credentials exposed in development
- ✅ Basic input validation working
- ✅ Security scanning integrated into CI/CD
- ✅ Team awareness of security best practices
- ✅ Clean security audit before production

---

## 🚀 NEXT STEPS

### **Immediate Actions (Today):**
1. Review current `.env` file and implement basic protection
2. Create development-specific configuration
3. Implement simple input validation
4. Setup basic security logging

### **This Week:**
1. Complete credential management implementation
2. Add basic admin authentication
3. Integrate security scanning into CI/CD
4. Document security practices for team

### **Next Month:**
1. Review progress and adjust priorities
2. Begin production security planning
3. Consider advanced security features as needed

---

## 💡 DEV PHASE SECURITY PHILOSOPHY

### **Principles:**
- **Security should enable, not hinder development**
- **Start simple, scale intelligently**
- **Build security habits through practice**
- **Learn from security incidents, not fear**
- **Balance protection with productivity**

### **Mindset:**
- **Prevention over detection** for development
- **Practical security over perfect security**
- **Team education over complex tools**
- **Iterative improvement over big-bang fixes**

---

**This guide is specifically designed for MandiMonitor's development phase, focusing on practical security implementations that scale to production requirements while maintaining development velocity.**

**Remember:** Security is a journey, not a destination. Start with the basics, build good habits, and scale as your project grows.
