from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from decimal import Decimal


class Route(models.Model):
    """
    Optimized route for a technician's daily schedule.
    """

    ROUTE_STATUS_CHOICES = [
        ('planned', 'Planned'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    OPTIMIZATION_TYPES = [
        ('distance', 'Minimize Distance'),
        ('time', 'Minimize Time'),
        ('efficiency', 'Maximize Efficiency'),
    ]

    VEHICLE_TYPES = [
        ('car', 'Car'),
        ('truck', 'Truck'),
        ('van', 'Van'),
    ]

    technician = models.ForeignKey(
        'technicians.TechnicianProfile',
        on_delete=models.CASCADE,
        related_name='routes',
        help_text='Technician assigned to this route'
    )

    route_date = models.DateField(
        help_text='Date for this route'
    )

    status = models.CharField(
        max_length=20,
        choices=ROUTE_STATUS_CHOICES,
        default='planned',
        help_text='Current status of the route'
    )

    optimization_type = models.CharField(
        max_length=20,
        choices=OPTIMIZATION_TYPES,
        default='time',
        help_text='Type of optimization applied'
    )

    # Route metrics
    total_distance_km = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Total distance in kilometers'
    )

    total_duration_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Total estimated duration in minutes'
    )

    estimated_fuel_cost = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Estimated fuel cost'
    )

    # Start/end locations
    start_address = models.TextField(
        blank=True,
        help_text='Starting address (usually home base or first stop)'
    )

    start_latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text='Starting latitude'
    )

    start_longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text='Starting longitude'
    )

    end_address = models.TextField(
        blank=True,
        help_text='Ending address (usually home base or last stop)'
    )

    end_latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text='Ending latitude'
    )

    end_longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text='Ending longitude'
    )

    # Google Maps integration
    google_route_id = models.CharField(
        max_length=100,
        blank=True,
        help_text='Google Maps route ID for tracking'
    )

    route_polyline = models.TextField(
        blank=True,
        help_text='Encoded polyline for the route (Google Maps format)'
    )

    # Optimization settings
    avoid_tolls = models.BooleanField(
        default=False,
        help_text='Avoid toll roads in route optimization'
    )

    avoid_highways = models.BooleanField(
        default=False,
        help_text='Avoid highways in route optimization'
    )

    vehicle_type = models.CharField(
        max_length=20,
        choices=VEHICLE_TYPES,
        default='truck',
        help_text='Type of vehicle for route optimization'
    )

    # Metadata
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_routes',
        help_text='User who created this route'
    )

    optimized_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When the route was last optimized'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-route_date', 'technician']
        verbose_name = 'Route'
        verbose_name_plural = 'Routes'
        unique_together = ['technician', 'route_date']
        indexes = [
            models.Index(fields=['technician', 'route_date']),
            models.Index(fields=['route_date', 'status']),
            models.Index(fields=['status', 'created_at']),
        ]

    def __str__(self):
        return f"{self.technician.full_name} - {self.route_date} ({self.get_status_display()})"

    @property
    def total_stops(self):
        """Get total number of stops in this route"""
        return self.waypoints.count()

    @property
    def completed_stops(self):
        """Get number of completed stops"""
        return self.waypoints.filter(status='completed').count()

    @property
    def is_optimized(self):
        """Check if route has been optimized"""
        return self.optimized_at is not None

    @property
    def progress_percentage(self):
        """Calculate route completion percentage"""
        if self.total_stops == 0:
            return 0
        return int((self.completed_stops / self.total_stops) * 100)

    def optimize_route(self):
        """
        Optimize the route using Google Maps API.
        This is a placeholder for the actual optimization logic.
        """
        from .services import RouteOptimizationService
        service = RouteOptimizationService()
        return service.optimize_route(self)

    def get_waypoints_ordered(self):
        """Get waypoints in optimized order"""
        return self.waypoints.order_by('stop_order')


