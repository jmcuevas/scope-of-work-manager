from django.db import models
from django.conf import settings


class Project(models.Model):
    company = models.ForeignKey(
        'core.Company', on_delete=models.CASCADE, related_name='projects'
    )
    name = models.CharField(max_length=255)
    number = models.CharField(max_length=50, blank=True)
    project_type = models.ForeignKey(
        'core.ProjectType', on_delete=models.PROTECT, related_name='projects'
    )
    description = models.TextField(blank=True)
    address = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='created_projects'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.number} - {self.name}' if self.number else self.name


class Trade(models.Model):
    class Status(models.TextChoices):
        NOT_STARTED = 'NOT_STARTED', 'Not Started'
        SCOPE_IN_PROGRESS = 'SCOPE_IN_PROGRESS', 'Scope In Progress'
        OUT_TO_BID = 'OUT_TO_BID', 'Out to Bid'
        BIDS_RECEIVED = 'BIDS_RECEIVED', 'Bids Received'
        SUBCONTRACT_ISSUED = 'SUBCONTRACT_ISSUED', 'Subcontract Issued'

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='trades')
    csi_trade = models.ForeignKey(
        'core.CSITrade', on_delete=models.PROTECT, related_name='trades'
    )
    budget = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    status = models.CharField(
        max_length=25, choices=Status.choices, default=Status.NOT_STARTED
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_trades',
    )
    order = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'csi_trade__csi_code']
        constraints = [
            models.UniqueConstraint(
                fields=['project', 'csi_trade'], name='unique_trade_per_project'
            )
        ]

    def __str__(self):
        return f'{self.project} / {self.csi_trade}'
