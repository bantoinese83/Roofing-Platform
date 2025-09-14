from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'payments'

router = DefaultRouter()
router.register(r'payment-methods', views.PaymentMethodViewSet, basename='payment-method')
router.register(r'invoices', views.InvoiceViewSet, basename='invoice')
router.register(r'payments', views.PaymentViewSet, basename='payment')
router.register(r'settings', views.PaymentSettingsViewSet, basename='payment-settings')

urlpatterns = [
    path('', include(router.urls)),
    path('create-payment-intent/', views.create_payment_intent, name='create-payment-intent'),
    path('webhook/', views.stripe_webhook, name='stripe-webhook'),
    path('stats/', views.payment_stats, name='payment-stats'),
]
