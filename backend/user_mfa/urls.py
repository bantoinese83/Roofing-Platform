from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'tokens', views.MFATokenViewSet)
router.register(r'recovery-codes', views.RecoveryCodeViewSet)
router.register(r'attempts', views.MFAAttemptViewSet)
router.register(r'sms-verifications', views.SMSVerificationViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('setup/', views.MFASetupView.as_view(), name='mfa-setup'),
    path('verify/', views.MFAVerifyView.as_view(), name='mfa-verify'),
    path('disable/', views.disable_mfa, name='mfa-disable'),
    path('security-status/', views.security_status, name='security-status'),
]
