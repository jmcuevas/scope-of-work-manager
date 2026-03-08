from django.contrib import admin

from .models import AIRequestLog


@admin.register(AIRequestLog)
class AIRequestLogAdmin(admin.ModelAdmin):
    list_display = ['created_at', 'request_type', 'exhibit', 'success', 'tokens_used', 'latency_ms']
    list_filter = ['request_type', 'success']
    readonly_fields = ['request_type', 'exhibit', 'success', 'error_message', 'tokens_used', 'latency_ms', 'created_at']
    ordering = ['-created_at']
