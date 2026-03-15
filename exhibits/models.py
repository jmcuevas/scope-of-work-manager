from django.db import models
from django.conf import settings


class ScopeExhibit(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        READY_FOR_REVIEW = 'READY_FOR_REVIEW', 'Ready for Review'
        READY_FOR_BID = 'READY_FOR_BID', 'Ready for Bid'
        FINALIZED = 'FINALIZED', 'Finalized'

    company = models.ForeignKey(
        'core.Company', on_delete=models.CASCADE, related_name='scope_exhibits'
    )
    csi_trade = models.ForeignKey(
        'core.CSITrade', on_delete=models.PROTECT, related_name='scope_exhibits'
    )
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='scope_exhibits',
        null=True,
        blank=True,
    )
    is_template = models.BooleanField(default=False)
    scope_description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    based_on = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='derived_exhibits',
    )
    last_edited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='last_edited_exhibits',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='created_exhibits',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        label = 'Template' if self.is_template else str(self.project)
        return f'{self.csi_trade} — {label}'


class ExhibitSection(models.Model):
    scope_exhibit = models.ForeignKey(
        ScopeExhibit, on_delete=models.CASCADE, related_name='sections'
    )
    name = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f'{self.scope_exhibit} / {self.name}'


class ScopeItem(models.Model):
    section = models.ForeignKey(
        ExhibitSection, on_delete=models.CASCADE, related_name='items'
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
    )
    level = models.PositiveSmallIntegerField(default=0)
    text = models.TextField()
    original_input = models.TextField(blank=True)
    is_ai_generated = models.BooleanField(default=False)
    is_pending_review = models.BooleanField(default=False)
    pending_original_text = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='created_scope_items',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f'{self.section} / item {self.order}'
