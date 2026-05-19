from django.contrib import admin
from .models import Client, Project, Task, Notification, UserProfile, ProjectAssignment

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'phone')
    list_filter = ('role',)
    search_fields = ('user__username', 'phone')

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'created_at')
    search_fields = ('name', 'email')

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'client', 'manager', 'status', 'deadline')
    list_filter = ('status', 'client')
    search_fields = ('title', 'description')

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'project', 'assigned_to', 'status', 'deadline')
    list_filter = ('status', 'project')
    search_fields = ('title', 'description')

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'message', 'is_read', 'created_at')
    list_filter = ('is_read',)

@admin.register(ProjectAssignment)
class ProjectAssignmentAdmin(admin.ModelAdmin):
    list_display = ('project', 'team_leader', 'assigned_by', 'status', 'assigned_at')
    list_filter = ('status', 'assigned_at')
    search_fields = ('project__title', 'team_leader__username')
    readonly_fields = ('assigned_at', 'updated_at')
