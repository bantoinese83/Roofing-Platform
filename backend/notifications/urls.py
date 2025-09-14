from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    # Notification templates
    path('templates/', views.NotificationTemplateListCreateView.as_view(), name='template-list-create'),
    path('templates/<int:pk>/', views.NotificationTemplateDetailView.as_view(), name='template-detail'),
    path('templates/test/', views.NotificationTemplateTestView.as_view(), name='template-test'),

    # Notification logs
    path('logs/', views.NotificationLogListView.as_view(), name='log-list'),
    path('logs/<int:pk>/', views.NotificationLogDetailView.as_view(), name='log-detail'),
    path('logs/<int:notification_id>/retry/', views.NotificationRetryView.as_view(), name='log-retry'),

    # Notification settings
    path('settings/', views.NotificationSettingsView.as_view(), name='settings'),

    # Bulk notifications
    path('bulk/', views.BulkNotificationView.as_view(), name='bulk-send'),

    # Trigger notifications
    path('trigger/', views.TriggerNotificationView.as_view(), name='trigger'),

    # Statistics
    path('stats/', views.NotificationStatsView.as_view(), name='stats'),
]
