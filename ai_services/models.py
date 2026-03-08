from django.db import models


class AIRequestLog(models.Model):
    class RequestType(models.TextChoices):
        SCOPE_FROM_DESCRIPTION = 'SCOPE_FROM_DESCRIPTION', 'Scope from Description'
        SCOPE_ITEM = 'SCOPE_ITEM', 'Scope Item'

    request_type = models.CharField(max_length=30, choices=RequestType.choices)
    exhibit = models.ForeignKey(
        'exhibits.ScopeExhibit',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ai_request_logs',
    )
    success = models.BooleanField()
    error_message = models.TextField(blank=True)
    tokens_used = models.PositiveIntegerField(null=True, blank=True)
    latency_ms = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        status = 'OK' if self.success else 'FAIL'
        return f'[{status}] {self.get_request_type_display()} — {self.created_at:%Y-%m-%d %H:%M}'
