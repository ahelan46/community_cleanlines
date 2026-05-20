from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from django.db.models import Count, Q
from .models import Client, Project, Task, Notification, Report, Message, Team, UserProfile, ProjectFile, Feedback, Meeting, Invoice, MeetingNote, ActivityLog, ClientPermission
from .forms import SignUpForm, ProjectForm, TaskForm, ReportForm, FeedbackForm, ClientProjectForm
from datetime import date, datetime
from django.utils.dateparse import parse_datetime, parse_date
from .models import Client, Project, Task, Notification, Report, Message, Team, UserProfile, ProjectFile, Feedback, ProjectAssignment
from .forms import SignUpForm, ProjectForm, TaskForm, ReportForm, FeedbackForm, ClientProjectForm, ProjectAssignmentForm
from datetime import date
from django.contrib.auth.models import User
from django.template.loader import get_template, TemplateDoesNotExist
from django.views.decorators.http import require_POST
from django.http import JsonResponse
import json

@login_required
def dashboard(request):
    try:
        user_role = request.user.profile.role
    except UserProfile.DoesNotExist:
        user_role = 'team_member'
    
    projects = Project.objects.all()
    tasks = Task.objects.all()
    
    if user_role == 'admin':
        pass
    elif user_role == 'project_manager':
        projects = projects.filter(manager=request.user)
        tasks = tasks.filter(project__manager=request.user)
    elif user_role == 'team_leader':
        projects = projects.filter(Q(manager=request.user) | Q(tasks__assigned_to=request.user)).distinct()
        tasks = tasks.filter(project__in=projects)
    elif user_role == 'team_member':
        tasks = tasks.filter(assigned_to=request.user)
        projects = projects.filter(tasks__assigned_to=request.user).distinct()
    elif user_role == 'client':
        projects = projects.filter(client__email=request.user.email)
        tasks = tasks.filter(project__client__email=request.user.email)

    total_projects = projects.count()
    completed_projects = projects.filter(status='completed').count()
    ongoing_projects = projects.filter(status='ongoing').count()
    pending_projects = projects.filter(status='planning').count()
    
    total_tasks = tasks.count()
    done_tasks = tasks.filter(status='done').count()
    pending_tasks = total_tasks - done_tasks
    task_completion_rate = int((done_tasks / total_tasks) * 100) if total_tasks > 0 else 0
    
    recent_projects = projects.order_by('-created_at')[:5]
    
    # Calculate color-coded upcoming deadlines widget
    upcoming_deadlines = []
    db_upcoming = tasks.filter(status__in=['todo', 'in_progress']).order_by('deadline')[:5]
    for t in db_upcoming:
        days_left = (t.deadline - date.today()).days
        if days_left <= 2:
            urgency = 'danger'  # urgent (red)
        elif days_left <= 7:
            urgency = 'warning' # medium (yellow)
        else:
            urgency = 'success' # safe (green)
        upcoming_deadlines.append({
            'title': t.title,
            'project_title': t.project.title,
            'deadline': t.deadline.strftime('%b %d'),
            'days_left': days_left,
            'urgency': urgency
        })

    # Timeline and Team logic for Client / PM
    import random
    from django.db.models import Sum
    activity_logs = []
    team_data = []
    health_data = []
    chart_completion = [0, 0, 0, 0]
    
    # Common stats for PM and general roles
    overdue_tasks_count = tasks.exclude(status='done').filter(deadline__lt=date.today()).count()
    
    # Revenue calculations (Dynamic sum from database)
    revenue_this_month = Client.objects.aggregate(Sum('revenue_paid'))['revenue_paid__sum'] or 0.00
    pending_payments = Client.objects.aggregate(Sum('revenue_pending'))['revenue_pending__sum'] or 0.00
    
    # Project Status counts
    planning_projects = projects.filter(status='planning').count()
    development_projects = projects.filter(status='ongoing').count()
    testing_projects = projects.filter(status='on_hold').count()
    deployment_projects = projects.filter(status='completed').count()
    
    # Activities (Combined recent logs and tasks changes)
    activity_logs = list(ActivityLog.objects.all().order_by('-created_at')[:8])
    if not activity_logs:
        # Fallback to realistic timeline logs
        activity_logs = [
            {'activity_type': 'File Uploaded', 'description': 'John Doe uploaded mobile designs to Velo Project', 'created_at': datetime.now()},
            {'activity_type': 'Feedback Received', 'description': 'Carlos Mendez approved landing page feedback', 'created_at': datetime.now()},
            {'activity_type': 'Task Updated', 'description': 'Alex Mercer completed UI alignment review', 'created_at': datetime.now()},
            {'activity_type': 'Payment Received', 'description': 'Payment of $4,500.00 secured for invoice #INV-029', 'created_at': datetime.now()}
        ]
        
    # Team Members (Avatars, role, online status and productivity ratings)
    pm_team_members = [
        {'name': 'Alex Mercer', 'role': 'Team Leader', 'tasks': 3, 'productivity': 92, 'status': 'Online', 'avatar': 'https://api.dicebear.com/7.x/avataaars/svg?seed=Alex'},
        {'name': 'John Doe', 'role': 'Backend Developer', 'tasks': 5, 'productivity': 88, 'status': 'Online', 'avatar': 'https://api.dicebear.com/7.x/avataaars/svg?seed=John'},
        {'name': 'Sarah Connor', 'role': 'UI Designer', 'tasks': 2, 'productivity': 95, 'status': 'Busy', 'avatar': 'https://api.dicebear.com/7.x/avataaars/svg?seed=Sarah'},
        {'name': 'David Okafor', 'role': 'Tester', 'tasks': 4, 'productivity': 84, 'status': 'On Leave', 'avatar': 'https://api.dicebear.com/7.x/avataaars/svg?seed=David'},
    ]
    
    # Deadline Alert calculations
    today = date.today()
    tasks_due_today = tasks.filter(deadline=today).exclude(status='done')
    delayed_projects = projects.filter(deadline__lt=today).exclude(status='completed')
    upcoming_meetings = Meeting.objects.filter(start_time__gte=datetime.now()).order_by('start_time')[:3]
    
    # Team Leader premium execution metrics
    tl_tasks_in_progress = tasks.filter(status='in_progress').count()
    tl_tasks_completed = tasks.filter(status='done').count()
    tl_tasks_delayed = tasks.exclude(status='done').filter(deadline__lt=today).count()
    tl_bugs_reported = tasks.filter(Q(title__icontains='bug') | Q(priority='urgent')).count()
    
    tl_team_members = [
        {'name': 'Ravi Patel', 'role': 'Senior Backend Dev', 'status': 'Online', 'mood': '😊 Happy', 'workload': 'Balanced', 'tasks': 3, 'avatar': 'https://api.dicebear.com/7.x/avataaars/svg?seed=Ravi'},
        {'name': 'John Doe', 'role': 'Frontend Engineer', 'status': 'Busy', 'mood': '😐 Neutral', 'workload': 'Overloaded', 'tasks': 5, 'avatar': 'https://api.dicebear.com/7.x/avataaars/svg?seed=John'},
        {'name': 'Sarah Connor', 'role': 'QA Tester', 'status': 'In Meeting', 'mood': '😊 Happy', 'workload': 'Free', 'tasks': 1, 'avatar': 'https://api.dicebear.com/7.x/avataaars/svg?seed=Sarah'},
        {'name': 'David Okafor', 'role': 'UI Designer', 'status': 'On Leave', 'mood': '😓 Stressed', 'workload': 'Balanced', 'tasks': 2, 'avatar': 'https://api.dicebear.com/7.x/avataaars/svg?seed=David'},
    ]
    
    tl_activities = [
        {'activity_type': 'Task Completed', 'description': 'Ravi Patel completed API integration for payment gateway', 'time': '10 mins ago'},
        {'activity_type': 'Design Uploaded', 'description': 'David Okafor uploaded new dashboard UI prototypes', 'time': '1 hr ago'},
        {'activity_type': 'Bug Reported', 'description': 'Sarah Connor filed a bug: "Authentication token expiration bypass"', 'time': '2 hrs ago'},
        {'activity_type': 'Sprint Started', 'description': 'Sprint 4 development phase officially initialized', 'time': '1 day ago'},
    ]
    
    tl_urgent_issues = [
        {'title': 'Auth token expiration bug', 'category': 'Overdue Bug', 'severity': 'Critical', 'color': 'danger'},
        {'title': 'Payment gateway callback test failing', 'category': 'Blocked Task', 'severity': 'High', 'color': 'warning'},
        {'title': 'Sitemap layout mockup missing', 'category': 'Missing Asset', 'severity': 'Medium', 'color': 'info'},
    ]
    
    if user_role == 'client':
        # Recent Activity Timeline
        activity_logs = ActivityLog.objects.filter(client__email=request.user.email).order_by('-created_at')[:5]
        
        # Working Team Members
        client_projects = Project.objects.filter(client__email=request.user.email)
        team_members = User.objects.filter(assigned_tasks__project__in=client_projects).distinct()[:5]
        mock_roles = ['UI Designer', 'Backend Developer', 'Tester', 'Fullstack Engineer', 'Project Manager']
        for i, m in enumerate(team_members):
            team_data.append({
                'name': m.get_full_name() or m.username,
                'role': m.profile.get_role_display() if m.profile.role != 'team_member' else mock_roles[i % len(mock_roles)],
                'online': random.choice([True, False]) if i % 2 == 0 else True,
                'avatar': f'https://api.dicebear.com/7.x/avataaars/svg?seed={m.username}'
            })
            
        if not team_data:
            team_data = [
                {'name': 'Sarah Connor', 'role': 'Project Manager', 'online': True, 'avatar': 'https://api.dicebear.com/7.x/avataaars/svg?seed=Sarah'},
                {'name': 'John Doe', 'role': 'Backend Developer', 'online': True, 'avatar': 'https://api.dicebear.com/7.x/avataaars/svg?seed=John'},
                {'name': 'Alex Mercer', 'role': 'UI Designer', 'online': False, 'avatar': 'https://api.dicebear.com/7.x/avataaars/svg?seed=Alex'},
            ]
            
        # Project Health
        for p in client_projects:
            health = 'on_track'
            if p.status == 'completed':
                health = 'on_track'
            elif p.priority == 'urgent' and p.deadline < date.today():
                health = 'delayed'
            elif p.priority == 'high' or p.priority == 'urgent':
                health = 'at_risk'
            health_data.append({
                'project_title': p.title,
                'health': health,
                'health_display': 'On Track' if health == 'on_track' else ('At Risk' if health == 'at_risk' else 'Delayed'),
                'health_color': 'success' if health == 'on_track' else ('warning' if health == 'at_risk' else 'danger'),
            })
            
        # Charts Completion
        todo_c = tasks.filter(status='todo').count()
        ip_c = tasks.filter(status='in_progress').count()
        rev_c = tasks.filter(status='review').count()
        done_c = tasks.filter(status='done').count()
        chart_completion = [todo_c, ip_c, rev_c, done_c]

    # Task Completion counts for PM
    todo_count = tasks.filter(status='todo').count()
    inprogress_count = tasks.filter(status='in_progress').count()
    review_count = tasks.filter(status='review').count()
    done_count = tasks.filter(status='done').count()
    pm_chart_completion = [todo_count, inprogress_count, review_count, done_count]

    # Add projects assigned to team leader by project manager
    assigned_projects = []
    tl_clients = Client.objects.none()
    if user_role == 'team_leader':
        # Get projects assigned to the current team leader
        assignments = ProjectAssignment.objects.filter(
            team_leader=request.user
        ).select_related('project', 'assigned_by').order_by('-assigned_at')
        assigned_projects = list(assignments)
        
        # Get unique clients whose projects are assigned to this team leader
        if assignments.exists():
            assigned_project_ids = list(assignments.values_list('project_id', flat=True))
            tl_clients = Client.objects.filter(
                projects__id__in=assigned_project_ids
            ).annotate(
                project_count=Count('projects', filter=Q(projects__id__in=assigned_project_ids))
            ).distinct().order_by('-project_count')
        else:
            tl_clients = Client.objects.none()
    
    # Add client data for project managers
    all_clients = []
    if user_role == 'project_manager':
        all_clients = Client.objects.annotate(project_count=Count('projects')).order_by('-project_count')
    
    context = {
        'user_role': user_role,
        'total_projects': total_projects,
        'completed_projects': completed_projects,
        'ongoing_projects': ongoing_projects,
        'pending_projects': pending_projects,
        'total_tasks': total_tasks,
        'done_tasks': done_tasks,
        'pending_tasks': pending_tasks,
        'task_completion_rate': task_completion_rate,
        'recent_projects': recent_projects,
        'upcoming_deadlines': upcoming_deadlines,
        'notifications': Notification.objects.filter(user=request.user).order_by('-created_at')[:5],
        
        # Premium Dashboard Calculations
        'overdue_tasks_count': overdue_tasks_count,
        'revenue_this_month': float(revenue_this_month),
        'pending_payments': float(pending_payments),
        'planning_projects': planning_projects,
        'development_projects': development_projects,
        'testing_projects': testing_projects,
        'deployment_projects': deployment_projects,
        'pm_team_members': pm_team_members,
        'tasks_due_today': tasks_due_today,
        'delayed_projects_alerts': delayed_projects,
        'upcoming_meetings': upcoming_meetings,
        'pm_chart_completion': pm_chart_completion,
        
        # Team Leader Premium KPIs
        'tl_tasks_in_progress': tl_tasks_in_progress,
        'tl_tasks_completed': tl_tasks_completed,
        'tl_tasks_delayed': tl_tasks_delayed,
        'tl_bugs_reported': tl_bugs_reported,
        'tl_team_members': tl_team_members,
        'tl_activities': tl_activities,
        'tl_urgent_issues': tl_urgent_issues,
        
        # Client Portal Premium Additions
        'activity_logs': activity_logs,
        'team_members_working': team_data,
        'project_health': health_data,
        'chart_completion': chart_completion,
        'chart_progress': [25, 45, 60, 85, 100] if done_tasks > 0 else [0, 0, 0, 0, 0],
        'chart_team_productivity': [8, 12, 10, 15, 6] if done_tasks > 0 else [0, 0, 0, 0, 0],
        'assigned_projects': assigned_projects,
        'all_clients': all_clients,
        'tl_clients': tl_clients,
    }
    
    template_name = f'projects/dashboards/{user_role}.html'
    try:
        get_template(template_name)
    except TemplateDoesNotExist:
        template_name = 'projects/dashboard.html'
    
    return render(request, template_name, context)

