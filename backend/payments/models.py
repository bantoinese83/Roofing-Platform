from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from decimal import Decimal


class PaymentMethod(models.Model):
    """
    Customer payment methods stored securely with Stripe.
    """

    PAYMENT_TYPES = [
        ('card', 'Credit/Debit Card'),
        ('bank_account', 'Bank Account'),
    ]

    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.CASCADE,
        related_name='payment_methods',
        help_text='Customer this payment method belongs to'
    )

    payment_type = models.CharField(
        max_length=20,
        choices=PAYMENT_TYPES,
        help_text='Type of payment method'
    )

    # Stripe identifiers
    stripe_payment_method_id = models.CharField(
        max_length=100,
        unique=True,
        help_text='Stripe PaymentMethod ID'
    )

    stripe_customer_id = models.CharField(
        max_length=100,
        help_text='Stripe Customer ID'
    )

    # Payment method details (masked for security)
    last4 = models.CharField(
        max_length=4,
        blank=True,
        help_text='Last 4 digits of card/bank account'
    )

    brand = models.CharField(
        max_length=50,
        blank=True,
        help_text='Card brand (visa, mastercard, etc.)'
    )

    expiry_month = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Card expiry month'
    )

    expiry_year = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Card expiry year'
    )

    bank_name = models.CharField(
        max_length=100,
        blank=True,
        help_text='Bank name for ACH payments'
    )

    # Status
    is_default = models.BooleanField(
        default=False,
        help_text='Whether this is the default payment method'
    )

    is_active = models.BooleanField(
        default=True,
        help_text='Whether this payment method is active'
    )

    # Metadata
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_payment_methods',
        help_text='User who added this payment method'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_default', '-created_at']
        verbose_name = 'Payment Method'
        verbose_name_plural = 'Payment Methods'
        unique_together = ['customer', 'stripe_payment_method_id']

    def __str__(self):
        return f"{self.customer.get_full_name()} - {self.get_payment_type_display()} ****{self.last4}"

    def save(self, *args, **kwargs):
        # Ensure only one default payment method per customer
        if self.is_default:
            PaymentMethod.objects.filter(
                customer=self.customer,
                is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)


class Invoice(models.Model):
    """
    Invoices for jobs and services.
    """

    INVOICE_STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
    ]

    # Relationships
    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.CASCADE,
        related_name='invoices',
        help_text='Customer being invoiced'
    )

    job = models.ForeignKey(
        'jobs.Job',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invoices',
        help_text='Job this invoice is for (optional)'
    )

    # Invoice details
    invoice_number = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        help_text='Unique invoice number'
    )

    title = models.CharField(
        max_length=200,
        help_text='Invoice title/description'
    )

    description = models.TextField(
        blank=True,
        help_text='Detailed description of services'
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
        help_text='Tax rate as percentage (e.g., 8.25 for 8.25%)'
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

    # Status and dates
    status = models.CharField(
        max_length=20,
        choices=INVOICE_STATUS_CHOICES,
        default='draft',
        help_text='Current status of the invoice'
    )

    issue_date = models.DateField(
        help_text='Date the invoice was issued'
    )

    due_date = models.DateField(
        help_text='Payment due date'
    )

    paid_date = models.DateField(
        null=True,
        blank=True,
        help_text='Date payment was received'
    )

    # Stripe integration
    stripe_invoice_id = models.CharField(
        max_length=100,
        blank=True,
        help_text='Stripe Invoice ID'
    )

    # Notes
    notes = models.TextField(
        blank=True,
        help_text='Internal notes'
    )

    customer_notes = models.TextField(
        blank=True,
        help_text='Notes visible to customer'
    )

    # Metadata
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_invoices',
        help_text='User who created this invoice'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-issue_date', '-created_at']
        verbose_name = 'Invoice'
        verbose_name_plural = 'Invoices'
        indexes = [
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['status', 'due_date']),
            models.Index(fields=['invoice_number']),
            models.Index(fields=['job', 'status']),
        ]

    def __str__(self):
        return f"Invoice {self.invoice_number} - {self.customer.get_full_name()}"

    def save(self, *args, **kwargs):
        # Auto-generate invoice number if not set
        if not self.invoice_number:
            import datetime
            today = datetime.date.today()
            date_str = today.strftime('%Y%m%d')

            # Find the next number for today
            today_invoices = Invoice.objects.filter(
                invoice_number__startswith=f'INV-{date_str}',
                created_at__date=today
            ).count()

            self.invoice_number = f'INV-{date_str}-{str(today_invoices + 1).zfill(3)}'

        # Calculate tax and total
        self.tax_amount = (self.subtotal * self.tax_rate) / 100
        self.total_amount = self.subtotal + self.tax_amount - self.discount_amount

        super().save(*args, **kwargs)

    @property
    def is_overdue(self):
        """Check if invoice is overdue"""
        from django.utils import timezone
        return (
            self.status in ['sent', 'overdue'] and
            self.due_date < timezone.now().date()
        )

    @property
    def days_overdue(self):
        """Calculate days overdue"""
        if not self.is_overdue:
            return 0
        from django.utils import timezone
        return (timezone.now().date() - self.due_date).days

    @property
    def amount_paid(self):
        """Calculate total amount paid"""
        return sum(payment.amount for payment in self.payments.filter(status='succeeded'))

    @property
    def amount_due(self):
        """Calculate remaining amount due"""
        return self.total_amount - self.amount_paid

    def mark_as_paid(self, paid_date=None):
        """Mark invoice as paid"""
        from django.utils import timezone
        self.status = 'paid'
        self.paid_date = paid_date or timezone.now().date()
        self.save()

    def send_to_customer(self):
        """Send invoice to customer via email"""
        from notifications.services import notification_service

        # This would integrate with email service to send invoice
        # For now, just mark as sent
        if self.status == 'draft':
            self.status = 'sent'
            self.save()

        return True


