from django.contrib import admin

from .models import AIRequestLog, ChatMessage, ChatSession


@admin.register(AIRequestLog)
class AIRequestLogAdmin(admin.ModelAdmin):
    list_display = ['created_at', 'request_type', 'exhibit', 'success', 'tokens_used', 'latency_ms']
    list_filter = ['request_type', 'success']
    readonly_fields = ['request_type', 'exhibit', 'success', 'error_message', 'tokens_used', 'latency_ms', 'created_at']
    ordering = ['-created_at']


class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    extra = 0
    readonly_fields = ['role', 'content', 'user', 'tokens_used', 'created_at']


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'exhibit', 'user', 'context_type', 'created_at', 'updated_at']
    list_filter = ['context_type']
    readonly_fields = ['exhibit', 'user', 'context_type', 'created_at', 'updated_at']
    inlines = [ChatMessageInline]


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'session', 'role', 'user', 'tokens_used', 'created_at']
    list_filter = ['role']
    readonly_fields = ['session', 'role', 'content', 'user', 'tokens_used', 'created_at']
