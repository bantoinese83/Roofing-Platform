from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class TechnicianProfile(models.Model):
    """
    Extended profile for technicians with additional information.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='technician_profile'
    )

    # Additional technician information
    employee_id = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        help_text='Employee identification number'
    )

    hourly_rate = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Hourly pay rate in dollars'
    )

    emergency_contact_name = models.CharField(
        max_length=100,
        blank=True,
        help_text='Name of emergency contact'
    )

    emergency_contact_phone = models.CharField(
        max_length=20,
        blank=True,
        help_text='Phone number of emergency contact'
    )

    # Professional information
    license_number = models.CharField(
        max_length=50,
        blank=True,
        help_text='Professional license number'
    )

    license_expiry = models.DateField(
        null=True,
        blank=True,
        help_text='License expiration date'
    )

    # Work preferences
    max_daily_hours = models.PositiveIntegerField(
        default=8,
        help_text='Maximum hours technician can work per day'
    )

    preferred_start_time = models.TimeField(
        null=True,
        blank=True,
        help_text='Preferred daily start time'
    )

    # Status
    is_available = models.BooleanField(
        default=True,
        help_text='Whether technician is currently available for work'
    )

    # Availability management (Version 1.1)
    timezone = models.CharField(
        max_length=50,
        default='America/New_York',
        help_text='Technician timezone'
    )

    working_days = models.JSONField(
        default=list,
        help_text='List of working days (0=Monday, 6=Sunday)'
    )

    default_start_time = models.TimeField(
        default='09:00:00',
        help_text='Default work start time'
    )

    default_end_time = models.TimeField(
        default='17:00:00',
        help_text='Default work end time'
    )

    break_duration_minutes = models.PositiveIntegerField(
        default=60,
        help_text='Break duration in minutes'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['user__first_name', 'user__last_name']
        verbose_name = 'Technician Profile'
        verbose_name_plural = 'Technician Profiles'

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.user.email})"

    @property
    def full_name(self):
        return self.user.get_full_name()

    @property
    def skills_list(self):
        """Return list of skills from certifications"""
        return list(self.certifications.values_list('skill__name', flat=True).distinct())


class Skill(models.Model):
    """
    Skills that technicians can have (e.g., roofing, siding, gutter installation).
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    category = models.CharField(
        max_length=50,
        choices=[
            ('roofing', 'Roofing'),
            ('siding', 'Siding'),
            ('gutters', 'Gutters'),
            ('insulation', 'Insulation'),
            ('general', 'General Construction'),
            ('other', 'Other'),
        ],
        default='roofing'
    )
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['category', 'name']

    def __str__(self):
        return f"{self.name} ({self.category})"


class Certification(models.Model):
    """
    Certifications held by technicians.
    """
    technician = models.ForeignKey(
        TechnicianProfile,
        on_delete=models.CASCADE,
        related_name='certifications'
    )
    skill = models.ForeignKey(
        Skill,
        on_delete=models.CASCADE,
        related_name='certifications'
    )

    # Certification details
    certification_number = models.CharField(
        max_length=100,
        blank=True,
        help_text='Official certification number'
    )

    issued_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)

    # Verification
    is_verified = models.BooleanField(
        default=False,
        help_text='Whether certification has been verified'
    )

    verification_document = models.FileField(
        upload_to='certifications/',
        blank=True,
        null=True,
        help_text='Uploaded verification document'
    )

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['technician', 'skill']
        ordering = ['-expiry_date', 'skill__name']

    def __str__(self):
        return f"{self.technician} - {self.skill}"

    @property
    def is_expired(self):
        """Check if certification is expired"""
        if self.expiry_date:
            from django.utils import timezone
            return self.expiry_date < timezone.now().date()
        return False

    @property
    def days_until_expiry(self):
        """Calculate days until expiry"""
        if self.expiry_date:
            from django.utils import timezone
            delta = self.expiry_date - timezone.now().date()
            return delta.days
        return None


