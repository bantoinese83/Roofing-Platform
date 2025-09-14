from rest_framework import serializers
from decimal import Decimal
from .models import PaymentMethod, Invoice, InvoiceItem, Payment, PaymentSettings


class PaymentMethodSerializer(serializers.ModelSerializer):
    """
    Serializer for PaymentMethod model.
    """
    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)

    class Meta:
        model = PaymentMethod
        fields = [
            'id', 'customer', 'customer_name', 'payment_type',
            'stripe_payment_method_id', 'stripe_customer_id',
            'last4', 'brand', 'expiry_month', 'expiry_year',
            'bank_name', 'is_default', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'stripe_payment_method_id', 'stripe_customer_id', 'created_at', 'updated_at']


class InvoiceItemSerializer(serializers.ModelSerializer):
    """
    Serializer for InvoiceItem model.
    """
    class Meta:
        model = InvoiceItem
        fields = [
            'id', 'description', 'quantity', 'unit_price',
            'total_price', 'inventory_item'
        ]
        read_only_fields = ['id', 'total_price']


class InvoiceSerializer(serializers.ModelSerializer):
    """
    Serializer for Invoice model.
    """
    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    job_title = serializers.CharField(source='job.title', read_only=True)
    items = InvoiceItemSerializer(many=True, read_only=True)
    amount_paid = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    amount_due = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    days_overdue = serializers.IntegerField(read_only=True)

    class Meta:
        model = Invoice
        fields = [
            'id', 'customer', 'customer_name', 'job', 'job_title',
            'invoice_number', 'title', 'description', 'subtotal',
            'tax_rate', 'tax_amount', 'discount_amount', 'total_amount',
            'status', 'issue_date', 'due_date', 'paid_date',
            'stripe_invoice_id', 'notes', 'customer_notes',
            'items', 'amount_paid', 'amount_due', 'is_overdue',
            'days_overdue', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'invoice_number', 'tax_amount', 'total_amount',
            'stripe_invoice_id', 'amount_paid', 'amount_due',
            'is_overdue', 'days_overdue', 'created_at', 'updated_at'
        ]


class InvoiceCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating invoices with line items.
    """
    items = InvoiceItemSerializer(many=True, required=False)

    class Meta:
        model = Invoice
        fields = [
            'customer', 'job', 'title', 'description', 'subtotal',
            'tax_rate', 'discount_amount', 'issue_date', 'due_date',
            'notes', 'customer_notes', 'items'
        ]

    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        invoice = Invoice.objects.create(**validated_data)

        # Create invoice items
        for item_data in items_data:
            InvoiceItem.objects.create(invoice=invoice, **item_data)

        return invoice


class PaymentSerializer(serializers.ModelSerializer):
    """
    Serializer for Payment model.
    """
    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    invoice_number = serializers.CharField(source='invoice.invoice_number', read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id', 'invoice', 'invoice_number', 'customer',
            'customer_name', 'payment_method', 'amount',
            'currency', 'status', 'stripe_payment_intent_id',
            'stripe_charge_id', 'processing_fee', 'net_amount',
            'failure_reason', 'payment_date', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'stripe_payment_intent_id', 'stripe_charge_id',
            'processing_fee', 'net_amount', 'payment_date',
            'created_at', 'updated_at'
        ]


class PaymentIntentSerializer(serializers.Serializer):
    """
    Serializer for PaymentIntent creation requests.
    """
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    currency = serializers.CharField(max_length=3, default='usd')
    customer_id = serializers.CharField(required=False)
    payment_method_id = serializers.CharField(required=False)
    metadata = serializers.DictField(required=False)


class PaymentSettingsSerializer(serializers.ModelSerializer):
    """
    Serializer for PaymentSettings model.
    """
    class Meta:
        model = PaymentSettings
        fields = [
            'id', 'stripe_publishable_key', 'stripe_secret_key',
            'stripe_webhook_secret', 'default_currency', 'default_tax_rate',
            'payment_terms_days', 'enable_payment_processing',
            'enable_automatic_invoicing', 'require_payment_method',
            'send_invoice_emails', 'send_payment_receipts',
            'notify_on_payment_success', 'notify_on_payment_failure'
        ]
        extra_kwargs = {
            'stripe_secret_key': {'write_only': True},
            'stripe_webhook_secret': {'write_only': True}
        }
