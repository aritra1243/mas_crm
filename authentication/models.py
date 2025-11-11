from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


class User(AbstractUser):
    """Custom User model with role-based access control"""
    
    ROLE_CHOICES = [
        ('super_admin', 'Super Admin'),
        ('admin', 'Admin'),
        ('manager', 'Manager'),
        ('marketing_team', 'Marketing Team'),
        ('allocater', 'Allocater'),
        ('writer', 'Writer'),
        ('process_team', 'Process Team'),
        ('accounts_team', 'Accounts Team'),
    ]
    
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='writer'
    )
    phone_number = models.CharField(
        max_length=15,
        blank=True,
        null=True
    )
    is_approved = models.BooleanField(
        default=False,
        help_text="Designates whether this user has been approved by an admin."
    )
    profile_picture = models.ImageField(
        upload_to='profile_pictures/',
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'users'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['role', 'is_approved']),
            models.Index(fields=['username']),
        ]
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
    def is_admin_or_super_admin(self):
        """Check if user has admin privileges"""
        return self.role in ['admin', 'super_admin']
    
    def can_allocate_jobs(self):
        """Check if user can allocate jobs"""
        return self.role in ['admin', 'super_admin', 'manager', 'allocater']


class Job(models.Model):
    """Job model with dual status tracking for writers and process team"""
    
    STATUS_CHOICES = [
        ('drop', 'Drop'),
        ('allocated', 'Allocated'),
        ('query', 'Query'),
        ('cancel', 'Cancel'),
        ('hold', 'Hold'),
        ('process', 'Process'),
        ('completed', 'Completed'),
    ]
    
    WRITER_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('closed', 'Closed'),
    ]
    
    PROCESS_TEAM_STATUS_CHOICES = [
        ('not_assigned', 'Not Assigned'),
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('closed', 'Closed'),
    ]
    
    # Core Identifiers
    job_id = models.CharField(
        max_length=100,
        unique=True,
        db_index=True
    )
    
    # User Assignments
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_jobs'
    )
    allocated_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='allocated_jobs',
        help_text="Writer assigned to this job"
    )
    process_team_member = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='process_team_jobs',
        help_text="Process team member assigned to this job"
    )
    
    # Job Details
    topic = models.TextField()
    word_count = models.IntegerField()
    referencing_style = models.CharField(
        max_length=100,
        blank=True
    )
    writing_style = models.CharField(
        max_length=100,
        blank=True
    )
    instruction = models.TextField()
    job_summary = models.TextField(
        blank=True,
        help_text="Brief summary of the job"
    )
    
    # Attachments
    attachment = models.FileField(
        upload_to='job_attachments/',
        null=True,
        blank=True,
        help_text="Initial job attachment"
    )
    
    # Deadlines
    expected_deadline = models.DateTimeField(
        help_text="Expected completion deadline"
    )
    strict_deadline = models.DateTimeField(
        help_text="Absolute deadline for job completion"
    )
    
    # Financial
    value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Job value in currency"
    )
    
    # Status Fields
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='drop',
        db_index=True
    )
    status_note = models.TextField(
        blank=True,
        help_text="Additional notes about current status"
    )
    
    writer_status = models.CharField(
        max_length=20,
        choices=WRITER_STATUS_CHOICES,
        default='pending',
        db_index=True
    )
    
    process_team_status = models.CharField(
        max_length=20,
        choices=PROCESS_TEAM_STATUS_CHOICES,
        default='not_assigned',
        db_index=True
    )
    
    # Time Tracking (Writer specific)
    start_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Time when writer started working"
    )
    end_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Time when writer completed work"
    )
    
    # Writer Upload Fields
    structure_file = models.FileField(
        upload_to='writer_uploads/structure/',
        null=True,
        blank=True,
        help_text="Structure/outline document"
    )
    final_copy = models.FileField(
        upload_to='writer_uploads/final/',
        null=True,
        blank=True,
        help_text="Final written document"
    )
    software_files = models.FileField(
        upload_to='writer_uploads/software/',
        null=True,
        blank=True,
        help_text="Software-related files (if applicable)"
    )
    final_copy_summary = models.TextField(
        blank=True,
        help_text="Summary of the final copy"
    )
    
    # Process Team Upload Fields - AI & Plagiarism Check
    ai_plag_final_file = models.FileField(
        upload_to='process_team/ai_plag/final/',
        null=True,
        blank=True
    )
    ai_plag_ai_report = models.FileField(
        upload_to='process_team/ai_plag/ai_report/',
        null=True,
        blank=True
    )
    ai_plag_plag_report = models.FileField(
        upload_to='process_team/ai_plag/plag_report/',
        null=True,
        blank=True
    )
    ai_plag_software = models.FileField(
        upload_to='process_team/ai_plag/software/',
        null=True,
        blank=True
    )
    
    # Process Team Upload Fields - Decoration
    decoration_final_file = models.FileField(
        upload_to='process_team/decoration/final/',
        null=True,
        blank=True
    )
    decoration_ai_report = models.FileField(
        upload_to='process_team/decoration/ai_report/',
        null=True,
        blank=True
    )
    decoration_plag_report = models.FileField(
        upload_to='process_team/decoration/plag_report/',
        null=True,
        blank=True
    )
    decoration_software = models.FileField(
        upload_to='process_team/decoration/software/',
        null=True,
        blank=True
    )
    decoration_decorated_file = models.FileField(
        upload_to='process_team/decoration/decorated/',
        null=True,
        blank=True,
        help_text="Final decorated/formatted document"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'jobs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'writer_status']),
            models.Index(fields=['allocated_to', 'writer_status']),
            models.Index(fields=['process_team_member', 'process_team_status']),
            models.Index(fields=['strict_deadline']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"{self.job_id} - {self.get_status_display()}"
    
    def get_masked_job_id(self):
        """
        Return masked job ID for writer and process team
        Shows only last 4 characters for privacy
        """
        if len(self.job_id) > 4:
            return f"***{self.job_id[-4:]}"
        return "****"
    
    def is_overdue(self):
        """Check if job has passed its strict deadline"""
        return timezone.now() > self.strict_deadline and self.status != 'completed'
    
    def get_time_spent(self):
        """Calculate time spent by writer (if both start and end times are set)"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None
    
    def can_be_allocated(self):
        """Check if job can be allocated to a writer"""
        return self.status == 'drop' and self.allocated_to is None
    
    def is_ready_for_process_team(self):
        """Check if job is ready for process team"""
        return (
            self.writer_status == 'closed' and
            self.final_copy and
            self.process_team_status == 'not_assigned'
        )


class Notification(models.Model):
    """Notification system for all users"""
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    job = models.ForeignKey(
        Job,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='job_notifications'
    )
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        read_status = 'Read' if self.is_read else 'Unread'
        return f"{self.user.username} - {self.message[:50]} - {read_status}"
    
    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.save(update_fields=['is_read'])
    
    @classmethod
    def create_notification(cls, user, message, job=None):
        """Create a new notification"""
        return cls.objects.create(
            user=user,
            message=message,
            job=job
        )
    
    @classmethod
    def get_unread_count(cls, user):
        """Get count of unread notifications for a user"""
        return cls.objects.filter(user=user, is_read=False).count()


# Signal handlers (optional - add these in signals.py)
"""
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=Job)
def notify_on_job_allocation(sender, instance, created, **kwargs):
    '''Send notification when job is allocated to a writer'''
    if instance.allocated_to and not created:
        Notification.create_notification(
            user=instance.allocated_to,
            message=f"New job allocated: {instance.get_masked_job_id()}",
            job=instance
        )

@receiver(post_save, sender=Job)
def notify_process_team_on_completion(sender, instance, **kwargs):
    '''Notify process team when writer completes job'''
    if instance.writer_status == 'closed' and instance.process_team_member:
        Notification.create_notification(
            user=instance.process_team_member,
            message=f"Job ready for processing: {instance.get_masked_job_id()}",
            job=instance
        )
"""