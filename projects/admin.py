from django.contrib import admin
from .models import Project, Trade


class TradeInline(admin.TabularInline):
    model = Trade
    extra = 0
    fields = ('csi_trade', 'budget', 'status', 'assigned_to', 'order')
    ordering = ('order',)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'number', 'company', 'project_type', 'created_by', 'created_at')
    list_filter = ('company', 'project_type')
    search_fields = ('name', 'number')
    inlines = [TradeInline]


@admin.register(Trade)
class TradeAdmin(admin.ModelAdmin):
    list_display = ('csi_trade', 'project', 'status', 'budget', 'assigned_to')
    list_filter = ('status', 'project__company')
    search_fields = ('csi_trade__name', 'csi_trade__csi_code', 'project__name')
