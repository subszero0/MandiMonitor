"""Docker container security tests."""

import subprocess
import sys
from pathlib import Path

def test_docker_build():
    """Test that Dockerfile.dev builds successfully."""
    print("🧪 Testing Docker build...")

    try:
        # Build the Docker image
        result = subprocess.run([
            'docker', 'build',
            '-f', 'Dockerfile.dev',
            '-t', 'mandimonitor-dev-test',
            '.'
        ], capture_output=True, text=True, timeout=300)

        print(f"Build exit code: {result.returncode}")

        if result.returncode != 0:
            print("❌ Docker build failed!")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            return False

        print("✅ Docker build successful!")
        return True

    except subprocess.TimeoutExpired:
        print("❌ Docker build timed out!")
        return False
    except FileNotFoundError:
        print("❌ Docker command not found!")
        return False

def test_docker_container_user():
    """Test that container runs as non-root user."""
    print("🧪 Testing Docker container user...")

    try:
        # Run a simple command to check the user
        result = subprocess.run([
            'docker', 'run', '--rm',
            'mandimonitor-dev-test',
            'whoami'
        ], capture_output=True, text=True, timeout=30)

        print(f"Container user check exit code: {result.returncode}")

        if result.returncode != 0:
            print("❌ Container user check failed!")
            print("STDERR:", result.stderr)
            return False

        user = result.stdout.strip()
        print(f"Container runs as user: {user}")

        if user == 'devuser':
            print("✅ Container correctly runs as non-root user 'devuser'!")
            return True
        else:
            print(f"❌ Container runs as '{user}' instead of 'devuser'!")
            return False

    except subprocess.TimeoutExpired:
        print("❌ Container user check timed out!")
        return False

def test_docker_container_permissions():
    """Test that container has proper file permissions."""
    print("🧪 Testing Docker container file permissions...")

    try:
        # Check if /app directory exists and is owned by devuser
        result = subprocess.run([
            'docker', 'run', '--rm',
            'mandimonitor-dev-test',
            'ls', '-la', '/app'
        ], capture_output=True, text=True, timeout=30)

        print(f"Permissions check exit code: {result.returncode}")

        if result.returncode != 0:
            print("❌ Container permissions check failed!")
            print("STDERR:", result.stderr)
            return False

        print("App directory listing:")
        print(result.stdout)

        # Check if the directory is owned by devuser (should show devuser in owner column)
        if 'devuser' in result.stdout:
            print("✅ Container has correct file ownership!")
            return True
        else:
            print("❌ Container file ownership is incorrect!")
            return False

    except subprocess.TimeoutExpired:
        print("❌ Container permissions check timed out!")
        return False

def test_docker_cleanup():
    """Clean up test Docker image."""
    print("🧪 Cleaning up test Docker image...")

    try:
        result = subprocess.run([
            'docker', 'rmi', 'mandimonitor-dev-test'
        ], capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            print("✅ Test Docker image cleaned up successfully!")
        else:
            print("⚠️  Could not clean up test Docker image (may not exist)")

    except subprocess.TimeoutExpired:
        print("⚠️  Docker cleanup timed out")

def run_docker_tests():
    """Run all Docker security tests."""
    print("🚀 Starting Docker Security Tests")
    print("=" * 50)

    tests_passed = 0
    total_tests = 3

    # Test 1: Docker build
    if test_docker_build():
        tests_passed += 1
    print()

    # Test 2: Container user
    if test_docker_container_user():
        tests_passed += 1
    print()

    # Test 3: Container permissions
    if test_docker_container_permissions():
        tests_passed += 1
    print()

    # Cleanup
    test_docker_cleanup()

    print("=" * 50)
    print(f"🎯 Docker Security Test Results: {tests_passed}/{total_tests} passed")

    if tests_passed == total_tests:
        print("🎉 All Docker security tests PASSED!")
        return True
    else:
        print(f"❌ {total_tests - tests_passed} Docker security tests FAILED!")
        return False

if __name__ == "__main__":
    success = run_docker_tests()
    sys.exit(0 if success else 1)
