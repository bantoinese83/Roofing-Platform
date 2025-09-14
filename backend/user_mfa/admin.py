from django.contrib import admin
from .models import MFAToken, RecoveryCode, MFAAttempt, SMSVerification


@admin.register(MFAToken)
class MFATokenAdmin(admin.ModelAdmin):
    list_display = ['user', 'token_type', 'name', 'is_active', 'created_at', 'last_used_at']
    list_filter = ['token_type', 'is_active', 'created_at']
    search_fields = ['user__email', 'user__first_name', 'user__last_name', 'name']
    readonly_fields = ['secret']


@admin.register(RecoveryCode)
class RecoveryCodeAdmin(admin.ModelAdmin):
    list_display = ['user', 'code', 'is_used', 'used_at', 'created_at']
    list_filter = ['is_used', 'created_at']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    readonly_fields = ['code']


@admin.register(MFAAttempt)
class MFAAttemptAdmin(admin.ModelAdmin):
    list_display = ['user', 'attempt_type', 'success', 'method_used', 'ip_address', 'created_at']
    list_filter = ['attempt_type', 'success', 'method_used', 'created_at']
    search_fields = ['user__email', 'user__first_name', 'user__last_name', 'ip_address']
    readonly_fields = ['created_at']


@admin.register(SMSVerification)
class SMSVerificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone_number', 'is_used', 'expires_at', 'created_at']
    list_filter = ['is_used', 'created_at']
    search_fields = ['user__email', 'user__first_name', 'user__last_name', 'phone_number']
    readonly_fields = ['code', 'created_at']