# Client Views
from django.http import JsonResponse

@login_required
def client_list(request):
    try:
        user_role = request.user.profile.role
    except UserProfile.DoesNotExist:
        user_role = 'team_member'
    
    if user_role == 'team_leader':
        # For team leaders, show only clients whose projects are assigned to them
        assigned_projects = ProjectAssignment.objects.filter(
            team_leader=request.user
        ).values_list('project_id', flat=True)
        clients = Client.objects.filter(
            projects__id__in=assigned_projects
        ).annotate(
            project_count=Count('projects', filter=Q(projects__id__in=assigned_projects)),
            active_project_count=Count('projects', filter=Q(projects__status__in=['planning', 'ongoing', 'on_hold'], projects__id__in=assigned_projects))
        ).distinct()
    else:
        # For all other roles, show all clients
        clients = Client.objects.annotate(
            project_count=Count('projects'),
            active_project_count=Count('projects', filter=Q(projects__status__in=['planning', 'ongoing', 'on_hold']))
        )
    
    return render(request, 'projects/client_list.html', {'clients': clients})

@login_required
def client_detail_json(request, pk):
    client = get_object_or_404(Client, pk=pk)
    
    # Projects
    projects = []
    for p in client.projects.all():
        projects.append({
            'id': p.id,
            'title': p.title,
            'status': p.get_status_display(),
            'status_code': p.status,
            'deadline': p.deadline.strftime('%b %d, %Y') if p.deadline else 'N/A',
            'progress': p.get_progress()
        })
        
    # Files
    files = []
    for p in client.projects.all():
        for f in p.files.all():
            files.append({
                'name': f.name,
                'url': f.file.url if f.file else '',
                'project_title': p.title,
                'uploaded_at': f.uploaded_at.strftime('%b %d, %Y %I:%M %p') if f.uploaded_at else 'N/A'
            })
            
    # Messages / Communication History
    client_users = User.objects.filter(email=client.email)
    messages = []
    
    project_ids = client.projects.values_list('id', flat=True)
    q_filter = Q(project_id__in=project_ids)
    if client_users.exists():
        q_filter |= Q(sender__in=client_users) | Q(receiver__in=client_users)
        
    db_messages = Message.objects.filter(q_filter).order_by('-created_at')[:15]
    for m in db_messages:
        messages.append({
            'sender': m.sender.get_full_name() or m.sender.username,
            'receiver': (m.receiver.get_full_name() or m.receiver.username) if m.receiver else 'All',
            'project_title': m.project.title if m.project else 'General',
            'content': m.content,
            'created_at': m.created_at.strftime('%b %d, %Y %I:%M %p') if m.created_at else 'N/A'
        })

    # Invoices Tab Data
    invoices = []
    for inv in client.invoices.all():
        invoices.append({
            'invoice_number': inv.invoice_number,
            'amount': float(inv.amount),
            'status': inv.get_status_display(),
            'status_code': inv.status,
            'due_date': inv.due_date.strftime('%b %d, %Y')
        })

    # Meeting Notes Tab Data
    meeting_notes = []
    for note in client.meeting_notes.all().order_by('-created_at'):
        meeting_notes.append({
            'title': note.title,
            'summary': note.summary,
            'discussion_points': note.discussion_points,
            'next_actions': note.next_actions,
            'created_at': note.created_at.strftime('%b %d, %Y')
        })

    # Activity Logs Tab Data
    activity_logs = []
    for log in client.activity_logs.all().order_by('-created_at'):
        activity_logs.append({
            'activity_type': log.activity_type,
            'description': log.description,
            'created_at': log.created_at.strftime('%b %d, %Y %I:%M %p')
        })

    # Permissions Tab Data
    perms = {
        'can_upload': client.permissions.can_upload if hasattr(client, 'permissions') else True,
        'can_comment': client.permissions.can_comment if hasattr(client, 'permissions') else True,
        'can_edit': client.permissions.can_edit if hasattr(client, 'permissions') else False,
    }
        
    data = {
        'id': client.id,
        'name': client.name,
        'email': client.email,
        'phone': client.phone or 'N/A',
        'address': client.address or 'No company info',
        'client_id': client.client_id or f'CLT-2026-{100 + client.id}',
        'revenue_paid': float(client.revenue_paid),
        'revenue_pending': float(client.revenue_pending),
        'priority': client.get_priority_display(),
        'priority_code': client.priority,
        'satisfaction': float(client.satisfaction),
        'notes': client.notes or '',
        'projects': projects,
        'files': files,
        'messages': messages,
        'invoices': invoices,
        'meeting_notes': meeting_notes,
        'activity_logs': activity_logs,
        'permissions': perms,
    }
    return JsonResponse(data)

