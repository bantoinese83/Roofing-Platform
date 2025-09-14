from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
from decimal import Decimal


class Job(models.Model):
    """
    Comprehensive job model for roofing jobs with scheduling and management features.
    """

    STATUS_CHOICES = [
        ('new', 'New'),
        ('scheduled', 'Scheduled'),
        ('dispatched', 'Dispatched'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('on_hold', 'On Hold'),
    ]

    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]

    JOB_TYPES = [
        ('repair', 'Repair'),
        ('replacement', 'Replacement'),
        ('inspection', 'Inspection'),
        ('maintenance', 'Maintenance'),
        ('emergency', 'Emergency'),
        ('other', 'Other'),
    ]

    # Customer relationship
    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.CASCADE,
        related_name='jobs',
        help_text='Customer this job belongs to'
    )

    # Job identification
    job_number = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        help_text='Unique job number (auto-generated)'
    )

    # Job details
    title = models.CharField(
        max_length=200,
        help_text='Brief title describing the job'
    )

    description = models.TextField(
        blank=True,
        help_text='Detailed description of the work to be done'
    )

    job_type = models.CharField(
        max_length=20,
        choices=JOB_TYPES,
        default='repair',
        help_text='Type of roofing job'
    )

    # Status and priority
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='new',
        help_text='Current status of the job'
    )

    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default='medium',
        help_text='Priority level of the job'
    )

    # Scheduling
    scheduled_date = models.DateField(
        null=True,
        blank=True,
        help_text='Date when the job is scheduled'
    )

    scheduled_time = models.TimeField(
        null=True,
        blank=True,
        help_text='Time when the job is scheduled to start'
    )

    estimated_duration_hours = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.1'))],
        help_text='Estimated duration in hours'
    )

    actual_start_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Actual time the job started'
    )

    actual_end_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Actual time the job ended'
    )

    # Assignment
    assigned_crew = models.ForeignKey(
        'technicians.Crew',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_jobs',
        help_text='Crew assigned to this job'
    )

    assigned_technicians = models.ManyToManyField(
        'technicians.TechnicianProfile',
        blank=True,
        related_name='assigned_jobs',
        help_text='Individual technicians assigned to this job'
    )

    # Location and mapping
    address = models.TextField(
        blank=True,
        help_text='Job address (can be different from customer address)'
    )

    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text='GPS latitude for mapping'
    )

    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text='GPS longitude for mapping'
    )

    # Materials and requirements
    required_materials = models.JSONField(
        null=True,
        blank=True,
        help_text='List of required materials with quantities'
    )

    special_instructions = models.TextField(
        blank=True,
        help_text='Special instructions for the job'
    )

    customer_notes = models.TextField(
        blank=True,
        help_text='Notes visible to customer'
    )

    internal_notes = models.TextField(
        blank=True,
        help_text='Internal notes not visible to customer'
    )

    # Financial information
    estimated_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Estimated cost of the job'
    )

    actual_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Actual cost of the job'
    )

    # Progress tracking
    progress_percentage = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text='Job completion percentage (0-100)'
    )

    # Quality and feedback
    quality_rating = models.PositiveIntegerField(
        null=True,
        blank=True,
        choices=[(i, str(i)) for i in range(1, 6)],
        help_text='Quality rating (1-5 stars)'
    )

    customer_feedback = models.TextField(
        blank=True,
        help_text='Customer feedback after job completion'
    )

    # Metadata
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_jobs',
        help_text='User who created this job'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-scheduled_date', '-created_at']
        verbose_name = 'Job'
        verbose_name_plural = 'Jobs'
        indexes = [
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['scheduled_date', 'status']),
            models.Index(fields=['assigned_crew', 'status']),
            models.Index(fields=['job_number']),
            models.Index(fields=['created_at']),
            models.Index(fields=['status', 'priority']),
        ]

    def __str__(self):
        return f"{self.job_number or 'No Number'} - {self.customer.get_full_name()} - {self.title}"

    def save(self, *args, **kwargs):
        # Auto-generate job number if not set
        if not self.job_number:
            # Generate job number like JOB-20241215-001
            import datetime
            today = datetime.date.today()
            date_str = today.strftime('%Y%m%d')

            # Find the next number for today
            today_jobs = Job.objects.filter(
                job_number__startswith=f'JOB-{date_str}',
                created_at__date=today
            ).count()

            self.job_number = f'JOB-{date_str}-{str(today_jobs + 1).zfill(3)}'

        super().save(*args, **kwargs)

    @property
    def is_overdue(self):
        """Check if scheduled job is overdue"""
        if self.scheduled_date and self.status in ['scheduled', 'dispatched', 'in_progress']:
            from django.utils import timezone
            return self.scheduled_date < timezone.now().date()
        return False

    @property
    def duration_display(self):
        """Display estimated duration in a readable format"""
        if self.estimated_duration_hours:
            hours = int(self.estimated_duration_hours)
            minutes = int((self.estimated_duration_hours - hours) * 60)
            if minutes > 0:
                return f"{hours}h {minutes}m"
            return f"{hours}h"
        return "Not specified"

    @property
    def actual_duration(self):
        """Calculate actual job duration if completed"""
        if self.actual_start_time and self.actual_end_time:
            duration = self.actual_end_time - self.actual_start_time
            return duration.total_seconds() / 3600  # Convert to hours
        return None

    def get_status_color(self):
        """Get color code for job status (for UI)"""
        colors = {
            'new': 'gray',
            'scheduled': 'blue',
            'dispatched': 'purple',
            'in_progress': 'yellow',
            'completed': 'green',
            'cancelled': 'red',
            'on_hold': 'orange',
        }
        return colors.get(self.status, 'gray')

    def get_priority_color(self):
        """Get color code for job priority"""
        colors = {
            'low': 'green',
            'medium': 'yellow',
            'high': 'orange',
            'urgent': 'red',
        }
        return colors.get(self.priority, 'gray')

    def can_be_assigned_to_crew(self, crew):
        """Check if this job can be assigned to a crew"""
        # Check if crew has capacity
        if crew.max_concurrent_jobs <= crew.assigned_jobs.filter(
            status__in=['scheduled', 'dispatched', 'in_progress']
        ).count():
            return False

        # Check if crew has required skills (basic check)
        if self.required_materials and crew.primary_skill:
            # This is a simplified check - in reality, you'd check specific skills needed
            pass

        return True


