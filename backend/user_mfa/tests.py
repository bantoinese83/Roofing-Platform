from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import MFAToken, RecoveryCode, MFAAttempt, SMSVerification
import pyotp


class MFATokenModelTestCase(TestCase):
    """Test cases for MFAToken model"""

    def setUp(self):
        self.user = get_user_model().objects.create_user(username='testuser', first_name='Test', last_name='User', 
            email='test@example.com',
            password='testpass123',
            role='manager'
        )

    def test_token_creation(self):
        """Test MFA token creation"""
        token = MFAToken.objects.create(
            user=self.user,
            name='Test Token'
        )

        self.assertEqual(token.user, self.user)
        self.assertEqual(token.name, 'Test Token')
        self.assertEqual(token.token_type, 'totp')
        self.assertTrue(token.is_active)
        self.assertIsNotNone(token.secret)

    def test_token_verification(self):
        """Test token verification"""
        token = MFAToken.objects.create(
            user=self.user,
            name='Verification Test'
        )

        # Generate a valid code
        totp = pyotp.TOTP(token.secret)
        valid_code = totp.now()

        # Test valid code
        self.assertTrue(token.verify_token(valid_code))

        # Test invalid code
        self.assertFalse(token.verify_token('000000'))

    def test_provisioning_uri(self):
        """Test provisioning URI generation"""
        token = MFAToken.objects.create(
            user=self.user,
            name='URI Test'
        )

        uri = token.get_provisioning_uri()
        self.assertIn('otpauth://totp', uri)
        self.assertIn(self.user.email, uri)
        self.assertIn('URITest', uri)

    def test_qr_code_url(self):
        """Test QR code URL generation"""
        token = MFAToken.objects.create(
            user=self.user,
            name='QR Test'
        )

        qr_url = token.qr_code_url
        self.assertIn('api.qrserver.com', qr_url)
        self.assertIn('otpauth', qr_url)


class RecoveryCodeModelTestCase(TestCase):
    """Test cases for RecoveryCode model"""

    def setUp(self):
        self.user = get_user_model().objects.create_user(username='testuser', first_name='Test', last_name='User', 
            email='test@example.com',
            password='testpass123',
            role='manager'
        )

    def test_recovery_code_creation(self):
        """Test recovery code creation"""
        code = RecoveryCode.objects.create(
            user=self.user
        )

        self.assertEqual(code.user, self.user)
        self.assertIsNotNone(code.code)
        self.assertEqual(len(code.code), 10)
        self.assertFalse(code.is_used)

    def test_code_marking_as_used(self):
        """Test marking recovery code as used"""
        code = RecoveryCode.objects.create(
            user=self.user
        )

        self.assertFalse(code.is_used)

        code.mark_as_used()

        self.assertTrue(code.is_used)
        self.assertIsNotNone(code.used_at)

    def test_code_generation(self):
        """Test recovery code generation"""
        code1 = RecoveryCode.generate_code()
        code2 = RecoveryCode.generate_code()

        # Codes should be different
        self.assertNotEqual(code1, code2)

        # Codes should be 10 characters
        self.assertEqual(len(code1), 10)
        self.assertEqual(len(code2), 10)

        # Codes should contain only uppercase letters and digits
        import string
        valid_chars = string.ascii_uppercase + string.digits
        for char in code1:
            self.assertIn(char, valid_chars)


class MFAAttemptModelTestCase(TestCase):
    """Test cases for MFAAttempt model"""

    def setUp(self):
        self.user = get_user_model().objects.create_user(username='testuser', first_name='Test', last_name='User', 
            email='test@example.com',
            password='testpass123',
            role='manager'
        )

    def test_attempt_creation(self):
        """Test MFA attempt creation"""
        attempt = MFAAttempt.objects.create(
            user=self.user,
            attempt_type='login',
            method_used='totp',
            ip_address='192.168.1.1'
        )

        self.assertEqual(attempt.user, self.user)
        self.assertEqual(attempt.attempt_type, 'login')
        self.assertEqual(attempt.method_used, 'totp')
        self.assertEqual(attempt.ip_address, '192.168.1.1')
        self.assertFalse(attempt.success)

    def test_attempt_success(self):
        """Test successful MFA attempt"""
        attempt = MFAAttempt.objects.create(
            user=self.user,
            attempt_type='login',
            method_used='totp',
            success=True
        )

        self.assertTrue(attempt.success)


class SMSVerificationModelTestCase(TestCase):
    """Test cases for SMSVerification model"""

    def setUp(self):
        self.user = get_user_model().objects.create_user(username='testuser', first_name='Test', last_name='User', 
            email='test@example.com',
            password='testpass123',
            role='manager'
        )

    def test_sms_creation(self):
        """Test SMS verification creation"""
        sms = SMSVerification.objects.create(
            user=self.user,
            phone_number='+1234567890'
        )

        self.assertEqual(sms.user, self.user)
        self.assertEqual(sms.phone_number, '+1234567890')
        self.assertIsNotNone(sms.code)
        self.assertEqual(len(sms.code), 6)
        self.assertFalse(sms.is_used)
        self.assertIsNotNone(sms.expires_at)

    def test_code_verification(self):
        """Test SMS code verification"""
        sms = SMSVerification.objects.create(
            user=self.user,
            phone_number='+1234567890'
        )

        # Test valid code
        self.assertTrue(sms.verify_code(sms.code))

        # Test invalid code
        self.assertFalse(sms.verify_code('000000'))

    def test_expiry_check(self):
        """Test SMS code expiry"""
        sms = SMSVerification.objects.create(
            user=self.user,
            phone_number='+1234567890'
        )

        # Should not be expired initially
        self.assertFalse(sms.is_expired())

        # Make it expired
        sms.expires_at = timezone.now() - timezone.timedelta(minutes=1)
        sms.save()

        self.assertTrue(sms.is_expired())

    def test_code_marking_as_used(self):
        """Test marking SMS code as used"""
        sms = SMSVerification.objects.create(
            user=self.user,
            phone_number='+1234567890'
        )

        self.assertFalse(sms.is_used)

        sms.mark_as_used()

        self.assertTrue(sms.is_used)


