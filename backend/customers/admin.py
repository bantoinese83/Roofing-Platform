from django.contrib import admin
from .models import Customer, CustomerAddress, CustomerCommunication


class CustomerAddressInline(admin.TabularInline):
    """
    Inline admin for CustomerAddress.
    """
    model = CustomerAddress
    extra = 0
    fields = ['address_type', 'street_address', 'city', 'state', 'postal_code', 'is_primary', 'is_active']
    readonly_fields = ['created_at', 'updated_at']


class CustomerCommunicationInline(admin.TabularInline):
    """
    Inline admin for CustomerCommunication.
    """
    model = CustomerCommunication
    extra = 0
    fields = ['communication_type', 'subject', 'message', 'requires_followup', 'created_by']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    """
    Admin for Customer model.
    """
    list_display = ['get_full_name', 'email', 'phone_number', 'is_active', 'total_jobs', 'created_at']
    list_filter = ['is_active', 'marketing_opt_in', 'created_at', 'created_by']
    search_fields = ['first_name', 'last_name', 'email', 'phone_number', 'alt_phone_number']
    ordering = ['-created_at']

    fieldsets = (
        ('Personal Information', {
            'fields': ('first_name', 'last_name', 'email')
        }),
        ('Contact Information', {
            'fields': ('phone_number', 'alt_phone_number')
        }),
        ('Status & Preferences', {
            'fields': ('is_active', 'marketing_opt_in', 'notes')
        }),
        ('Metadata', {
            'fields': ('created_by',),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['created_at', 'updated_at', 'created_by']
    inlines = [CustomerAddressInline, CustomerCommunicationInline]

    def get_full_name(self, obj):
        return obj.get_full_name()
    get_full_name.short_description = 'Full Name'

    def total_jobs(self, obj):
        return obj.total_jobs
    total_jobs.short_description = 'Total Jobs'


@admin.register(CustomerAddress)
class CustomerAddressAdmin(admin.ModelAdmin):
    """
    Admin for CustomerAddress model.
    """
    list_display = ['customer', 'address_type', 'street_address', 'city', 'state', 'postal_code', 'is_primary', 'is_active']
    list_filter = ['address_type', 'is_primary', 'is_active', 'state', 'created_at']
    search_fields = ['customer__first_name', 'customer__last_name', 'customer__email', 'street_address', 'city', 'postal_code']
    ordering = ['customer__last_name', 'customer__first_name', '-is_primary']

    fieldsets = (
        ('Customer & Type', {
            'fields': ('customer', 'address_type', 'is_primary')
        }),
        ('Address Information', {
            'fields': ('street_address', 'apartment_unit', 'city', 'state', 'postal_code', 'country')
        }),
        ('Geographic Information', {
            'fields': ('latitude', 'longitude'),
            'classes': ('collapse',)
        }),
        ('Status & Instructions', {
            'fields': ('is_active', 'instructions')
        }),
    )

    readonly_fields = ['created_at', 'updated_at']


@admin.register(CustomerCommunication)
class CustomerCommunicationAdmin(admin.ModelAdmin):
    """
    Admin for CustomerCommunication model.
    """
    list_display = ['customer', 'communication_type', 'subject', 'created_by', 'requires_followup', 'created_at']
    list_filter = ['communication_type', 'requires_followup', 'followup_date', 'created_by', 'created_at']
    search_fields = ['customer__first_name', 'customer__last_name', 'customer__email', 'subject', 'message']
    ordering = ['-created_at']

    fieldsets = (
        ('Customer & Type', {
            'fields': ('customer', 'communication_type')
        }),
        ('Communication Details', {
            'fields': ('subject', 'message', 'contact_method')
        }),
        ('Follow-up', {
            'fields': ('requires_followup', 'followup_date')
        }),
        ('Metadata', {
            'fields': ('created_by',),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['created_at', 'updated_at', 'created_by']

    def save_model(self, request, obj, form, change):
        """Set created_by when creating new communications"""
        if not change:  # Only when creating
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
