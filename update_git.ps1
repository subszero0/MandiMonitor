#!/usr/bin/env pwsh
# Git update script for MandiMonitor fixes

Write-Host "📝 Updating git with fixes..." -ForegroundColor Cyan

# Check git status
Write-Host "`n1. Checking git status..." -ForegroundColor Yellow
git status

# Add all changes
Write-Host "`n2. Adding changes..." -ForegroundColor Yellow
git add .

# Create comprehensive commit message
$commitMessage = @"
🐛 Fix admin panel and bot flow issues

## Fixed Issues:
1. **Admin Panel Enhancement**
   - Fixed template syntax error (moment() -> datetime)
   - Added comprehensive HTML dashboard with metrics, activity, and system health
   - Real-time monitoring with auto-refresh

2. **Bot Flow Improvements** 
   - Fixed text handler to distinguish questions from product requests
   - Streamlined watch creation for specific product names (3+ words or brand detected)
   - Added intelligent product search with PA-API integration
   - Improved ASIN detection and resolution

3. **Messaging Clarity**
   - Eliminated confusing success/error message combinations
   - Single comprehensive response based on search results
   - Better user guidance with actionable tips
   - Clear success confirmations with product details

## Technical Changes:
- Enhanced PA-API wrapper with search_products() function
- Improved watch parser logic for missing field detection
- Better error handling and user feedback
- Optimized admin dashboard with responsive design

## Testing:
- All modules load successfully
- Watch creation flow works for specific product names
- Admin panel renders correctly with detailed metrics
- PA-API integration functional for both item lookup and search

Fixes #admin-panel-error #bot-flow-issues #confusing-messages
"@

# Commit changes
Write-Host "`n3. Committing changes..." -ForegroundColor Yellow
git commit -m $commitMessage

# Show final status
Write-Host "`n4. Final git status..." -ForegroundColor Yellow
git status

Write-Host "`n✅ Git update complete!" -ForegroundColor Green
Write-Host "📊 Admin panel: localhost:8000/admin" -ForegroundColor Cyan
Write-Host "🤖 Bot improvements: Better product search and clearer messaging" -ForegroundColor Cyan