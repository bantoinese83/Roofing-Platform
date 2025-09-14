from rest_framework import serializers
from .models import (
    InventoryCategory, Supplier, InventoryItem, ItemSupplier,
    StockTransaction, PurchaseOrder, PurchaseOrderItem
)


class InventoryCategorySerializer(serializers.ModelSerializer):
    """Serializer for inventory categories"""
    subcategories = serializers.SerializerMethodField()
    parent_name = serializers.CharField(source='parent_category.name', read_only=True)

    class Meta:
        model = InventoryCategory
        fields = [
            'id', 'name', 'description', 'parent_category', 'parent_name',
            'subcategories', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_subcategories(self, obj):
        subcategories = obj.subcategories.filter(is_active=True)
        return InventoryCategorySerializer(subcategories, many=True, context=self.context).data


class SupplierSerializer(serializers.ModelSerializer):
    """Serializer for suppliers"""
    item_count = serializers.SerializerMethodField()

    class Meta:
        model = Supplier
        fields = [
            'id', 'name', 'contact_person', 'email', 'phone', 'address',
            'website', 'notes', 'is_active', 'item_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_item_count(self, obj):
        return obj.supplied_items.count()


class ItemSupplierSerializer(serializers.ModelSerializer):
    """Serializer for item-supplier relationships"""
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    item_name = serializers.CharField(source='item.name', read_only=True)

    class Meta:
        model = ItemSupplier
        fields = [
            'id', 'item', 'item_name', 'supplier', 'supplier_name',
            'supplier_sku', 'supplier_price', 'minimum_order_quantity',
            'lead_time_days', 'is_preferred', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class InventoryItemSerializer(serializers.ModelSerializer):
    """Serializer for inventory items"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    stock_status = serializers.ReadOnlyField()
    stock_value = serializers.ReadOnlyField()
    needs_reorder = serializers.ReadOnlyField()
    suppliers = ItemSupplierSerializer(source='supplier_relationships', many=True, read_only=True)

    class Meta:
        model = InventoryItem
        fields = [
            'id', 'name', 'sku', 'description', 'category', 'category_name',
            'unit', 'current_stock', 'minimum_stock', 'maximum_stock',
            'reorder_point', 'unit_cost', 'selling_price', 'status',
            'is_active', 'location', 'barcode', 'stock_status', 'stock_value',
            'needs_reorder', 'suppliers', 'created_by', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'stock_status', 'stock_value', 'needs_reorder']


class StockTransactionSerializer(serializers.ModelSerializer):
    """Serializer for stock transactions"""
    item_name = serializers.CharField(source='item.name', read_only=True)
    performed_by_name = serializers.CharField(source='performed_by.get_full_name', read_only=True)
    job_number = serializers.CharField(source='related_job.job_number', read_only=True)
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)

    class Meta:
        model = StockTransaction
        fields = [
            'id', 'item', 'item_name', 'transaction_type', 'quantity_change',
            'new_quantity', 'related_job', 'job_number', 'supplier', 'supplier_name',
            'reason', 'reference', 'notes', 'performed_by', 'performed_by_name', 'created_at'
        ]
        read_only_fields = ['created_at']


class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    """Serializer for purchase order items"""
    inventory_item_name = serializers.CharField(source='inventory_item.name', read_only=True)
    inventory_item_sku = serializers.CharField(source='inventory_item.sku', read_only=True)
    quantity_remaining = serializers.ReadOnlyField()
    is_fully_received = serializers.ReadOnlyField()

    class Meta:
        model = PurchaseOrderItem
        fields = [
            'id', 'purchase_order', 'inventory_item', 'inventory_item_name',
            'inventory_item_sku', 'quantity_ordered', 'quantity_received',
            'unit_price', 'line_total', 'notes', 'quantity_remaining',
            'is_fully_received', 'created_at'
        ]
        read_only_fields = ['created_at', 'quantity_remaining', 'is_fully_received']


class PurchaseOrderSerializer(serializers.ModelSerializer):
    """Serializer for purchase orders"""
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    items = PurchaseOrderItemSerializer(many=True, read_only=True)
    item_count = serializers.SerializerMethodField()
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.get_full_name', read_only=True)

    class Meta:
        model = PurchaseOrder
        fields = [
            'id', 'supplier', 'supplier_name', 'po_number', 'status', 'order_date',
            'expected_delivery_date', 'actual_delivery_date', 'subtotal', 'tax_amount',
            'shipping_cost', 'total_amount', 'notes', 'tracking_number',
            'created_by', 'created_by_name', 'approved_by', 'approved_by_name',
            'item_count', 'items', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'po_number', 'item_count']

    def get_item_count(self, obj):
        return obj.items.count()


class PurchaseOrderCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating purchase orders with items"""
    items = PurchaseOrderItemSerializer(many=True)

    class Meta:
        model = PurchaseOrder
        fields = [
            'supplier', 'expected_delivery_date', 'notes', 'items'
        ]

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        purchase_order = PurchaseOrder.objects.create(**validated_data)

        # Calculate subtotal
        subtotal = 0
        for item_data in items_data:
            item = PurchaseOrderItem.objects.create(
                purchase_order=purchase_order,
                **item_data
            )
            subtotal += item.line_total

        purchase_order.subtotal = subtotal
        purchase_order.save()

        return purchase_order


class StockUpdateSerializer(serializers.Serializer):
    """Serializer for stock updates"""
    item_id = serializers.IntegerField()
    quantity_change = serializers.DecimalField(max_digits=8, decimal_places=2)
    reason = serializers.CharField(max_length=200, required=False)
    reference = serializers.CharField(max_length=100, required=False)

    def validate_item_id(self, value):
        try:
            item = InventoryItem.objects.get(id=value)
            return value
        except InventoryItem.DoesNotExist:
            raise serializers.ValidationError("Inventory item not found.")

    def validate(self, data):
        item_id = data['item_id']
        quantity_change = data['quantity_change']

        item = InventoryItem.objects.get(id=item_id)
        new_stock = item.current_stock + quantity_change

        if new_stock < 0:
            raise serializers.ValidationError("Stock cannot go below zero.")

        return data


class InventoryReportSerializer(serializers.Serializer):
    """Serializer for inventory reports"""
    total_items = serializers.IntegerField()
    total_value = serializers.DecimalField(max_digits=12, decimal_places=2)
    low_stock_items = serializers.IntegerField()
    out_of_stock_items = serializers.IntegerField()
    items_by_category = serializers.DictField()
    recent_transactions = serializers.ListField()

    def to_representation(self, instance):
        return instance
