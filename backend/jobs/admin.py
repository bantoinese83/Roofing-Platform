from django.contrib import admin
from .models import Job, JobPhoto, JobDocument, JobStatusUpdate


class JobPhotoInline(admin.TabularInline):
    """
    Inline admin for JobPhoto.
    """
    model = JobPhoto
    extra = 0
    readonly_fields = ['uploaded_at']
    fields = ['image', 'photo_type', 'caption', 'uploaded_by', 'uploaded_at']


class JobDocumentInline(admin.TabularInline):
    """
    Inline admin for JobDocument.
    """
    model = JobDocument
    extra = 0
    readonly_fields = ['uploaded_at']
    fields = ['document', 'document_type', 'title', 'uploaded_by', 'uploaded_at']


class JobStatusUpdateInline(admin.TabularInline):
    """
    Inline admin for JobStatusUpdate.
    """
    model = JobStatusUpdate
    extra = 0
    readonly_fields = ['updated_at']
    fields = ['old_status', 'new_status', 'notes', 'updated_by', 'updated_at']
    ordering = ['-updated_at']


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    """
    Admin for Job model.
    """
    list_display = [
        'job_number', 'title', 'customer', 'status', 'priority',
        'scheduled_date', 'assigned_crew', 'is_overdue', 'created_at'
    ]
    list_filter = [
        'status', 'priority', 'job_type', 'scheduled_date',
        'assigned_crew', 'created_at'
    ]
    search_fields = [
        'job_number', 'title', 'description', 'customer__first_name',
        'customer__last_name', 'customer__email'
    ]
    ordering = ['-scheduled_date', '-created_at']

    fieldsets = (
        ('Job Information', {
            'fields': ('job_number', 'title', 'description', 'job_type')
        }),
        ('Customer & Scheduling', {
            'fields': ('customer', 'scheduled_date', 'scheduled_time', 'estimated_duration_hours')
        }),
        ('Assignment & Status', {
            'fields': ('status', 'priority', 'assigned_crew', 'assigned_technicians')
        }),
        ('Location', {
            'fields': ('address', 'latitude', 'longitude'),
            'classes': ('collapse',)
        }),
        ('Materials & Instructions', {
            'fields': ('required_materials', 'special_instructions', 'customer_notes', 'internal_notes'),
            'classes': ('collapse',)
        }),
        ('Financial', {
            'fields': ('estimated_cost', 'actual_cost'),
            'classes': ('collapse',)
        }),
        ('Progress & Quality', {
            'fields': ('progress_percentage', 'quality_rating', 'customer_feedback'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('actual_start_time', 'actual_end_time', 'created_by'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['job_number', 'created_at', 'updated_at']
    inlines = [JobPhotoInline, JobDocumentInline, JobStatusUpdateInline]
    filter_horizontal = ['assigned_technicians']

    def get_queryset(self, request):
        """Optimize queryset for admin"""
        return super().get_queryset(request).select_related(
            'customer', 'assigned_crew', 'created_by'
        )


@admin.register(JobPhoto)
class JobPhotoAdmin(admin.ModelAdmin):
    """
    Admin for JobPhoto model.
    """
    list_display = ['job', 'photo_type', 'caption', 'uploaded_by', 'uploaded_at']
    list_filter = ['photo_type', 'uploaded_at', 'uploaded_by']
    search_fields = ['job__job_number', 'job__title', 'caption', 'uploaded_by__username']
    readonly_fields = ['uploaded_at']

    fieldsets = (
        ('Job & Photo', {
            'fields': ('job', 'image', 'photo_type')
        }),
        ('Details', {
            'fields': ('caption', 'uploaded_by', 'uploaded_at')
        }),
        ('Location', {
            'fields': ('latitude', 'longitude'),
            'classes': ('collapse',)
        }),
    )


@admin.register(JobDocument)
class JobDocumentAdmin(admin.ModelAdmin):
    """
    Admin for JobDocument model.
    """
    list_display = ['job', 'document_type', 'title', 'uploaded_by', 'uploaded_at']
    list_filter = ['document_type', 'uploaded_at', 'uploaded_by']
    search_fields = ['job__job_number', 'job__title', 'title', 'uploaded_by__username']
    readonly_fields = ['uploaded_at']

    fieldsets = (
        ('Job & Document', {
            'fields': ('job', 'document', 'document_type', 'title')
        }),
        ('Details', {
            'fields': ('description', 'uploaded_by', 'uploaded_at')
        }),
    )


@admin.register(JobStatusUpdate)
class JobStatusUpdateAdmin(admin.ModelAdmin):
    """
    Admin for JobStatusUpdate model.
    """
    list_display = ['job', 'old_status', 'new_status', 'updated_by', 'updated_at']
    list_filter = ['old_status', 'new_status', 'updated_by', 'updated_at']
    search_fields = ['job__job_number', 'job__title', 'notes']
    readonly_fields = ['updated_at']

    fieldsets = (
        ('Job & Status', {
            'fields': ('job', 'old_status', 'new_status')
        }),
        ('Details', {
            'fields': ('notes', 'updated_by', 'updated_at')
        }),
        ('Location', {
            'fields': ('latitude', 'longitude'),
            'classes': ('collapse',)
        }),
    )