@login_required
def client_projects(request):
    projects = Project.objects.filter(client__email=request.user.email)
    return render(request, 'projects/client_projects.html', {'projects': projects})

@login_required
def client_reports(request):
    reports = Report.objects.filter(project__client__email=request.user.email).order_by('-created_at')
    return render(request, 'projects/client_reports.html', {'reports': reports})

@login_required
def client_files(request):
    files = ProjectFile.objects.filter(project__client__email=request.user.email).order_by('-uploaded_at')
    projects = Project.objects.filter(client__email=request.user.email)
    return render(request, 'projects/client_files.html', {'files': files, 'projects': projects})

@login_required
def client_feedback(request):
    if request.method == 'POST':
        form = FeedbackForm(request.POST)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.client = request.user
            feedback.save()
            return redirect('client_feedback')
    else:
        form = FeedbackForm()
        form.fields['project'].queryset = Project.objects.filter(client__email=request.user.email)
    feedbacks = Feedback.objects.filter(client=request.user).order_by('-created_at')
    return render(request, 'projects/client_feedback.html', {'form': form, 'feedbacks': feedbacks})

# Project Views
@login_required
def project_list(request):
    projects = Project.objects.all().order_by('-created_at')
    clients_all = Client.objects.all()
    
    # Calculate overview stats
    completed_count = projects.filter(status='completed').count()
    active_count = projects.filter(status='ongoing').count()
    
    today = date.today()
    delayed_count = projects.filter(deadline__lt=today).exclude(status='completed').count()
    
    return render(request, 'projects/project_list.html', {
        'projects': projects, 
        'clients_all': clients_all,
        'completed_count': completed_count,
        'active_count': active_count,
        'delayed_count': delayed_count,
        'today': today
    })

