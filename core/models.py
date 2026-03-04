from django.contrib.auth.models import AbstractUser
from django.db import models


class Company(models.Model):
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'companies'

    def __str__(self):
        return self.name


class User(AbstractUser):
    class Role(models.TextChoices):
        PM = 'PM', 'Project Manager'
        PE = 'PE', 'Project Engineer'
        SUPERINTENDENT = 'SUPERINTENDENT', 'Superintendent'
        ADMIN = 'ADMIN', 'Admin'

    username = None
    email = models.EmailField(unique=True)
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='users',
        null=True,
        blank=True,
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.PE)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email

    @property
    def is_pm(self):
        return self.role == self.Role.PM

    @property
    def is_pe(self):
        return self.role == self.Role.PE

    @property
    def is_company_admin(self):
        return self.role == self.Role.ADMIN


class ProjectType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class CSITrade(models.Model):
    csi_code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['csi_code']
        verbose_name = 'CSI Trade'

    def __str__(self):
        return f'{self.csi_code} - {self.name}'
