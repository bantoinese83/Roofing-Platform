from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from .models import MFAToken, RecoveryCode, MFAAttempt, SMSVerification
from .serializers import (
    MFATokenSerializer, RecoveryCodeSerializer, MFAAttemptSerializer,
    MFASetupSerializer, MFAVerifySerializer, SMSVerificationSerializer
)
from accounts.permissions import ManagerAndAbove


class MFATokenViewSet(viewsets.ModelViewSet):
    """ViewSet for managing MFA tokens"""
    serializer_class = MFATokenSerializer
    permission_classes = [IsAuthenticated]
    queryset = MFAToken.objects.all()  # Base queryset for router

    def get_queryset(self):
        return MFAToken.objects.filter(user=self.request.user, is_active=True)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['get'])
    def qr_code(self, request, pk=None):
        """Get QR code URL for MFA setup"""
        try:
            mfa_token = self.get_object()
            return Response({
                'qr_code_url': mfa_token.qr_code_url,
                'provisioning_uri': mfa_token.get_provisioning_uri()
            })
        except ObjectDoesNotExist:
            return Response(
                {'error': 'MFA token not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'])
    def verify_setup(self, request, pk=None):
        """Verify MFA setup with a test code"""
        mfa_token = self.get_object()
        code = request.data.get('code')

        if not code:
            return Response(
                {'error': 'Code is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if mfa_token.verify_token(code):
            # Enable MFA for the user
            request.user.enable_mfa('totp')
            return Response({'message': 'MFA setup verified successfully'})
        else:
            return Response(
                {'error': 'Invalid code'},
                status=status.HTTP_400_BAD_REQUEST
            )


class RecoveryCodeViewSet(viewsets.ModelViewSet):
    """ViewSet for managing recovery codes"""
    serializer_class = RecoveryCodeSerializer
    permission_classes = [IsAuthenticated]
    queryset = RecoveryCode.objects.all()  # Base queryset for router

    def get_queryset(self):
        return RecoveryCode.objects.filter(
            user=self.request.user,
            is_used=False
        ).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['post'])
    def generate_new_set(self, request):
        """Generate a new set of recovery codes"""
        # Mark existing codes as used
        RecoveryCode.objects.filter(user=request.user, is_used=False).update(is_used=True)

        # Generate new codes
        codes = []
        for _ in range(8):  # Generate 8 recovery codes
            code_obj = RecoveryCode.objects.create(user=request.user)
            codes.append(code_obj.code)

        return Response({
            'message': 'New recovery codes generated',
            'codes': codes,
            'warning': 'Save these codes securely. They will only be shown once.'
        })


class MFAAttemptViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing MFA attempts"""
    serializer_class = MFAAttemptSerializer
    permission_classes = [IsAuthenticated]
    queryset = MFAAttempt.objects.all()  # Base queryset for router

    def get_queryset(self):
        return MFAAttempt.objects.filter(user=self.request.user).order_by('-created_at')


class SMSVerificationViewSet(viewsets.ModelViewSet):
    """ViewSet for SMS MFA verification"""
    serializer_class = SMSVerificationSerializer
    permission_classes = [IsAuthenticated]
    queryset = SMSVerification.objects.all()  # Base queryset for router

    def get_queryset(self):
        return SMSVerification.objects.filter(
            user=self.request.user,
            is_used=False
        ).filter(expires_at__gt=timezone.now())

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        """Verify SMS code"""
        sms_verification = self.get_object()
        code = request.data.get('code')

        if not code:
            return Response(
                {'error': 'Code is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if sms_verification.verify_code(code):
            sms_verification.mark_as_used()
            return Response({'message': 'SMS code verified successfully'})
        else:
            return Response(
                {'error': 'Invalid or expired code'},
                status=status.HTTP_400_BAD_REQUEST
            )


class MFASetupView(APIView):
    """API view for MFA setup"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get MFA setup status"""
        user = request.user

        setup_data = {
            'mfa_enabled': user.mfa_enabled,
            'mfa_required': user.is_mfa_required(),
            'mfa_method': user.mfa_method,
        }

        if user.mfa_enabled:
            # Get existing MFA token
            try:
                mfa_token = MFAToken.objects.get(user=user, is_active=True)
                setup_data['has_token'] = True
                setup_data['token_name'] = mfa_token.name
            except ObjectDoesNotExist:
                setup_data['has_token'] = False

            # Get recovery codes count
            recovery_codes_count = RecoveryCode.objects.filter(
                user=user, is_used=False
            ).count()
            setup_data['recovery_codes_count'] = recovery_codes_count
        else:
            setup_data['has_token'] = False
            setup_data['recovery_codes_count'] = 0

        return Response(setup_data)

    def post(self, request):
        """Setup MFA for the user"""
        user = request.user
        method = request.data.get('method', 'totp')

        if method not in ['totp', 'sms', 'email']:
            return Response(
                {'error': 'Invalid MFA method'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create MFA token
        if method == 'totp':
            mfa_token, created = MFAToken.objects.get_or_create(
                user=user,
                defaults={'name': 'Roofing Platform'}
            )

            if created:
                # Generate recovery codes
                for _ in range(8):
                    RecoveryCode.objects.create(user=user)

            return Response({
                'message': 'MFA setup initiated',
                'method': 'totp',
                'qr_code_url': mfa_token.qr_code_url,
                'recovery_codes_generated': created
            })

        elif method == 'sms':
            # For SMS, we would integrate with Twilio
            # For now, return a placeholder
            user.enable_mfa('sms')
            return Response({
                'message': 'SMS MFA setup completed',
                'method': 'sms'
            })

        elif method == 'email':
            user.enable_mfa('email')
            return Response({
                'message': 'Email MFA setup completed',
                'method': 'email'
            })


class MFAVerifyView(APIView):
    """API view for MFA verification"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Verify MFA code"""
        user = request.user
        code = request.data.get('code')
        method = request.data.get('method', 'totp')

        if not code:
            return Response(
                {'error': 'Code is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Record the attempt
        attempt = MFAAttempt.objects.create(
            user=user,
            attempt_type='login',
            method_used=method,
            ip_address=self.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )

        if method == 'totp':
            try:
                mfa_token = MFAToken.objects.get(user=user, is_active=True)
                if mfa_token.verify_token(code):
                    attempt.success = True
                    attempt.save()
                    return Response({'message': 'MFA verified successfully'})
                else:
                    attempt.error_message = 'Invalid TOTP code'
                    attempt.save()
            except ObjectDoesNotExist:
                attempt.error_message = 'MFA token not found'
                attempt.save()

        elif method == 'recovery':
            try:
                recovery_code = RecoveryCode.objects.get(
                    user=user,
                    code=code,
                    is_used=False
                )
                recovery_code.mark_as_used()
                attempt.success = True
                attempt.save()
                return Response({'message': 'Recovery code verified successfully'})
            except ObjectDoesNotExist:
                attempt.error_message = 'Invalid recovery code'
                attempt.save()

        return Response(
            {'error': 'Invalid code'},
            status=status.HTTP_400_BAD_REQUEST
        )

    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def disable_mfa(request):
    """Disable MFA for the current user"""
    user = request.user

    if not user.mfa_enabled:
        return Response(
            {'error': 'MFA is not enabled'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Deactivate MFA token
    MFAToken.objects.filter(user=user).update(is_active=False)

    # Mark recovery codes as used
    RecoveryCode.objects.filter(user=user, is_used=False).update(is_used=True)

    # Disable MFA for user
    user.disable_mfa()

    return Response({'message': 'MFA disabled successfully'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def security_status(request):
    """Get user's security status"""
    user = request.user
    return Response(user.get_security_status())
