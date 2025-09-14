from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'categories', views.InventoryCategoryViewSet)
router.register(r'suppliers', views.SupplierViewSet)
router.register(r'items', views.InventoryItemViewSet)
router.register(r'item-suppliers', views.ItemSupplierViewSet)
router.register(r'transactions', views.StockTransactionViewSet)
router.register(r'purchase-orders', views.PurchaseOrderViewSet)
router.register(r'reports', views.InventoryReportsViewSet, basename='inventory-reports')

urlpatterns = [
    path('', include(router.urls)),
]
