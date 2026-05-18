from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('clients/', views.client_list, name='client_list'),
    path('projects/', views.project_list, name='project_list'),
    path('projects/<int:pk>/', views.project_detail, name='project_detail'),
    path('tasks/', views.task_list, name='task_list'),
    path('create-project/', views.create_project, name='create_project'),
    path('client-form/', views.client_form, name='client_form'),
    path('task-board/', views.task_board, name='task_board'),
    path('reports/', views.team_reports, name='team_reports'),
    path('reports/<int:pk>/approve/', views.approve_report, name='approve_report'),
    path('calendar/', views.calendar_view, name='calendar'),
    path('messages/', views.messages_view, name='messages'),
    path('client-projects/', views.client_projects, name='client_projects'),
    path('client-reports/', views.client_reports, name='client_reports'),
    path('client-files/', views.client_files, name='client_files'),
    path('client-feedback/', views.client_feedback, name='client_feedback'),
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('feedback/<int:pk>/edit/', views.edit_feedback, name='edit_feedback'),

]
