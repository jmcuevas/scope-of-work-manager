from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from ai_services.models import ChatSession


class Command(BaseCommand):
    help = 'Delete empty ChatSession records older than a given number of days (default: 90).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=90,
            help='Delete empty sessions older than this many days (default: 90).',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Print what would be deleted without actually deleting.',
        )

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']
        cutoff = timezone.now() - timedelta(days=days)

        qs = ChatSession.objects.filter(
            updated_at__lt=cutoff,
            messages__isnull=True,
        )
        count = qs.count()

        if dry_run:
            self.stdout.write(
                self.style.WARNING(f'[dry-run] Would delete {count} empty session(s) older than {days} days.')
            )
        else:
            qs.delete()
            self.stdout.write(
                self.style.SUCCESS(f'Deleted {count} empty session(s) older than {days} days.')
            )
