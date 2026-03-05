from django.db import models
from django.conf import settings


class ChecklistItem(models.Model):
    company = models.ForeignKey(
        'core.Company', on_delete=models.CASCADE, related_name='checklist_items'
    )
    csi_trade = models.ForeignKey(
        'core.CSITrade', on_delete=models.CASCADE, related_name='checklist_items'
    )
    text = models.TextField()
    project_type_tags = models.ManyToManyField(
        'core.ProjectType', blank=True, related_name='checklist_items'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='created_checklist_items',
    )
    source_project = models.ForeignKey(
        'projects.Project',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='checklist_items',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.csi_trade} — {self.text[:60]}'


class FinalReview(models.Model):
    class Status(models.TextChoices):
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        COMPLETED = 'COMPLETED', 'Completed'

    scope_exhibit = models.ForeignKey(
        'exhibits.ScopeExhibit', on_delete=models.CASCADE, related_name='final_reviews'
    )
    initiated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='initiated_reviews',
    )
    initiated_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=15, choices=Status.choices, default=Status.IN_PROGRESS
    )

    class Meta:
        ordering = ['-initiated_at']

    def __str__(self):
        return f'Review of {self.scope_exhibit} — {self.get_status_display()}'


class FinalReviewItem(models.Model):
    class CheckType(models.TextChoices):
        OPEN_NOTE = 'OPEN_NOTE', 'Open Note'
        CROSS_TRADE = 'CROSS_TRADE', 'Cross-Trade'
        CUSTOM_CHECKLIST = 'CUSTOM_CHECKLIST', 'Custom Checklist'

    class ItemStatus(models.TextChoices):
        PASS = 'PASS', 'Pass'
        WARNING = 'WARNING', 'Warning'
        FAIL = 'FAIL', 'Fail'

    final_review = models.ForeignKey(
        FinalReview, on_delete=models.CASCADE, related_name='items'
    )
    check_type = models.CharField(max_length=20, choices=CheckType.choices)
    description = models.TextField()
    status = models.CharField(max_length=10, choices=ItemStatus.choices)
    pm_response = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'{self.get_check_type_display()} — {self.get_status_display()}'
