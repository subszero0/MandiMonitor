#!/usr/bin/env python3
"""Run integration tests for watch flow scenarios."""

import sys
import subprocess
import asyncio
from pathlib import Path

def run_unit_tests():
    """Run the pytest suite."""
    print("🧪 Running unit tests...")
    result = subprocess.run([
        sys.executable, "-m", "pytest", 
        "tests/test_watch_flow.py", 
        "-v", "--tb=short"
    ], capture_output=True, text=True)
    
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    
    return result.returncode == 0

def run_linting():
    """Run code quality checks."""
    print("🔍 Running linting checks...")
    
    # Run ruff
    ruff_result = subprocess.run([
        sys.executable, "-m", "ruff", "check", "bot/", "tests/"
    ], capture_output=True, text=True)
    
    # Run black check
    black_result = subprocess.run([
        sys.executable, "-m", "black", "--check", "bot/", "tests/"
    ], capture_output=True, text=True)
    
    print("Ruff output:", ruff_result.stdout)
    if ruff_result.stderr:
        print("Ruff errors:", ruff_result.stderr)
        
    print("Black output:", black_result.stdout)
    if black_result.stderr:
        print("Black errors:", black_result.stderr)
    
    return ruff_result.returncode == 0 and black_result.returncode == 0

def check_database_schema():
    """Verify database schema is up to date."""
    print("🗄️  Checking database schema...")
    try:
        from bot.models import SQLModel
        from bot.cache_service import engine
        
        # Try to create tables - this will fail if schema is wrong
        SQLModel.metadata.create_all(engine)
        print("✅ Database schema is valid")
        return True
    except Exception as e:
        print(f"❌ Database schema error: {e}")
        return False

def main():
    """Run all integration tests."""
    print("🚀 Starting MandiMonitor Integration Tests")
    print("=" * 50)
    
    # Change to project directory
    project_root = Path(__file__).parent
    import os
    os.chdir(project_root)
    
    all_passed = True
    
    # Check database schema
    if not check_database_schema():
        all_passed = False
        print("❌ Database schema check failed")
    else:
        print("✅ Database schema check passed")
    
    # Run linting
    if not run_linting():
        all_passed = False
        print("❌ Linting checks failed")
    else:
        print("✅ Linting checks passed")
    
    # Run unit tests
    if not run_unit_tests():
        all_passed = False
        print("❌ Unit tests failed")
    else:
        print("✅ Unit tests passed")
    
    print("=" * 50)
    if all_passed:
        print("🎉 All integration tests PASSED!")
        return 0
    else:
        print("💥 Some integration tests FAILED!")
        return 1

if __name__ == "__main__":
    sys.exit(main())