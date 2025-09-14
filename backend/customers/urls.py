from django.urls import path
from . import views

app_name = 'customers'

urlpatterns = [
    # Customer management
    path('', views.CustomerListCreateView.as_view(), name='customer-list-create'),
    path('<int:pk>/', views.CustomerDetailView.as_view(), name='customer-detail'),

    # Customer addresses
    path('<int:customer_id>/addresses/', views.CustomerAddressListCreateView.as_view(), name='customer-address-list-create'),
    path('<int:customer_id>/addresses/<int:pk>/', views.CustomerAddressDetailView.as_view(), name='customer-address-detail'),

    # Customer communications
    path('<int:customer_id>/communications/', views.CustomerCommunicationListCreateView.as_view(), name='customer-communication-list-create'),
    path('<int:customer_id>/communications/<int:pk>/', views.CustomerCommunicationDetailView.as_view(), name='customer-communication-detail'),

    # Search and utilities
    path('search/', views.CustomerSearchView.as_view(), name='customer-search'),
    path('stats/', views.CustomerStatsView.as_view(), name='customer-stats'),
]
