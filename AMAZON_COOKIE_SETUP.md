# 🍪 Amazon Cookie Setup for MandiMonitor

If you encounter captchas or need to improve scraper success rates, you can optionally add Amazon cookies to simulate a logged-in user session.

## 📋 **Step-by-Step Instructions (For Non-Coders)**

### **Step 1: Get Your Amazon Cookies**

1. **Open your web browser** (Chrome, Firefox, Edge, etc.)
2. **Go to Amazon India**: `https://amazon.in`
3. **Log in to your Amazon account** (if you want better success rates)
4. **Open Developer Tools**:
   - **Windows**: Press `F12` or `Ctrl + Shift + I`
   - **Mac**: Press `Cmd + Option + I`
5. **Go to Application/Storage tab**:
   - In Chrome: Click "Application" tab
   - In Firefox: Click "Storage" tab
6. **Find Cookies section**:
   - Click on "Cookies" in the left sidebar
   - Click on "https://www.amazon.in"
7. **Copy important cookies** (copy the Value column):

### **Step 2: Essential Cookies to Copy**

Look for these cookie names and copy their **Value**:

| Cookie Name | Purpose | Required |
|-------------|---------|----------|
| `session-id` | Session identifier | ✅ **Critical** |
| `csrf` | Security token | ✅ **Critical** |
| `ubid-acbin` | User browser ID | 🔶 **Important** |
| `at-main` | Authentication token | 🔶 **Important** |
| `x-main` | User preferences | 🟡 **Optional** |
| `skin` | Site theme | 🟡 **Optional** |

### **Step 3: Format Your Cookies**

Create a text file with this format:
```
session-id=YOUR_SESSION_ID_VALUE_HERE; ubid-acbin=YOUR_UBID_VALUE_HERE; csrf=YOUR_CSRF_VALUE_HERE; at-main=YOUR_AT_MAIN_VALUE_HERE
```

**Example:**
```
session-id=257-1234567-9876543; ubid-acbin=123-4567890-1234567; csrf=abcd1234efgh5678; at-main=token123xyz789
```

### **Step 4: Add Cookies to MandiMonitor**

**Option A: Environment Variable (Recommended)**
1. Open your `.env` file in the MandiMonitor folder
2. Add this line:
   ```
   AMAZON_COOKIES="session-id=YOUR_VALUE; ubid-acbin=YOUR_VALUE; csrf=YOUR_VALUE"
   ```

**Option B: Direct File**
1. Create a file called `amazon_cookies.txt` in the project folder
2. Paste your formatted cookies in this file

### **Step 5: Restart MandiMonitor**

```bash
# If using Docker
docker compose down
docker compose up -d

# If running locally
# Just restart your bot
```

## 🛡️ **Security Notes**

⚠️ **Important Security Considerations:**

1. **Keep cookies private** - Never share them publicly
2. **Cookies expire** - You may need to update them every few weeks
3. **Use a separate account** - Consider using a dedicated Amazon account for scraping
4. **Monitor your account** - Check for unusual activity

## 🔧 **Advanced Configuration**

If you're comfortable with code, you can also modify `bot/scraper.py` directly:

```python
# Add this in the browser context creation
extra_http_headers={
    "Cookie": "session-id=YOUR_VALUE; ubid-acbin=YOUR_VALUE; csrf=YOUR_VALUE",
    # ... other headers
}
```

## 🆘 **Troubleshooting**

### **Common Issues:**

1. **"Captcha detected"** error:
   - ✅ Add cookies as described above
   - ✅ Wait longer between requests
   - ✅ Try different ASINs

2. **"Product not found"** error:
   - ✅ Verify the ASIN is correct (10 characters)
   - ✅ Check if product exists on Amazon India
   - ✅ Try the Amazon URL directly in browser

3. **Cookies not working:**
   - ✅ Make sure cookies are recent (less than 1 week old)
   - ✅ Verify you copied the values correctly
   - ✅ Check if you're logged into Amazon India (not .com)

### **Testing Cookie Setup:**

Run the test script to verify cookies are working:
```bash
poetry run python test_scraper_fix.py
```

## 📞 **Need Help?**

If you're still having issues:

1. **Check the logs** in your MandiMonitor console
2. **Try with different products** - some may be temporarily unavailable
3. **Verify your internet connection** and VPN settings
4. **Update your cookies** if they're more than a week old

---

*Note: Cookie requirements may change if Amazon updates their anti-bot measures. The scraper has been designed to work without cookies in most cases, but they can improve reliability.*