from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from django.db.models import Count, Q
from .models import Client, Project, Task, Notification, Report, Message, UserProfile, ProjectFile, Feedback
from .forms import SignUpForm, ProjectForm, TaskForm, ReportForm, FeedbackForm, ClientProjectForm
from datetime import date, datetime
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
        'notifications': Notification.objects.filter(user=request.user).order_by('-created_at')[:5],
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
        
    data = {
        'id': client.id,
        'name': client.name,
        'email': client.email,
        'phone': client.phone or 'N/A',
        'address': client.address or 'No company info',
        'projects': projects,
        'files': files,
        'messages': messages,
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
                deadline='2099-12-31'  # Default deadline, can be updated later
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
    from .models import Meeting
    user_role = request.user.profile.role
    if user_role == 'project_manager':
        projects = Project.objects.filter(manager=request.user)
        tasks = Task.objects.filter(project__manager=request.user)
        meetings = Meeting.objects.filter(Q(project__manager=request.user) | Q(organizer=request.user))
    else:
        projects = Project.objects.all()
        tasks = Task.objects.all()
        meetings = Meeting.objects.all()
    return render(request, 'projects/calendar.html', {'projects': projects, 'tasks': tasks, 'meetings': meetings})

@login_required
def calendar_events_json(request):
    from .models import Meeting
    user_role = request.user.profile.role
    if user_role == 'project_manager':
        projects = Project.objects.filter(manager=request.user)
        tasks = Task.objects.filter(project__manager=request.user)
        meetings = Meeting.objects.filter(Q(project__manager=request.user) | Q(organizer=request.user))
    else:
        projects = Project.objects.all()
        tasks = Task.objects.all()
        meetings = Meeting.objects.all()
        
    events = []
    
    # 1. Project Deadlines
    for p in projects:
        if p.deadline:
            events.append({
                'id': f'project_{p.id}',
                'title': f'🏁 Project: {p.title}',
                'start': p.deadline.strftime('%Y-%m-%d'),
                'allDay': True,
                'backgroundColor': '#4f46e5',
                'borderColor': '#4f46e5',
                'extendedProps': {
                    'type': 'project',
                    'status': p.get_status_display(),
                    'priority': p.get_priority_display() if hasattr(p, 'get_priority_display') else 'N/A',
                    'client': p.client.name,
                    'manager': p.manager.get_full_name() or p.manager.username if p.manager else 'Unassigned'
                }
            })
            
    # 2. Task Deadlines
    for t in tasks:
        if t.deadline:
            color = '#64748b'
            if t.status == 'in_progress':
                color = '#2563eb'
            elif t.status == 'review':
                color = '#ea580c'
            elif t.status == 'done':
                color = '#16a34a'
                
            events.append({
                'id': f'task_{t.id}',
                'title': f'📋 Task: {t.title}',
                'start': t.deadline.strftime('%Y-%m-%d'),
                'allDay': True,
                'backgroundColor': color,
                'borderColor': color,
                'extendedProps': {
                    'type': 'task',
                    'project': t.project.title,
                    'status': t.get_status_display(),
                    'priority': t.get_priority_display(),
                    'assignee': t.assigned_to.get_full_name() or t.assigned_to.username if t.assigned_to else 'Unassigned'
                }
            })
            
    # 3. Meetings
    for m in meetings:
        events.append({
            'id': f'meeting_{m.id}',
            'title': f'🤝 Meet: {m.title}',
            'start': m.start_time.isoformat(),
            'end': m.end_time.isoformat(),
            'allDay': False,
            'backgroundColor': '#db2777',
            'borderColor': '#db2777',
            'extendedProps': {
                'type': 'meeting',
                'project': m.project.title if m.project else 'General Workspace',
                'organizer': m.organizer.get_full_name() or m.organizer.username,
                'description': m.description or 'No description provided.'
            }
        })
        
    return JsonResponse(events, safe=False)

@login_required
@require_POST
def update_calendar_event(request, type, pk):
    from .models import Meeting
    try:
        data = json.loads(request.body)
        new_start_str = data.get('start')
        new_end_str = data.get('end')
        
        # Parse datetime or date
        if 'T' in new_start_str:
            new_start = datetime.fromisoformat(new_start_str.replace('Z', ''))
        else:
            new_start = datetime.strptime(new_start_str, '%Y-%m-%d').date()
            
        if type == 'project':
            project = get_object_or_404(Project, pk=pk)
            project.deadline = new_start
            project.save()
            
            Notification.objects.create(
                user=project.manager or request.user,
                message=f"Project '{project.title}' deadline rescheduled to {new_start.strftime('%b %d, %Y')}."
            )
            return JsonResponse({'status': 'success', 'message': 'Project deadline updated'})
            
        elif type == 'task':
            task = get_object_or_404(Task, pk=pk)
            task.deadline = new_start
            task.save()
            
            Notification.objects.create(
                user=task.assigned_to or request.user,
                message=f"Task '{task.title}' deadline rescheduled to {new_start.strftime('%b %d, %Y')}."
            )
            return JsonResponse({'status': 'success', 'message': 'Task deadline updated'})
            
        elif type == 'meeting':
            meeting = get_object_or_404(Meeting, pk=pk)
            meeting.start_time = datetime.fromisoformat(new_start_str.replace('Z', ''))
            if new_end_str:
                meeting.end_time = datetime.fromisoformat(new_end_str.replace('Z', ''))
            else:
                from datetime import timedelta
                meeting.end_time = meeting.start_time + timedelta(hours=1)
            meeting.save()
            
            Notification.objects.create(
                user=meeting.organizer,
                message=f"Meeting '{meeting.title}' rescheduled to {meeting.start_time.strftime('%b %d, %Y %I:%M %p')}."
            )
            return JsonResponse({'status': 'success', 'message': 'Meeting schedule updated'})
            
        return JsonResponse({'status': 'error', 'message': 'Invalid event type'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

@login_required
@require_POST
def create_meeting_json(request):
    from .models import Meeting
    try:
        data = json.loads(request.body)
        title = data.get('title')
        project_id = data.get('project_id')
        start_str = data.get('start')
        end_str = data.get('end')
        description = data.get('description', '')
        
        project = None
        if project_id:
            project = get_object_or_404(Project, id=project_id)
            
        start_time = datetime.fromisoformat(start_str.replace('Z', ''))
        if end_str:
            end_time = datetime.fromisoformat(end_str.replace('Z', ''))
        else:
            from datetime import timedelta
            end_time = start_time + timedelta(hours=1)
            
        meeting = Meeting.objects.create(
            title=title,
            project=project,
            organizer=request.user,
            start_time=start_time,
            end_time=end_time,
            description=description
        )
        
        return JsonResponse({
            'status': 'success',
            'meeting': {
                'id': meeting.id,
                'title': meeting.title,
                'start': meeting.start_time.isoformat(),
                'end': meeting.end_time.isoformat()
            }
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

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
            
    # Sort
    managers.sort(key=lambda x: x['latest_time'] or datetime.min, reverse=True)
    team_members.sort(key=lambda x: x['latest_time'] or datetime.min, reverse=True)
    clients.sort(key=lambda x: x['latest_time'] or datetime.min, reverse=True)

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