class RouteWaypoint(models.Model):
    """
    Individual stop in a route.
    """

    WAYPOINT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('skipped', 'Skipped'),
    ]

    route = models.ForeignKey(
        Route,
        on_delete=models.CASCADE,
        related_name='waypoints',
        help_text='Route this waypoint belongs to'
    )

    job = models.ForeignKey(
        'jobs.Job',
        on_delete=models.CASCADE,
        related_name='route_waypoints',
        help_text='Job associated with this waypoint'
    )

    stop_order = models.PositiveIntegerField(
        help_text='Order of this stop in the route (1-based)'
    )

    status = models.CharField(
        max_length=20,
        choices=WAYPOINT_STATUS_CHOICES,
        default='pending',
        help_text='Current status of this waypoint'
    )

    # Location data
    address = models.TextField(
        help_text='Job address'
    )

    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        help_text='Latitude coordinate'
    )

    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        help_text='Longitude coordinate'
    )

    # Timing estimates
    estimated_arrival_time = models.TimeField(
        null=True,
        blank=True,
        help_text='Estimated arrival time'
    )

    estimated_departure_time = models.TimeField(
        null=True,
        blank=True,
        help_text='Estimated departure time'
    )

    estimated_duration_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Estimated time to complete job at this stop'
    )

    # Actual timing
    actual_arrival_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Actual arrival time'
    )

    actual_departure_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Actual departure time'
    )

    actual_duration_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Actual time spent at this stop'
    )

    # Distance from previous stop
    distance_from_previous_km = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Distance from previous waypoint in kilometers'
    )

    travel_time_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Estimated travel time from previous stop'
    )

    # Notes
    arrival_notes = models.TextField(
        blank=True,
        help_text='Notes taken upon arrival'
    )

    departure_notes = models.TextField(
        blank=True,
        help_text='Notes taken upon departure'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['route', 'stop_order']
        verbose_name = 'Route Waypoint'
        verbose_name_plural = 'Route Waypoints'
        unique_together = ['route', 'job']
        indexes = [
            models.Index(fields=['route', 'stop_order']),
            models.Index(fields=['job', 'status']),
            models.Index(fields=['status', 'estimated_arrival_time']),
        ]

    def __str__(self):
        return f"{self.route} - Stop {self.stop_order}: {self.job.title}"

    @property
    def is_overdue(self):
        """Check if this waypoint is overdue"""
        if self.status == 'pending' and self.estimated_arrival_time:
            from django.utils import timezone
            now = timezone.now()
            if now.date() > self.route.route_date:
                return True
            if now.date() == self.route.route_date and now.time() > self.estimated_arrival_time:
                return True
        return False

    def mark_arrived(self, notes=''):
        """Mark technician as arrived at this waypoint"""
        from django.utils import timezone
        self.actual_arrival_time = timezone.now()
        self.status = 'in_progress'
        self.arrival_notes = notes
        self.save()

    def mark_departed(self, notes=''):
        """Mark technician as departed from this waypoint"""
        from django.utils import timezone
        self.actual_departure_time = timezone.now()
        self.status = 'completed'
        self.departure_notes = notes
        if self.actual_arrival_time:
            duration = self.actual_departure_time - self.actual_arrival_time
            self.actual_duration_minutes = int(duration.total_seconds() / 60)
        self.save()


class RouteSettings(models.Model):
    """
    Global settings for route optimization.
    """

    # Google Maps API settings
    google_maps_api_key = models.CharField(
        max_length=100,
        blank=True,
        help_text='Google Maps API key for route optimization'
    )

    # Default optimization settings
    default_optimization_type = models.CharField(
        max_length=20,
        choices=Route.OPTIMIZATION_TYPES,
        default='time',
        help_text='Default optimization type'
    )

    default_vehicle_type = models.CharField(
        max_length=20,
        choices=Route.VEHICLE_TYPES,
        default='truck',
        help_text='Default vehicle type'
    )

    default_avoid_tolls = models.BooleanField(
        default=False,
        help_text='Default setting for avoiding tolls'
    )

    default_avoid_highways = models.BooleanField(
        default=False,
        help_text='Default setting for avoiding highways'
    )

    # Business settings
    max_stops_per_route = models.PositiveIntegerField(
        default=8,
        help_text='Maximum number of stops per route'
    )

    default_break_duration_minutes = models.PositiveIntegerField(
        default=30,
        help_text='Default break duration between jobs'
    )

    # Cost calculation settings
    fuel_efficiency_kmpl = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal('8.0'),
        help_text='Fuel efficiency in km per liter'
    )

    fuel_cost_per_liter = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('1.50'),
        help_text='Fuel cost per liter in dollars'
    )

    # Time estimation settings
    average_job_duration_minutes = models.PositiveIntegerField(
        default=120,
        help_text='Average job duration in minutes'
    )

    buffer_time_percentage = models.PositiveIntegerField(
        default=20,
        help_text='Buffer time percentage for unexpected delays'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Route Settings'
        verbose_name_plural = 'Route Settings'

    def __str__(self):
        return "Route Optimization Settings"

    @classmethod
    def get_settings(cls):
        """Get the global route settings (singleton pattern)."""
        settings_obj, created = cls.objects.get_or_create(
            defaults={
                'default_optimization_type': 'time',
                'default_vehicle_type': 'truck',
            }
        )
        return settings_obj
