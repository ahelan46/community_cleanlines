import os
import django
import random
from datetime import date, timedelta, datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tracker.settings')
django.setup()

from django.contrib.auth.models import User
from projects.models import Client, Project, Task, Invoice, MeetingNote, ActivityLog, ClientPermission, Feedback, UserProfile, Message

def populate():
    print("Clearing existing data...")
    # Clear existing data
    ActivityLog.objects.all().delete()
    ClientPermission.objects.all().delete()
    Invoice.objects.all().delete()
    MeetingNote.objects.all().delete()
    Feedback.objects.all().delete()
    Task.objects.all().delete()
    Project.objects.all().delete()
    Client.objects.all().delete()
    Message.objects.all().delete()
    
    # Delete users except active superusers if any, or just recreation
    User.objects.exclude(username='admin_custom').delete()

    # Create users
    print("Creating users with roles...")
    # 1. Admin
    admin_user = User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    admin_user.profile.role = 'admin'
    admin_user.profile.phone = '+1 555-0100'
    admin_user.profile.save()

    # 2. PM
    pm_user = User.objects.create_user('pm', 'pm@example.com', 'admin123')
    pm_user.first_name = "Sarah"
    pm_user.last_name = "Connor"
    pm_user.save()
    pm_user.profile.role = 'project_manager'
    pm_user.profile.phone = '+1 555-0111'
    pm_user.profile.save()

    # 3. Team Leader
    lead_user = User.objects.create_user('lead', 'lead@example.com', 'admin123')
    lead_user.first_name = "Alex"
    lead_user.last_name = "Mercer"
    lead_user.save()
    lead_user.profile.role = 'team_leader'
    lead_user.profile.save()

    # 4. Team Member / Dev
    dev_user = User.objects.create_user('dev', 'dev@example.com', 'admin123')
    dev_user.first_name = "John"
    dev_user.last_name = "Doe"
    dev_user.save()
    dev_user.profile.role = 'team_member'
    dev_user.profile.save()

    # 5. Client Users (so they can log in!)
    client_auths = {}
    client_credentials = [
        ('carlos', 'carlos@apexsolutions.mx'),
        ('michael', 'michael@horizontech.io'),
        ('priya', 'priya@elevatebrands.com'),
    ]
    for username, email in client_credentials:
        c_user = User.objects.create_user(username, email, 'admin123')
        c_user.profile.role = 'client'
        c_user.profile.save()
        client_auths[email] = c_user

    # Create clients
    clients_data = [
        {
            'client_id': 'CLT-2026-101',
            'name': 'Carlos Mendez', 
            'address': 'Apex Solutions', 
            'email': 'carlos@apexsolutions.mx', 
            'phone': '+52 55-5555-0127',
            'revenue_paid': 45000.00,
            'revenue_pending': 10000.00,
            'priority': 'vip',
            'satisfaction': 4.9,
            'notes': 'Prefers Slack for quick updates. Weekly sync on Thursdays.',
            'last_message_date': date.today() - timedelta(days=1),
            'last_meeting_date': date.today() - timedelta(days=3)
        },
        {
            'client_id': 'CLT-2026-102',
            'name': 'Michael Thornton', 
            'address': 'Horizon Tech', 
            'email': 'michael@horizontech.io', 
            'phone': '+1 415-555-0101',
            'revenue_paid': 85000.00,
            'revenue_pending': 25000.00,
            'priority': 'premium',
            'satisfaction': 4.7,
            'notes': 'Strict adherence to design prototypes. Requires detailed invoices.',
            'last_message_date': date.today() - timedelta(days=2),
            'last_meeting_date': date.today() - timedelta(days=5)
        },
        {
            'client_id': 'CLT-2026-103',
            'name': 'Priya Patel', 
            'address': 'Elevate Brands', 
            'email': 'priya@elevatebrands.com', 
            'phone': '+1 312-555-0182',
            'revenue_paid': 15000.00,
            'revenue_pending': 5000.00,
            'priority': 'regular',
            'satisfaction': 4.5,
            'notes': 'Looking for ongoing maintenance packages post-launch.',
            'last_message_date': date.today() - timedelta(days=4),
            'last_meeting_date': date.today() - timedelta(days=8)
        },
        {
            'client_id': 'CLT-2026-104',
            'name': 'David Okafor', 
            'address': 'GreenLeaf Co.', 
            'email': 'david@greenleafco.com', 
            'phone': '+1 718-555-0143',
            'revenue_paid': 30000.00,
            'revenue_pending': 12000.00,
            'priority': 'premium',
            'satisfaction': 4.8,
            'notes': 'Needs double confirmation on all deadline updates.',
            'last_message_date': date.today() - timedelta(days=5),
            'last_meeting_date': date.today() - timedelta(days=10)
        },
        {
            'client_id': 'CLT-2026-105',
            'name': 'Sophie Müller', 
            'address': 'Nordik Design', 
            'email': 'sophie@nordikdesign.eu', 
            'phone': '+49 30-555-0165',
            'revenue_paid': 60000.00,
            'revenue_pending': 0.00,
            'priority': 'vip',
            'satisfaction': 5.0,
            'notes': 'Highly satisfied. Prefers formal documentation.',
            'last_message_date': date.today() - timedelta(days=3),
            'last_meeting_date': date.today() - timedelta(days=12)
        },
    ]

    clients = []
    for data in clients_data:
        client = Client.objects.create(**data)
        clients.append(client)
        # Create default permissions
        ClientPermission.objects.create(
            client=client,
            can_upload=True,
            can_comment=True,
            can_edit=False
        )
    
    print(f"Created {len(clients)} clients.")

    # Create projects
    projects_data = [
        {
            'title': 'Nordik Product Catalog', 
            'client': clients[4], 
            'status': 'completed', 
            'priority': 'medium', 
            'deadline': date.today() - timedelta(days=5),
            'estimated_hours': 80,
            'worked_hours': 80,
            'approval_status': 'approved',
            'current_stage': 'deployment',
            'tags': 'UI/UX, Django, Web App',
            'budget_type': 'fixed',
            'budget_amount': 25000.00
        },
        {
            'title': 'Brand Identity Redesign', 
            'client': clients[1], 
            'status': 'ongoing', 
            'priority': 'high', 
            'deadline': date.today() + timedelta(days=15),
            'estimated_hours': 60,
            'worked_hours': 45,
            'approval_status': 'pending',
            'current_stage': 'design',
            'tags': 'UI/UX, Branding',
            'budget_type': 'fixed',
            'budget_amount': 15000.00
        },
        {
            'title': 'E-commerce Platform v2', 
            'client': clients[2], 
            'status': 'ongoing', 
            'priority': 'urgent', 
            'deadline': date.today() + timedelta(days=3),
            'estimated_hours': 150,
            'worked_hours': 125,
            'approval_status': 'revision',
            'current_stage': 'development',
            'tags': 'Django, Python, API',
            'budget_type': 'hourly',
            'budget_amount': 45000.00
        },
        {
            'title': 'Mobile App Development', 
            'client': clients[1], 
            'status': 'planning', 
            'priority': 'high', 
            'deadline': date.today() + timedelta(days=45),
            'estimated_hours': 200,
            'worked_hours': 10,
            'approval_status': 'pending',
            'current_stage': 'planning',
            'tags': 'Mobile App, React Native',
            'budget_type': 'fixed',
            'budget_amount': 60000.00
        },
        {
            'title': 'AI Recommendation System', 
            'client': clients[0], 
            'status': 'ongoing', 
            'priority': 'urgent', 
            'deadline': date.today() + timedelta(days=1),
            'estimated_hours': 120,
            'worked_hours': 118,
            'approval_status': 'pending',
            'current_stage': 'testing',
            'tags': 'AI, Python, API',
            'budget_type': 'fixed',
            'budget_amount': 55000.00
        },
    ]

    projects = []
    for data in projects_data:
        project = Project.objects.create(
            title=data['title'],
            client=data['client'],
            status=data['status'],
            priority=data['priority'],
            deadline=data['deadline'],
            manager=pm_user,
            description=f"Advanced setup for {data['title']}.",
            estimated_hours=data['estimated_hours'],
            worked_hours=data['worked_hours'],
            approval_status=data['approval_status'],
            current_stage=data['current_stage'],
            tags=data['tags'],
            budget_type=data['budget_type'],
            budget_amount=data['budget_amount']
        )
        projects.append(project)

    # Seed Tasks
    task_templates = [
        ("Setup environment and repositories", "done", "high", -10),
        ("UI/UX Design Mockups", "done", "medium", -5),
        ("Database Architecture planning", "done", "high", -3),
        ("Core Backend Development", "in_progress", "urgent", 3),
        ("API Integrations and testing", "todo", "high", 5),
        ("Frontend/UI Implementation", "in_progress", "medium", 4),
        ("Deployment & Release", "todo", "low", 12),
    ]

    for p in projects:
        for title, status, priority, days in task_templates:
            # Shift deadlines relative to project deadline
            dl = p.deadline + timedelta(days=days)
            # Make sure status matches project state
            if p.status == 'completed':
                status = 'done'
            elif p.status == 'planning':
                status = 'todo'
            Task.objects.create(
                project=p,
                title=f"{title} ({p.title})",
                assigned_to=dev_user if random.choice([True, False]) else lead_user,
                status=status,
                priority=priority,
                deadline=dl
            )

    # Seed Invoices
    print("Seeding invoices...")
    invoice_count = 1
    for p in projects:
        # Create a paid invoice
        Invoice.objects.create(
            client=p.client,
            project=p,
            invoice_number=f"INV-2026-00{invoice_count}",
            amount=decimal_helper(p.budget_amount) * decimal_helper(0.6),
            status='paid',
            due_date=date.today() - timedelta(days=15)
        )
        invoice_count += 1
        
        # Create a pending invoice if project ongoing
        if p.status == 'ongoing':
            Invoice.objects.create(
                client=p.client,
                project=p,
                invoice_number=f"INV-2026-00{invoice_count}",
                amount=decimal_helper(p.budget_amount) * decimal_helper(0.4),
                status='pending',
                due_date=date.today() + timedelta(days=10)
            )
            invoice_count += 1

    # Seed Meeting Notes
    print("Seeding meeting notes...")
    for c in clients:
        MeetingNote.objects.create(
            client=c,
            title=f"Kickoff Meeting - {c.address}",
            summary="Introduced team members, discussed goals, reviewed technology stack requirements.",
            discussion_points="1. High availability architecture\n2. Integration with third-party billing CRM\n3. Mobile app compatibility",
            next_actions="1. Sarah to send design mocks by Friday\n2. Client to review asset folders"
        )
        MeetingNote.objects.create(
            client=c,
            title=f"Sprint Review & Demo - {c.address}",
            summary="Showcased homepage and database integration templates. Collected general feedback.",
            discussion_points="1. Colors are too dark, need more vibrant tones\n2. Fast page transition speeds are premium\n3. Search functionality should include filters",
            next_actions="1. Development team to apply glassmorphism design variables\n2. Schedule next sync in 2 weeks"
        )

    # Seed Activity Logs
    print("Seeding activity logs...")
    for p in projects:
        ActivityLog.objects.create(
            client=p.client,
            user=pm_user,
            activity_type="Uploaded file",
            description=f"Sarah uploaded 'design_specification_v2.pdf' for {p.title}"
        )
        ActivityLog.objects.create(
            client=p.client,
            user=dev_user,
            activity_type="Edited task",
            description=f"John Doe marked task 'Setup repositories' as Completed in {p.title}"
        )
        ActivityLog.objects.create(
            client=p.client,
            user=pm_user,
            activity_type="Changed deadline",
            description=f"Deadline was extended by 5 days for {p.title}"
        )

    # Seed Feedback
    print("Seeding feedback tickets...")
    categories = ['ui_design', 'bug', 'performance', 'communication', 'feature_request']
    for p in projects:
        # Get client auth user
        c_user = client_auths.get(p.client.email, admin_user)
        Feedback.objects.create(
            project=p,
            client=c_user,
            subject=f"UI Enhancements for {p.title}",
            message="The page designs look extremely clean, but could we add smoother hover animations and a subtle card shadow system? That would feel much more professional.",
            rating=4,
            category='ui_design',
            status='in_progress',
            reply="Thanks for the input Carlos! We have updated static/css/style.css to include soft CSS transitions and soft shadows, which renders beautifully across both light and dark modes."
        )
        Feedback.objects.create(
            project=p,
            client=c_user,
            subject=f"Loading performance on mobile in {p.title}",
            message="On cellular connections, the database loading takes a couple seconds. Skeleton loader screens would represent an awesome UX improvement.",
            rating=5,
            category='performance',
            status='open'
        )

    print("Database seeding completed successfully!")

def decimal_helper(float_val):
    from decimal import Decimal
    return Decimal(str(float_val))

if __name__ == '__main__':
    populate()
