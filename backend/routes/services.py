import logging
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from django.utils import timezone
from django.conf import settings
from .models import Route, RouteWaypoint, RouteSettings

logger = logging.getLogger(__name__)


class RouteOptimizationService:
    """
    Service for optimizing routes using Google Maps API.
    """

    def __init__(self):
        self.settings = RouteSettings.get_settings()
        self.google_api_key = getattr(settings, 'GOOGLE_MAPS_API_KEY', '') or self.settings.google_maps_api_key
        self.base_url = "https://maps.googleapis.com/maps/api"

    def optimize_route(self, route: Route) -> bool:
        """
        Optimize a route using Google Maps Directions API.
        """
        try:
            # Get all waypoints for this route
            waypoints = route.get_waypoints_ordered()
            if not waypoints.exists():
                logger.warning(f"No waypoints found for route {route.id}")
                return False

            # Prepare waypoints for Google Maps API
            origin = self._get_origin_destination(route, waypoints, 'origin')
            destination = self._get_origin_destination(route, waypoints, 'destination')
            intermediate_waypoints = self._prepare_waypoints(waypoints)

            # Call Google Maps Directions API
            directions_result = self._get_directions(
                origin, destination, intermediate_waypoints, route
            )

            if not directions_result:
                return False

            # Update route with optimized data
            self._update_route_with_directions(route, directions_result)

            # Update waypoints with optimized order and timing
            self._update_waypoints_with_directions(route, directions_result, waypoints)

            route.optimized_at = timezone.now()
            route.save()

            logger.info(f"Successfully optimized route {route.id}")
            return True

        except Exception as e:
            logger.error(f"Failed to optimize route {route.id}: {e}")
            return False

    def _get_origin_destination(self, route: Route, waypoints: List[RouteWaypoint], type_: str) -> str:
        """Get origin or destination coordinates for Google Maps API"""
        if type_ == 'origin':
            # Use route start location or first waypoint
            if route.start_latitude and route.start_longitude:
                return f"{route.start_latitude},{route.start_longitude}"
            elif waypoints:
                first_waypoint = waypoints[0]
                return f"{first_waypoint.latitude},{first_waypoint.longitude}"
        else:  # destination
            # Use route end location or last waypoint
            if route.end_latitude and route.end_longitude:
                return f"{route.end_latitude},{route.end_longitude}"
            elif waypoints:
                last_waypoint = waypoints[len(waypoints) - 1]
                return f"{last_waypoint.latitude},{last_waypoint.longitude}"

        # Fallback to first/last waypoint
        if waypoints:
            waypoint = waypoints[0] if type_ == 'origin' else waypoints[len(waypoints) - 1]
            return f"{waypoint.latitude},{waypoint.longitude}"

        raise ValueError("No valid origin/destination found")

    def _prepare_waypoints(self, waypoints: List[RouteWaypoint]) -> List[str]:
        """Prepare intermediate waypoints for Google Maps API"""
        intermediate_waypoints = []
        for waypoint in waypoints[1:-1]:  # Skip first and last (origin/destination)
            intermediate_waypoints.append(f"{waypoint.latitude},{waypoint.longitude}")
        return intermediate_waypoints

    def _get_directions(self, origin: str, destination: str, waypoints: List[str],
                       route: Route) -> Optional[Dict[str, Any]]:
        """Call Google Maps Directions API"""
        if not self.google_api_key:
            logger.error("Google Maps API key not configured")
            return None

        # Build API request
        params = {
            'origin': origin,
            'destination': destination,
            'key': self.google_api_key,
            'mode': 'driving',
            'units': 'metric',
            'optimize': 'true',  # Optimize waypoint order
        }

        if waypoints:
            params['waypoints'] = 'optimize:true|' + '|'.join(waypoints)

        # Add route preferences
        if route.avoid_tolls:
            params['avoid'] = 'tolls'
        elif route.avoid_highways:
            params['avoid'] = 'highways'

        try:
            response = requests.get(
                f"{self.base_url}/directions/json",
                params=params,
                timeout=30
            )
            response.raise_for_status()

            data = response.json()
            if data['status'] == 'OK' and data['routes']:
                return data['routes'][0]  # Return the first (best) route
            else:
                logger.error(f"Google Maps API error: {data.get('status', 'Unknown error')}")
                return None

        except requests.RequestException as e:
            logger.error(f"Failed to call Google Maps API: {e}")
            return None

    def _update_route_with_directions(self, route: Route, directions: Dict[str, Any]):
        """Update route with directions data"""
        route_data = directions['legs'][0] if directions['legs'] else {}

        # Update total distance and duration
        total_distance = sum(leg.get('distance', {}).get('value', 0) for leg in directions['legs']) / 1000  # Convert to km
        total_duration = sum(leg.get('duration', {}).get('value', 0) for leg in directions['legs']) / 60  # Convert to minutes

        route.total_distance_km = round(total_distance, 2)
        route.total_duration_minutes = int(total_duration)

        # Store route polyline
        route.route_polyline = directions.get('overview_polyline', {}).get('points', '')

        # Calculate estimated fuel cost
        if route.total_distance_km:
            fuel_needed = route.total_distance_km / self.settings.fuel_efficiency_kmpl
            route.estimated_fuel_cost = round(fuel_needed * self.settings.fuel_cost_per_liter, 2)

    def _update_waypoints_with_directions(self, route: Route, directions: Dict[str, Any],
                                        waypoints: List[RouteWaypoint]):
        """Update waypoints with optimized order and timing"""
        legs = directions['legs']
        waypoint_order = directions.get('waypoint_order', [])

        # Update stop order based on optimization
        for i, waypoint_index in enumerate(waypoint_order):
            if waypoint_index < len(waypoints):
                waypoints[waypoint_index].stop_order = i + 1
                waypoints[waypoint_index].save()

        # Update timing estimates for each waypoint
        current_time = datetime.combine(route.route_date, route.technician.default_start_time)
        current_time = timezone.make_aware(current_time)

        for i, leg in enumerate(legs):
            # Travel time to this stop
            travel_duration = leg.get('duration', {}).get('value', 0) / 60  # minutes
            distance = leg.get('distance', {}).get('value', 0) / 1000  # km

            # Update waypoint data
            if i < len(waypoints):
                waypoint = waypoints[i]

                # Set estimated arrival time
                waypoint.estimated_arrival_time = (current_time + timedelta(minutes=travel_duration)).time()
                waypoint.distance_from_previous_km = round(distance, 2)
                waypoint.travel_time_minutes = int(travel_duration)

                # Estimate departure time (arrival + job duration + buffer)
                job_duration = waypoint.estimated_duration_minutes or self.settings.average_job_duration_minutes
                buffer_time = int(job_duration * (self.settings.buffer_time_percentage / 100))
                total_stop_time = job_duration + buffer_time

                waypoint.estimated_departure_time = (
                    current_time + timedelta(minutes=travel_duration + total_stop_time)
                ).time()

                waypoint.save()

                # Update current time for next waypoint
                current_time += timedelta(minutes=travel_duration + total_stop_time + self.settings.default_break_duration_minutes)

    def calculate_route_efficiency(self, route: Route) -> Dict[str, Any]:
        """
        Calculate efficiency metrics for a completed route.
        """
        waypoints = route.get_waypoints_ordered()

        if not waypoints.exists():
            return {}

        completed_waypoints = waypoints.filter(status='completed')

        # Calculate actual vs estimated metrics
        actual_distance = sum(w.distance_from_previous_km or 0 for w in waypoints)
        actual_duration = sum(w.actual_duration_minutes or 0 for w in waypoints)

        estimated_distance = route.total_distance_km or 0
        estimated_duration = route.total_duration_minutes or 0

        # Efficiency scores (lower is better)
        distance_efficiency = (actual_distance / estimated_distance * 100) if estimated_distance > 0 else 100
        time_efficiency = (actual_duration / estimated_duration * 100) if estimated_duration > 0 else 100

        return {
            'total_stops': waypoints.count(),
            'completed_stops': completed_waypoints.count(),
            'actual_distance_km': round(actual_distance, 2),
            'estimated_distance_km': round(estimated_distance, 2),
            'actual_duration_hours': round(actual_duration / 60, 2),
            'estimated_duration_hours': round(estimated_duration / 60, 2),
            'distance_efficiency_percent': round(distance_efficiency, 1),
            'time_efficiency_percent': round(time_efficiency, 1),
            'on_time_completion_rate': round(
                (completed_waypoints.filter(actual_arrival_time__isnull=False).count() / completed_waypoints.count() * 100)
                if completed_waypoints.exists() else 0, 1
            ),
        }

    def get_route_suggestions(self, technician_id: int, date: str, jobs: List[int]) -> List[Dict[str, Any]]:
        """
        Get route optimization suggestions for a set of jobs.
        """
        from technicians.models import TechnicianProfile
        from jobs.models import Job

        try:
            technician = TechnicianProfile.objects.get(id=technician_id)
            selected_jobs = Job.objects.filter(id__in=jobs)

            # Create a temporary route for suggestions
            temp_route = Route(
                technician=technician,
                route_date=date,
                status='planned'
            )

            # Create temporary waypoints
            waypoints = []
            for i, job in enumerate(selected_jobs):
                waypoint = RouteWaypoint(
                    route=temp_route,
                    job=job,
                    stop_order=i + 1,
                    address=job.address,
                    latitude=job.latitude,
                    longitude=job.longitude,
                    estimated_duration_minutes=120  # Default estimate
                )
                waypoints.append(waypoint)

            # Get optimization suggestions
            suggestions = self._analyze_route_options(temp_route, waypoints)

            return suggestions

        except Exception as e:
            logger.error(f"Failed to get route suggestions: {e}")
            return []

    def _analyze_route_options(self, route: Route, waypoints: List[RouteWaypoint]) -> List[Dict[str, Any]]:
        """Analyze different route optimization options"""
        options = []

        # Option 1: Distance optimization
        distance_option = self._calculate_route_option(route, waypoints, 'distance')
        options.append(distance_option)

        # Option 2: Time optimization
        time_option = self._calculate_route_option(route, waypoints, 'time')
        options.append(time_option)

        # Option 3: Efficiency optimization
        efficiency_option = self._calculate_route_option(route, waypoints, 'efficiency')
        options.append(efficiency_option)

        return sorted(options, key=lambda x: x['total_duration_minutes'])

    def _calculate_route_option(self, route: Route, waypoints: List[RouteWaypoint],
                               optimization_type: str) -> Dict[str, Any]:
        """Calculate metrics for a route option"""
        # This is a simplified calculation - in production, you'd use Google Maps API
        total_distance = 0
        total_duration = 0

        for i, waypoint in enumerate(waypoints):
            if i > 0:
                # Estimate distance between points (simplified)
                prev_waypoint = waypoints[i-1]
                # In production, calculate actual distance using Google Maps Distance Matrix API
                distance = 10  # Placeholder km
                duration = 15  # Placeholder minutes

                total_distance += distance
                total_duration += duration

            # Add job duration
            job_duration = waypoint.estimated_duration_minutes or 120
            total_duration += job_duration

            # Add break time between jobs
            if i > 0:
                total_duration += self.settings.default_break_duration_minutes

        fuel_cost = (total_distance / self.settings.fuel_efficiency_kmpl) * self.settings.fuel_cost_per_liter

        return {
            'optimization_type': optimization_type,
            'total_distance_km': round(total_distance, 2),
            'total_duration_minutes': total_duration,
            'estimated_fuel_cost': round(fuel_cost, 2),
            'stop_count': len(waypoints),
        }
