from django.contrib import admin
from .models import (
    InventoryCategory, Supplier, InventoryItem, ItemSupplier,
    StockTransaction, PurchaseOrder, PurchaseOrderItem
)


@admin.register(InventoryCategory)
class InventoryCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent_category', 'is_active', 'created_at']
    list_filter = ['is_active', 'parent_category', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['name']


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ['name', 'contact_person', 'email', 'phone', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'contact_person', 'email']
    ordering = ['name']


class ItemSupplierInline(admin.TabularInline):
    model = ItemSupplier
    extra = 0
    fields = ['supplier', 'supplier_sku', 'supplier_price', 'minimum_order_quantity', 'lead_time_days', 'is_preferred']


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'sku', 'category', 'current_stock', 'unit',
        'stock_status', 'unit_cost', 'selling_price', 'status', 'is_active'
    ]
    list_filter = ['status', 'is_active', 'category', 'unit']
    search_fields = ['name', 'sku', 'description']
    ordering = ['name']
    inlines = [ItemSupplierInline]

    def stock_status(self, obj):
        return obj.stock_status.replace('_', ' ').title()
    stock_status.short_description = 'Stock Status'


@admin.register(ItemSupplier)
class ItemSupplierAdmin(admin.ModelAdmin):
    list_display = ['item', 'supplier', 'supplier_price', 'minimum_order_quantity', 'lead_time_days', 'is_preferred']
    list_filter = ['is_preferred', 'supplier']
    search_fields = ['item__name', 'supplier__name', 'supplier_sku']
    ordering = ['item__name', 'supplier__name']


@admin.register(StockTransaction)
class StockTransactionAdmin(admin.ModelAdmin):
    list_display = [
        'item', 'transaction_type', 'quantity_change', 'new_quantity',
        'reason', 'performed_by', 'created_at'
    ]
    list_filter = ['transaction_type', 'created_at', 'performed_by']
    search_fields = ['item__name', 'reason', 'reference']
    ordering = ['-created_at']
    readonly_fields = ['created_at']


class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 0
    fields = ['inventory_item', 'quantity_ordered', 'quantity_received', 'unit_price', 'line_total']
    readonly_fields = ['line_total']


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = [
        'po_number', 'supplier', 'status', 'order_date',
        'total_amount', 'expected_delivery_date', 'created_by'
    ]
    list_filter = ['status', 'supplier', 'order_date', 'expected_delivery_date']
    search_fields = ['po_number', 'supplier__name', 'notes']
    ordering = ['-created_at']
    inlines = [PurchaseOrderItemInline]
    readonly_fields = ['po_number', 'created_at', 'updated_at']


@admin.register(PurchaseOrderItem)
class PurchaseOrderItemAdmin(admin.ModelAdmin):
    list_display = [
        'purchase_order', 'inventory_item', 'quantity_ordered',
        'quantity_received', 'unit_price', 'line_total'
    ]
    list_filter = ['purchase_order__status', 'inventory_item__category']
    search_fields = ['purchase_order__po_number', 'inventory_item__name']
    ordering = ['purchase_order__created_at']
    readonly_fields = ['line_total']
