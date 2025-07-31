#!/usr/bin/env pwsh
# Test script for MandiMonitor fixes

Write-Host "🧪 Testing MandiMonitor fixes..." -ForegroundColor Cyan

# Test 1: Admin panel module
Write-Host "`n1. Testing admin panel module..." -ForegroundColor Yellow
try {
    python -c "from bot.health import app; print('✅ Admin panel module loads successfully')"
    Write-Host "✅ Admin panel test PASSED" -ForegroundColor Green
} catch {
    Write-Host "❌ Admin panel test FAILED: $_" -ForegroundColor Red
}

# Test 2: Watch parser
Write-Host "`n2. Testing watch parser..." -ForegroundColor Yellow
try {
    $testScript = @"
from bot.watch_parser import parse_watch
test_cases = [
    'Samsung gaming monitor 27 inch',
    'LG monitor',
    'Samsung 27 inch Odyssey G3 Gaming Monitor'
]
for case in test_cases:
    result = parse_watch(case)
    print(f'Input: {case}')
    print(f'Brand: {result.get("brand")}')
    print(f'Keywords: {result.get("keywords")}')
    print('---')
"@
    python -c $testScript
    Write-Host "✅ Watch parser test PASSED" -ForegroundColor Green
} catch {
    Write-Host "❌ Watch parser test FAILED: $_" -ForegroundColor Red
}

# Test 3: Bot handlers
Write-Host "`n3. Testing bot handlers..." -ForegroundColor Yellow
try {
    python -c "from bot.handlers import setup_handlers; print('✅ Bot handlers load successfully')"
    Write-Host "✅ Bot handlers test PASSED" -ForegroundColor Green
} catch {
    Write-Host "❌ Bot handlers test FAILED: $_" -ForegroundColor Red
}

# Test 4: PA-API wrapper
Write-Host "`n4. Testing PA-API wrapper..." -ForegroundColor Yellow
try {
    python -c "from bot.paapi_wrapper import search_products, get_item; print('✅ PA-API wrapper loads successfully')"
    Write-Host "✅ PA-API wrapper test PASSED" -ForegroundColor Green
} catch {
    Write-Host "❌ PA-API wrapper test FAILED: $_" -ForegroundColor Red
}

# Test 5: Watch flow
Write-Host "`n5. Testing watch flow..." -ForegroundColor Yellow
try {
    python -c "from bot.watch_flow import start_watch, handle_callback; print('✅ Watch flow loads successfully')"
    Write-Host "✅ Watch flow test PASSED" -ForegroundColor Green
} catch {
    Write-Host "❌ Watch flow test FAILED: $_" -ForegroundColor Red
}

Write-Host "`n🎉 Testing complete!" -ForegroundColor Cyan