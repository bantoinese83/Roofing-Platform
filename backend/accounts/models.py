from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """
    Custom user model for the roofing platform.
    Extends Django's AbstractUser with additional fields.
    """
    ROLE_CHOICES = [
        ('owner', 'Business Owner'),
        ('manager', 'Office Manager'),
        ('technician', 'Field Technician'),
        ('admin', 'Administrator'),
    ]

    email = models.EmailField(_('email address'), unique=True)
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='technician',
        help_text='User role in the system'
    )
    phone_number = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)

    # MFA settings
    mfa_enabled = models.BooleanField(default=False)
    mfa_method = models.CharField(
        max_length=20,
        choices=[
            ('totp', 'TOTP (Authenticator App)'),
            ('sms', 'SMS'),
            ('email', 'Email'),
        ],
        blank=True,
        help_text='Preferred MFA method'
    )

    # Security settings
    login_attempts = models.PositiveIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    password_changed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Make email the username field
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return f"{self.get_full_name()} ({self.email})"

    def get_full_name(self):
        """
        Return the first_name plus the last_name, with a space in between.
        """
        full_name = f"{self.first_name} {self.last_name}".strip()
        if full_name:
            return full_name
        return self.username

    @property
    def is_owner(self):
        return self.role == 'owner'

    @property
    def is_manager(self):
        return self.role == 'manager'

    @property
    def is_technician(self):
        return self.role == 'technician'

    @property
    def is_admin(self):
        return self.role == 'admin'

    # MFA methods
    def enable_mfa(self, method='totp'):
        """Enable MFA for the user"""
        self.mfa_enabled = True
        self.mfa_method = method
        self.save()

    def disable_mfa(self):
        """Disable MFA for the user"""
        self.mfa_enabled = False
        self.mfa_method = ''
        self.save()

    def is_mfa_required(self):
        """Check if MFA is required for this user"""
        # Require MFA for owners and managers
        return self.role in ['owner', 'manager', 'admin']

    # Security methods
    def record_login_attempt(self, success=True, ip_address=None):
        """Record a login attempt"""
        from django.utils import timezone

        if success:
            self.login_attempts = 0
            self.locked_until = None
            self.last_login_ip = ip_address
            self.last_login = timezone.now()
        else:
            self.login_attempts += 1
            self.last_login_ip = ip_address

            # Lock account after 5 failed attempts
            if self.login_attempts >= 5:
                self.locked_until = timezone.now() + timezone.timedelta(minutes=30)

        self.save()

    def is_account_locked(self):
        """Check if account is currently locked"""
        from django.utils import timezone
        if self.locked_until and self.locked_until > timezone.now():
            return True
        return False

    def reset_login_attempts(self):
        """Reset login attempts counter"""
        self.login_attempts = 0
        self.locked_until = None
        self.save()

    def update_password_changed(self):
        """Update password changed timestamp"""
        from django.utils import timezone
        self.password_changed_at = timezone.now()
        self.save()

    def get_security_status(self):
        """Get comprehensive security status"""
        from django.utils import timezone

        return {
            'mfa_enabled': self.mfa_enabled,
            'mfa_method': self.mfa_method,
            'mfa_required': self.is_mfa_required(),
            'account_locked': self.is_account_locked(),
            'login_attempts': self.login_attempts,
            'locked_until': self.locked_until,
            'last_login_ip': self.last_login_ip,
            'password_changed_at': self.password_changed_at,
            'password_age_days': (timezone.now() - (self.password_changed_at or self.date_joined)).days if self.password_changed_at else None,
        }
