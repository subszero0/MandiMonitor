# 🛡️ Security Development Guide - MandiMonitor
**For Developers Working on MandiMonitor Bot**

This guide provides security best practices specifically tailored for MandiMonitor development. Follow these practices to maintain security throughout the development lifecycle.

---

## 🎯 SECURITY-FIRST DEVELOPMENT MINDSET

### **Golden Rules for MandiMonitor Development**

#### **Rule #1: Never Commit Secrets**
```bash
# ❌ NEVER DO THIS
git add .env
git commit -m "Add configuration"

# ✅ ALWAYS DO THIS
# Add to .gitignore
echo ".env" >> .gitignore
echo "*.key" >> .gitignore
echo "*.pem" >> .gitignore
```

#### **Rule #2: Validate All User Input**
```python
# ❌ DANGEROUS - Direct user input usage
async def search_products(user_query: str):
    return await paapi_client.search(user_query)

# ✅ SECURE - Validate and sanitize input
async def search_products(user_query: str):
    # Validate input
    if not user_query or len(user_query) > 200:
        raise ValueError("Invalid query length")
    
    # Sanitize input
    clean_query = sanitize_search_query(user_query)
    return await paapi_client.search(clean_query)
```

#### **Rule #3: Use Async Safely**
```python
# ❌ DANGEROUS - Mixing sync/async unsafely
async def process_data():
    result = some_sync_function()  # Could block event loop
    
# ✅ SECURE - Proper async usage
async def process_data():
    result = await asyncio.to_thread(some_sync_function)
```

---

## 🔐 DEVELOPMENT ENVIRONMENT SECURITY

### **Setting Up Secure Development Environment**

#### **1. Environment Configuration**
```bash
# Create secure development setup
cp .env.example .env.dev
chmod 600 .env.dev

# Use development-specific values
TELEGRAM_TOKEN=your_dev_bot_token_here
PAAPI_ACCESS_KEY=dev_access_key
PAAPI_SECRET_KEY=dev_secret_key
ADMIN_USER=dev_admin
ADMIN_PASS=secure_dev_password_123!
```

#### **2. Git Configuration for Security**
```bash
# Setup git hooks for security
git config core.hooksPath .githooks

# Create pre-commit security check
echo '#!/bin/bash
bandit -r bot/ -f json || exit 1
' > .githooks/pre-commit
chmod +x .githooks/pre-commit
```

#### **3. Development Dependencies**
```bash
# Install security tools for development
pip install bandit safety pre-commit detect-secrets
pre-commit install
```

---

## 🔒 SECURE CODING PATTERNS

### **Authentication & Authorization**

#### **Secure Admin Endpoint Pattern**
```python
from functools import wraps
from flask import request, abort

def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check authentication
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            abort(401)
        
        # Log admin access
        log_admin_access(auth.username, request.endpoint)
        return f(*args, **kwargs)
    return decorated_function

@app.route('/admin/analytics')
@require_auth
def admin_analytics():
    return render_template('analytics.html')
```

#### **Telegram User Validation Pattern**
```python
async def validate_telegram_user(update: Update) -> bool:
    """Validate Telegram user and log access."""
    user = update.effective_user
    
    # Basic validation
    if not user or user.is_bot:
        return False
    
    # Rate limiting check
    if not check_user_rate_limit(user.id):
        await update.message.reply_text("Too many requests. Please wait.")
        return False
    
    # Log user action
    log_user_action(user.id, update.message.text)
    return True
```

### **Input Validation & Sanitization**

#### **User Query Validation Pattern**
```python
import re
from typing import Optional

def validate_search_query(query: str) -> Optional[str]:
    """Validate and sanitize user search queries."""
    if not query:
        return None
    
    # Length validation
    if len(query) > 200:
        raise ValueError("Query too long")
    
    # Remove potentially dangerous characters
    clean_query = re.sub(r'[<>"\';]', '', query)
    
    # Remove excessive whitespace
    clean_query = ' '.join(clean_query.split())
    
    return clean_query

def validate_price_range(min_price: int, max_price: int) -> tuple[int, int]:
    """Validate price range inputs."""
    # Range validation
    if min_price < 0 or max_price < 0:
        raise ValueError("Prices cannot be negative")
    
    if min_price > max_price:
        raise ValueError("Min price cannot exceed max price")
    
    # Reasonable limits
    if max_price > 10_00_000:  # 10 lakh rupees
        raise ValueError("Price limit exceeded")
    
    return min_price, max_price
```

#### **ASIN Validation Pattern**
```python
def validate_asin(asin: str) -> str:
    """Validate Amazon ASIN format."""
    if not asin:
        raise ValueError("ASIN cannot be empty")
    
    # ASIN format: 10 alphanumeric characters
    if not re.match(r'^[A-Z0-9]{10}$', asin.upper()):
        raise ValueError("Invalid ASIN format")
    
    return asin.upper()
```

