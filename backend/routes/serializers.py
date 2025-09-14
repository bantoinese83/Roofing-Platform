from rest_framework import serializers
from .models import Route, RouteWaypoint, RouteSettings


class RouteWaypointSerializer(serializers.ModelSerializer):
    """
    Serializer for RouteWaypoint model.
    """
    job_title = serializers.CharField(source='job.title', read_only=True)
    customer_name = serializers.CharField(source='job.customer.full_name', read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = RouteWaypoint
        fields = [
            'id', 'route', 'job', 'job_title', 'customer_name',
            'stop_order', 'status', 'address', 'latitude', 'longitude',
            'estimated_arrival_time', 'estimated_departure_time',
            'estimated_duration_minutes', 'actual_arrival_time',
            'actual_departure_time', 'actual_duration_minutes',
            'distance_from_previous_km', 'travel_time_minutes',
            'arrival_notes', 'departure_notes', 'is_overdue'
        ]
        read_only_fields = ['id', 'is_overdue']


class RouteSerializer(serializers.ModelSerializer):
    """
    Serializer for Route model.
    """
    technician_name = serializers.CharField(source='technician.full_name', read_only=True)
    technician_phone = serializers.CharField(source='technician.phone_number', read_only=True)
    waypoints = RouteWaypointSerializer(many=True, read_only=True)
    total_stops = serializers.IntegerField(read_only=True)
    completed_stops = serializers.IntegerField(read_only=True)
    progress_percentage = serializers.IntegerField(read_only=True)
    is_optimized = serializers.BooleanField(read_only=True)

    class Meta:
        model = Route
        fields = [
            'id', 'technician', 'technician_name', 'technician_phone',
            'route_date', 'status', 'optimization_type',
            'total_distance_km', 'total_duration_minutes',
            'estimated_fuel_cost', 'start_address', 'start_latitude',
            'start_longitude', 'end_address', 'end_latitude',
            'end_longitude', 'google_route_id', 'route_polyline',
            'avoid_tolls', 'avoid_highways', 'vehicle_type',
            'optimized_at', 'created_at', 'updated_at',
            'waypoints', 'total_stops', 'completed_stops',
            'progress_percentage', 'is_optimized'
        ]
        read_only_fields = [
            'google_route_id', 'route_polyline', 'optimized_at',
            'created_at', 'updated_at', 'total_stops', 'completed_stops',
            'progress_percentage', 'is_optimized'
        ]


class RouteCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating routes with waypoints.
    """
    waypoints = RouteWaypointSerializer(many=True, required=False)

    class Meta:
        model = Route
        fields = [
            'technician', 'route_date', 'optimization_type',
            'start_address', 'start_latitude', 'start_longitude',
            'end_address', 'end_latitude', 'end_longitude',
            'avoid_tolls', 'avoid_highways', 'vehicle_type',
            'waypoints'
        ]

    def create(self, validated_data):
        waypoints_data = validated_data.pop('waypoints', [])
        route = Route.objects.create(**validated_data)

        # Create waypoints
        for waypoint_data in waypoints_data:
            RouteWaypoint.objects.create(route=route, **waypoint_data)

        return route


class RouteOptimizationSerializer(serializers.Serializer):
    """
    Serializer for route optimization requests.
    """
    technician_id = serializers.IntegerField()
    date = serializers.DateField()
    job_ids = serializers.ListField(child=serializers.IntegerField())


class RouteSettingsSerializer(serializers.ModelSerializer):
    """
    Serializer for RouteSettings model.
    """
    class Meta:
        model = RouteSettings
        fields = [
            'id', 'google_maps_api_key', 'default_optimization_type',
            'default_vehicle_type', 'default_avoid_tolls',
            'default_avoid_highways', 'max_stops_per_route',
            'default_break_duration_minutes', 'fuel_efficiency_kmpl',
            'fuel_cost_per_liter', 'average_job_duration_minutes',
            'buffer_time_percentage'
        ]
        extra_kwargs = {
            'google_maps_api_key': {'write_only': True}
        }