@login_required
def project_detail_json(request, pk):
    project = get_object_or_404(Project, pk=pk)
    
    # Tasks
    tasks = []
    for t in project.tasks.all():
        tasks.append({
            'title': t.title,
            'status': t.get_status_display(),
            'status_code': t.status,
            'priority': t.get_priority_display(),
            'priority_code': t.priority,
            'assignee': t.assigned_to.get_full_name() or t.assigned_to.username if t.assigned_to else 'Unassigned',
            'deadline': t.deadline.strftime('%b %d, %Y') if t.deadline else 'N/A'
        })
        
    # Files
    files = []
    for f in project.files.all():
        files.append({
            'name': f.name,
            'url': f.file.url if f.file else '',
            'uploaded_at': f.uploaded_at.strftime('%b %d, %Y') if f.uploaded_at else 'N/A'
        })
        
    data = {
        'id': project.id,
        'title': project.title,
        'description': project.description or 'No description provided.',
        'client_name': project.client.name,
        'client_email': project.client.email,
        'manager': project.manager.get_full_name() or project.manager.username if project.manager else 'Unassigned',
        'status': project.get_status_display(),
        'status_code': project.status,
        'priority': project.get_priority_display(),
        'priority_code': project.priority,
        'deadline': project.deadline.strftime('%b %d, %Y') if project.deadline else 'N/A',
        'progress': project.get_progress(),
        'tasks': tasks,
        'files': files
    }
    return JsonResponse(data)

@login_required
def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)
    tasks = project.tasks.all()
    return render(request, 'projects/project_detail.html', {'project': project, 'tasks': tasks})

@login_required
def create_project(request):
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.manager = request.user
            project.save()
            return redirect('dashboard')
    else:
        form = ProjectForm()
    return render(request, 'projects/create_project.html', {'form': form})

@login_required
def client_form(request):
    if request.method == 'POST':
        form = ClientProjectForm(request.POST, request.FILES)
        if form.is_valid():
            # Create or get the client
            client, created = Client.objects.get_or_create(
                email=form.cleaned_data['email'],
                defaults={
                    'name': form.cleaned_data['client_name'],
                    'phone': form.cleaned_data['phone'],
                }
            )
            
            # Create the project
            project = Project(
                title=form.cleaned_data['project_title'],
                description='',
                client=client,
                manager=request.user,
                deadline=form.cleaned_data['deadline']
            )
            project.save()
            
            # Handle file upload if provided
            if form.cleaned_data.get('file_upload'):
                project_file = ProjectFile(
                    project=project,
                    name=form.cleaned_data['file_upload'].name,
                    file=form.cleaned_data['file_upload']
                )
                project_file.save()
            
            return redirect('dashboard')
    else:
        form = ClientProjectForm()
    return render(request, 'projects/client_form.html', {'form': form})

# Task Views
@login_required
def task_list(request):
    tasks = Task.objects.all()
    projects_all = Project.objects.all()
    return render(request, 'projects/task_list.html', {'tasks': tasks, 'projects_all': projects_all})