class JobPhoto(models.Model):
    """
    Photos uploaded for jobs (before, during, and after).
    """
    PHOTO_TYPES = [
        ('before', 'Before Work'),
        ('during', 'During Work'),
        ('after', 'After Work'),
        ('damage', 'Damage Documentation'),
        ('other', 'Other'),
    ]

    job = models.ForeignKey(
        Job,
        on_delete=models.CASCADE,
        related_name='photos',
        help_text='Job this photo belongs to'
    )

    image = models.ImageField(
        upload_to='job_photos/',
        help_text='Photo file'
    )

    photo_type = models.CharField(
        max_length=20,
        choices=PHOTO_TYPES,
        default='other',
        help_text='Type of photo'
    )

    caption = models.CharField(
        max_length=200,
        blank=True,
        help_text='Optional caption for the photo'
    )

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_job_photos',
        help_text='User who uploaded this photo'
    )

    uploaded_at = models.DateTimeField(auto_now_add=True)

    # Location data if photo was taken on site
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text='GPS latitude where photo was taken'
    )

    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text='GPS longitude where photo was taken'
    )

    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = 'Job Photo'
        verbose_name_plural = 'Job Photos'

    def __str__(self):
        return f"{self.job.job_number} - {self.get_photo_type_display()}"


class JobDocument(models.Model):
    """
    Documents uploaded for jobs (estimates, contracts, permits, etc.).
    """
    DOCUMENT_TYPES = [
        ('estimate', 'Estimate'),
        ('contract', 'Contract'),
        ('permit', 'Permit'),
        ('invoice', 'Invoice'),
        ('warranty', 'Warranty'),
        ('other', 'Other'),
    ]

    job = models.ForeignKey(
        Job,
        on_delete=models.CASCADE,
        related_name='documents',
        help_text='Job this document belongs to'
    )

    document = models.FileField(
        upload_to='job_documents/',
        help_text='Document file'
    )

    document_type = models.CharField(
        max_length=20,
        choices=DOCUMENT_TYPES,
        default='other',
        help_text='Type of document'
    )

    title = models.CharField(
        max_length=200,
        help_text='Document title'
    )

    description = models.TextField(
        blank=True,
        help_text='Optional description'
    )

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_job_documents',
        help_text='User who uploaded this document'
    )

    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = 'Job Document'
        verbose_name_plural = 'Job Documents'

    def __str__(self):
        return f"{self.job.job_number} - {self.title}"


