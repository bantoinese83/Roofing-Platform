from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'scheduling'

router = DefaultRouter()
router.register(r'job-schedules', views.JobScheduleViewSet, basename='job-schedules')
router.register(r'calendar-events', views.CalendarEventViewSet, basename='calendar-events')
router.register(r'settings', views.SchedulingSettingsViewSet, basename='scheduling-settings')

urlpatterns = [
    path('', include(router.urls)),
    path('calendar-data/', views.calendar_data, name='calendar-data'),
    path('bulk-update/', views.bulk_schedule_update, name='bulk-schedule-update'),
]
