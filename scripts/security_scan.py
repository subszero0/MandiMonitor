#!/usr/bin/env python3
"""
Security scanning and monitoring script for MandiMonitor.

This script performs automated security checks including:
- Dependency vulnerability scanning
- Security configuration validation
- Log analysis for security events
- File permission checks
- Container security assessment
"""

import os
import sys
import json
import subprocess
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import logging

# Add bot module to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from bot.logging_config import SecurityEventLogger
    security_logger = SecurityEventLogger()
except ImportError:
    security_logger = None


class SecurityScanner:
    """Comprehensive security scanner for MandiMonitor."""

    def __init__(self):
        self.results = {
            'scan_time': datetime.now(timezone.utc).isoformat(),
            'vulnerabilities': [],
            'warnings': [],
            'passed_checks': [],
            'failed_checks': []
        }

    def run_full_scan(self) -> Dict[str, Any]:
        """Run complete security scan."""
        print("🔐 Starting MandiMonitor Security Scan...")
        print("=" * 50)

        # Dependency scanning
        self._scan_dependencies()

        # Configuration security
        self._check_configuration_security()

        # File permissions
        self._check_file_permissions()

        # Log security analysis
        self._analyze_security_logs()

        # Container security (if running in Docker)
        self._check_container_security()

        # Generate report
        self._generate_report()

        return self.results

    def _scan_dependencies(self):
        """Scan Python dependencies for vulnerabilities."""
        print("\n📦 Scanning Dependencies...")

        try:
            # Check if safety is available
            result = subprocess.run(
                [sys.executable, '-c', 'import safety'],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                # Run safety check
                safety_result = subprocess.run(
                    [sys.executable, '-m', 'safety', 'check', '--json'],
                    capture_output=True,
                    text=True,
                    cwd=Path(__file__).parent.parent
                )

                if safety_result.returncode == 0:
                    try:
                        safety_data = json.loads(safety_result.stdout)
                        vulnerable_packages = [
                            pkg for pkg in safety_data.get('vulnerable_packages', [])
                            if pkg.get('severity', '').upper() in ['HIGH', 'CRITICAL']
                        ]

                        if vulnerable_packages:
                            for pkg in vulnerable_packages:
                                self.results['vulnerabilities'].append({
                                    'type': 'dependency',
                                    'severity': 'high',
                                    'package': pkg.get('package'),
                                    'version': pkg.get('version'),
                                    'advisory': pkg.get('advisory', 'N/A'),
                                    'vulnerability_id': pkg.get('vulnerability_id', 'N/A')
                                })
                        else:
                            self.results['passed_checks'].append('dependency_vulnerability_scan')
                    except json.JSONDecodeError:
                        self.results['warnings'].append('Could not parse safety scan results')
                else:
                    self.results['warnings'].append('Safety scan failed to run')
            else:
                self.results['warnings'].append('Safety tool not available - install with: pip install safety')

        except Exception as e:
            self.results['warnings'].append(f'Dependency scan error: {str(e)}')

    def _check_configuration_security(self):
        """Check configuration files for security issues."""
        print("\n⚙️ Checking Configuration Security...")

        # Check .env file
        env_file = Path('../.env')
        if env_file.exists():
            # Check for hardcoded secrets
            with open(env_file, 'r') as f:
                content = f.read()

            sensitive_patterns = [
                r'TELEGRAM_TOKEN\s*=',
                r'PAAPI_ACCESS_KEY\s*=',
                r'PAAPI_SECRET_KEY\s*=',
                r'ADMIN_PASS\s*=',
                r'SECRET_KEY\s*=',
            ]

            for pattern in sensitive_patterns:
                if 'placeholder' in content.lower() or 'changeme' in content.lower():
                    self.results['vulnerabilities'].append({
                        'type': 'configuration',
                        'severity': 'critical',
                        'issue': 'Placeholder/default credentials detected',
                        'file': '.env',
                        'recommendation': 'Replace with secure credentials'
                    })
                    break

        # Check for exposed secrets in source code
        source_files = Path('../bot').rglob('*.py')
        secret_patterns = [
            r'TELEGRAM_TOKEN\s*=\s*["\'][^"\']+["\']',
            r'PAAPI_ACCESS_KEY\s*=\s*["\'][^"\']+["\']',
            r'PAAPI_SECRET_KEY\s*=\s*["\'][^"\']+["\']',
        ]

        for file_path in source_files:
            try:
                with open(file_path, 'r') as f:
                    content = f.read()

                for pattern in secret_patterns:
                    if 'placeholder' in content.lower() or 'changeme' in content.lower():
                        self.results['vulnerabilities'].append({
                            'type': 'hardcoded_secret',
                            'severity': 'high',
                            'file': str(file_path.relative_to(Path('../'))),
                            'pattern': pattern
                        })
                        break
            except Exception:
                continue

        if not self.results['vulnerabilities']:
            self.results['passed_checks'].append('configuration_security')

    def _check_file_permissions(self):
        """Check file permissions for security issues."""
        print("\n📁 Checking File Permissions...")

        sensitive_files = [
            '../.env',
            '../dealbot.db',
            '../logs/security.log',
            '../backups/'
        ]

        for file_path in sensitive_files:
            path = Path(file_path)
            if path.exists():
                # Check if file is world-readable
                if os.name != 'nt':  # Unix-like systems
                    stat_info = path.stat()
                    permissions = oct(stat_info.st_mode)[-3:]

                    if permissions[2] in ['4', '5', '6', '7']:  # World readable
                        self.results['vulnerabilities'].append({
                            'type': 'file_permissions',
                            'severity': 'medium',
                            'file': file_path,
                            'permissions': permissions,
                            'recommendation': 'Restrict file permissions to owner only'
                        })

        if not any(v['type'] == 'file_permissions' for v in self.results['vulnerabilities']):
            self.results['passed_checks'].append('file_permissions')

    def _analyze_security_logs(self):
        """Analyze security logs for suspicious activity."""
        print("\n📊 Analyzing Security Logs...")

        log_files = [
            '../logs/security.log',
            '../logs/app.log'
        ]

        suspicious_patterns = [
            'authentication failure',
            'rate limit exceeded',
            'invalid input',
            'suspicious activity'
        ]

        recent_suspicious_events = 0

        for log_file in log_files:
            path = Path(log_file)
            if path.exists():
                try:
                    with open(path, 'r') as f:
                        content = f.read()

                    for pattern in suspicious_patterns:
                        if pattern.lower() in content.lower():
                            recent_suspicious_events += 1
                except Exception:
                    continue

        if recent_suspicious_events > 10:
            self.results['warnings'].append(f'High number of suspicious events detected: {recent_suspicious_events}')
        else:
            self.results['passed_checks'].append('log_security_analysis')

    def _check_container_security(self):
        """Check container security if running in Docker."""
        print("\n🐳 Checking Container Security...")

        # Check if running in Docker
        if Path('/.dockerenv').exists() or os.path.exists('/proc/1/cgroup') and 'docker' in open('/proc/1/cgroup').read():
            # Check if running as root
            if os.geteuid() == 0:
                self.results['vulnerabilities'].append({
                    'type': 'container_security',
                    'severity': 'high',
                    'issue': 'Container running as root user',
                    'recommendation': 'Use non-root user in Dockerfile'
                })

            # Check for sensitive files
            sensitive_paths = ['/.env', '/app/.env']
            for path in sensitive_paths:
                if Path(path).exists():
                    self.results['vulnerabilities'].append({
                        'type': 'container_security',
                        'severity': 'medium',
                        'issue': f'Sensitive file accessible: {path}',
                        'recommendation': 'Use secrets management instead'
                    })

        self.results['passed_checks'].append('container_security_check')

    def _generate_report(self):
        """Generate security scan report."""
        print("\n📋 Security Scan Results")
        print("=" * 50)

        # Summary
        vuln_count = len(self.results['vulnerabilities'])
        warning_count = len(self.results['warnings'])
        passed_count = len(self.results['passed_checks'])

        print(f"🔴 Vulnerabilities: {vuln_count}")
        print(f"🟡 Warnings: {warning_count}")
        print(f"🟢 Passed Checks: {passed_count}")

        if vuln_count == 0 and warning_count == 0:
            print("\n✅ All security checks passed!")
        else:
            print("\n⚠️  Security issues found - review details below")

        # Save detailed report
        report_file = Path('../security_scan_report.json')
        with open(report_file, 'w') as f:
            json.dump(self.results, f, indent=2)

        print(f"\n📄 Detailed report saved to: {report_file}")

        # Log security scan event
        if security_logger:
            security_logger.log_security_event(
                "SECURITY_SCAN_COMPLETED",
                "low" if vuln_count == 0 else "medium",
                {
                    'vulnerabilities_found': vuln_count,
                    'warnings': warning_count,
                    'passed_checks': passed_count
                }
            )


def main():
    """Main entry point for security scanning."""
    scanner = SecurityScanner()
    results = scanner.run_full_scan()

    # Exit with appropriate code
    if results['vulnerabilities']:
        sys.exit(1)  # Critical issues found
    elif results['warnings']:
        sys.exit(2)  # Warnings found
    else:
        sys.exit(0)  # All good


if __name__ == '__main__':
    main()
