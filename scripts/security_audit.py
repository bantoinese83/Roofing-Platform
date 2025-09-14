#!/usr/bin/env python3
"""
Security Audit and Vulnerability Assessment Script
Version 1.1 - Roofing Platform Security Assessment
"""

import os
import sys
import json
import subprocess
import requests
from datetime import datetime
from typing import Dict, List, Any

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

# Configure Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'roof_platform.settings')
import django
django.setup()

from django.conf import settings
from django.contrib.auth import get_user_model
from accounts.models import User
from customers.models import Customer
from technicians.models import TechnicianProfile
from jobs.models import Job


class SecurityAuditor:
    """Comprehensive security audit tool"""

    def __init__(self):
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'summary': {},
            'vulnerabilities': [],
            'recommendations': [],
            'compliance': {},
            'scores': {}
        }

    def log_vulnerability(self, severity: str, category: str, title: str,
                         description: str, impact: str, remediation: str):
        """Log a security vulnerability"""
        self.results['vulnerabilities'].append({
            'severity': severity,
            'category': category,
            'title': title,
            'description': description,
            'impact': impact,
            'remediation': remediation,
            'status': 'open'
        })

    def log_recommendation(self, priority: str, category: str, title: str,
                          description: str, implementation: str):
        """Log a security recommendation"""
        self.results['recommendations'].append({
            'priority': priority,
            'category': category,
            'title': title,
            'description': description,
            'implementation': implementation
        })

    def audit_environment_configuration(self):
        """Audit environment and configuration security"""
        print("🔍 Auditing Environment Configuration...")

        # Check DEBUG setting
        if settings.DEBUG:
            self.log_vulnerability(
                severity='HIGH',
                category='Configuration',
                title='DEBUG Mode Enabled in Production',
                description='Django DEBUG mode is enabled, which can leak sensitive information.',
                impact='Information disclosure, potential data leakage',
                remediation='Set DEBUG=False in production settings'
            )

        # Check SECRET_KEY security
        secret_key = getattr(settings, 'SECRET_KEY', '')
        if len(secret_key) < 32:
            self.log_vulnerability(
                severity='HIGH',
                category='Configuration',
                title='Weak SECRET_KEY',
                description=f'SECRET_KEY is too short: {len(secret_key)} characters',
                impact='Session hijacking, data tampering',
                remediation='Use a strong, random SECRET_KEY of at least 32 characters'
            )

        # Check database configuration
        if 'sqlite' in settings.DATABASES['default']['ENGINE'].lower():
            self.log_vulnerability(
                severity='MEDIUM',
                category='Database',
                title='SQLite Database in Production',
                description='Using SQLite database which is not suitable for production.',
                impact='Performance issues, concurrency problems',
                remediation='Use PostgreSQL or MySQL for production'
            )

        # Check allowed hosts
        if '*' in settings.ALLOWED_HOSTS:
            self.log_vulnerability(
                severity='HIGH',
                category='Configuration',
                title='Wildcard ALLOWED_HOSTS',
                description='ALLOWED_HOSTS contains wildcard (*), allowing requests from any host.',
                impact='Host header attacks, cache poisoning',
                remediation='Specify exact allowed hosts in ALLOWED_HOSTS'
            )

        # Check CORS settings
        cors_origins = getattr(settings, 'CORS_ALLOWED_ORIGINS', [])
        if '*' in cors_origins:
            self.log_vulnerability(
                severity='MEDIUM',
                category='Configuration',
                title='Wildcard CORS Origins',
                description='CORS allows requests from any origin (*).',
                impact='Cross-origin attacks, data leakage',
                remediation='Specify exact allowed origins in CORS_ALLOWED_ORIGINS'
            )

    def audit_authentication_security(self):
        """Audit authentication and authorization security"""
        print("🔍 Auditing Authentication Security...")

        # Check password policies
        from django.contrib.auth.password_validation import get_password_validators
        validators = get_password_validators()

        if len(validators) < 3:
            self.log_recommendation(
                priority='HIGH',
                category='Authentication',
                title='Implement Strong Password Policies',
                description='Password policies should include minimum length, complexity requirements, and common password checks.',
                implementation='Configure AUTH_PASSWORD_VALIDATORS in settings with multiple validators'
            )

        # Check session settings
        session_age = getattr(settings, 'SESSION_COOKIE_AGE', 86400)
        if session_age > 86400:  # More than 24 hours
            self.log_vulnerability(
                severity='MEDIUM',
                category='Session',
                title='Long Session Timeout',
                description=f'Session timeout is {session_age} seconds, which is too long.',
                impact='Increased risk of session hijacking',
                remediation='Set SESSION_COOKIE_AGE to a reasonable value (e.g., 3600 for 1 hour)'
            )

        # Check user accounts
        User = get_user_model()

        # Check for admin users
        admin_users = User.objects.filter(is_superuser=True)
        if admin_users.count() > 2:
            self.log_recommendation(
                priority='MEDIUM',
                category='Access Control',
                title='Limit Superuser Accounts',
                description=f'Found {admin_users.count()} superuser accounts. Limit to essential personnel only.',
                implementation='Review and remove unnecessary superuser accounts'
            )

        # Check for inactive users
        inactive_users = User.objects.filter(is_active=False)
        if inactive_users.exists():
            self.log_recommendation(
                priority='LOW',
                category='Account Management',
                title='Clean Up Inactive Accounts',
                description=f'Found {inactive_users.count()} inactive user accounts.',
                implementation='Review and remove or reactivate inactive accounts as appropriate'
            )

    def audit_data_security(self):
        """Audit data handling and storage security"""
        print("🔍 Auditing Data Security...")

        # Check for sensitive data in logs (simplified check)
        try:
            # Check for password fields in model definitions
            from django.apps import apps
            models_with_passwords = []

            for model in apps.get_models():
                for field in model._meta.fields:
                    if 'password' in field.name.lower():
                        models_with_passwords.append(f"{model._meta.label}: {field.name}")

            if models_with_passwords:
                self.log_recommendation(
                    priority='HIGH',
                    category='Data Protection',
                    title='Verify Password Field Security',
                    description=f'Found password fields in models: {", ".join(models_with_passwords)}',
                    implementation='Ensure password fields use proper hashing and never log password values'
                )
        except Exception as e:
            print(f"Could not check model fields: {e}")

        # Check for PII in logs
        try:
            # This is a simplified check - in production, you'd scan actual log files
            sensitive_patterns = ['password', 'ssn', 'credit_card', 'api_key', 'secret']

            # Check environment variables
            for key, value in os.environ.items():
                if any(pattern in key.lower() for pattern in sensitive_patterns):
                    if len(str(value)) > 10:  # Don't log short values
                        self.log_vulnerability(
                            severity='HIGH',
                            category='Environment',
                            title='Sensitive Data in Environment',
                            description=f'Environment variable {key} contains sensitive data',
                            impact='Information disclosure',
                            remediation='Move sensitive data to secure secret management system'
                        )
        except Exception as e:
            print(f"Could not check environment variables: {e}")

    def audit_api_security(self):
        """Audit API security"""
        print("🔍 Auditing API Security...")

        # Check for REST framework settings
        rest_settings = getattr(settings, 'REST_FRAMEWORK', {})

        # Check authentication classes
        auth_classes = rest_settings.get('DEFAULT_AUTHENTICATION_CLASSES', [])
        if not auth_classes:
            self.log_vulnerability(
                severity='HIGH',
                category='API',
                title='No Default Authentication',
                description='REST framework has no default authentication classes configured.',
                impact='Unauthorized API access',
                remediation='Configure DEFAULT_AUTHENTICATION_CLASSES in REST_FRAMEWORK settings'
            )

        # Check permission classes
        permission_classes = rest_settings.get('DEFAULT_PERMISSION_CLASSES', [])
        if not permission_classes:
            self.log_vulnerability(
                severity='HIGH',
                category='API',
                title='No Default Permissions',
                description='REST framework has no default permission classes configured.',
                impact='Unauthorized API access',
                remediation='Configure DEFAULT_PERMISSION_CLASSES in REST_FRAMEWORK settings'
            )

        # Check throttling
        throttling_classes = rest_settings.get('DEFAULT_THROTTLE_CLASSES', [])
        if not throttling_classes:
            self.log_recommendation(
                priority='MEDIUM',
                category='API',
                title='Implement API Throttling',
                description='No API throttling is configured, which can lead to abuse.',
                implementation='Configure DEFAULT_THROTTLE_CLASSES and throttle rates in REST_FRAMEWORK'
            )

    def audit_file_upload_security(self):
        """Audit file upload security"""
        print("🔍 Auditing File Upload Security...")

        # Check file upload settings
        max_upload_size = getattr(settings, 'FILE_UPLOAD_MAX_MEMORY_SIZE', 2.5 * 1024 * 1024)
        if max_upload_size > 10 * 1024 * 1024:  # 10MB
            self.log_vulnerability(
                severity='MEDIUM',
                category='File Upload',
                title='Large File Upload Limit',
                description=f'File upload limit is {max_upload_size} bytes, which is very large.',
                impact='DoS attacks, storage exhaustion',
                remediation='Set FILE_UPLOAD_MAX_MEMORY_SIZE to a reasonable limit (e.g., 5MB)'
            )

        # Check allowed file extensions (simplified check)
        # In a real audit, you'd check model file fields and their upload_to paths
        dangerous_extensions = ['.exe', '.bat', '.cmd', '.scr', '.pif', '.com']

        # This is a placeholder - real implementation would scan actual upload configurations
        self.log_recommendation(
            priority='HIGH',
            category='File Upload',
            title='Implement File Type Validation',
            description='File uploads should validate allowed file types and extensions.',
            implementation='Add file type validation in model save methods and forms'
        )

    def check_dependencies_vulnerabilities(self):
        """Check for known vulnerabilities in dependencies"""
        print("🔍 Checking Dependencies for Vulnerabilities...")

        try:
            # Check if safety is available
            import safety
            # This would run safety check-db in a real implementation
            self.log_recommendation(
                priority='HIGH',
                category='Dependencies',
                title='Implement Dependency Vulnerability Scanning',
                description='Regular scanning for known vulnerabilities in Python packages is essential.',
                implementation='Use tools like safety or pip-audit to scan dependencies regularly'
            )
        except ImportError:
            self.log_recommendation(
                priority='HIGH',
                category='Dependencies',
                title='Install Vulnerability Scanning Tools',
                description='No vulnerability scanning tools are installed.',
                implementation='Install and configure safety or pip-audit for dependency scanning'
            )

    def generate_compliance_report(self):
        """Generate compliance status report"""
        print("🔍 Generating Compliance Report...")

        # GDPR Compliance Check
        gdpr_compliant = True
        gdpr_issues = []

        # Check for data retention policies
        if not hasattr(settings, 'DATA_RETENTION_DAYS'):
            gdpr_issues.append('No data retention policy configured')
            gdpr_compliant = False

        # Check for consent management (simplified)
        customers_with_marketing = Customer.objects.filter(marketing_opt_in=True).count()
        if customers_with_marketing == 0:
            gdpr_issues.append('No customers have marketing consent')
            gdpr_compliant = False

        self.results['compliance']['gdpr'] = {
            'compliant': gdpr_compliant,
            'issues': gdpr_issues
        }

        # HIPAA Compliance (if handling medical data)
        hipaa_compliant = True
        hipaa_issues = []

        # Check if any sensitive health data is stored
        # This is a placeholder - real implementation would scan for PHI
        self.results['compliance']['hipaa'] = {
            'compliant': hipaa_compliant,
            'issues': hipaa_issues,
            'applicable': False  # Assuming this is not healthcare data
        }

    def calculate_security_score(self):
        """Calculate overall security score"""
        vulnerabilities = self.results['vulnerabilities']

        # Weight vulnerabilities by severity
        weights = {'CRITICAL': 10, 'HIGH': 7, 'MEDIUM': 4, 'LOW': 2}
        total_score = 0

        for vuln in vulnerabilities:
            severity = vuln['severity'].upper()
            total_score += weights.get(severity, 1)

        # Maximum possible score (for normalization)
        max_score = 50  # Arbitrary maximum

        # Calculate percentage score (lower is better)
        security_score = max(0, 100 - (total_score / max_score * 100))

        self.results['scores']['overall_security'] = round(security_score, 1)
        self.results['scores']['vulnerability_count'] = len(vulnerabilities)
        self.results['scores']['high_severity_count'] = len([
            v for v in vulnerabilities if v['severity'].upper() == 'HIGH'
        ])

    def generate_report(self):
        """Generate the final audit report"""
        print("📊 Generating Security Audit Report...")

        self.results['summary'] = {
            'total_vulnerabilities': len(self.results['vulnerabilities']),
            'total_recommendations': len(self.results['recommendations']),
            'critical_vulnerabilities': len([
                v for v in self.results['vulnerabilities'] if v['severity'].upper() == 'CRITICAL'
            ]),
            'high_vulnerabilities': len([
                v for v in self.results['vulnerabilities'] if v['severity'].upper() == 'HIGH'
            ]),
            'scan_completed': datetime.now().isoformat()
        }

        return self.results

    def run_full_audit(self):
        """Run the complete security audit"""
        print("🔒 Roofing Platform Security Audit - Version 1.1")
        print("=" * 60)

        try:
            self.audit_environment_configuration()
            self.audit_authentication_security()
            self.audit_data_security()
            self.audit_api_security()
            self.audit_file_upload_security()
            self.check_dependencies_vulnerabilities()
            self.generate_compliance_report()
            self.calculate_security_score()

            report = self.generate_report()

            # Save report to file
            report_file = f"security_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)

            print(f"\n📄 Report saved to: {report_file}")

            return report

        except Exception as e:
            print(f"❌ Audit failed: {e}")
            import traceback
            traceback.print_exc()
            return None


def main():
    """Run the security audit"""
    auditor = SecurityAuditor()
    report = auditor.run_full_audit()

    if report:
        print("\n🎯 Security Audit Summary:")
        print(f"   Vulnerabilities: {report['summary']['total_vulnerabilities']}")
        print(f"   Critical: {report['summary']['critical_vulnerabilities']}")
        print(f"   High: {report['summary']['high_vulnerabilities']}")
        print(f"   Recommendations: {report['summary']['total_recommendations']}")
        print(f"   Security Score: {report['scores']['overall_security']}/100")

        if report['scores']['overall_security'] >= 80:
            print("✅ Security posture is GOOD")
        elif report['scores']['overall_security'] >= 60:
            print("⚠️  Security posture needs IMPROVEMENT")
        else:
            print("❌ Security posture requires URGENT attention")

        print("\n🔧 Next Steps:")
        print("1. Review and address high-priority vulnerabilities")
        print("2. Implement recommended security measures")
        print("3. Schedule regular security audits")
        print("4. Consider third-party penetration testing")

    else:
        print("❌ Security audit failed to complete")
        sys.exit(1)


if __name__ == '__main__':
    main()
    
    
