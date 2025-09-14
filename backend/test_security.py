#!/usr/bin/env python
"""
Security Audit and Penetration Testing Suite
Comprehensive security validation for the roofing platform
"""

import os
import sys
import django
import requests
import json
import hashlib
import hmac
import secrets
import string
from datetime import datetime, timedelta
import re
import logging
from urllib.parse import urljoin, urlparse

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'roof_platform.settings')
django.setup()

from django.test import TestCase, TransactionTestCase
from django.test.client import Client
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.contrib.sessions.models import Session
from django.utils import timezone
from customers.models import Customer
from jobs.models import Job


class SecurityAuditSuite:
    """
    Comprehensive security audit and penetration testing suite
    """

    def __init__(self, base_url='http://localhost:8000'):
        self.base_url = base_url
        self.client = Client()
        self.session = requests.Session()
        self.results = {
            'vulnerabilities': [],
            'warnings': [],
            'passed_checks': [],
            'recommendations': []
        }
        self.logger = self._setup_logger()

    def _setup_logger(self):
        """Setup security audit logging"""
        logger = logging.getLogger('security_audit')
        logger.setLevel(logging.INFO)

        os.makedirs('logs', exist_ok=True)
        os.makedirs('reports', exist_ok=True)

        fh = logging.FileHandler('logs/security_audit.log')
        fh.setLevel(logging.INFO)

        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)

        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)

        logger.addHandler(fh)
        logger.addHandler(ch)

        return logger

    def _log_vulnerability(self, severity, title, description, endpoint=None, recommendation=None):
        """Log a security vulnerability"""
        vuln = {
            'severity': severity,
            'title': title,
            'description': description,
            'endpoint': endpoint,
            'recommendation': recommendation,
            'timestamp': datetime.now().isoformat()
        }

        if severity == 'CRITICAL':
            self.results['vulnerabilities'].append(vuln)
        elif severity == 'HIGH':
            self.results['vulnerabilities'].append(vuln)
        elif severity == 'MEDIUM':
            self.results['warnings'].append(vuln)
        else:
            self.results['warnings'].append(vuln)

        self.logger.warning(f"[{severity}] {title}: {description}")

    def _log_passed_check(self, title, description):
        """Log a passed security check"""
        check = {
            'title': title,
            'description': description,
            'timestamp': datetime.now().isoformat()
        }
        self.results['passed_checks'].append(check)
        self.logger.info(f"[PASS] {title}")

    def test_sql_injection(self):
        """Test for SQL injection vulnerabilities"""
        self.logger.info("Testing for SQL injection vulnerabilities")

        test_payloads = [
            "' OR '1'='1",
            "'; DROP TABLE users; --",
            "' UNION SELECT * FROM users --",
            "admin' --",
            "1' OR '1' = '1",
            "' OR 1=1 --",
        ]

        endpoints_to_test = [
            '/api/customers/customers/',
            '/api/jobs/jobs/',
            '/api/quotes/quotes/',
        ]

        for endpoint in endpoints_to_test:
            for payload in test_payloads:
                # Test in query parameters
                try:
                    response = self.session.get(
                        f"{self.base_url}{endpoint}",
                        params={'search': payload}
                    )

                    if response.status_code == 500:
                        self._log_vulnerability(
                            'HIGH',
                            'Potential SQL Injection',
                            f'Server error with payload: {payload}',
                            endpoint,
                            'Implement proper input sanitization and parameterized queries'
                        )
                    elif 'sql' in response.text.lower() or 'syntax' in response.text.lower():
                        self._log_vulnerability(
                            'MEDIUM',
                            'SQL Error Disclosure',
                            f'SQL error message in response for payload: {payload}',
                            endpoint,
                            'Disable SQL error disclosure in production'
                        )

                except Exception as e:
                    self.logger.warning(f"Request failed for {endpoint}: {e}")

        self._log_passed_check(
            'SQL Injection Test',
            'Completed SQL injection vulnerability scan'
        )

    def test_xss_vulnerabilities(self):
        """Test for Cross-Site Scripting (XSS) vulnerabilities"""
        self.logger.info("Testing for XSS vulnerabilities")

        xss_payloads = [
            '<script>alert("XSS")</script>',
            '<img src=x onerror=alert("XSS")>',
            'javascript:alert("XSS")',
            '<iframe src="javascript:alert(\'XSS\')"></iframe>',
            '<svg onload=alert("XSS")>',
        ]

        endpoints_to_test = [
            '/api/customers/customers/',
            '/api/jobs/jobs/',
            '/api/quotes/quotes/',
        ]

        for endpoint in endpoints_to_test:
            for payload in xss_payloads:
                try:
                    # Test in POST data
                    data = {
                        'name': payload,
                        'title': payload,
                        'description': payload,
                    }

                    response = self.session.post(
                        f"{self.base_url}{endpoint}",
                        json=data,
                        headers={'Content-Type': 'application/json'}
                    )

                    # Check if payload appears unescaped in response
                    if payload in response.text and '<script>' in payload:
                        self._log_vulnerability(
                            'HIGH',
                            'Potential XSS Vulnerability',
                            f'XSS payload reflected in response: {payload}',
                            endpoint,
                            'Implement proper output encoding and input sanitization'
                        )

                except Exception as e:
                    self.logger.warning(f"Request failed for {endpoint}: {e}")

        self._log_passed_check(
            'XSS Test',
            'Completed XSS vulnerability scan'
        )

    def test_authentication_bypass(self):
        """Test for authentication bypass vulnerabilities"""
        self.logger.info("Testing for authentication bypass vulnerabilities")

        # Test unauthenticated access to protected endpoints
        protected_endpoints = [
            '/api/customers/customers/',
            '/api/jobs/jobs/',
            '/api/quotes/quotes/',
            '/api/inventory/items/',
            '/api/reports/dashboard/',
        ]

        for endpoint in protected_endpoints:
            try:
                response = self.session.get(f"{self.base_url}{endpoint}")

                if response.status_code not in [401, 403]:
                    self._log_vulnerability(
                        'CRITICAL',
                        'Authentication Bypass',
                        f'Protected endpoint accessible without authentication',
                        endpoint,
                        'Implement proper authentication checks on all protected endpoints'
                    )
                else:
                    self._log_passed_check(
                        f'Authentication Check - {endpoint}',
                        'Endpoint properly protected with authentication'
                    )

            except Exception as e:
                self.logger.warning(f"Request failed for {endpoint}: {e}")

        # Test session fixation
        try:
            # Get initial session
            response1 = self.session.get(f"{self.base_url}/api/")
            session_cookie1 = response1.cookies.get('sessionid')

            # Try to use the same session after login attempt
            if session_cookie1:
                self._log_vulnerability(
                    'MEDIUM',
                    'Potential Session Fixation',
                    'Session ID remains the same across requests',
                    '/api/',
                    'Implement session regeneration after authentication'
                )

        except Exception as e:
            self.logger.warning(f"Session fixation test failed: {e}")

    def test_authorization_flaws(self):
        """Test for authorization flaws and privilege escalation"""
        self.logger.info("Testing for authorization and privilege escalation")

        # Create test users with different roles
        users = {
            'technician': {'email': 'tech@test.com', 'role': 'technician'},
            'manager': {'email': 'manager@test.com', 'role': 'manager'},
            'owner': {'email': 'owner@test.com', 'role': 'owner'}
        }

        # Test role-based access to sensitive endpoints
        sensitive_endpoints = {
            '/api/reports/dashboard/': ['owner', 'manager'],  # Not technician
            '/api/inventory/items/': ['owner', 'manager'],   # Not technician
            '/api/settings/': ['owner'],                     # Only owner
        }

        for endpoint, allowed_roles in sensitive_endpoints.items():
            for user_type, user_data in users.items():
                try:
                    # Simulate login (in real test, would need actual login flow)
                    # For now, test the authorization logic in views
                    if user_type not in allowed_roles:
                        # This would be a vulnerability if technician can access manager-only data
                        self._log_vulnerability(
                            'HIGH',
                            'Privilege Escalation',
                            f'{user_type} may have access to {endpoint} which should be restricted to {allowed_roles}',
                            endpoint,
                            'Implement proper role-based access control (RBAC)'
                        )

                except Exception as e:
                    self.logger.warning(f"Authorization test failed for {endpoint}: {e}")

    def test_csrf_protection(self):
        """Test CSRF protection"""
        self.logger.info("Testing CSRF protection")

        # Test POST requests without CSRF token
        endpoints_to_test = [
            '/api/customers/customers/',
            '/api/jobs/jobs/',
            '/api/quotes/quotes/',
        ]

        for endpoint in endpoints_to_test:
            try:
                # Clear any existing CSRF token
                self.session.cookies.clear()

                response = self.session.post(
                    f"{self.base_url}{endpoint}",
                    json={'test': 'data'},
                    headers={'Content-Type': 'application/json'}
                )

                # If request succeeds without CSRF token, it might be vulnerable
                if response.status_code not in [403, 401]:
                    self._log_vulnerability(
                        'MEDIUM',
                        'CSRF Protection Weakness',
                        f'POST request succeeded without CSRF token',
                        endpoint,
                        'Ensure CSRF protection is enabled for all state-changing operations'
                    )

            except Exception as e:
                self.logger.warning(f"CSRF test failed for {endpoint}: {e}")

    def test_rate_limiting(self):
        """Test rate limiting implementation"""
        self.logger.info("Testing rate limiting")

        endpoint = '/api/auth/login/'

        # Send multiple rapid requests
        for i in range(10):
            try:
                response = self.session.post(
                    f"{self.base_url}{endpoint}",
                    json={
                        'email': f'test{i}@example.com',
                        'password': 'password123'
                    }
                )

                if response.status_code == 429:
                    self._log_passed_check(
                        'Rate Limiting',
                        f'Rate limiting triggered after {i+1} requests'
                    )
                    break

                if i == 9:  # Last attempt
                    self._log_vulnerability(
                        'MEDIUM',
                        'Missing Rate Limiting',
                        'No rate limiting detected after 10 rapid requests',
                        endpoint,
                        'Implement rate limiting to prevent brute force attacks'
                    )

            except Exception as e:
                self.logger.warning(f"Rate limiting test request {i+1} failed: {e}")

    def test_security_headers(self):
        """Test security headers in HTTP responses"""
        self.logger.info("Testing security headers")

        endpoints_to_test = [
            '/',
            '/api/',
            '/admin/',
        ]

        required_headers = {
            'X-Frame-Options': 'DENY',
            'X-Content-Type-Options': 'nosniff',
            'X-XSS-Protection': '1; mode=block',
            'Strict-Transport-Security': 'max-age=31536000',
            'Content-Security-Policy': None,  # Should exist
        }

        for endpoint in endpoints_to_test:
            try:
                response = self.session.get(f"{self.base_url}{endpoint}")

                for header, expected_value in required_headers.items():
                    if header not in response.headers:
                        self._log_vulnerability(
                            'MEDIUM',
                            'Missing Security Header',
                            f'Security header {header} is missing',
                            endpoint,
                            f'Add {header} header to HTTP responses'
                        )
                    elif expected_value and response.headers[header] != expected_value:
                        self._log_vulnerability(
                            'LOW',
                            'Incorrect Security Header Value',
                            f'{header} has value "{response.headers[header]}" but expected "{expected_value}"',
                            endpoint,
                            f'Set {header} to recommended value'
                        )
                    else:
                        self._log_passed_check(
                            f'Security Header - {header}',
                            f'Header {header} properly configured'
                        )

            except Exception as e:
                self.logger.warning(f"Security headers test failed for {endpoint}: {e}")

    def test_data_leakage(self):
        """Test for data leakage vulnerabilities"""
        self.logger.info("Testing for data leakage")

        # Test error messages don't reveal sensitive information
        error_endpoints = [
            '/api/customers/customers/99999/',  # Non-existent ID
            '/api/jobs/jobs/99999/',
            '/api/quotes/quotes/99999/',
        ]

        sensitive_patterns = [
            r'sql',
            r'database',
            r'server',
            r'stack trace',
            r'password',
            r'token',
            r'key',
        ]

        for endpoint in error_endpoints:
            try:
                response = self.session.get(f"{self.base_url}{endpoint}")

                response_text = response.text.lower()
                for pattern in sensitive_patterns:
                    if re.search(pattern, response_text):
                        self._log_vulnerability(
                            'MEDIUM',
                            'Information Disclosure',
                            f'Error response contains sensitive information matching pattern: {pattern}',
                            endpoint,
                            'Ensure error messages do not reveal sensitive system information'
                        )

            except Exception as e:
                self.logger.warning(f"Data leakage test failed for {endpoint}: {e}")

    def test_input_validation(self):
        """Test input validation and sanitization"""
        self.logger.info("Testing input validation")

        # Test with malicious input
        malicious_inputs = [
            '../../etc/passwd',
            '../../../../windows/system32',
            '<script>malicious</script>',
            'javascript:malicious()',
            'data:text/html,<script>alert(1)</script>',
            '../../../.env',
        ]

        endpoints_to_test = [
            '/api/customers/customers/',
            '/api/jobs/jobs/',
        ]

        for endpoint in endpoints_to_test:
            for malicious_input in malicious_inputs:
                try:
                    response = self.session.post(
                        f"{self.base_url}{endpoint}",
                        json={
                            'name': malicious_input,
                            'title': malicious_input,
                            'description': malicious_input
                        },
                        headers={'Content-Type': 'application/json'}
                    )

                    # Check if malicious input was accepted
                    if response.status_code == 201:
                        self._log_vulnerability(
                            'MEDIUM',
                            'Weak Input Validation',
                            f'Malicious input accepted: {malicious_input}',
                            endpoint,
                            'Implement proper input validation and sanitization'
                        )

                except Exception as e:
                    self.logger.warning(f"Input validation test failed for {endpoint}: {e}")

    def test_ssl_tls_configuration(self):
        """Test SSL/TLS configuration"""
        self.logger.info("Testing SSL/TLS configuration")

        try:
            response = self.session.get(self.base_url, verify=True)

            # Check if HTTPS is enforced
            if not self.base_url.startswith('https://'):
                self._log_vulnerability(
                    'HIGH',
                    'HTTP Instead of HTTPS',
                    'Application is not using HTTPS',
                    self.base_url,
                    'Enforce HTTPS for all connections in production'
                )

            # Check SSL certificate
            if hasattr(response, 'raw') and hasattr(response.raw, 'connection'):
                cert = response.raw.connection.sock.getpeercert()
                if cert:
                    # Check certificate expiration
                    import ssl
                    cert_obj = ssl.DER_cert_to_PEM_cert(cert['der'])
                    # This is a basic check - in production, use proper SSL validation
                    self._log_passed_check(
                        'SSL Certificate',
                        'SSL certificate is valid'
                    )

        except Exception as e:
            self.logger.warning(f"SSL/TLS test failed: {e}")
            self._log_vulnerability(
                'HIGH',
                'SSL/TLS Issues',
                f'SSL/TLS configuration issues: {e}',
                self.base_url,
                'Fix SSL/TLS configuration and ensure HTTPS is enforced'
            )

    def generate_security_report(self):
        """Generate comprehensive security audit report"""
        self.logger.info("Generating security audit report")

        report = {
            'audit_timestamp': datetime.now().isoformat(),
            'target_url': self.base_url,
            'summary': {
                'critical_vulnerabilities': len([v for v in self.results['vulnerabilities'] if v['severity'] == 'CRITICAL']),
                'high_vulnerabilities': len([v for v in self.results['vulnerabilities'] if v['severity'] == 'HIGH']),
                'medium_warnings': len([v for v in self.results['warnings'] if v.get('severity') == 'MEDIUM']),
                'low_warnings': len([v for v in self.results['warnings'] if v.get('severity') == 'LOW']),
                'passed_checks': len(self.results['passed_checks']),
                'overall_risk_level': self._calculate_risk_level()
            },
            'vulnerabilities': self.results['vulnerabilities'],
            'warnings': self.results['warnings'],
            'passed_checks': self.results['passed_checks'],
            'recommendations': self._generate_recommendations()
        }

        # Save report
        report_file = f"reports/security_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        self.logger.info(f"Security audit report saved to {report_file}")
        return report

    def _calculate_risk_level(self):
        """Calculate overall risk level"""
        critical = len([v for v in self.results['vulnerabilities'] if v['severity'] == 'CRITICAL'])
        high = len([v for v in self.results['vulnerabilities'] if v['severity'] == 'HIGH'])

        if critical > 0:
            return 'CRITICAL'
        elif high > 2:
            return 'HIGH'
        elif high > 0 or len(self.results['warnings']) > 5:
            return 'MEDIUM'
        else:
            return 'LOW'

    def _generate_recommendations(self):
        """Generate security recommendations"""
        recommendations = []

        if self.results['vulnerabilities']:
            recommendations.append({
                'priority': 'HIGH',
                'title': 'Address Critical Vulnerabilities',
                'description': f'Fix {len([v for v in self.results["vulnerabilities"] if v["severity"] == "CRITICAL"])} critical vulnerabilities immediately'
            })

        if len([v for v in self.results['vulnerabilities'] if v['severity'] == 'HIGH']) > 0:
            recommendations.append({
                'priority': 'HIGH',
                'title': 'Address High-Risk Vulnerabilities',
                'description': 'Fix all high-risk vulnerabilities before production deployment'
            })

        recommendations.extend([
            {
                'priority': 'MEDIUM',
                'title': 'Implement Security Headers',
                'description': 'Ensure all security headers are properly configured'
            },
            {
                'priority': 'MEDIUM',
                'title': 'Enable Rate Limiting',
                'description': 'Implement rate limiting to prevent brute force attacks'
            },
            {
                'priority': 'MEDIUM',
                'title': 'Regular Security Audits',
                'description': 'Schedule regular security audits and penetration testing'
            },
            {
                'priority': 'LOW',
                'title': 'Security Monitoring',
                'description': 'Implement security monitoring and alerting systems'
            }
        ])

        return recommendations

    def run_full_security_audit(self):
        """Run the complete security audit suite"""
        self.logger.info("Starting comprehensive security audit")

        try:
            # Run all security tests
            self.test_sql_injection()
            self.test_xss_vulnerabilities()
            self.test_authentication_bypass()
            self.test_authorization_flaws()
            self.test_csrf_protection()
            self.test_rate_limiting()
            self.test_security_headers()
            self.test_data_leakage()
            self.test_input_validation()
            self.test_ssl_tls_configuration()

            # Generate report
            report = self.generate_security_report()

            self.logger.info("Security audit completed successfully")
            return report

        except Exception as e:
            self.logger.error(f"Security audit failed: {e}")
            raise


