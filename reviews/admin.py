from django.contrib import admin
from .models import ChecklistItem, FinalReview, FinalReviewItem


class FinalReviewItemInline(admin.TabularInline):
    model = FinalReviewItem
    extra = 0
    fields = ('check_type', 'description', 'status', 'pm_response')


@admin.register(ChecklistItem)
class ChecklistItemAdmin(admin.ModelAdmin):
    list_display = ('csi_trade', 'company', 'text', 'source_project', 'created_at')
    list_filter = ('company', 'csi_trade')
    search_fields = ('text',)
    filter_horizontal = ('project_type_tags',)


@admin.register(FinalReview)
class FinalReviewAdmin(admin.ModelAdmin):
    list_display = ('scope_exhibit', 'status', 'initiated_by', 'initiated_at', 'completed_at')
    list_filter = ('status',)
    inlines = [FinalReviewItemInline]


@admin.register(FinalReviewItem)
class FinalReviewItemAdmin(admin.ModelAdmin):
    list_display = ('final_review', 'check_type', 'status', 'reviewed_at')
    list_filter = ('check_type', 'status')
