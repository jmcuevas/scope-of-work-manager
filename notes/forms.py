from django import forms

from projects.models import Trade

from .models import Note


class NoteForm(forms.ModelForm):
    class Meta:
        model = Note
        fields = ['text', 'note_type', 'primary_trade', 'related_trades', 'source']
        widgets = {
            'text': forms.Textarea(attrs={'rows': 2}),
            'source': forms.TextInput(),
            'related_trades': forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        if project is not None:
            qs = Trade.objects.filter(project=project).select_related('csi_trade')
            self.fields['primary_trade'].queryset = qs
            self.fields['related_trades'].queryset = qs
        self.fields['primary_trade'].empty_label = 'Select trade…'
        self.fields['source'].required = False
        self.fields['related_trades'].required = False