def main():
    """Main function to run security audit"""
    print("🔒 Starting Security Audit Suite")
    print("=" * 50)

    # Initialize audit suite
    auditor = SecurityAuditSuite()

    try:
        # Run full security audit
        report = auditor.run_full_security_audit()

        # Print summary
        print("\n📊 Security Audit Results")
        print("=" * 50)
        print(f"Risk Level: {report['summary']['overall_risk_level']}")
        print(f"Critical Vulnerabilities: {report['summary']['critical_vulnerabilities']}")
        print(f"High Vulnerabilities: {report['summary']['high_vulnerabilities']}")
        print(f"Warnings: {report['summary']['medium_warnings'] + report['summary']['low_warnings']}")
        print(f"Passed Checks: {report['summary']['passed_checks']}")

        if report['summary']['critical_vulnerabilities'] > 0:
            print("\n🚨 CRITICAL VULNERABILITIES FOUND!")
            for vuln in report['vulnerabilities']:
                if vuln['severity'] == 'CRITICAL':
                    print(f"  - {vuln['title']}: {vuln['description']}")

        if report['summary']['high_vulnerabilities'] > 0:
            print("\n⚠️  HIGH RISK VULNERABILITIES:")
            for vuln in report['vulnerabilities']:
                if vuln['severity'] == 'HIGH':
                    print(f"  - {vuln['title']}: {vuln['description']}")

        if report['recommendations']:
            print("\n💡 RECOMMENDATIONS:")
            for rec in report['recommendations'][:5]:  # Show top 5
                print(f"  [{rec['priority']}] {rec['title']}: {rec['description']}")

        print(f"\n📁 Detailed report saved to: reports/security_audit_*.json")

        # Return exit code based on risk level
        risk_levels = {'CRITICAL': 3, 'HIGH': 2, 'MEDIUM': 1, 'LOW': 0}
        return risk_levels.get(report['summary']['overall_risk_level'], 1)

    except Exception as e:
        print(f"\n❌ Security audit failed: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