### **Database Security Patterns**

#### **Secure Database Operations**
```python
from sqlmodel import Session, select
from typing import Optional

async def get_user_watches_secure(user_id: int, session: Session) -> List[Watch]:
    """Securely fetch user watches with validation."""
    # Validate user_id
    if user_id <= 0:
        raise ValueError("Invalid user ID")
    
    # Use parameterized query (SQLModel handles this)
    statement = select(Watch).where(Watch.user_id == user_id)
    watches = session.exec(statement).all()
    
    # Log data access
    log_data_access("watches", user_id, len(watches))
    
    return watches

def log_data_access(table: str, user_id: int, record_count: int):
    """Log database access for audit trail."""
    logger.info(
        "Database access",
        extra={
            "table": table,
            "user_id": user_id,
            "record_count": record_count,
            "timestamp": datetime.utcnow().isoformat()
        }
    )
```

### **API Security Patterns**

#### **Secure PA-API Calls**
```python
async def secure_paapi_call(func, *args, **kwargs):
    """Wrapper for secure PA-API calls with error handling."""
    try:
        # Rate limiting
        await acquire_api_permission("normal")
        
        # Execute API call
        result = await func(*args, **kwargs)
        
        # Log successful call
        log_api_success(func.__name__, args)
        
        return result
        
    except QuotaExceededError:
        log_security_event("quota_exceeded", func.__name__)
        raise
        
    except Exception as e:
        log_security_event("api_error", func.__name__, str(e))
        raise
```

#### **Webhook Security Pattern**
```python
import hmac
import hashlib

def verify_telegram_webhook(token: str, data: bytes, signature: str) -> bool:
    """Verify Telegram webhook authenticity."""
    expected_signature = hmac.new(
        token.encode(),
        data,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected_signature)
```

---

## 🔍 SECURITY TESTING PATTERNS

### **Unit Test Security Checks**

#### **Authentication Testing**
```python
import pytest
from bot.config import settings

def test_admin_auth_required():
    """Test that admin endpoints require authentication."""
    response = client.get('/admin/analytics')
    assert response.status_code == 401

def test_weak_password_rejection():
    """Test that weak passwords are rejected."""
    with pytest.raises(ValueError):
        validate_password("123456")

def test_sql_injection_protection():
    """Test SQL injection protection."""
    malicious_input = "'; DROP TABLE users; --"
    with pytest.raises(ValueError):
        validate_search_query(malicious_input)
```

#### **Input Validation Testing**
```python
def test_query_validation():
    """Test user query validation."""
    # Valid queries
    assert validate_search_query("gaming monitor") == "gaming monitor"
    
    # Invalid queries
    with pytest.raises(ValueError):
        validate_search_query("x" * 201)  # Too long
    
    with pytest.raises(ValueError):
        validate_search_query("<script>alert('xss')</script>")

def test_price_validation():
    """Test price range validation."""
    # Valid prices
    assert validate_price_range(1000, 5000) == (1000, 5000)
    
    # Invalid prices
    with pytest.raises(ValueError):
        validate_price_range(-100, 5000)  # Negative price
```

### **Integration Security Tests**

#### **API Security Testing**
```python
async def test_rate_limiting():
    """Test that rate limiting works correctly."""
    user_id = 12345
    
    # Should succeed initially
    assert await check_user_rate_limit(user_id) == True
    
    # Should fail after too many requests
    for _ in range(10):
        await make_user_request(user_id)
    
    assert await check_user_rate_limit(user_id) == False

async def test_paapi_error_handling():
    """Test PA-API error handling."""
    with pytest.raises(QuotaExceededError):
        await paapi_client.search_with_quota_exceeded()
```

---

## 📝 SECURITY LOGGING PATTERNS

### **Structured Security Logging**

#### **Security Event Logging**
```python
import structlog
from enum import Enum

class SecurityEvent(Enum):
    AUTH_FAILURE = "auth_failure"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SUSPICIOUS_INPUT = "suspicious_input"
    API_ABUSE = "api_abuse"

logger = structlog.get_logger()

def log_security_event(event: SecurityEvent, user_id: int = None, details: dict = None):
    """Log security events with structured data."""
    log_data = {
        "event_type": "security",
        "security_event": event.value,
        "timestamp": datetime.utcnow().isoformat(),
        "severity": "warning"
    }
    
    if user_id:
        log_data["user_id"] = user_id
    
    if details:
        log_data["details"] = details
    
    logger.warning("Security event detected", **log_data)

def log_admin_action(admin_user: str, action: str, target: str = None):
    """Log admin actions for audit trail."""
    logger.info(
        "Admin action",
        admin_user=admin_user,
        action=action,
        target=target,
        timestamp=datetime.utcnow().isoformat()
    )
```

