from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from datetime import date, datetime

# In models.py, add this field to UserProfile class:

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
    department = models.CharField(max_length=100, default='General')
    phone = models.CharField(max_length=20, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profiles/', blank=True, null=True)
    is_frozen = models.BooleanField(default=False)  # Add this line
    skills = models.CharField(max_length=500, blank=True, null=True)

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

    def get_accepted_assignment(self):
        return self.assignments.filter(status='accepted').first()

    def get_team_leader(self):
        assignment = self.get_accepted_assignment()
        return assignment.team_leader if assignment else None

    def get_team(self):
        leader = self.get_team_leader()
        if leader:
            return Team.objects.filter(leaders=leader).first()
        return None

    def get_team_members(self):
        team = self.get_team()
        return team.members.all() if team else []

    def get_completed_team_projects_count(self):
        leader = self.get_team_leader()
        if leader:
            return Project.objects.filter(
                assignments__team_leader=leader,
                assignments__status='accepted',
                status='completed'
            ).distinct().count()
        return 0

    def __str__(self):
        return self.title
    
class DemoURL(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("rejected", "Rejected"),
    ]

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="demo_urls")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="demo_urls")
    demo_video_url = models.URLField(blank=True, null=True)
    demo_project_url = models.URLField(blank=True, null=True)
    advance_payment = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    full_payment = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.client.name} - {self.project.title}"

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
    attachment = models.FileField(upload_to='report_files/', null=True, blank=True)
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

class ProjectAssignment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='assignments')
    team_leader = models.ForeignKey(User, on_delete=models.CASCADE, related_name='project_assignments')
    assigned_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assigned_projects')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    assigned_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('project', 'team_leader')

    def __str__(self):
        return f"{self.project.title} -> {self.team_leader.username} ({self.status})"

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

class Attendance(models.Model):
    STATUS_CHOICES = [
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('leave', 'Leave'),
    ]
    LOCATION_CHOICES = [
        ('office', 'Office'),
        ('remote', 'Remote'),
    ]
    DEVICE_CHOICES = [
        ('desktop', 'Desktop'),
        ('mobile', 'Mobile Login'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='attendances')
    date = models.DateField(default=date.today)
    check_in = models.DateTimeField(null=True, blank=True)
    check_out = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='present')
    location = models.CharField(max_length=20, choices=LOCATION_CHOICES, default='office')
    device = models.CharField(max_length=20, choices=DEVICE_CHOICES, default='desktop')
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    check_in_photo = models.TextField(blank=True, null=True)  # Store base64 photo data
    photo_captured_at = models.DateTimeField(null=True, blank=True)
    
    # Daily status update (standup)
    today_work = models.TextField(blank=True, null=True)
    blockers = models.TextField(blank=True, null=True)
    progress = models.IntegerField(default=0) # 0 to 100
    last_activity = models.DateTimeField(null=True, blank=True)
    # Mood status
    mood = models.CharField(max_length=20, blank=True, null=True) # e.g. Happy, Normal, Tired
    
    # Streak count
    streak = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'date')

    def __str__(self):
        return f"{self.user.username} - {self.date} - {self.status}"

    def total_work_seconds(self):
        if not self.check_in:
            return 0
        from django.utils import timezone
        end_time = self.check_out if self.check_out else timezone.now()
        diff = (end_time - self.check_in).total_seconds()
        # Subtract completed break durations
        break_duration = sum([b.duration_seconds() for b in self.breaks.all() if b.end_time])
        # Subtract active break duration
        ongoing_break = self.breaks.filter(end_time__isnull=True).first()
        if ongoing_break:
            break_duration += (timezone.now() - ongoing_break.start_time).total_seconds()
            
        return max(0, int(diff - break_duration))

class BreakLog(models.Model):
    BREAK_CHOICES = [
        ('lunch', 'Lunch Break'),
        ('tea', 'Tea Break'),
        ('meeting', 'Meeting Break'),
    ]
    attendance = models.ForeignKey(Attendance, on_delete=models.CASCADE, related_name='breaks')
    break_type = models.CharField(max_length=20, choices=BREAK_CHOICES, default='lunch')
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)

    def duration_seconds(self):
        if not self.end_time:
            from django.utils import timezone
            return int((timezone.now() - self.start_time).total_seconds())
        return int((self.end_time - self.start_time).total_seconds())

    def __str__(self):
        return f"{self.attendance.user.username} - {self.break_type} ({self.start_time})"

class LeaveRequest(models.Model):
    LEAVE_CHOICES = [
        ('sick', 'Sick Leave'),
        ('casual', 'Casual Leave'),
        ('emergency', 'Emergency Leave'),
        ('wfh', 'Work From Home'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='leave_requests')
    leave_type = models.CharField(max_length=20, choices=LEAVE_CHOICES, default='casual')
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_leaves')
    rejection_reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def required_approver_role(self):
        days = self.duration_days()
        if 1 <= days <= 2:
            return 'team_leader'
        elif 3 <= days <= 5:
            return 'project_manager'
        else:
            return 'admin'
        
    def __str__(self):
        return f"{self.user.username} - {self.leave_type} ({self.start_date} to {self.end_date})"

    def duration_days(self):
        return (self.end_date - self.start_date).days + 1

class LeaveBalance(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='leave_balance')
    sick_balance = models.PositiveIntegerField(default=12)
    casual_balance = models.PositiveIntegerField(default=15)
    emergency_balance = models.PositiveIntegerField(default=5)
    wfh_balance = models.PositiveIntegerField(default=20)

    def __str__(self):
        return f"{self.user.username}'s Leave Balance"

class ProductivityLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='productivity_logs')
    date = models.DateField(default=date.today)
    focus_time_seconds = models.PositiveIntegerField(default=0)
    efficiency = models.PositiveIntegerField(default=90)
    tasks_completed = models.PositiveIntegerField(default=0)
    bugs_fixed = models.PositiveIntegerField(default=0)
    files_uploaded = models.PositiveIntegerField(default=0)
    meetings_attended = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('user', 'date')

    def __str__(self):
        return f"{self.user.username} - {self.date} - {self.efficiency}%"

# Signals to automatically create LeaveBalance
@receiver(post_save, sender=User)
def create_leave_balance(sender, instance, created, **kwargs):
    if created:
        LeaveBalance.objects.get_or_create(user=instance)

@receiver(post_save, sender=User)
def save_leave_balance(sender, instance, **kwargs):
    if hasattr(instance, 'leave_balance'):
        instance.leave_balance.save()
    else:
        LeaveBalance.objects.get_or_create(user=instance)

class DemoSubmission(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('pm_approved', 'Approved by PM'),
        ('client_approved', 'Approved by Client'),
        ('rejected', 'Rejected'),
    ]
    PAYMENT_CHOICES = [
        ('advance', 'Advance Payment'),
        ('full', 'Full Payment'),
    ]
    
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='demo_submissions')
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='demo_submissions')
    demo_url = models.URLField(max_length=500, blank=True, null=True)
    demo_video = models.FileField(upload_to='demo_videos/', blank=True, null=True)
    main_project_url = models.URLField(max_length=500, blank=True, null=True)
    
    payment_type = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default='advance')
    payment_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    payment_notes = models.TextField(blank=True, null=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    submitted_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='submitted_demos')
    
    version = models.PositiveIntegerField(default=1)
    expires_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Demo v{self.version} - {self.project.title}"
