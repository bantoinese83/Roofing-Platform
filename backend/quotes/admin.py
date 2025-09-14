from django.contrib import admin
from .models import Quote, QuoteItem, QuoteTemplate, QuoteSettings


class QuoteItemInline(admin.TabularInline):
    model = QuoteItem
    extra = 0
    fields = ['description', 'quantity', 'unit', 'unit_price', 'total_price']
    readonly_fields = ['total_price']


@admin.register(Quote)
class QuoteAdmin(admin.ModelAdmin):
    list_display = [
        'quote_number', 'customer', 'title', 'status', 'total_amount',
        'valid_until', 'created_by', 'created_at'
    ]
    list_filter = ['status', 'project_type', 'created_at', 'valid_until']
    search_fields = ['quote_number', 'customer__first_name', 'customer__last_name', 'title']
    readonly_fields = ['quote_number', 'created_at', 'updated_at']
    inlines = [QuoteItemInline]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('customer', 'created_by')


@admin.register(QuoteItem)
class QuoteItemAdmin(admin.ModelAdmin):
    list_display = [
        'quote', 'description', 'quantity', 'unit', 'unit_price', 'total_price'
    ]
    list_filter = ['category', 'unit']
    search_fields = ['quote__quote_number', 'description']
    readonly_fields = ['total_price']


@admin.register(QuoteTemplate)
class QuoteTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'project_type', 'usage_count', 'is_active', 'created_by']
    list_filter = ['project_type', 'is_active', 'created_at']
    search_fields = ['name', 'description']


@admin.register(QuoteSettings)
class QuoteSettingsAdmin(admin.ModelAdmin):
    list_display = ['company_name', 'default_tax_rate', 'default_validity_days']
    readonly_fields = ['created_at', 'updated_at']

    def has_add_permission(self, request):
        # Only allow one settings object
        return not QuoteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        # Prevent deletion of the settings object
        return False
