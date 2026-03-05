from django import forms
from core.models import CSITrade
from .models import Project, Trade


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


class TradeForm(forms.ModelForm):
    class Meta:
        model = Trade
        fields = ['csi_trade', 'budget']
        widgets = {
            'csi_trade': forms.Select(attrs={
                'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent',
            }),
            'budget': forms.NumberInput(attrs={
                'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent',
                'placeholder': '450000',
                'step': '1000',
            }),
        }
        labels = {
            'csi_trade': 'CSI Trade',
            'budget': 'Budget ($)',
        }

    def __init__(self, *args, **kwargs):
        self.project = kwargs.pop('project', None)
        super().__init__(*args, **kwargs)
        self.fields['csi_trade'].queryset = CSITrade.objects.all()

    def clean_csi_trade(self):
        csi_trade = self.cleaned_data['csi_trade']
        if self.project and Trade.objects.filter(project=self.project, csi_trade=csi_trade).exists():
            raise forms.ValidationError(
                f'{csi_trade} is already on this project.'
            )
        return csi_trade
