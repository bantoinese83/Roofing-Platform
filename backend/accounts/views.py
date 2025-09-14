from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator as token_generator

from .models import User
from .serializers import (
    UserSerializer,
    UserRegistrationSerializer,
    UserLoginSerializer,
    ChangePasswordSerializer
)
from .permissions import (
    IsOwnerOrAdmin,
    IsManagerOrAbove,
    TechnicianAndAbove,
    IsOwnerOfObject,
    AdminOnly,
    ManagerAndAbove
)


class UserListCreateView(generics.ListCreateAPIView):
    """
    List all users or create a new user.
    Only managers and above can create users.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [ManagerAndAbove]

    def get_queryset(self):
        """
        Filter users based on user role using RBAC.
        """
        user = self.request.user
        if user.is_admin or user.is_owner:
            return User.objects.all()
        elif user.is_manager:
            # Managers can see technicians and other managers
            return User.objects.filter(role__in=['technician', 'manager'])
        else:
            # This shouldn't happen due to permissions, but fallback
            return User.objects.filter(id=user.id)


class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a user instance.
    Users can access their own profile, managers can access technician/manager profiles,
    owners/admins can access all profiles.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [TechnicianAndAbove]

    def get_queryset(self):
        """
        Filter based on user permissions using RBAC.
        """
        user = self.request.user
        if user.is_admin or user.is_owner:
            return User.objects.all()
        elif user.is_manager:
            return User.objects.filter(role__in=['technician', 'manager'])
        else:
            return User.objects.filter(id=user.id)

    def get_permissions(self):
        """
        Override permissions for different operations.
        """
        if self.request.method == 'DELETE':
            # Only admins can delete users
            return [AdminOnly()]
        elif self.request.method in ['PUT', 'PATCH']:
            # Users can update their own profile, managers can update technician profiles
            return [TechnicianAndAbove()]
        else:
            return [TechnicianAndAbove()]


class UserRegistrationView(generics.CreateAPIView):
    """
    Register a new user.
    """
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Generate tokens
        refresh = RefreshToken.for_user(user)
        return Response({
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_201_CREATED)


class UserLoginView(APIView):
    """
    Login view that returns JWT tokens.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']

        # Update last login
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])

        # Generate tokens
        refresh = RefreshToken.for_user(user)
        return Response({
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        })


class ChangePasswordView(APIView):
    """
    Change user password.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        old_password = serializer.validated_data['old_password']

        # Check old password
        if not user.check_password(old_password):
            return Response(
                {'error': 'Old password is incorrect'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Set new password
        user.set_password(serializer.validated_data['new_password'])
        user.save()

        return Response({'message': 'Password changed successfully'})


class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    Get or update current user profile.
    """
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class PasswordResetRequestView(APIView):
    """
    Request password reset via email.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response(
                {'error': 'Email is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Don't reveal if email exists or not for security
            return Response(
                {'message': 'If the email exists, a password reset link has been sent.'},
                status=status.HTTP_200_OK
            )

        # Generate password reset token
        token = token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))

        # In a real implementation, send email with reset link
        reset_url = f"{settings.FRONTEND_URL}/auth/reset-password/{uid}/{token}"

        try:
            # Send password reset email
            subject = 'Password Reset Request'
            message = render_to_string('accounts/password_reset_email.html', {
                'user': user,
                'reset_url': reset_url,
                'site_name': 'Roofing Platform',
            })
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [email])
        except Exception as e:
            # Log error but don't expose to user
            print(f"Error sending password reset email: {e}")

        return Response(
            {'message': 'If the email exists, a password reset link has been sent.'},
            status=status.HTTP_200_OK
        )


class PasswordResetConfirmView(APIView):
    """
    Confirm password reset with token and set new password.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, uidb64, token):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user is not None and token_generator.check_token(user, token):
            new_password = request.data.get('new_password')
            if not new_password:
                return Response(
                    {'error': 'New password is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            user.set_password(new_password)
            user.save()

            return Response(
                {'message': 'Password has been reset successfully.'},
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                {'error': 'Invalid or expired password reset token'},
                status=status.HTTP_400_BAD_REQUEST
            )
