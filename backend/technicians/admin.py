from django.contrib import admin
from .models import TechnicianProfile, Skill, Certification, Crew


@admin.register(TechnicianProfile)
class TechnicianProfileAdmin(admin.ModelAdmin):
    """
    Admin for TechnicianProfile model.
    """
    list_display = ['full_name', 'user_email', 'employee_id', 'is_available', 'license_number', 'created_at']
    list_filter = ['is_available', 'license_expiry', 'created_at']
    search_fields = ['user__email', 'user__first_name', 'user__last_name', 'employee_id', 'license_number']
    ordering = ['user__first_name', 'user__last_name']

    def user_email(self, obj):
        """Return the user's email address"""
        return obj.user.email
    user_email.short_description = 'Email'
    user_email.admin_order_field = 'user__email'

    fieldsets = (
        ('User Information', {
            'fields': ('user', 'employee_id')
        }),
        ('Professional Information', {
            'fields': ('license_number', 'license_expiry')
        }),
        ('Work Information', {
            'fields': ('hourly_rate', 'max_daily_hours', 'preferred_start_time', 'is_available')
        }),
        ('Emergency Contact', {
            'fields': ('emergency_contact_name', 'emergency_contact_phone')
        }),
    )

    readonly_fields = ['created_at', 'updated_at']


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    """
    Admin for Skill model.
    """
    list_display = ['name', 'category', 'is_active', 'created_at']
    list_filter = ['category', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['category', 'name']


@admin.register(Certification)
class CertificationAdmin(admin.ModelAdmin):
    """
    Admin for Certification model.
    """
    list_display = ['technician', 'skill', 'certification_number', 'expiry_date', 'is_verified', 'is_expired']
    list_filter = ['is_verified', 'expiry_date', 'skill__category', 'created_at']
    search_fields = ['technician__user__email', 'technician__user__first_name', 'skill__name', 'certification_number']
    ordering = ['-expiry_date']

    fieldsets = (
        ('Basic Information', {
            'fields': ('technician', 'skill')
        }),
        ('Certification Details', {
            'fields': ('certification_number', 'issued_date', 'expiry_date', 'is_verified')
        }),
        ('Documentation', {
            'fields': ('verification_document', 'notes')
        }),
    )

    readonly_fields = ['created_at', 'updated_at']


@admin.register(Crew)
class CrewAdmin(admin.ModelAdmin):
    """
    Admin for Crew model.
    """
    list_display = ['name', 'leader', 'member_count', 'primary_skill', 'is_active', 'max_concurrent_jobs']
    list_filter = ['is_active', 'primary_skill__category', 'created_at']
    search_fields = ['name', 'description', 'leader__user__email']
    ordering = ['name']
    filter_horizontal = ['members']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'leader', 'is_active')
        }),
        ('Members & Skills', {
            'fields': ('members', 'primary_skill')
        }),
        ('Work Capacity', {
            'fields': ('max_concurrent_jobs', 'contact_phone')
        }),
        ('Additional Information', {
            'fields': ('notes',)
        }),
    )

    readonly_fields = ['created_at', 'updated_at']
