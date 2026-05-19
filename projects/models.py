from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('project_manager', 'Project Manager'),
        ('team_leader', 'Team Leader'),
        ('team_member', 'Team Member'),
        ('client', 'Client'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='team_member')
    phone = models.CharField(max_length=20, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profiles/', blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"
    
class Team(models.Model):
    name = models.CharField(max_length=200)
    project_manager = models.ForeignKey(User, on_delete=models.CASCADE, related_name='teams_managed')
    leaders = models.ManyToManyField(User, related_name='teams_led', blank=True)
    members = models.ManyToManyField(User, related_name='teams_joined', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

# Signals to automatically create UserProfile
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()
    else:
        UserProfile.objects.get_or_create(user=instance)

class Client(models.Model):
    PRIORITY_CHOICES = [
        ('vip', 'VIP'),
        ('premium', 'Premium'),
        ('regular', 'Regular'),
    ]
    name = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Professional Additions
    client_id = models.CharField(max_length=50, blank=True, null=True)
    revenue_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    revenue_pending = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='regular')
    satisfaction = models.DecimalField(max_digits=3, decimal_places=1, default=5.0)
    notes = models.TextField(blank=True, null=True)
    last_message_date = models.DateField(blank=True, null=True)
    last_meeting_date = models.DateField(blank=True, null=True)

    def __str__(self):
        return self.name

class Project(models.Model):
    STATUS_CHOICES = [
        ('planning', 'Planning'),
        ('ongoing', 'In Progress'),
        ('completed', 'Completed'),
        ('on_hold', 'On Hold'),
    ]
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    APPROVAL_CHOICES = [
        ('pending', 'Waiting for approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('revision', 'Revision requested'),
    ]
    STAGE_CHOICES = [
        ('planning', 'Planning'),
        ('design', 'Design'),
        ('development', 'Development'),
        ('testing', 'Testing'),
        ('deployment', 'Deployment'),
    ]
    BUDGET_CHOICES = [
        ('fixed', 'Fixed'),
        ('hourly', 'Hourly'),
    ]
    title = models.CharField(max_length=200)
    description = models.TextField()
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='projects')
    manager = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='managed_projects')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planning')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    deadline = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Professional Additions
    estimated_hours = models.PositiveIntegerField(default=100)
    worked_hours = models.PositiveIntegerField(default=0)
    approval_status = models.CharField(max_length=30, choices=APPROVAL_CHOICES, default='pending')
    current_stage = models.CharField(max_length=30, choices=STAGE_CHOICES, default='planning')
    tags = models.CharField(max_length=200, default='UI/UX, Django')
    budget_type = models.CharField(max_length=20, choices=BUDGET_CHOICES, default='fixed')
    budget_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def get_progress(self):
        total_tasks = self.tasks.count()
        if total_tasks == 0:
            return 0
        done_tasks = self.tasks.filter(status='done').count()
        return int((done_tasks / total_tasks) * 100)

    def __str__(self):
        return self.title

class Task(models.Model):
    STATUS_CHOICES = [
        ('todo', 'To Do'),
        ('in_progress', 'In Progress'),
        ('review', 'In Review'),
        ('done', 'Completed'),
    ]
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='assigned_tasks')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='todo')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    deadline = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notification for {self.user.username}"

class Report(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='reports')
    submitted_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='submitted_reports')
    title = models.CharField(max_length=200)
    content = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Report: {self.title} - {self.submitted_by.username}"

class Message(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages', null=True, blank=True)
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True, related_name='messages')
    content = models.TextField(blank=True, null=True)
    file = models.FileField(upload_to='chat_files/', null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"From {self.sender.username} at {self.created_at}"

class ProjectFile(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='files')
    name = models.CharField(max_length=200)
    file = models.FileField(upload_to='project_files/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Feedback(models.Model):
    CATEGORY_CHOICES = [
        ('ui_design', 'UI Design'),
        ('bug', 'Bug'),
        ('performance', 'Performance'),
        ('communication', 'Communication'),
        ('feature_request', 'Feature Request'),
    ]
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
    ]
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='feedbacks')
    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name='given_feedback')
    subject = models.CharField(max_length=200)
    message = models.TextField()
    rating = models.PositiveSmallIntegerField(default=0)  
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Professional Additions
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='ui_design')
    attachment = models.FileField(upload_to='feedback_attachments/', null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    reply = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Feedback from {self.client.username} on {self.project.title}"

class TaskComment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.author.username} on {self.task.title}"

class TaskFile(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='files')
    name = models.CharField(max_length=200)
    file = models.FileField(upload_to='task_files/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Meeting(models.Model):
    title = models.CharField(max_length=200)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='meetings', null=True, blank=True)
    organizer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='organized_meetings')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.title

# New Models for the Enterprise Level Features
class Invoice(models.Model):
    STATUS_CHOICES = [
        ('paid', 'Paid'),
        ('pending', 'Pending'),
    ]
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='invoices')
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='invoices')
    invoice_number = models.CharField(max_length=50, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    due_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Invoice {self.invoice_number} - {self.client.name}"

class MeetingNote(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='meeting_notes')
    title = models.CharField(max_length=200)
    summary = models.TextField()
    discussion_points = models.TextField()
    next_actions = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Meeting Note: {self.title} ({self.client.name})"

class ActivityLog(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='activity_logs', null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activity_logs')
    activity_type = models.CharField(max_length=100)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.activity_type} - {self.user.username} at {self.created_at}"

class ClientPermission(models.Model):
    client = models.OneToOneField(Client, on_delete=models.CASCADE, related_name='permissions')
    can_upload = models.BooleanField(default=True)
    can_comment = models.BooleanField(default=True)
    can_edit = models.BooleanField(default=False)

    def __str__(self):
        return f"Permissions for {self.client.name}"