#### **PII-Safe Logging**
```python
def sanitize_log_data(data: dict) -> dict:
    """Remove PII from log data."""
    sensitive_fields = ['password', 'token', 'secret', 'key']
    
    sanitized = {}
    for key, value in data.items():
        if any(field in key.lower() for field in sensitive_fields):
            sanitized[key] = "[REDACTED]"
        elif isinstance(value, str) and len(value) > 50:
            # Truncate long strings that might contain PII
            sanitized[key] = value[:50] + "..."
        else:
            sanitized[key] = value
    
    return sanitized
```

---

## 🛠️ DEVELOPMENT WORKFLOW SECURITY

### **Pre-Commit Security Checklist**

#### **Automated Security Checks**
```bash
#!/bin/bash
# .githooks/pre-commit

echo "🔒 Running security checks..."

# Check for secrets
echo "Checking for secrets..."
detect-secrets scan --all-files --force-use-all-plugins

# Static security analysis
echo "Running static security analysis..."
bandit -r bot/ -f json

# Dependency vulnerability check
echo "Checking dependencies..."
safety check

# Input validation tests
echo "Running input validation tests..."
python -m pytest tests/security/ -v

echo "✅ Security checks passed!"
```

#### **Code Review Security Checklist**
```markdown
## Security Review Checklist

### Authentication & Authorization
- [ ] Are all admin endpoints protected?
- [ ] Is user input properly validated?
- [ ] Are rate limits implemented?

### Data Protection
- [ ] No PII in logs?
- [ ] Sensitive data encrypted?
- [ ] Database queries parameterized?

### Error Handling
- [ ] No sensitive data in error messages?
- [ ] Proper exception handling?
- [ ] Security events logged?

### Dependencies
- [ ] No known vulnerabilities?
- [ ] Dependencies up to date?
- [ ] No unnecessary packages?
```

### **Security Testing in CI/CD**

#### **GitHub Actions Security Workflow**
```yaml
name: Security Tests
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
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install bandit safety pytest
      
      - name: Run security tests
        run: |
          bandit -r bot/ -f json --output bandit-report.json
          safety check --json --output safety-report.json
          pytest tests/security/ -v
      
      - name: Upload security reports
        uses: actions/upload-artifact@v3
        with:
          name: security-reports
          path: |
            bandit-report.json
            safety-report.json
```

---

## 🚨 INCIDENT RESPONSE FOR DEVELOPERS

### **When You Find a Security Issue**

#### **Immediate Actions**
1. **Don't Panic** - Security issues are part of development
2. **Document Everything** - What you found, how you found it
3. **Assess Impact** - Is this exploitable? What data is at risk?
4. **Report Immediately** - Follow your team's security reporting process

#### **Security Issue Template**
```markdown
## Security Issue Report

**Severity:** [Critical/High/Medium/Low]
**Component:** [affected module/file]
**Discovered:** [date/time]

### Description
Brief description of the security issue.

### Impact
What could an attacker do with this vulnerability?

### Reproduction Steps
1. Step 1
2. Step 2
3. Step 3

### Affected Code
```python
# Code snippet showing the issue
```

### Proposed Fix
Brief description of how to fix this issue.

### Additional Notes
Any other relevant information.
```

### **Common Security Issues in MandiMonitor**

#### **Telegram Bot Specific Issues**
- **Command Injection:** User input directly used in commands
- **Rate Limit Bypass:** Users circumventing rate limits
- **Data Leakage:** Sensitive data in bot responses

#### **API Integration Issues**
- **Credential Leakage:** API keys in logs or responses
- **Quota Abuse:** Malicious users exhausting API quotas
- **Man-in-the-Middle:** Insecure API communications

#### **Database Issues**
- **Data Exposure:** Excessive data in API responses
- **Privilege Escalation:** Users accessing other users' data
- **Injection Attacks:** Despite ORM, still possible in raw queries

---

## 📚 SECURITY RESOURCES

### **Security Tools for MandiMonitor Development**

#### **Static Analysis Tools**
- **Bandit:** Python security linter
- **Safety:** Dependency vulnerability scanner
- **Semgrep:** Advanced static analysis

#### **Dynamic Testing Tools**
- **OWASP ZAP:** Web application security testing
- **SQLMap:** SQL injection testing
- **Burp Suite:** Comprehensive security testing

#### **Monitoring Tools**
- **Sentry:** Error tracking and monitoring
- **Prometheus:** Metrics collection
- **Grafana:** Security dashboards

### **Learning Resources**

#### **Python Security Best Practices**
- [OWASP Python Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Python_Security_Cheat_Sheet.html)
- [Python Security Guidelines](https://python.org/dev/security/)

#### **Telegram Bot Security**
- [Telegram Bot Security Guide](https://core.telegram.org/bots/security)
- [Bot API Security Best Practices](https://core.telegram.org/bots/api#security-considerations)

#### **General Security Resources**
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CWE Common Weakness Enumeration](https://cwe.mitre.org/)

---

**Remember: Security is everyone's responsibility. When in doubt, ask for a security review before merging your code.**