class UserMFATestCase(TestCase):
    """Test cases for MFA-related user methods"""

    def setUp(self):
        self.user = get_user_model().objects.create_user(username='testuser', first_name='Test', last_name='User', 
            email='test@example.com',
            password='testpass123',
            role='manager'
        )

    def test_mfa_enable_disable(self):
        """Test MFA enable/disable functionality"""
        self.assertFalse(self.user.mfa_enabled)

        # Enable MFA
        self.user.enable_mfa('totp')
        self.assertTrue(self.user.mfa_enabled)
        self.assertEqual(self.user.mfa_method, 'totp')

        # Disable MFA
        self.user.disable_mfa()
        self.assertFalse(self.user.mfa_enabled)
        self.assertEqual(self.user.mfa_method, '')

    def test_mfa_required_check(self):
        """Test MFA required check"""
        # Manager should require MFA
        self.assertTrue(self.user.is_mfa_required())

        # Technician should not require MFA
        self.user.role = 'technician'
        self.assertFalse(self.user.is_mfa_required())

    def test_security_status(self):
        """Test security status generation"""
        status = self.user.get_security_status()

        self.assertIn('mfa_enabled', status)
        self.assertIn('mfa_method', status)
        self.assertIn('mfa_required', status)
        self.assertIn('account_locked', status)
        self.assertIn('login_attempts', status)
        self.assertIn('locked_until', status)
        self.assertIn('last_login_ip', status)
        self.assertIn('password_changed_at', status)

    def test_login_attempt_tracking(self):
        """Test login attempt tracking"""
        initial_attempts = self.user.login_attempts

        # Successful login
        self.user.record_login_attempt(success=True, ip_address='192.168.1.1')
        self.assertEqual(self.user.login_attempts, 0)  # Reset on success
        self.assertEqual(self.user.last_login_ip, '192.168.1.1')

        # Failed login
        self.user.record_login_attempt(success=False, ip_address='192.168.1.2')
        self.assertEqual(self.user.login_attempts, 1)
        self.assertEqual(self.user.last_login_ip, '192.168.1.2')

    def test_account_locking(self):
        """Test account locking after failed attempts"""
        # Simulate multiple failed attempts
        for i in range(5):
            self.user.record_login_attempt(success=False, ip_address='192.168.1.1')

        self.assertTrue(self.user.is_account_locked())
        self.assertIsNotNone(self.user.locked_until)

    def test_reset_login_attempts(self):
        """Test login attempt reset"""
        # Add some failed attempts
        self.user.login_attempts = 3
        self.user.save()

        self.user.reset_login_attempts()

        self.assertEqual(self.user.login_attempts, 0)
        self.assertIsNone(self.user.locked_until)


class MFAAPITestCase(TestCase):
    """Test cases for MFA API endpoints"""

    def setUp(self):
        self.user = get_user_model().objects.create_user(username='testuser', first_name='Test', last_name='User', 
            email='test@example.com',
            password='testpass123',
            role='manager'
        )
        self.client.force_authenticate(user=self.user)

    def test_mfa_setup_status(self):
        """Test MFA setup status API"""
        response = self.client.get('/api/mfa/setup/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('mfa_enabled', response.data)
        self.assertIn('mfa_required', response.data)

    def test_mfa_setup_totp(self):
        """Test TOTP MFA setup API"""
        data = {
            'method': 'totp'
        }

        response = self.client.post('/api/mfa/setup/', data, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('qr_code_url', response.data)

    def test_mfa_disable(self):
        """Test MFA disable API"""
        # First enable MFA
        self.user.enable_mfa('totp')

        response = self.client.post('/api/mfa/disable/')
        self.assertEqual(response.status_code, 200)

        self.user.refresh_from_db()
        self.assertFalse(self.user.mfa_enabled)

    def test_security_status(self):
        """Test security status API"""
        response = self.client.get('/api/mfa/security-status/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('mfa_enabled', response.data)
        self.assertIn('mfa_required', response.data)

    def test_recovery_codes_generation(self):
        """Test recovery codes generation API"""
        response = self.client.post('/api/mfa/recovery-codes/generate_new_set/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('codes', response.data)
        self.assertEqual(len(response.data['codes']), 8)

    def test_recovery_codes_list(self):
        """Test recovery codes list API"""
        # Create some recovery codes
        for _ in range(3):
            RecoveryCode.objects.create(user=self.user)

        response = self.client.get('/api/mfa/recovery-codes/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 3)

    def test_mfa_attempts_list(self):
        """Test MFA attempts list API"""
        # Create some attempts
        MFAAttempt.objects.create(
            user=self.user,
            attempt_type='login',
            method_used='totp'
        )

        response = self.client.get('/api/mfa/attempts/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
