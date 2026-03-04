from django.contrib import admin
from .models import ScopeExhibit, ExhibitSection, ScopeItem


class ExhibitSectionInline(admin.TabularInline):
    model = ExhibitSection
    extra = 0
    fields = ('name', 'order')
    ordering = ('order',)


@admin.register(ScopeExhibit)
class ScopeExhibitAdmin(admin.ModelAdmin):
    list_display = ('csi_trade', 'project', 'is_template', 'status', 'last_edited_by', 'updated_at')
    list_filter = ('is_template', 'status', 'company')
    search_fields = ('csi_trade__name', 'project__name')
    inlines = [ExhibitSectionInline]


@admin.register(ExhibitSection)
class ExhibitSectionAdmin(admin.ModelAdmin):
    list_display = ('name', 'scope_exhibit', 'order')
    search_fields = ('name',)


@admin.register(ScopeItem)
class ScopeItemAdmin(admin.ModelAdmin):
    list_display = ('section', 'level', 'order', 'is_ai_generated', 'created_by')
    list_filter = ('is_ai_generated', 'level')
    search_fields = ('text',)