class JobStatusUpdate(models.Model):
    """
    Track status changes and updates for jobs.
    """
    job = models.ForeignKey(
        Job,
        on_delete=models.CASCADE,
        related_name='status_updates',
        help_text='Job this update belongs to'
    )

    old_status = models.CharField(
        max_length=20,
        choices=Job.STATUS_CHOICES,
        help_text='Previous job status'
    )

    new_status = models.CharField(
        max_length=20,
        choices=Job.STATUS_CHOICES,
        help_text='New job status'
    )

    notes = models.TextField(
        blank=True,
        help_text='Notes about the status change'
    )

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='job_status_updates',
        help_text='User who made this status update'
    )

    updated_at = models.DateTimeField(auto_now_add=True)

    # Location data if status was updated on site
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text='GPS latitude where status was updated'
    )

    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text='GPS longitude where status was updated'
    )

    class Meta:
        ordering = ['-updated_at']
        verbose_name = 'Job Status Update'
        verbose_name_plural = 'Job Status Updates'

    def __str__(self):
        return f"{self.job.job_number}: {self.old_status} → {self.new_status}"


class JobNote(models.Model):
    """
    Internal notes and chat messages for jobs (Version 1.1).
    """

    NOTE_TYPES = [
        ('note', 'Internal Note'),
        ('chat', 'Chat Message'),
        ('system', 'System Message'),
        ('status_change', 'Status Change'),
    ]

    VISIBILITY_CHOICES = [
        ('all', 'All Users'),
        ('office', 'Office Staff Only'),
        ('technicians', 'Technicians Only'),
        ('private', 'Private Note'),
    ]

    job = models.ForeignKey(
        Job,
        on_delete=models.CASCADE,
        related_name='notes',
        help_text='Job this note belongs to'
    )

    note_type = models.CharField(
        max_length=20,
        choices=NOTE_TYPES,
        default='note',
        help_text='Type of note/message'
    )

    content = models.TextField(
        help_text='Content of the note or message'
    )

    visibility = models.CharField(
        max_length=20,
        choices=VISIBILITY_CHOICES,
        default='all',
        help_text='Who can see this note'
    )

    # File attachments (optional)
    attachment = models.FileField(
        upload_to='job_notes/',
        blank=True,
        null=True,
        help_text='Optional file attachment'
    )

    attachment_name = models.CharField(
        max_length=255,
        blank=True,
        help_text='Original filename of attachment'
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='job_notes_created',
        help_text='User who created this note'
    )

    # For chat-like threading
    parent_note = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='replies',
        help_text='Parent note for threaded conversations'
    )

    # Read status for chat messages
    read_by = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='read_job_notes',
        help_text='Users who have read this note'
    )

    is_pinned = models.BooleanField(
        default=False,
        help_text='Whether this note is pinned to the top'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_pinned', '-created_at']
        verbose_name = 'Job Note'
        verbose_name_plural = 'Job Notes'
        indexes = [
            models.Index(fields=['job', 'created_at']),
            models.Index(fields=['job', 'visibility']),
            models.Index(fields=['created_by', 'created_at']),
            models.Index(fields=['parent_note']),
        ]

    def __str__(self):
        return f"{self.job.job_number} - {self.get_note_type_display()} by {self.created_by.get_full_name() if self.created_by else 'Unknown'}"

    @property
    def has_replies(self):
        """Check if this note has replies"""
        return self.replies.exists()

    @property
    def reply_count(self):
        """Get the number of replies"""
        return self.replies.count()

    @property
    def is_reply(self):
        """Check if this is a reply to another note"""
        return self.parent_note is not None

    def mark_as_read(self, user):
        """Mark this note as read by a user"""
        self.read_by.add(user)

    def is_read_by(self, user):
        """Check if this note has been read by a user"""
        return self.read_by.filter(id=user.id).exists()

    def get_thread_notes(self):
        """Get all notes in this thread (including replies)"""
        if self.is_reply:
            # This is a reply, get the root note's thread
            root_note = self.parent_note
            while root_note.is_reply:
                root_note = root_note.parent_note
            return root_note.get_thread_notes()

        # This is the root note, get all replies
        thread_notes = [self]
        for reply in self.replies.all():
            thread_notes.extend(reply.get_thread_notes())
        return thread_notes


class JobHistory(models.Model):
    """
    Complete audit trail for all job changes (Version 1.1).
    """

    HISTORY_TYPES = [
        ('created', 'Job Created'),
        ('updated', 'Field Updated'),
        ('status_changed', 'Status Changed'),
        ('assigned', 'Assignment Changed'),
        ('photo_added', 'Photo Added'),
        ('photo_removed', 'Photo Removed'),
        ('document_added', 'Document Added'),
        ('document_removed', 'Document Removed'),
        ('note_added', 'Note Added'),
        ('notification_sent', 'Notification Sent'),
    ]

    job = models.ForeignKey(
        Job,
        on_delete=models.CASCADE,
        related_name='history',
        help_text='Job this history entry belongs to'
    )

    history_type = models.CharField(
        max_length=30,
        choices=HISTORY_TYPES,
        help_text='Type of change that occurred'
    )

    # Change details
    field_name = models.CharField(
        max_length=100,
        blank=True,
        help_text='Name of the field that was changed (if applicable)'
    )

    old_value = models.TextField(
        blank=True,
        help_text='Previous value of the field'
    )

    new_value = models.TextField(
        blank=True,
        help_text='New value of the field'
    )

    # Additional context
    description = models.TextField(
        blank=True,
        help_text='Human-readable description of the change'
    )

    # Related objects
    related_photo = models.ForeignKey(
        'JobPhoto',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='history_entries',
        help_text='Related photo (if applicable)'
    )

    related_document = models.ForeignKey(
        'JobDocument',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='history_entries',
        help_text='Related document (if applicable)'
    )

    related_note = models.ForeignKey(
        'JobNote',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='history_entries',
        help_text='Related note (if applicable)'
    )

    # Who made the change
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='job_changes',
        help_text='User who made this change'
    )

    # Metadata
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text='IP address of the user who made the change'
    )

    user_agent = models.TextField(
        blank=True,
        help_text='User agent string of the browser/device'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Job History'
        verbose_name_plural = 'Job History'
        indexes = [
            models.Index(fields=['job', 'created_at']),
            models.Index(fields=['history_type', 'created_at']),
            models.Index(fields=['changed_by', 'created_at']),
        ]

    def __str__(self):
        return f"{self.job.job_number} - {self.get_history_type_display()} at {self.created_at}"

    @property
    def is_field_change(self):
        """Check if this is a field value change"""
        return self.history_type in ['updated', 'status_changed', 'assigned']

    @property
    def is_asset_change(self):
        """Check if this is an asset (photo/document) change"""
        return self.history_type in ['photo_added', 'photo_removed', 'document_added', 'document_removed']

    @property
    def is_communication(self):
        """Check if this is a communication-related change"""
        return self.history_type in ['note_added', 'notification_sent']