class InvoiceItem(models.Model):
    """
    Individual line items on an invoice.
    """

    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name='items',
        help_text='Invoice this item belongs to'
    )

    description = models.CharField(
        max_length=200,
        help_text='Description of the item/service'
    )

    quantity = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('1.00'),
        help_text='Quantity of items'
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
        related_name='invoice_items',
        help_text='Related inventory item'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = 'Invoice Item'
        verbose_name_plural = 'Invoice Items'

    def __str__(self):
        return f"{self.invoice.invoice_number} - {self.description}"

    def save(self, *args, **kwargs):
        # Calculate total price
        self.total_price = self.quantity * self.unit_price
        super().save(*args, **kwargs)


class Payment(models.Model):
    """
    Payment transactions processed through Stripe.
    """

    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('succeeded', 'Succeeded'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]

    # Relationships
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name='payments',
        help_text='Invoice being paid'
    )

    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.CASCADE,
        related_name='payments',
        help_text='Customer making the payment'
    )

    payment_method = models.ForeignKey(
        PaymentMethod,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payments',
        help_text='Payment method used'
    )

    # Payment details
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text='Payment amount'
    )

    currency = models.CharField(
        max_length=3,
        default='usd',
        help_text='Payment currency'
    )

    status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending',
        help_text='Payment status'
    )

    # Stripe identifiers
    stripe_payment_intent_id = models.CharField(
        max_length=100,
        blank=True,
        help_text='Stripe PaymentIntent ID'
    )

    stripe_charge_id = models.CharField(
        max_length=100,
        blank=True,
        help_text='Stripe Charge ID'
    )

    # Processing details
    processing_fee = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Stripe processing fee'
    )

    net_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Net amount after fees'
    )

    # Error handling
    failure_reason = models.TextField(
        blank=True,
        help_text='Reason for payment failure'
    )

    # Metadata
    payment_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Date/time payment was processed'
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='processed_payments',
        help_text='User who processed this payment'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-payment_date', '-created_at']
        verbose_name = 'Payment'
        verbose_name_plural = 'Payments'
        indexes = [
            models.Index(fields=['invoice', 'status']),
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['status', 'payment_date']),
        ]

    def __str__(self):
        return f"Payment {self.stripe_payment_intent_id} - ${self.amount}"

    def process_refund(self, amount=None, reason=''):
        """Process a refund through Stripe"""
        from .services import PaymentService
        service = PaymentService()
        return service.process_refund(self, amount, reason)

    def mark_as_succeeded(self, stripe_charge_id=None, processing_fee=None):
        """Mark payment as succeeded"""
        from django.utils import timezone

        self.status = 'succeeded'
        self.payment_date = timezone.now()

        if stripe_charge_id:
            self.stripe_charge_id = stripe_charge_id

        if processing_fee is not None:
            self.processing_fee = processing_fee
            self.net_amount = self.amount - processing_fee

        self.save()

        # Update invoice status if fully paid
        if self.invoice.amount_due <= 0:
            self.invoice.mark_as_paid(self.payment_date.date())


class PaymentSettings(models.Model):
    """
    Global payment processing settings.
    """

    # Stripe API settings
    stripe_publishable_key = models.CharField(
        max_length=200,
        blank=True,
        help_text='Stripe Publishable Key (safe to expose to frontend)'
    )

    stripe_secret_key = models.CharField(
        max_length=200,
        blank=True,
        help_text='Stripe Secret Key (keep secure)'
    )

    stripe_webhook_secret = models.CharField(
        max_length=200,
        blank=True,
        help_text='Stripe Webhook Secret for webhook verification'
    )

    # Business settings
    default_currency = models.CharField(
        max_length=3,
        default='usd',
        help_text='Default currency for payments'
    )

    default_tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Default tax rate as percentage'
    )

    payment_terms_days = models.PositiveIntegerField(
        default=30,
        help_text='Default payment terms in days'
    )

    # Feature toggles
    enable_payment_processing = models.BooleanField(
        default=True,
        help_text='Enable payment processing features'
    )

    enable_automatic_invoicing = models.BooleanField(
        default=False,
        help_text='Automatically create invoices for completed jobs'
    )

    require_payment_method = models.BooleanField(
        default=False,
        help_text='Require customers to save payment methods'
    )

    # Email settings
    send_invoice_emails = models.BooleanField(
        default=True,
        help_text='Send invoice emails to customers'
    )

    send_payment_receipts = models.BooleanField(
        default=True,
        help_text='Send payment receipt emails'
    )

    # Notification settings
    notify_on_payment_success = models.BooleanField(
        default=True,
        help_text='Notify office staff of successful payments'
    )

    notify_on_payment_failure = models.BooleanField(
        default=True,
        help_text='Notify office staff of failed payments'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Payment Settings'
        verbose_name_plural = 'Payment Settings'

    def __str__(self):
        return "Payment Processing Settings"

    @classmethod
    def get_settings(cls):
        """Get the global payment settings (singleton pattern)."""
        settings_obj, created = cls.objects.get_or_create(
            defaults={
                'default_currency': 'usd',
                'enable_payment_processing': True,
            }
        )
        return settings_obj
