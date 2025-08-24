#!/usr/bin/env python3
"""
Quick E2E Test Runner for MandiMonitor Bot

This script runs comprehensive end-to-end tests to catch basic issues
before manual testing. Run this after any code changes.

Usage:
    python scripts/run_e2e_tests.py
    OR
    pyenv exec python scripts/run_e2e_tests.py
"""

import asyncio
import sys
import os
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def run_e2e_tests():
    """Run the comprehensive E2E test suite."""
    print(f"🕐 Starting E2E tests at {datetime.now().strftime('%H:%M:%S')}")
    
    try:
        # Import and run the comprehensive test
        from tests.test_e2e_comprehensive import test_comprehensive_e2e_flow
        
        results = await test_comprehensive_e2e_flow()
        
        # Exit with appropriate code
        if results['failed'] > 0:
            print(f"\n❌ {results['failed']} critical tests failed - do not proceed to manual testing")
            sys.exit(1)
        elif results['warnings'] > 0:
            print(f"\n⚠️  {results['warnings']} tests had warnings - proceed with caution")
            sys.exit(0)
        else:
            print(f"\n✅ All tests passed - ready for manual testing!")
            sys.exit(0)
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you're in the project root and dependencies are installed")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(run_e2e_tests())
