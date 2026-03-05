from django import forms
from .models import Project


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['name', 'number', 'project_type', 'description', 'address']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent',
                'placeholder': '456 Montgomery St — Lab TI',
            }),
            'number': forms.TextInput(attrs={
                'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent',
                'placeholder': '2026-0142',
            }),
            'project_type': forms.Select(attrs={
                'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent',
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent',
                'rows': 3,
                'placeholder': '5-story lab TI in existing office building, 45,000 SF, LEED Gold target',
            }),
            'address': forms.TextInput(attrs={
                'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent',
                'placeholder': '456 Montgomery St, San Francisco, CA',
            }),
        }
        labels = {
            'number': 'Project Number',
            'project_type': 'Project Type',
        }
