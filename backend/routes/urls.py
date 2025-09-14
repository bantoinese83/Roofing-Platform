from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'routes'

router = DefaultRouter()
router.register(r'routes', views.RouteViewSet, basename='route')
router.register(r'waypoints', views.RouteWaypointViewSet, basename='waypoint')
router.register(r'settings', views.RouteSettingsViewSet, basename='route-settings')

urlpatterns = [
    path('', include(router.urls)),
]
