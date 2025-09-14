from rest_framework import serializers
from .models import MFAToken, RecoveryCode, MFAAttempt, SMSVerification


class MFATokenSerializer(serializers.ModelSerializer):
    """Serializer for MFA tokens"""
    qr_code_url = serializers.ReadOnlyField()

    class Meta:
        model = MFAToken
        fields = [
            'id', 'token_type', 'name', 'is_active',
            'created_at', 'last_used_at', 'qr_code_url'
        ]
        read_only_fields = ['id', 'created_at', 'last_used_at', 'qr_code_url']


class RecoveryCodeSerializer(serializers.ModelSerializer):
    """Serializer for recovery codes"""
    code_display = serializers.SerializerMethodField()

    class Meta:
        model = RecoveryCode
        fields = [
            'id', 'code', 'code_display', 'is_used', 'used_at', 'created_at'
        ]
        read_only_fields = ['id', 'used_at', 'created_at']

    def get_code_display(self, obj):
        """Mask the recovery code for security"""
        if obj.code:
            return f"{obj.code[:3]}***{obj.code[-3:]}"
        return None


class MFAAttemptSerializer(serializers.ModelSerializer):
    """Serializer for MFA attempts"""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)

    class Meta:
        model = MFAAttempt
        fields = [
            'id', 'user', 'user_name', 'attempt_type', 'success',
            'method_used', 'ip_address', 'error_message', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class SMSVerificationSerializer(serializers.ModelSerializer):
    """Serializer for SMS verifications"""
    is_expired = serializers.ReadOnlyField()

    class Meta:
        model = SMSVerification
        fields = [
            'id', 'phone_number', 'is_used', 'expires_at',
            'is_expired', 'created_at'
        ]
        read_only_fields = ['id', 'expires_at', 'is_expired', 'created_at']


class MFASetupSerializer(serializers.Serializer):
    """Serializer for MFA setup"""
    method = serializers.ChoiceField(
        choices=['totp', 'sms', 'email'],
        default='totp'
    )
    phone_number = serializers.CharField(max_length=20, required=False)

    def validate(self, data):
        method = data.get('method')
        phone_number = data.get('phone_number')

        if method == 'sms' and not phone_number:
            raise serializers.ValidationError("Phone number is required for SMS MFA")

        return data


class MFAVerifySerializer(serializers.Serializer):
    """Serializer for MFA verification"""
    code = serializers.CharField(max_length=10)
    method = serializers.ChoiceField(
        choices=['totp', 'recovery', 'sms', 'email'],
        default='totp'
    )

    def validate_code(self, value):
        """Validate the MFA code format"""
        if not value:
            raise serializers.ValidationError("Code is required")

        # For TOTP codes, should be 6 digits
        if len(value) != 6 and value.isdigit():
            raise serializers.ValidationError("TOTP code must be 6 digits")

        return value


class MFASecurityStatusSerializer(serializers.Serializer):
    """Serializer for MFA security status"""
    mfa_enabled = serializers.BooleanField()
    mfa_method = serializers.CharField()
    mfa_required = serializers.BooleanField()
    account_locked = serializers.BooleanField()
    login_attempts = serializers.IntegerField()
    locked_until = serializers.DateTimeField()
    last_login_ip = serializers.IPAddressField()
    password_changed_at = serializers.DateTimeField()
    password_age_days = serializers.IntegerField()

    def to_representation(self, instance):
        return instance