class Crew(models.Model):
    """
    Crews that group technicians together for jobs.
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    # Crew leader (must be a technician)
    leader = models.ForeignKey(
        TechnicianProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='led_crews',
        help_text='Crew leader/foreman'
    )

    # Crew members
    members = models.ManyToManyField(
        TechnicianProfile,
        related_name='crews',
        blank=True,
        help_text='Technicians in this crew'
    )

    # Crew status
    is_active = models.BooleanField(
        default=True,
        help_text='Whether this crew is currently active'
    )

    # Crew specialization
    primary_skill = models.ForeignKey(
        Skill,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text='Primary skill/specialization of this crew'
    )

    # Work capacity
    max_concurrent_jobs = models.PositiveIntegerField(
        default=1,
        help_text='Maximum number of jobs this crew can work on simultaneously'
    )

    # Contact information
    contact_phone = models.CharField(
        max_length=20,
        blank=True,
        help_text='Crew contact phone number'
    )

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def member_count(self):
        """Get the number of active members in the crew"""
        return self.members.filter(user__is_active=True).count()

    @property
    def active_members(self):
        """Get active crew members"""
        return self.members.filter(
            user__is_active=True,
            is_available=True
        )

    @property
    def available_capacity(self):
        """Calculate available capacity based on concurrent jobs"""
        # This is a simplified calculation - in reality, you'd check current job assignments
        return self.max_concurrent_jobs

    def get_skills_summary(self):
        """Get summary of skills available in this crew"""
        skills = Skill.objects.filter(
            certifications__technician__in=self.members.all()
        ).distinct()

        skill_counts = {}
        for skill in skills:
            count = self.members.filter(
                certifications__skill=skill
            ).distinct().count()
            skill_counts[skill.name] = count

        return skill_counts


class TimeOffRequest(models.Model):
    """
    Time-off requests from technicians with approval workflow.
    """

    REQUEST_TYPES = [
        ('vacation', 'Vacation'),
        ('sick', 'Sick Leave'),
        ('personal', 'Personal Day'),
        ('jury_duty', 'Jury Duty'),
        ('bereavement', 'Bereavement'),
        ('other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('denied', 'Denied'),
        ('cancelled', 'Cancelled'),
    ]

    technician = models.ForeignKey(
        TechnicianProfile,
        on_delete=models.CASCADE,
        related_name='time_off_requests',
        help_text='Technician requesting time off'
    )

    request_type = models.CharField(
        max_length=20,
        choices=REQUEST_TYPES,
        help_text='Type of time-off request'
    )

    start_date = models.DateField(
        help_text='Start date of time off'
    )

    end_date = models.DateField(
        help_text='End date of time off'
    )

    start_time = models.TimeField(
        null=True,
        blank=True,
        help_text='Start time (for partial day requests)'
    )

    end_time = models.TimeField(
        null=True,
        blank=True,
        help_text='End time (for partial day requests)'
    )

    reason = models.TextField(
        blank=True,
        help_text='Reason for the time-off request'
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text='Approval status of the request'
    )

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='time_off_requests_created',
        help_text='User who created this request (usually the technician)'
    )

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='time_off_requests_approved',
        help_text='User who approved/denied this request'
    )

    approval_notes = models.TextField(
        blank=True,
        help_text='Notes from the approver'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Time-Off Request'
        verbose_name_plural = 'Time-Off Requests'
        indexes = [
            models.Index(fields=['technician', 'status']),
            models.Index(fields=['start_date', 'end_date']),
            models.Index(fields=['status', 'created_at']),
        ]

    def __str__(self):
        return f"{self.technician.full_name} - {self.get_request_type_display()} ({self.start_date} to {self.end_date})"

    @property
    def duration_days(self):
        """Calculate the duration in days"""
        if self.start_date and self.end_date:
            return (self.end_date - self.start_date).days + 1
        return 0

    @property
    def is_partial_day(self):
        """Check if this is a partial day request"""
        return self.start_time is not None and self.end_time is not None

    @property
    def conflicts_with_jobs(self):
        """Check if this request conflicts with scheduled jobs"""
        from jobs.models import Job
        conflicting_jobs = Job.objects.filter(
            assigned_technicians=self.technician,
            scheduled_date__gte=self.start_date,
            scheduled_date__lte=self.end_date,
            status__in=['scheduled', 'dispatched', 'in_progress']
        )
        return conflicting_jobs.exists()

    def approve(self, approved_by, notes=''):
        """Approve the time-off request"""
        self.status = 'approved'
        self.approved_by = approved_by
        self.approval_notes = notes
        self.save()

    def deny(self, approved_by, notes=''):
        """Deny the time-off request"""
        self.status = 'denied'
        self.approved_by = approved_by
        self.approval_notes = notes
        self.save()

    def cancel(self):
        """Cancel the time-off request"""
        self.status = 'cancelled'
        self.save()


class TechnicianSchedule(models.Model):
    """
    Custom schedule overrides for technicians (holidays, special hours, etc.).
    """

    SCHEDULE_TYPES = [
        ('holiday', 'Holiday'),
        ('special_hours', 'Special Hours'),
        ('unavailable', 'Unavailable'),
        ('training', 'Training'),
    ]

    technician = models.ForeignKey(
        TechnicianProfile,
        on_delete=models.CASCADE,
        related_name='schedule_overrides',
        help_text='Technician this schedule applies to'
    )

    schedule_type = models.CharField(
        max_length=20,
        choices=SCHEDULE_TYPES,
        help_text='Type of schedule override'
    )

    title = models.CharField(
        max_length=200,
        help_text='Title/description of the schedule override'
    )

    start_date = models.DateField(
        help_text='Start date of the override'
    )

    end_date = models.DateField(
        help_text='End date of the override'
    )

    start_time = models.TimeField(
        null=True,
        blank=True,
        help_text='Custom start time (for special hours)'
    )

    end_time = models.TimeField(
        null=True,
        blank=True,
        help_text='Custom end time (for special hours)'
    )

    is_all_day = models.BooleanField(
        default=True,
        help_text='Whether this override applies to the entire day'
    )

    notes = models.TextField(
        blank=True,
        help_text='Additional notes about this schedule'
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='schedule_overrides_created',
        help_text='User who created this schedule override'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['start_date', 'technician']
        verbose_name = 'Technician Schedule Override'
        verbose_name_plural = 'Technician Schedule Overrides'
        indexes = [
            models.Index(fields=['technician', 'start_date', 'end_date']),
            models.Index(fields=['schedule_type']),
        ]

    def __str__(self):
        return f"{self.technician.full_name} - {self.title} ({self.start_date} to {self.end_date})"
