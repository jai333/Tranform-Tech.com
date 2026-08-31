from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, JobSeekerApplication, Job

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField()
    first_name = forms.CharField(
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your first name'})
    )
    last_name = forms.CharField(
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your last name'})
    )
    about_me = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={
            'class': 'form-control', 
            'rows': 4, 
            'placeholder': 'Tell others about your experience, interests, and goals...'
        })
    )
    skills = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={
            'class': 'form-control', 
            'rows': 3, 
            'placeholder': 'e.g., Python, JavaScript, Project Management, Communication...'
        })
    )
    role = forms.ChoiceField(
        choices=User.ROLE_CHOICES,
        initial=User.ROLE_JOBSEEKER,
        widget=forms.RadioSelect,
        help_text="Select your role in the system."
    )
    profile_image = forms.ImageField(
        required=False, 
        widget=forms.FileInput(attrs={'class': 'form-control'}),
        help_text="Upload your profile picture (optional)"
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'about_me', 'skills', 'role', 'profile_image', 'password1', 'password2']

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'about_me', 'skills', 'profile_image']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'about_me': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Tell others about your experience, interests, and goals...'}),
            'skills': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'e.g., Python, JavaScript, Project Management, Communication...'}),
            'profile_image': forms.FileInput(attrs={'class': 'form-control'})
        }

class JobSeekerApplicationForm(forms.ModelForm):
    class Meta:
        model = JobSeekerApplication
        fields = ['cover_letter', 'resume']
        widgets = {
            'cover_letter': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 5, 
                'placeholder': 'Introduce yourself and explain why you are a good fit for this position...'
            }),
            'resume': forms.FileInput(attrs={'class': 'form-control'})
        }

class JobForm(forms.ModelForm):
    deadline = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        help_text="Optional application deadline date"
    )
    
    class Meta:
        model = Job
        fields = [
            'title', 'company', 'department', 'job_type', 'status',
            'location', 'salary', 'experience', 'skills',
            'description', 'requirements', 'benefits', 'deadline'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Senior Software Engineer'
            }),
            'company': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Transform-Tech'
            }),
            'department': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Engineering, Marketing, HR'
            }),
            'job_type': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Remote, Bangalore, Mumbai'
            }),
            'salary': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., ₹15-20 LPA, $80,000-$100,000'
            }),
            'experience': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., 3-5 years, Entry level'
            }),
            'skills': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Python, Java, React, Project Management'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Provide a comprehensive job description'
            }),
            'requirements': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'List all job qualifications and requirements'
            }),
            'benefits': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'List benefits, perks, and compensation details'
            }),
        } 