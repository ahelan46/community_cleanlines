from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import UserProfile

class SignUpForm(UserCreationForm):
    role = forms.ChoiceField(choices=UserProfile.ROLE_CHOICES, required=True)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('email',)

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            profile = user.profile
            profile.role = self.cleaned_data.get('role')
            profile.save()
        return user

from .models import Project, Task, Report, Client, ProjectFile, ProjectAssignment

class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['title', 'description', 'client', 'status', 'priority', 'deadline']
        widgets = {
            'deadline': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Project Title'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Project Description'}),
            'client': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
        }

class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['project', 'title', 'description', 'assigned_to', 'status', 'priority', 'deadline']
        widgets = {
            'deadline': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'project': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Task Title'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Task Description'}),
            'assigned_to': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
        }

class ReportForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = ['project', 'title', 'content']
        widgets = {
            'project': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Report Title'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Report Details'}),
        }

from .models import Feedback

class FeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ['project', 'subject', 'message', 'rating']
        widgets = {
            'project': forms.Select(attrs={'class': 'form-select'}),
            'subject': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Subject'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Your Feedback'}),
            'rating': forms.RadioSelect(choices=[(i, '⭐'*i) for i in range(1, 6)])
        }

class ClientProjectForm(forms.Form):
    # Client Information
    client_name = forms.CharField(
        label='Client Name',
        max_length=200,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter client name'
        })
    )
    
    phone = forms.CharField(
        label='Phone Number',
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter phone number',
            'type': 'tel'
        })
    )
    
    email = forms.EmailField(
        label='Email Address',
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter email address'
        })
    )
    
    # Project Information
    project_title = forms.CharField(
        label='Project Title',
        max_length=200,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter project title'
        })
    )
    
    # Project Deadline
    deadline = forms.DateField(
        label='Project Deadline',
        required=True,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'id': 'deadline_field'
        })
    )
    
    # File Upload (Optional)
    file_upload = forms.FileField(
        label='Upload File (Optional)',
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '*/*'
        })
    )


class ProjectAssignmentForm(forms.ModelForm):
    team_leader = forms.ModelChoiceField(
        queryset=User.objects.filter(profile__role='team_leader'),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Assign to Team Leader'
    )
    
    class Meta:
        model = ProjectAssignment
        fields = ['team_leader']




