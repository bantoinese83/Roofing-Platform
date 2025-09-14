import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
import pyotp
import secrets
import string


class MFAToken(models.Model):
    """
    TOTP tokens for MFA
    """
    TOKEN_TYPES = [
        ('totp', 'TOTP'),
        ('hotp', 'HOTP'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='mfa_token',
        help_text='User this MFA token belongs to'
    )

    token_type = models.CharField(
        max_length=10,
        choices=TOKEN_TYPES,
        default='totp',
        help_text='Type of MFA token'
    )

    secret = models.CharField(
        max_length=32,
        help_text='Secret key for TOTP generation'
    )

    name = models.CharField(
        max_length=100,
        default='Roofing Platform',
        help_text='Name displayed in authenticator app'
    )

    is_active = models.BooleanField(
        default=True,
        help_text='Whether this token is active'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    backup_codes_generated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'MFA Token'
        verbose_name_plural = 'MFA Tokens'

    def __str__(self):
        return f"MFA Token for {self.user.get_full_name()}"

    def save(self, *args, **kwargs):
        # Generate secret if not provided
        if not self.secret:
            self.secret = pyotp.random_base32()
        super().save(*args, **kwargs)

    def verify_token(self, token):
        """Verify the provided token"""
        totp = pyotp.TOTP(self.secret)
        return totp.verify(token)

    def get_provisioning_uri(self):
        """Get the provisioning URI for QR code generation"""
        return pyotp.totp.TOTP(self.secret).provisioning_uri(
            name=self.user.email,
            issuer_name=self.name
        )

    @property
    def qr_code_url(self):
        """Get URL for QR code generation"""
        import urllib.parse
        uri = self.get_provisioning_uri()
        return f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={urllib.parse.quote(uri)}"


class RecoveryCode(models.Model):
    """
    Recovery codes for MFA fallback
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='recovery_codes',
        help_text='User this recovery code belongs to'
    )

    code = models.CharField(
        max_length=10,
        unique=True,
        help_text='Recovery code'
    )

    is_used = models.BooleanField(
        default=False,
        help_text='Whether this code has been used'
    )

    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Recovery Code'
        verbose_name_plural = 'Recovery Codes'
        ordering = ['-created_at']

    def __str__(self):
        return f"Recovery Code for {self.user.get_full_name()}"

    def save(self, *args, **kwargs):
        # Generate code if not provided
        if not self.code:
            self.code = self.generate_code()
        super().save(*args, **kwargs)

    @staticmethod
    def generate_code():
        """Generate a random recovery code"""
        alphabet = string.ascii_uppercase + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(10))

    def mark_as_used(self):
        """Mark the recovery code as used"""
        from django.utils import timezone
        self.is_used = True
        self.used_at = timezone.now()
        self.save()


class MFAAttempt(models.Model):
    """
    Track MFA verification attempts
    """
    ATTEMPT_TYPES = [
        ('login', 'Login'),
        ('setup', 'Setup'),
        ('recovery', 'Recovery'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='mfa_attempts',
        help_text='User attempting MFA'
    )

    attempt_type = models.CharField(
        max_length=20,
        choices=ATTEMPT_TYPES,
        help_text='Type of MFA attempt'
    )

    success = models.BooleanField(
        default=False,
        help_text='Whether the attempt was successful'
    )

    method_used = models.CharField(
        max_length=20,
        choices=[
            ('totp', 'TOTP'),
            ('recovery', 'Recovery Code'),
            ('sms', 'SMS'),
            ('email', 'Email'),
        ],
        help_text='MFA method used'
    )

    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text='IP address of the attempt'
    )

    user_agent = models.TextField(
        blank=True,
        help_text='User agent string'
    )

    error_message = models.TextField(
        blank=True,
        help_text='Error message if attempt failed'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'MFA Attempt'
        verbose_name_plural = 'MFA Attempts'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['attempt_type', 'success']),
        ]

    def __str__(self):
        return f"MFA Attempt by {self.user.get_full_name()} - {'Success' if self.success else 'Failed'}"


class SMSVerification(models.Model):
    """
    SMS verification codes for MFA
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sms_verifications',
        help_text='User this SMS verification belongs to'
    )

    phone_number = models.CharField(
        max_length=20,
        help_text='Phone number to send SMS to'
    )

    code = models.CharField(
        max_length=6,
        help_text='6-digit verification code'
    )

    is_used = models.BooleanField(
        default=False,
        help_text='Whether this code has been used'
    )

    expires_at = models.DateTimeField(
        help_text='When this code expires'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'SMS Verification'
        verbose_name_plural = 'SMS Verifications'
        ordering = ['-created_at']

    def __str__(self):
        return f"SMS Code for {self.user.get_full_name()}"

    def save(self, *args, **kwargs):
        # Generate code if not provided
        if not self.code:
            self.code = self.generate_code()

        # Set expiration time (10 minutes from now)
        if not self.expires_at:
            from django.utils import timezone
            self.expires_at = timezone.now() + timezone.timedelta(minutes=10)

        super().save(*args, **kwargs)

    @staticmethod
    def generate_code():
        """Generate a 6-digit verification code"""
        return ''.join(secrets.choice(string.digits) for _ in range(6))

    def is_expired(self):
        """Check if the code is expired"""
        from django.utils import timezone
        return timezone.now() > self.expires_at

    def verify_code(self, code):
        """Verify the provided code"""
        if self.is_used or self.is_expired():
            return False
        return self.code == code

    def mark_as_used(self):
        """Mark the code as used"""
        self.is_used = True
        self.save()
