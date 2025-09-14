from rest_framework import serializers
from .models import Quote, QuoteItem, QuoteTemplate, QuoteSettings
from customers.models import Customer
from inventory.models import InventoryItem


class QuoteItemSerializer(serializers.ModelSerializer):
    """Serializer for quote items"""
    inventory_item_name = serializers.CharField(source='inventory_item.name', read_only=True)
    inventory_item_sku = serializers.CharField(source='inventory_item.sku', read_only=True)
    line_total = serializers.ReadOnlyField()

    class Meta:
        model = QuoteItem
        fields = [
            'id', 'quote', 'category', 'description', 'details',
            'inventory_item', 'inventory_item_name', 'inventory_item_sku',
            'quantity', 'unit', 'unit_price', 'total_price', 'notes',
            'sort_order', 'created_at'
        ]
        read_only_fields = ['created_at', 'total_price']


class QuoteSerializer(serializers.ModelSerializer):
    """Serializer for quotes"""
    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    items = QuoteItemSerializer(many=True, read_only=True)
    item_count = serializers.SerializerMethodField()
    is_expired = serializers.ReadOnlyField()
    days_until_expiry = serializers.ReadOnlyField()
    estimated_completion_date = serializers.ReadOnlyField()

    class Meta:
        model = Quote
        fields = [
            'id', 'quote_number', 'customer', 'customer_name', 'title', 'description',
            'project_address', 'project_type', 'subtotal', 'tax_rate', 'tax_amount',
            'discount_amount', 'total_amount', 'valid_until', 'estimated_start_date',
            'estimated_completion_days', 'status', 'viewed_at', 'accepted_at',
            'declined_at', 'customer_notes', 'converted_to_job', 'scope_of_work',
            'exclusions', 'terms_and_conditions', 'created_by', 'created_by_name',
            'items', 'item_count', 'is_expired', 'days_until_expiry',
            'estimated_completion_date', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'created_at', 'updated_at', 'quote_number', 'subtotal', 'tax_amount',
            'total_amount', 'viewed_at', 'accepted_at', 'declined_at', 'converted_to_job',
            'is_expired', 'days_until_expiry', 'estimated_completion_date'
        ]

    def get_item_count(self, obj):
        return obj.items.count()


class QuoteCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating quotes with items"""
    items = QuoteItemSerializer(many=True)

    class Meta:
        model = Quote
        fields = [
            'customer', 'title', 'description', 'project_address', 'project_type',
            'tax_rate', 'discount_amount', 'valid_until', 'estimated_start_date',
            'estimated_completion_days', 'scope_of_work', 'exclusions',
            'terms_and_conditions', 'items'
        ]

    def validate_customer(self, value):
        """Validate that customer exists"""
        try:
            Customer.objects.get(id=value.id)
            return value
        except Customer.DoesNotExist:
            raise serializers.ValidationError("Customer not found.")

    def validate_valid_until(self, value):
        """Validate that valid_until is in the future"""
        from django.utils import timezone
        if value <= timezone.now().date():
            raise serializers.ValidationError("Valid until date must be in the future.")
        return value

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        quote = Quote.objects.create(**validated_data)

        # Create quote items
        subtotal = 0
        for item_data in items_data:
            item = QuoteItem.objects.create(quote=quote, **item_data)
            subtotal += item.total_price

        # Update quote subtotal and recalculate totals
        quote.subtotal = subtotal
        quote.save()

        return quote


class QuoteTemplateSerializer(serializers.ModelSerializer):
    """Serializer for quote templates"""
    usage_count = serializers.ReadOnlyField()
    template_item_count = serializers.SerializerMethodField()

    class Meta:
        model = QuoteTemplate
        fields = [
            'id', 'name', 'description', 'project_type', 'default_tax_rate',
            'default_validity_days', 'default_completion_days', 'default_scope_of_work',
            'default_exclusions', 'default_terms', 'template_items', 'usage_count',
            'is_active', 'created_by', 'template_item_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'usage_count']

    def get_template_item_count(self, obj):
        return len(obj.template_items) if obj.template_items else 0


class QuoteSettingsSerializer(serializers.ModelSerializer):
    """Serializer for quote settings"""

    class Meta:
        model = QuoteSettings
        fields = [
            'id', 'company_name', 'company_address', 'company_phone', 'company_email',
            'default_tax_rate', 'default_validity_days', 'default_terms',
            'auto_calculate_tax', 'require_deposit', 'deposit_percentage',
            'send_quote_emails', 'quote_email_subject', 'quote_email_template',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class QuoteSummarySerializer(serializers.Serializer):
    """Serializer for quote summary reports"""
    total_quotes = serializers.IntegerField()
    draft_quotes = serializers.IntegerField()
    sent_quotes = serializers.IntegerField()
    accepted_quotes = serializers.IntegerField()
    declined_quotes = serializers.IntegerField()
    expired_quotes = serializers.IntegerField()
    converted_quotes = serializers.IntegerField()
    total_value = serializers.DecimalField(max_digits=12, decimal_places=2)
    average_quote_value = serializers.DecimalField(max_digits=10, decimal_places=2)
    conversion_rate = serializers.DecimalField(max_digits=5, decimal_places=2)

    def to_representation(self, instance):
        return instance
