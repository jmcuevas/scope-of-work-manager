from django.db import models
from django.conf import settings


class Note(models.Model):
    class NoteType(models.TextChoices):
        SCOPE_CLARIFICATION = 'SCOPE_CLARIFICATION', 'Scope Clarification'
        OPEN_QUESTION = 'OPEN_QUESTION', 'Open Question'
        MEANS_METHODS = 'MEANS_METHODS', 'Means & Methods'
        OWNER_ARCHITECT_DIRECTION = 'OWNER_ARCHITECT_DIRECTION', 'Owner/Architect Direction'

    class Status(models.TextChoices):
        OPEN = 'OPEN', 'Open'
        RESOLVED = 'RESOLVED', 'Resolved'

    project = models.ForeignKey(
        'projects.Project', on_delete=models.CASCADE, related_name='notes'
    )
    primary_trade = models.ForeignKey(
        'projects.Trade', on_delete=models.CASCADE, related_name='primary_notes'
    )
    related_trades = models.ManyToManyField(
        'projects.Trade', blank=True, related_name='related_notes'
    )
    text = models.TextField()
    note_type = models.CharField(max_length=30, choices=NoteType.choices)
    source = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)
    resolution = models.TextField(blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_notes',
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='created_notes',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'[{self.get_note_type_display()}] {self.text[:60]}'