@login_required
def task_board(request):
    try:
        user_role = request.user.profile.role
    except UserProfile.DoesNotExist:
        user_role = 'team_member'

    # Clients and Admins cannot view or access the Tasks page
    if user_role in ['client', 'admin']:
        return redirect('dashboard')

    if user_role == 'project_manager':
        projects = Project.objects.filter(manager=request.user)
        tasks = Task.objects.filter(project__manager=request.user)
    elif user_role == 'team_leader':
        assigned_project_ids = ProjectAssignment.objects.filter(
            team_leader=request.user,
            status='accepted'
        ).values_list('project_id', flat=True)
        projects = Project.objects.filter(id__in=assigned_project_ids)
        tasks = Task.objects.filter(project__in=projects)
    elif user_role == 'team_member':
        tasks = Task.objects.filter(assigned_to=request.user)
        projects = Project.objects.filter(tasks__assigned_to=request.user).distinct()
    else:
        tasks = Task.objects.all()
        projects = Project.objects.all()

    allowed_projects = Project.objects.all()
    allowed_members = User.objects.all()

    if user_role == 'team_leader':
        assigned_project_ids = ProjectAssignment.objects.filter(
            team_leader=request.user,
            status='accepted'
        ).values_list('project_id', flat=True)
        allowed_projects = Project.objects.filter(id__in=assigned_project_ids)
        
        # Show all team members, or team members from teams if teams exist
        allowed_teams = Team.objects.filter(leaders=request.user)
        if allowed_teams.exists():
            allowed_members = User.objects.filter(teams_joined__in=allowed_teams, profile__role='team_member').distinct()
        else:
            # If no teams are configured, show all team members
            allowed_members = User.objects.filter(profile__role='team_member')

    if request.method == 'POST':
        # Only team leaders can add tasks
        if user_role != 'team_leader':
            return redirect('task_board')
            
        form = TaskForm(request.POST)
        if user_role == 'team_leader':
            form.fields['project'].queryset = allowed_projects
            form.fields['assigned_to'].queryset = allowed_members

        if form.is_valid():
            form.save()
            return redirect('task_board')
    else:
        form = TaskForm()
        if user_role == 'team_leader':
            form.fields['project'].queryset = allowed_projects
            form.fields['assigned_to'].queryset = allowed_members
        else:
            form.fields['project'].queryset = allowed_projects
            form.fields['assigned_to'].queryset = allowed_members

    today = date.today()
    return render(request, 'projects/task_board.html', {'tasks': tasks, 'projects': projects, 'form': form, 'today': today})

# Report Views
@login_required
def team_reports(request):
    user_role = request.user.profile.role
    if user_role == 'project_manager':
        reports = Report.objects.filter(project__manager=request.user).order_by('-created_at')
    else:
        reports = Report.objects.all().order_by('-created_at')
    return render(request, 'projects/team_reports.html', {'reports': reports})

@login_required
def approve_report(request, pk):
    report = get_object_or_404(Report, pk=pk)
    if report.project.manager == request.user or request.user.profile.role == 'admin':
        report.status = 'approved'
        report.save()
        Notification.objects.create(user=report.submitted_by, message=f"Your report '{report.title}' has been approved.")
    return redirect('team_reports')

# Calendar and Messages
@login_required
def calendar_view(request):
    try:
        user_role = request.user.profile.role
    except UserProfile.DoesNotExist:
        user_role = 'team_member'

    # Clients cannot view or access the Calendar page
    if user_role == 'client':
        return redirect('dashboard')

    if user_role == 'project_manager':
        projects = Project.objects.filter(manager=request.user)
        tasks = Task.objects.filter(project__manager=request.user)
        meetings = Meeting.objects.filter(Q(project__manager=request.user) | Q(organizer=request.user))
        # Project managers see their own projects and ALL client projects
        pm_projects = Project.objects.filter(manager=request.user)
        client_projects = Project.objects.filter(client__isnull=False)
        projects = (pm_projects | client_projects).distinct()
        tasks = Task.objects.filter(project__in=projects)
    elif user_role == 'team_leader':
        # Team leaders see only their assigned projects
        assignments = ProjectAssignment.objects.filter(
            team_leader=request.user,
            status__in=['pending', 'accepted']
        ).values_list('project_id', flat=True)
        projects = Project.objects.filter(id__in=assignments)
        tasks = Task.objects.filter(project__in=projects)
    else:
        projects = Project.objects.all()
        tasks = Task.objects.all()
    return render(request, 'projects/calendar.html', {'projects': projects, 'tasks': tasks})

@login_required
def messages_view(request):
    from django.db.models import Max
    user_role = request.user.profile.role
    
    if user_role == 'project_manager':
        projects = Project.objects.filter(manager=request.user)
    elif user_role == 'client':
        projects = Project.objects.filter(client__email=request.user.email)
    else:
        projects = Project.objects.all()
        
    all_users = User.objects.exclude(id=request.user.id).select_related('profile')
    
    managers = []
    team_members = []
    clients = []
    
    for u in all_users:
        role = u.profile.role if hasattr(u, 'profile') else 'team_member'
        unread_count = Message.objects.filter(sender=u, receiver=request.user, is_read=False).count()
        latest_msg = Message.objects.filter(
            Q(sender=u, receiver=request.user) | Q(sender=request.user, receiver=u)
        ).aggregate(latest=Max('created_at'))['latest']
        
        user_info = {
            'id': u.id,
            'username': u.username,
            'name': u.get_full_name() or u.username,
            'unread': unread_count,
            'latest_time': latest_msg,
            'online': (u.id % 2 == 0 or u.id % 3 == 0)
        }
        
        if role == 'project_manager':
            managers.append(user_info)
        elif role in ['team_leader', 'team_member', 'admin']:
            team_members.append(user_info)
        elif role == 'client':
            clients.append(user_info)
            
    # Sort timezone safely to avoid TypeError when comparing offset-naive and offset-aware datetimes
    sort_key = lambda x: (1, x['latest_time']) if x['latest_time'] is not None else (0, datetime.min)
    managers.sort(key=sort_key, reverse=True)
    team_members.sort(key=sort_key, reverse=True)
    clients.sort(key=sort_key, reverse=True)

    return render(request, 'projects/messages.html', {
        'projects': projects,
        'managers': managers,
        'team': team_members,
        'clients': clients
    })

@login_required
def chat_history_json(request, target_type, target_id):
    if target_type == 'project':
        messages = Message.objects.filter(project_id=target_id).order_by('created_at')
    elif target_type == 'user':
        Message.objects.filter(sender_id=target_id, receiver=request.user, is_read=False).update(is_read=True)
        messages = Message.objects.filter(
            Q(sender=request.user, receiver_id=target_id) |
            Q(sender_id=target_id, receiver=request.user)
        ).order_by('created_at')
    else:
        return JsonResponse({'status': 'error', 'message': 'Invalid type'}, status=400)
        
    data = []
    for m in messages:
        is_image = False
        is_pdf = False
        file_url = m.file.url if m.file else ''
        file_name = m.file.name.split('/')[-1] if m.file else ''
        
        if file_url:
            ext = file_url.split('.')[-1].lower()
            if ext in ['png', 'jpg', 'jpeg', 'svg', 'gif', 'webp']:
                is_image = True
            elif ext == 'pdf':
                is_pdf = True
                
        data.append({
            'id': m.id,
            'sender_id': m.sender.id,
            'sender_name': m.sender.get_full_name() or m.sender.username,
            'content': m.content or '',
            'created_at': m.created_at.strftime('%I:%M %p'),
            'file_url': file_url,
            'file_name': file_name,
            'is_image': is_image,
            'is_pdf': is_pdf,
            'is_me': m.sender == request.user
        })
        
    return JsonResponse({'status': 'success', 'messages': data})

