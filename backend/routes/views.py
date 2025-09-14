from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import Route, RouteWaypoint, RouteSettings
from .serializers import (
    RouteSerializer, RouteCreateSerializer, RouteWaypointSerializer,
    RouteSettingsSerializer, RouteOptimizationSerializer
)
from .services import RouteOptimizationService
from accounts.permissions import ManagerAndAbove


class RouteViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing routes.
    """
    permission_classes = [IsAuthenticated, ManagerAndAbove]

    def get_queryset(self):
        queryset = Route.objects.select_related('technician', 'created_by')

        # Filter by technician for non-admin users
        user = self.request.user
        if not user.role in ['admin', 'manager']:
            queryset = queryset.filter(technician__user=user)

        # Apply filters
        technician_id = self.request.query_params.get('technician')
        date = self.request.query_params.get('date')
        status_filter = self.request.query_params.get('status')

        if technician_id:
            queryset = queryset.filter(technician_id=technician_id)
        if date:
            queryset = queryset.filter(route_date=date)
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset.order_by('-route_date', 'technician__user__first_name')

    def get_serializer_class(self):
        if self.action == 'create':
            return RouteCreateSerializer
        elif self.action == 'optimize':
            return RouteOptimizationSerializer
        return RouteSerializer

    @action(detail=True, methods=['post'])
    def optimize(self, request, pk=None):
        """
        Optimize a route using Google Maps API.
        """
        route = self.get_object()
        service = RouteOptimizationService()

        success = service.optimize_route(route)

        if success:
            serializer = self.get_serializer(route)
            return Response({
                'message': 'Route optimized successfully',
                'route': serializer.data
            })
        else:
            return Response(
                {'error': 'Failed to optimize route. Please check Google Maps API configuration.'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['get'])
    def efficiency(self, request, pk=None):
        """
        Get route efficiency metrics.
        """
        route = self.get_object()
        service = RouteOptimizationService()

        metrics = service.calculate_route_efficiency(route)
        return Response(metrics)

    @action(detail=False, methods=['post'])
    def suggestions(self, request):
        """
        Get route optimization suggestions for a set of jobs.
        """
        serializer = RouteOptimizationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = RouteOptimizationService()
        suggestions = service.get_route_suggestions(
            serializer.validated_data['technician_id'],
            serializer.validated_data['date'],
            serializer.validated_data['job_ids']
        )

        return Response({'suggestions': suggestions})


class RouteWaypointViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing route waypoints.
    """
    serializer_class = RouteWaypointSerializer
    permission_classes = [IsAuthenticated, ManagerAndAbove]

    def get_queryset(self):
        queryset = RouteWaypoint.objects.select_related(
            'route', 'route__technician', 'job'
        ).order_by('route', 'stop_order')

        route_id = self.request.query_params.get('route')
        if route_id:
            queryset = queryset.filter(route_id=route_id)

        return queryset

    @action(detail=True, methods=['post'])
    def arrive(self, request, pk=None):
        """
        Mark technician as arrived at waypoint.
        """
        waypoint = self.get_object()
        notes = request.data.get('notes', '')

        waypoint.mark_arrived(notes)
        serializer = self.get_serializer(waypoint)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def depart(self, request, pk=None):
        """
        Mark technician as departed from waypoint.
        """
        waypoint = self.get_object()
        notes = request.data.get('notes', '')

        waypoint.mark_departed(notes)
        serializer = self.get_serializer(waypoint)
        return Response(serializer.data)


class RouteSettingsViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing route optimization settings.
    """
    serializer_class = RouteSettingsSerializer
    permission_classes = [IsAuthenticated, ManagerAndAbove]

    def get_queryset(self):
        # RouteSettings is a singleton, so return all (should be one)
        return RouteSettings.objects.all()

    def get_object(self):
        # Return the singleton settings object
        return RouteSettings.get_settings()

    def list(self, request, *args, **kwargs):
        """
        Get the global route settings.
        """
        settings = RouteSettings.get_settings()
        serializer = self.get_serializer(settings)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        """
        Create is not allowed for singleton settings.
        """
        return Response(
            {'error': 'Settings already exist. Use PUT to update.'},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def destroy(self, request, *args, **kwargs):
        """
        Delete is not allowed for singleton settings.
        """
        return Response(
            {'error': 'Cannot delete global settings.'},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )
