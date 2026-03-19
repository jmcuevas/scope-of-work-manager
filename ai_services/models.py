from django.conf import settings
from django.db import models


class AIRequestLog(models.Model):
    class RequestType(models.TextChoices):
        SCOPE_FROM_DESCRIPTION = 'SCOPE_FROM_DESCRIPTION', 'Scope from Description'
        SCOPE_ITEM = 'SCOPE_ITEM', 'Scope Item'
        REWRITE_ITEM = 'REWRITE_ITEM', 'Rewrite Item'
        EXPAND_ITEM = 'EXPAND_ITEM', 'Expand Item'
        CHAT = 'CHAT', 'Chat'
        COMPLETENESS_CHECK = 'COMPLETENESS_CHECK', 'Completeness Check'

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


class ChatSession(models.Model):
    exhibit = models.ForeignKey(
        'exhibits.ScopeExhibit',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='chat_sessions',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='chat_sessions',
    )
    context_type = models.CharField(max_length=20, default='exhibit')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f'Chat #{self.pk} — {self.exhibit} ({self.created_at:%Y-%m-%d %H:%M})'


class ChatMessage(models.Model):
    class Role(models.TextChoices):
        USER = 'user', 'User'
        ASSISTANT = 'assistant', 'Assistant'

    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=Role.choices)
    content = models.TextField()
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='chat_messages',
    )
    tokens_used = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.role}: {self.content[:50]}'
