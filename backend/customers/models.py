from django.db import models
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _
from django.conf import settings


class Customer(models.Model):
    """
    Customer profile for the roofing platform.
    """
    # Contact Information
    first_name = models.CharField(
        max_length=50,
        help_text='Customer first name'
    )
    last_name = models.CharField(
        max_length=50,
        help_text='Customer last name'
    )
    email = models.EmailField(
        unique=True,
        help_text='Primary email address'
    )

    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    phone_number = models.CharField(
        validators=[phone_regex],
        max_length=17,
        blank=True,
        help_text='Primary phone number'
    )

    # Alternative Contact
    alt_phone_number = models.CharField(
        validators=[phone_regex],
        max_length=17,
        blank=True,
        help_text='Alternative phone number'
    )

    # Customer Status
    is_active = models.BooleanField(
        default=True,
        help_text='Whether this customer is active'
    )

    # Marketing Preferences
    marketing_opt_in = models.BooleanField(
        default=False,
        help_text='Whether customer has opted in for marketing communications'
    )

    # Customer Notes
    notes = models.TextField(
        blank=True,
        help_text='General notes about the customer'
    )

    # Metadata
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_customers',
        help_text='User who created this customer record'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Customer'
        verbose_name_plural = 'Customers'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['phone_number']),
            models.Index(fields=['first_name', 'last_name']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"{self.get_full_name()} ({self.email})"

    def get_full_name(self):
        """Return the customer's full name"""
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def primary_address(self):
        """Get the primary address for this customer"""
        return self.addresses.filter(is_primary=True).first()

    @property
    def all_addresses(self):
        """Get all addresses for this customer"""
        return self.addresses.all()

    @property
    def total_jobs(self):
        """Get total number of jobs for this customer"""
        return self.jobs.count()

    @property
    def active_jobs(self):
        """Get number of active jobs for this customer"""
        return self.jobs.filter(status__in=['scheduled', 'in_progress']).count()

    @property
    def completed_jobs(self):
        """Get number of completed jobs for this customer"""
        return self.jobs.filter(status='completed').count()


class CustomerAddress(models.Model):
    """
    Address information for customers (supports multiple addresses per customer).
    """
    ADDRESS_TYPES = [
        ('home', 'Home'),
        ('work', 'Work'),
        ('other', 'Other'),
    ]

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='addresses',
        help_text='Customer this address belongs to'
    )

    address_type = models.CharField(
        max_length=20,
        choices=ADDRESS_TYPES,
        default='home',
        help_text='Type of address'
    )

    # Address Fields
    street_address = models.CharField(
        max_length=255,
        help_text='Street address'
    )
    apartment_unit = models.CharField(
        max_length=50,
        blank=True,
        help_text='Apartment, suite, or unit number'
    )
    city = models.CharField(
        max_length=100,
        help_text='City'
    )
    state = models.CharField(
        max_length=50,
        help_text='State or province'
    )
    postal_code = models.CharField(
        max_length=20,
        help_text='ZIP or postal code'
    )
    country = models.CharField(
        max_length=100,
        default='United States',
        help_text='Country'
    )

    # Geographic Information (for future mapping integration)
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text='Latitude coordinate'
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text='Longitude coordinate'
    )

    # Address Status
    is_primary = models.BooleanField(
        default=False,
        help_text='Whether this is the primary address for the customer'
    )

    is_active = models.BooleanField(
        default=True,
        help_text='Whether this address is still active'
    )

    # Additional Information
    instructions = models.TextField(
        blank=True,
        help_text='Special instructions for accessing this address'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Customer Address'
        verbose_name_plural = 'Customer Addresses'
        ordering = ['-is_primary', 'address_type']
        unique_together = ['customer', 'is_primary']  # Only one primary address per customer

    def __str__(self):
        return f"{self.customer.get_full_name()} - {self.get_full_address()}"

    def get_full_address(self):
        """Return formatted full address"""
        address_parts = [
            self.street_address,
            self.apartment_unit,
            f"{self.city}, {self.state} {self.postal_code}",
            self.country
        ]
        return ", ".join(filter(None, address_parts))

    def save(self, *args, **kwargs):
        """Ensure only one primary address per customer"""
        if self.is_primary:
            # Set all other addresses for this customer as non-primary
            CustomerAddress.objects.filter(
                customer=self.customer,
                is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)


class CustomerCommunication(models.Model):
    """
    Log of communications with customers (calls, emails, notes).
    """
    COMMUNICATION_TYPES = [
        ('phone', 'Phone Call'),
        ('email', 'Email'),
        ('text', 'Text Message'),
        ('in_person', 'In Person'),
        ('note', 'Internal Note'),
    ]

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='communications',
        help_text='Customer this communication is about'
    )

    communication_type = models.CharField(
        max_length=20,
        choices=COMMUNICATION_TYPES,
        help_text='Type of communication'
    )

    # Communication Details
    subject = models.CharField(
        max_length=200,
        blank=True,
        help_text='Subject or brief description'
    )

    message = models.TextField(
        help_text='Communication content or notes'
    )

    # Contact Information
    contact_method = models.CharField(
        max_length=50,
        blank=True,
        help_text='How the customer was contacted (phone number, email, etc.)'
    )

    # User Information
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='customer_communications',
        help_text='User who logged this communication'
    )

    # Follow-up
    requires_followup = models.BooleanField(
        default=False,
        help_text='Whether this communication requires follow-up'
    )

    followup_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Date when follow-up is needed'
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Customer Communication'
        verbose_name_plural = 'Customer Communications'
        indexes = [
            models.Index(fields=['customer', 'created_at']),
            models.Index(fields=['communication_type']),
            models.Index(fields=['requires_followup']),
        ]

    def __str__(self):
        return f"{self.customer.get_full_name()} - {self.get_communication_type_display()} ({self.created_at.date()})"
