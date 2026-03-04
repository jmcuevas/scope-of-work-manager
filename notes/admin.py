from django.contrib import admin
from .models import Note


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ('note_type', 'primary_trade', 'project', 'status', 'created_by', 'created_at')
    list_filter = ('note_type', 'status', 'project__company')
    search_fields = ('text', 'resolution')
    filter_horizontal = ('related_trades',)
