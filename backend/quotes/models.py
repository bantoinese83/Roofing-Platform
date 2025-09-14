from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from decimal import Decimal


class Quote(models.Model):
    """
    Quotes and estimates for roofing projects.
    """

    QUOTE_STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sent', 'Sent to Customer'),
        ('viewed', 'Viewed by Customer'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
        ('expired', 'Expired'),
        ('converted', 'Converted to Job'),
    ]

    # Relationships
    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.CASCADE,
        related_name='quotes',
        help_text='Customer this quote is for'
    )

    # Quote details
    quote_number = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        help_text='Unique quote number'
    )

    title = models.CharField(
        max_length=200,
        help_text='Quote title'
    )

    description = models.TextField(
        blank=True,
        help_text='Detailed description of the proposed work'
    )

    # Project details
    project_address = models.TextField(
        help_text='Address where work will be performed'
    )

    project_type = models.CharField(
        max_length=50,
        choices=[
            ('repair', 'Repair'),
            ('replacement', 'Replacement'),
            ('inspection', 'Inspection'),
            ('maintenance', 'Maintenance'),
            ('emergency', 'Emergency'),
        ],
        help_text='Type of roofing project'
    )

    # Financial details
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text='Subtotal before tax and discounts'
    )

    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Tax rate as percentage'
    )

    tax_amount = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Calculated tax amount'
    )

    discount_amount = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Discount amount'
    )

    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text='Final total amount'
    )

    # Validity and timing
    valid_until = models.DateField(
        help_text='Date until which this quote is valid'
    )

    estimated_start_date = models.DateField(
        null=True,
        blank=True,
        help_text='Estimated project start date'
    )

    estimated_completion_days = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Estimated days to complete the project'
    )

    # Status and tracking
    status = models.CharField(
        max_length=20,
        choices=QUOTE_STATUS_CHOICES,
        default='draft',
        help_text='Current status of the quote'
    )

    # Customer interaction
    viewed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When the customer first viewed the quote'
    )

    accepted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When the customer accepted the quote'
    )

    declined_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When the customer declined the quote'
    )

    customer_notes = models.TextField(
        blank=True,
        help_text='Notes from the customer'
    )

    # Conversion to job
    converted_to_job = models.ForeignKey(
        'jobs.Job',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='source_quote',
        help_text='Job created from this quote'
    )

    # Additional details
    scope_of_work = models.TextField(
        blank=True,
        help_text='Detailed scope of work'
    )

    exclusions = models.TextField(
        blank=True,
        help_text='What is not included in this quote'
    )

    terms_and_conditions = models.TextField(
        blank=True,
        help_text='Terms and conditions for this quote'
    )

    # File attachments
    attachments = models.ManyToManyField(
        'jobs.JobDocument',
        blank=True,
        related_name='quotes',
        help_text='Documents attached to this quote (photos, drawings, etc.)'
    )

    # Metadata
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_quotes',
        help_text='User who created this quote'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Quote'
        verbose_name_plural = 'Quotes'
        indexes = [
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['status', 'valid_until']),
            models.Index(fields=['quote_number']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"Quote {self.quote_number} - {self.customer.get_full_name()}"

    def save(self, *args, **kwargs):
        # Auto-generate quote number if not set
        if not self.quote_number:
            import datetime
            today = datetime.date.today()
            date_str = today.strftime('%Y%m%d')

            # Find the next number for today
            today_quotes = Quote.objects.filter(
                quote_number__startswith=f'Q-{date_str}',
                created_at__date=today
            ).count()

            self.quote_number = f'Q-{date_str}-{str(today_quotes + 1).zfill(3)}'

        # Calculate tax and total
        self.tax_amount = (self.subtotal * self.tax_rate) / 100
        self.total_amount = self.subtotal + self.tax_amount - self.discount_amount

        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        """Check if quote has expired"""
        from django.utils import timezone
        return self.valid_until < timezone.now().date()

    @property
    def days_until_expiry(self):
        """Calculate days until expiry"""
        from django.utils import timezone
        if self.is_expired:
            return 0
        return (self.valid_until - timezone.now().date()).days

    @property
    def estimated_completion_date(self):
        """Calculate estimated completion date"""
        if self.estimated_start_date and self.estimated_completion_days:
            return self.estimated_start_date + timedelta(days=self.estimated_completion_days)
        return None

    def mark_as_viewed(self):
        """Mark quote as viewed by customer"""
        from django.utils import timezone
        if not self.viewed_at:
            self.viewed_at = timezone.now()
            if self.status == 'sent':
                self.status = 'viewed'
            self.save()

    def accept_quote(self, notes=''):
        """Accept the quote"""
        from django.utils import timezone
        self.status = 'accepted'
        self.accepted_at = timezone.now()
        self.customer_notes = notes
        self.save()

    def decline_quote(self, notes=''):
        """Decline the quote"""
        from django.utils import timezone
        self.status = 'declined'
        self.declined_at = timezone.now()
        self.customer_notes = notes
        self.save()

    def convert_to_job(self):
        """Convert accepted quote to a job"""
        if self.status != 'accepted':
            raise ValueError("Only accepted quotes can be converted to jobs")

        from jobs.models import Job

        job = Job.objects.create(
            customer=self.customer,
            title=f"Job from Quote {self.quote_number}",
            description=self.description,
            job_type=self.project_type,
            status='scheduled',
            address=self.project_address,
            estimated_cost=self.total_amount,
            special_instructions=self.scope_of_work,
            created_by=self.created_by
        )

        # Copy quote items to job notes
        from jobs.models import JobNote
        JobNote.objects.create(
            job=job,
            note_type='system',
            content=f"Converted from Quote {self.quote_number}",
            created_by=self.created_by
        )

        self.converted_to_job = job
        self.status = 'converted'
        self.save()

        return job


class QuoteItem(models.Model):
    """
    Individual line items in a quote.
    """

    ITEM_CATEGORIES = [
        ('labor', 'Labor'),
        ('materials', 'Materials'),
        ('equipment', 'Equipment'),
        ('permits', 'Permits & Inspections'),
        ('disposal', 'Waste Disposal'),
        ('other', 'Other'),
    ]

    quote = models.ForeignKey(
        Quote,
        on_delete=models.CASCADE,
        related_name='items',
        help_text='Quote this item belongs to'
    )

    category = models.CharField(
        max_length=20,
        choices=ITEM_CATEGORIES,
        help_text='Category of this line item'
    )

    description = models.CharField(
        max_length=200,
        help_text='Description of the item/service'
    )

    details = models.TextField(
        blank=True,
        help_text='Additional details about this item'
    )

    quantity = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('1.00'),
        help_text='Quantity of items'
    )

    unit = models.CharField(
        max_length=20,
        default='each',
        help_text='Unit of measurement (sq ft, linear ft, each, etc.)'
    )

    unit_price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        help_text='Price per unit'
    )

    total_price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        help_text='Total price for this line item'
    )

    # Optional reference to inventory item
    inventory_item = models.ForeignKey(
        'inventory.InventoryItem',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='quote_items',
        help_text='Related inventory item'
    )

    # Sorting
    sort_order = models.PositiveIntegerField(
        default=0,
        help_text='Order in which to display this item'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['sort_order', 'created_at']
        verbose_name = 'Quote Item'
        verbose_name_plural = 'Quote Items'
        indexes = [
            models.Index(fields=['quote', 'category']),
            models.Index(fields=['quote', 'sort_order']),
        ]

    def __str__(self):
        return f"{self.quote.quote_number} - {self.description}"

    def save(self, *args, **kwargs):
        # Calculate total price
        self.total_price = self.quantity * self.unit_price
        super().save(*args, **kwargs)


class QuoteTemplate(models.Model):
    """
    Reusable templates for creating quotes.
    """

    name = models.CharField(
        max_length=100,
        unique=True,
        help_text='Name of the template'
    )

    description = models.TextField(
        blank=True,
        help_text='Description of when to use this template'
    )

    project_type = models.CharField(
        max_length=50,
        choices=[
            ('repair', 'Repair'),
            ('replacement', 'Replacement'),
            ('inspection', 'Inspection'),
            ('maintenance', 'Maintenance'),
            ('emergency', 'Emergency'),
        ],
        help_text='Type of project this template is for'
    )

    # Default values
    default_tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Default tax rate for this template'
    )

    default_validity_days = models.PositiveIntegerField(
        default=30,
        help_text='Default validity period in days'
    )

    default_completion_days = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Default estimated completion days'
    )

    # Template content
    default_scope_of_work = models.TextField(
        blank=True,
        help_text='Default scope of work text'
    )

    default_exclusions = models.TextField(
        blank=True,
        help_text='Default exclusions text'
    )

    default_terms = models.TextField(
        blank=True,
        help_text='Default terms and conditions'
    )

    # Template items
    template_items = models.JSONField(
        default=list,
        help_text='Pre-defined line items for this template'
    )

    # Usage tracking
    usage_count = models.PositiveIntegerField(
        default=0,
        help_text='How many times this template has been used'
    )

    is_active = models.BooleanField(
        default=True,
        help_text='Whether this template is available for use'
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_quote_templates',
        help_text='User who created this template'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Quote Template'
        verbose_name_plural = 'Quote Templates'

    def __str__(self):
        return f"{self.name} ({self.get_project_type_display()})"

    def increment_usage(self):
        """Increment usage count"""
        self.usage_count += 1
        self.save(update_fields=['usage_count'])

    def create_quote_from_template(self, customer, project_address, estimated_start_date=None):
        """Create a new quote from this template"""
        from django.utils import timezone

        quote = Quote.objects.create(
            customer=customer,
            title=f"{self.name} - {customer.get_full_name()}",
            project_address=project_address,
            project_type=self.project_type,
            tax_rate=self.default_tax_rate,
            valid_until=timezone.now().date() + timedelta(days=self.default_validity_days),
            estimated_start_date=estimated_start_date,
            estimated_completion_days=self.default_completion_days,
            scope_of_work=self.default_scope_of_work,
            exclusions=self.default_exclusions,
            terms_and_conditions=self.default_terms,
        )

        # Add template items
        for item_data in self.template_items:
            QuoteItem.objects.create(
                quote=quote,
                **item_data
            )

        # Recalculate quote totals
        quote.save()

        # Increment usage count
        self.increment_usage()

        return quote


class QuoteSettings(models.Model):
    """
    Global quote and estimate settings.
    """

    # Business information
    company_name = models.CharField(
        max_length=100,
        default='Roofing Platform',
        help_text='Company name for quotes'
    )

    company_address = models.TextField(
        blank=True,
        help_text='Company address for quotes'
    )

    company_phone = models.CharField(
        max_length=20,
        blank=True,
        help_text='Company phone number'
    )

    company_email = models.EmailField(
        blank=True,
        help_text='Company email address'
    )

    # Default settings
    default_tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('8.25'),
        help_text='Default tax rate for quotes'
    )

    default_validity_days = models.PositiveIntegerField(
        default=30,
        help_text='Default quote validity in days'
    )

    default_terms = models.TextField(
        blank=True,
        default="""
Terms and Conditions:
1. This quote is valid for the period specified above.
2. Work will begin on the estimated start date, weather permitting.
3. Final pricing may vary based on actual conditions discovered during work.
4. Payment terms: 50% deposit required to schedule, 50% due upon completion.
5. All permits and inspections are the responsibility of the homeowner unless otherwise noted.
        """.strip(),
        help_text='Default terms and conditions text'
    )

    # Feature toggles
    auto_calculate_tax = models.BooleanField(
        default=True,
        help_text='Automatically calculate tax on quotes'
    )

    require_deposit = models.BooleanField(
        default=True,
        help_text='Require deposit for quote acceptance'
    )

    deposit_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('50.0'),
        help_text='Required deposit percentage'
    )

    # Email settings
    send_quote_emails = models.BooleanField(
        default=True,
        help_text='Automatically send quotes via email'
    )

    quote_email_subject = models.CharField(
        max_length=200,
        default='Quote for Roofing Services - {quote_number}',
        help_text='Email subject template (use {quote_number} placeholder)'
    )

    quote_email_template = models.TextField(
        default="""
Dear {customer_name},

Please find attached our quote {quote_number} for roofing services at {project_address}.

Quote Total: ${total_amount}
Valid Until: {valid_until}

If you have any questions or would like to proceed, please contact us at {company_phone}.

Thank you for considering our services!

Best regards,
{company_name}
{company_phone}
        """.strip(),
        help_text='Email template for sending quotes'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Quote Settings'
        verbose_name_plural = 'Quote Settings'

    def __str__(self):
        return "Quote Settings"

    @classmethod
    def get_settings(cls):
        """Get the global quote settings (singleton pattern)."""
        settings_obj, created = cls.objects.get_or_create(
            defaults={
                'company_name': 'Roofing Platform',
                'default_tax_rate': Decimal('8.25'),
                'default_validity_days': 30,
            }
        )
        return settings_obj
