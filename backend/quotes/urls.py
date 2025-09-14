from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'quotes', views.QuoteViewSet)
router.register(r'quote-items', views.QuoteItemViewSet)
router.register(r'templates', views.QuoteTemplateViewSet)
router.register(r'settings', views.QuoteSettingsViewSet, basename='quote-settings')

urlpatterns = [
    path('', include(router.urls)),
]