@login_required
@require_POST
def send_chat_message(request):
    try:
        content = request.POST.get('content', '').strip()
        project_id = request.POST.get('project_id')
        receiver_id = request.POST.get('receiver_id')
        uploaded_file = request.FILES.get('file')
        
        if not content and not uploaded_file:
            return JsonResponse({'status': 'error', 'message': 'Empty message'}, status=400)
            
        project = None
        if project_id:
            project = get_object_or_404(Project, id=project_id)
            
        receiver = None
        if receiver_id:
            receiver = get_object_or_404(User, id=receiver_id)
            
        message = Message.objects.create(
            sender=request.user,
            receiver=receiver,
            project=project,
            content=content,
            file=uploaded_file
        )
        
        is_image = False
        is_pdf = False
        file_url = message.file.url if message.file else ''
        file_name = message.file.name.split('/')[-1] if message.file else ''
        
        if file_url:
            ext = file_url.split('.')[-1].lower()
            if ext in ['png', 'jpg', 'jpeg', 'svg', 'gif', 'webp']:
                is_image = True
            elif ext == 'pdf':
                is_pdf = True
                
        return JsonResponse({
            'status': 'success',
            'message': {
                'id': message.id,
                'sender_id': message.sender.id,
                'sender_name': message.sender.get_full_name() or message.sender.username,
                'content': message.content or '',
                'created_at': message.created_at.strftime('%I:%M %p'),
                'file_url': file_url,
                'file_name': file_name,
                'is_image': is_image,
                'is_pdf': is_pdf,
                'is_me': True
            }
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

@login_required
def messages_view(request):
    user_role = request.user.profile.role
    if user_role == 'project_manager':
        managed_projects = Project.objects.filter(manager=request.user)
        messages = Message.objects.filter(Q(project__in=managed_projects) | Q(sender=request.user) | Q(receiver=request.user)).order_by('-created_at')
        projects = Project.objects.filter(manager=request.user)
    elif user_role == 'team_leader':
        # Team leaders can only have conversations with project managers and clients
        project_managers = User.objects.filter(profile__role='project_manager')
        clients = User.objects.filter(profile__role='client')
        allowed_users = project_managers | clients
        messages = Message.objects.filter(
            Q(sender=request.user, receiver__in=allowed_users) |
            Q(receiver=request.user, sender__in=allowed_users)
        ).order_by('-created_at')
        projects = Project.objects.none()
    else:
        messages = Message.objects.filter(Q(sender=request.user) | Q(receiver=request.user)).order_by('-created_at')
        projects = Project.objects.all()

    if request.method == 'POST':
        content = request.POST.get('content')
        project_id = request.POST.get('project')
        receiver_id = request.POST.get('receiver')
        if content:
            receiver = None
            if receiver_id:
                receiver = User.objects.get(pk=receiver_id)
            project = Project.objects.get(pk=project_id) if project_id else None
            Message.objects.create(sender=request.user, receiver=receiver, content=content, project=project)
            return redirect('messages')
    
    return render(request, 'projects/messages.html', {'messages': messages, 'projects': projects})

@login_required
def teams(request):
    try:
        user_role = request.user.profile.role
    except UserProfile.DoesNotExist:
        user_role = 'team_member'

    if user_role != 'project_manager':
        return redirect('dashboard')

    # Get all team leaders (users with team_leader role)
    team_leaders = User.objects.filter(profile__role='team_leader')
    
    # Get ALL projects (both client-uploaded and PM-created)
    # This allows PMs to assign any project to team leaders
    # Exclude projects that have already been assigned (pending or accepted)
    assigned_project_ids = ProjectAssignment.objects.filter(
        status__in=['pending', 'accepted']
    ).values_list('project_id', flat=True)
    projects = Project.objects.exclude(id__in=assigned_project_ids).order_by('-deadline')
    
    # Get assignments for each team leader
    team_leader_data = []
    for leader in team_leaders:
        assignments = ProjectAssignment.objects.filter(team_leader=leader)
        pending = assignments.filter(status='pending').count()
        accepted = assignments.filter(status='accepted').count()
        rejected = assignments.filter(status='rejected').count()
        
        team_leader_data.append({
            'user': leader,
            'pending_count': pending,
            'accepted_count': accepted,
            'rejected_count': rejected,
            'assignments': assignments,
            'assignment_count': assignments.count(),
        })
    
    teams = Team.objects.filter(project_manager=request.user).prefetch_related('leaders', 'members')

    context = {
        'teams': teams,
        'team_leader_data': team_leader_data,
        'projects': projects,
    }
    return render(request, 'projects/teams.html', context)

# Auth Views
def signup_view(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('client_form')
    else:
        form = SignUpForm()
    return render(request, 'registration/signup.html', {'form': form, 'hide_sidebar': True})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('dashboard')
    else:
        form = AuthenticationForm()
    return render(request, 'registration/login.html', {'form': form, 'hide_sidebar': True})

def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def edit_feedback(request, pk):
    feedback = get_object_or_404(Feedback, pk=pk, client=request.user)
    if request.method == 'POST':
        form = FeedbackForm(request.POST, instance=feedback)
        if form.is_valid():
            form.save()
            return redirect('client_feedback')
    else:
        form = FeedbackForm(instance=feedback)
        form.fields['project'].queryset = Project.objects.filter(client__email=request.user.email)
    return render(request, 'projects/edit_feedback.html', {'form': form})

@login_required
def task_detail_json(request, pk):
    from .models import TaskComment, TaskFile
    task = get_object_or_404(Task, pk=pk)
    
    # Comments
    comments = []
    for c in task.comments.all().order_by('-created_at'):
        comments.append({
            'author': c.author.get_full_name() or c.author.username,
            'content': c.content,
            'created_at': c.created_at.strftime('%b %d, %Y %I:%M %p')
        })
        
    # Files
    files = []
    for f in task.files.all():
        files.append({
            'id': f.id,
            'name': f.name,
            'url': f.file.url if f.file else '',
            'uploaded_at': f.uploaded_at.strftime('%b %d, %Y %I:%M %p')
        })
        
    # Check if overdue
    today = date.today()
    is_overdue = task.status != 'done' and task.deadline < today
    
    data = {
        'id': task.id,
        'title': task.title,
        'description': task.description or 'No description provided.',
        'project_title': task.project.title,
        'project_id': task.project.id,
        'assignee': task.assigned_to.get_full_name() or task.assigned_to.username if task.assigned_to else 'Unassigned',
        'status': task.get_status_display(),
        'status_code': task.status,
        'priority': task.get_priority_display(),
        'priority_code': task.priority,
        'deadline': task.deadline.strftime('%b %d, %Y') if task.deadline else 'N/A',
        'deadline_raw': task.deadline.strftime('%Y-%m-%d') if task.deadline else '',
        'is_overdue': is_overdue,
        'comments': comments,
        'files': files
    }
    return JsonResponse(data)

@login_required
@require_POST
def update_task_status(request, pk):
    task = get_object_or_404(Task, pk=pk)
    try:
        data = json.loads(request.body)
        new_status = data.get('status')
        if new_status in ['todo', 'in_progress', 'review', 'done']:
            task.status = new_status
            task.save()
            return JsonResponse({'status': 'success', 'new_status': task.status})
        return JsonResponse({'status': 'error', 'message': 'Invalid status'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

@login_required
@require_POST
def add_task_comment(request, pk):
    from .models import TaskComment
    task = get_object_or_404(Task, pk=pk)
    try:
        data = json.loads(request.body)
        content = data.get('content')
        if content and content.strip():
            comment = TaskComment.objects.create(
                task=task,
                author=request.user,
                content=content.strip()
            )
            return JsonResponse({
                'status': 'success',
                'comment': {
                    'author': comment.author.get_full_name() or comment.author.username,
                    'content': comment.content,
                    'created_at': comment.created_at.strftime('%b %d, %Y %I:%M %p')
                }
            })
        return JsonResponse({'status': 'error', 'message': 'Empty comment'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

@login_required
@require_POST
def add_task_attachment(request, pk):
    from .models import TaskFile
    task = get_object_or_404(Task, pk=pk)
    try:
        uploaded_file = request.FILES.get('file')
        if uploaded_file:
            task_file = TaskFile.objects.create(
                task=task,
                name=uploaded_file.name,
                file=uploaded_file
            )
            return JsonResponse({
                'status': 'success',
                'file': {
                    'id': task_file.id,
                    'name': task_file.name,
                    'url': task_file.file.url,
                    'uploaded_at': task_file.uploaded_at.strftime('%b %d, %Y %I:%M %p')
                }
            })
        return JsonResponse({'status': 'error', 'message': 'No file provided'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

@login_required
def calendar_events_json(request):
    events = []
    
    # 1. Projects
    projects = Project.objects.all()
    try:
        user_role = request.user.profile.role
    except UserProfile.DoesNotExist:
        user_role = 'team_member'
        
    if user_role == 'project_manager':
        projects = projects.filter(manager=request.user)
    elif user_role == 'team_leader':
        projects = projects.filter(Q(manager=request.user) | Q(tasks__assigned_to=request.user)).distinct()
    elif user_role == 'team_member':
        projects = projects.filter(tasks__assigned_to=request.user).distinct()
    elif user_role == 'client':
        projects = projects.filter(client__email=request.user.email)
        
    for project in projects:
        if project.deadline:
            events.append({
                'id': f"project_{project.id}",
                'title': f"📋 Project: {project.title}",
                'start': project.deadline.isoformat(),
                'allDay': True,
                'backgroundColor': '#4f46e5',
                'extendedProps': {
                    'type': 'project',
                    'client': project.client.name,
                    'manager': project.manager.get_full_name() or project.manager.username if project.manager else 'Unassigned',
                    'status': project.get_status_display()
                }
            })
            
    # 2. Tasks
    tasks = Task.objects.all()
    if user_role == 'project_manager':
        tasks = tasks.filter(project__manager=request.user)
    elif user_role == 'team_leader':
        tasks = tasks.filter(project__in=projects)
    elif user_role == 'team_member':
        tasks = tasks.filter(assigned_to=request.user)
    elif user_role == 'client':
        tasks = tasks.filter(project__client__email=request.user.email)
        
    for task in tasks:
        if task.deadline:
            color = '#64748b'
            if task.status == 'in_progress':
                color = '#2563eb'
            elif task.status == 'review':
                color = '#ea580c'
            elif task.status == 'done':
                color = '#16a34a'
                
            events.append({
                'id': f"task_{task.id}",
                'title': f"✓ Task: {task.title}",
                'start': task.deadline.isoformat(),
                'allDay': True,
                'backgroundColor': color,
                'extendedProps': {
                    'type': 'task',
                    'project': task.project.title,
                    'assignee': task.assigned_to.get_full_name() or task.assigned_to.username if task.assigned_to else 'Unassigned',
                    'status': task.get_status_display(),
                    'priority': task.get_priority_display()
                }
            })
            
    # 3. Meetings
    meetings = Meeting.objects.all()
    if user_role == 'project_manager':
        meetings = meetings.filter(Q(project__manager=request.user) | Q(organizer=request.user))
    elif user_role == 'team_leader':
        meetings = meetings.filter(Q(project__in=projects) | Q(organizer=request.user))
    elif user_role == 'team_member':
        meetings = meetings.filter(Q(project__in=projects) | Q(organizer=request.user))
    elif user_role == 'client':
        meetings = meetings.filter(project__client__email=request.user.email)
        
    for meeting in meetings:
        events.append({
            'id': f"meeting_{meeting.id}",
            'title': f"🤝 Meeting: {meeting.title}",
            'start': meeting.start_time.isoformat(),
            'end': meeting.end_time.isoformat() if meeting.end_time else None,
            'allDay': False,
            'backgroundColor': '#db2777',
            'extendedProps': {
                'type': 'meeting',
                'project': meeting.project.title if meeting.project else 'General',
                'organizer': meeting.organizer.get_full_name() or meeting.organizer.username,
                'description': meeting.description or ''
            }
        })
        
    return JsonResponse(events, safe=False)

@login_required
@require_POST
def update_calendar_event(request, type, pk):
    try:
        data = json.loads(request.body)
        start_str = data.get('start')
        end_str = data.get('end')
        
        if type == 'project':
            project = get_object_or_404(Project, pk=pk)
            if 'T' in start_str:
                dt = parse_datetime(start_str)
                project.deadline = dt.date()
            else:
                project.deadline = parse_date(start_str) or project.deadline
            project.save()
            return JsonResponse({'status': 'success'})
        elif type == 'task':
            task = get_object_or_404(Task, pk=pk)
            if 'T' in start_str:
                dt = parse_datetime(start_str)
                task.deadline = dt.date()
            else:
                task.deadline = parse_date(start_str) or task.deadline
            task.save()
            return JsonResponse({'status': 'success'})
        elif type == 'meeting':
            meeting = get_object_or_404(Meeting, pk=pk)
            if start_str:
                meeting.start_time = parse_datetime(start_str) or meeting.start_time
            if end_str:
                meeting.end_time = parse_datetime(end_str) or meeting.end_time
            meeting.save()
            return JsonResponse({'status': 'success'})
        else:
            return JsonResponse({'status': 'error', 'message': 'Invalid event type'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

@login_required
@require_POST
def create_meeting_json(request):
    try:
        data = json.loads(request.body)
        title = data.get('title')
        project_id = data.get('project_id')
        start_str = data.get('start')
        end_str = data.get('end')
        description = data.get('description')
        
        if not title or not start_str or not end_str:
            return JsonResponse({'status': 'error', 'message': 'Missing required fields'}, status=400)
            
        project = None
        if project_id:
            project = get_object_or_404(Project, id=project_id)
            
        meeting = Meeting.objects.create(
            title=title,
            project=project,
            organizer=request.user,
            start_time=parse_datetime(start_str),
            end_time=parse_datetime(end_str),
            description=description
        )
        return JsonResponse({'status': 'success', 'id': meeting.id})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

@login_required
def payments_view(request):
    try:
        user_role = request.user.profile.role
    except UserProfile.DoesNotExist:
        user_role = 'team_member'

    # Team leaders and Team members cannot view or access the Payments page
    if user_role in ['team_leader', 'team_member']:
        return redirect('dashboard')
        
    if user_role == 'client':
        invoices = Invoice.objects.filter(client__email=request.user.email).order_by('-created_at')
    else:
        invoices = Invoice.objects.all().order_by('-created_at')
        
    return render(request, 'projects/payments.html', {'invoices': invoices, 'user_role': user_role})

@login_required
def settings_view(request):
    try:
        user_role = request.user.profile.role
    except UserProfile.DoesNotExist:
        user_role = 'team_member'
        
    client = None
    if user_role == 'client':
        client = Client.objects.filter(email=request.user.email).first()
        
    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.email = request.POST.get('email', user.email)
        user.save()
        
        profile = user.profile
        profile.phone = request.POST.get('phone', profile.phone)
        profile.save()
        
        if client and user_role == 'client':
            client.address = request.POST.get('address', client.address)
            client.save()
            
        return redirect('settings')
        
    return render(request, 'projects/settings.html', {'user_role': user_role, 'client': client})
# Project Assignment Views for Team Leaders
@login_required
def assign_project_to_leader(request, project_id):
    """Project Manager assigns a project to a team leader"""
    project = get_object_or_404(Project, pk=project_id)
    
    # Check if user is the project manager
    if request.user != project.manager:
        return redirect('project_detail', pk=project_id)
    
    if request.method == 'POST':
        form = ProjectAssignmentForm(request.POST)
        if form.is_valid():
            team_leader = form.cleaned_data['team_leader']
            # Create or update assignment
            assignment, created = ProjectAssignment.objects.get_or_create(
                project=project,
                team_leader=team_leader,
                defaults={'assigned_by': request.user, 'status': 'pending'}
            )
            if not created:
                assignment.status = 'pending'
                assignment.assigned_by = request.user
                assignment.save()
            return redirect('project_detail', pk=project_id)
    else:
        form = ProjectAssignmentForm()
    
    return render(request, 'projects/assign_project.html', {'form': form, 'project': project})

@login_required
def team_leader_projects(request):
    """Team Leader sees all projects assigned to him"""
    # Get all project assignments for this team leader
    assignments = ProjectAssignment.objects.filter(team_leader=request.user)
    
    pending_assignments = assignments.filter(status='pending')
    accepted_assignments = assignments.filter(status='accepted')
    rejected_assignments = assignments.filter(status='rejected')
    
    context = {
        'pending_assignments': pending_assignments,
        'accepted_assignments': accepted_assignments,
        'rejected_assignments': rejected_assignments,
    }
    return render(request, 'projects/team_leader_projects.html', context)

@login_required
def accept_project_assignment(request, assignment_id):
    """Team Leader accepts a project assignment"""
    assignment = get_object_or_404(ProjectAssignment, pk=assignment_id, team_leader=request.user)
    assignment.status = 'accepted'
    assignment.save()
    return redirect('team_leader_projects')

@login_required
def reject_project_assignment(request, assignment_id):
    """Team Leader rejects a project assignment"""
    assignment = get_object_or_404(ProjectAssignment, pk=assignment_id, team_leader=request.user)
    assignment.status = 'rejected'
    assignment.save()
    return redirect('team_leader_projects')

@login_required
def quick_assign_project(request, project_id, team_leader_id):
    """Project Manager quickly assigns a project to a team leader from Teams page"""
    # Check that user is a project manager
    if request.user.profile.role != 'project_manager':
        return redirect('teams')
    
    project = get_object_or_404(Project, pk=project_id)
    team_leader = get_object_or_404(User, pk=team_leader_id, profile__role='team_leader')
    
    # Create or update assignment
    assignment, created = ProjectAssignment.objects.get_or_create(
        project=project,
        team_leader=team_leader,
        defaults={'assigned_by': request.user, 'status': 'pending'}
    )
    
    if not created and assignment.status != 'pending':
        assignment.status = 'pending'
        assignment.assigned_by = request.user
        assignment.save()
    
    return redirect('teams')
