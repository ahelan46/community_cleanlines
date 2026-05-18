from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from django.db.models import Count, Q
from .models import Client, Project, Task, Notification, Report, Message, UserProfile, ProjectFile, Feedback
from .forms import SignUpForm, ProjectForm, TaskForm, ReportForm, FeedbackForm, ClientProjectForm
from datetime import date
from django.contrib.auth.models import User
from django.template.loader import get_template, TemplateDoesNotExist

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
    upcoming_deadlines = tasks.filter(status__in=['todo', 'in_progress'], deadline__gte=date.today()).order_by('deadline')[:5]
    
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
    }
    
    template_name = f'projects/dashboards/{user_role}.html'
    try:
        get_template(template_name)
    except TemplateDoesNotExist:
        template_name = 'projects/dashboard.html'
    
    return render(request, template_name, context)

# Client Views
@login_required
def client_list(request):
    clients = Client.objects.annotate(project_count=Count('projects'))
    return render(request, 'projects/client_list.html', {'clients': clients})

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
    return render(request, 'projects/client_files.html', {'files': files})

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
    projects = Project.objects.all()
    clients_all = Client.objects.all()
    return render(request, 'projects/project_list.html', {'projects': projects, 'clients_all': clients_all})

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
    user_role = request.user.profile.role
    if user_role == 'project_manager':
        projects = Project.objects.filter(manager=request.user)
        tasks = Task.objects.filter(project__manager=request.user)
    else:
        tasks = Task.objects.all()
        projects = Project.objects.all()

    if request.method == 'POST':
        form = TaskForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('task_board')
    else:
        form = TaskForm()
        if user_role == 'project_manager':
            form.fields['project'].queryset = Project.objects.filter(manager=request.user)

    return render(request, 'projects/task_board.html', {'tasks': tasks, 'projects': projects, 'form': form})

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
    from datetime import datetime, timedelta
    import calendar as cal
    import json
    
    user_role = request.user.profile.role
    if user_role == 'project_manager':
        projects = Project.objects.filter(manager=request.user)
        tasks = Task.objects.filter(project__manager=request.user)
    else:
        projects = Project.objects.all()
        tasks = Task.objects.all()
    
    # Get current month and year from GET parameters or use today
    current_date = datetime.now()
    try:
        month = int(request.GET.get('month', current_date.month))
        year = int(request.GET.get('year', current_date.year))
        # Validate month
        if month < 1:
            month = 12
            year -= 1
        elif month > 12:
            month = 1
            year += 1
    except (ValueError, TypeError):
        month = current_date.month
        year = current_date.year
    
    # Get calendar data
    calendar_obj = cal.monthcalendar(year, month)
    month_name = cal.month_name[month]
    
    # Get all deadlines for this month
    start_date = datetime(year, month, 1).date()
    if month == 12:
        end_date = datetime(year + 1, 1, 1).date() - timedelta(days=1)
    else:
        end_date = datetime(year, month + 1, 1).date() - timedelta(days=1)
    
    # Create a dictionary of deadlines by date (formatted as YYYY-MM-DD)
    deadline_dict = {}
    for project in projects:
        deadline_key = project.deadline.strftime('%Y-%m-%d')
        if deadline_key not in deadline_dict:
            deadline_dict[deadline_key] = []
        deadline_dict[deadline_key].append({
            'type': 'project',
            'title': project.title,
            'deadline': project.deadline.isoformat()
        })
    
    for task in tasks:
        deadline_key = task.deadline.strftime('%Y-%m-%d')
        if deadline_key not in deadline_dict:
            deadline_dict[deadline_key] = []
        deadline_dict[deadline_key].append({
            'type': 'task',
            'title': task.title,
            'project': task.project.title,
            'deadline': task.deadline.isoformat()
        })
    
    # Previous and next month links
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1
    
    context = {
        'projects': projects,
        'tasks': tasks,
        'calendar': calendar_obj,
        'month': month,
        'year': year,
        'month_name': month_name,
        'deadline_dict': json.dumps(deadline_dict),
        'prev_month': prev_month,
        'prev_year': prev_year,
        'next_month': next_month,
        'next_year': next_year,
    }
    return render(request, 'projects/calendar.html', context)

@login_required
def messages_view(request):
    user_role = request.user.profile.role
    if user_role == 'project_manager':
        managed_projects = Project.objects.filter(manager=request.user)
        messages = Message.objects.filter(Q(project__in=managed_projects) | Q(sender=request.user) | Q(receiver=request.user)).order_by('-created_at')
    else:
        messages = Message.objects.filter(Q(sender=request.user) | Q(receiver=request.user)).order_by('-created_at')

    if request.method == 'POST':
        content = request.POST.get('content')
        project_id = request.POST.get('project')
        if content:
            project = Project.objects.get(pk=project_id) if project_id else None
            Message.objects.create(sender=request.user, content=content, project=project)
            return redirect('messages')
    projects = Project.objects.filter(manager=request.user) if user_role == 'project_manager' else Project.objects.all()
    return render(request, 'projects/messages.html', {'messages': messages, 'projects': projects})

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