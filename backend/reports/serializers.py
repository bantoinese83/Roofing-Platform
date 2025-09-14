from rest_framework import serializers
from .models import Report, ReportExecution, DashboardMetric


class ReportSerializer(serializers.ModelSerializer):
    """Serializer for reports"""
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    execution_count = serializers.SerializerMethodField()
    last_execution_status = serializers.SerializerMethodField()
    last_execution_date = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = [
            'id', 'name', 'report_type', 'description', 'date_range_start',
            'date_range_end', 'parameters', 'is_scheduled', 'frequency',
            'recipients', 'email_recipients', 'created_by', 'created_by_name',
            'is_active', 'last_run_at', 'execution_count', 'last_execution_status',
            'last_execution_date', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'last_run_at']

    def get_execution_count(self, obj):
        return obj.executions.count()

    def get_last_execution_status(self, obj):
        last_execution = obj.executions.order_by('-created_at').first()
        return last_execution.status if last_execution else None

    def get_last_execution_date(self, obj):
        last_execution = obj.executions.order_by('-created_at').first()
        return last_execution.created_at if last_execution else None


class ReportExecutionSerializer(serializers.ModelSerializer):
    """Serializer for report executions"""
    report_name = serializers.CharField(source='report.name', read_only=True)
    executed_by_name = serializers.CharField(source='executed_by.get_full_name', read_only=True)
    duration = serializers.ReadOnlyField()

    class Meta:
        model = ReportExecution
        fields = [
            'id', 'report', 'report_name', 'status', 'started_at', 'completed_at',
            'executed_by', 'executed_by_name', 'duration', 'error_message', 'created_at'
        ]
        read_only_fields = ['created_at', 'started_at', 'completed_at', 'duration']


class DashboardMetricSerializer(serializers.ModelSerializer):
    """Serializer for dashboard metrics"""
    trend_percentage = serializers.ReadOnlyField()

    class Meta:
        model = DashboardMetric
        fields = [
            'id', 'name', 'metric_type', 'value', 'value_text', 'unit',
            'previous_value', 'trend_direction', 'trend_percentage',
            'refresh_interval_minutes', 'last_updated', 'is_active',
            'display_order', 'color_code'
        ]
        read_only_fields = ['last_updated', 'trend_percentage']


class DashboardDataSerializer(serializers.Serializer):
    """Serializer for dashboard data"""
    metrics = DashboardMetricSerializer(many=True)
    recent_jobs = serializers.ListField()
    recent_quotes = serializers.ListField()
    alerts = serializers.ListField()
    last_updated = serializers.DateTimeField()

    def to_representation(self, instance):
        return instance


class ChartDataSerializer(serializers.Serializer):
    """Serializer for chart data"""
    title = serializers.CharField()
    type = serializers.CharField()
    data = serializers.ListField()
    period = serializers.CharField(required=False)
    total_items = serializers.IntegerField(required=False)
    conversion_rate = serializers.DecimalField(max_digits=5, decimal_places=1, required=False)

    def to_representation(self, instance):
        return instance


class AnalyticsDataSerializer(serializers.Serializer):
    """Serializer for analytics data"""
    period = serializers.CharField()
    job_performance = serializers.DictField()
    revenue = serializers.DictField()
    customers = serializers.DictField()
    technicians = serializers.DictField()

    def to_representation(self, instance):
        return instance


class TrendDataSerializer(serializers.Serializer):
    """Serializer for trend analysis data"""
    daily_trends = serializers.ListField()
    weekly_trends = serializers.ListField()
    period = serializers.CharField()

    def to_representation(self, instance):
        return instance
