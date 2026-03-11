from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from notes.models import Note
from .models import ChecklistItem, FinalReview, FinalReviewItem


def generate_final_review(exhibit, user):
    """
    Run a completeness check on a scope exhibit and return a FinalReview.

    Checks performed (in order):
      1. OPEN_NOTE   — unresolved notes where this trade is the primary trade
      2. CROSS_TRADE — unresolved notes from OTHER trades that mention this trade
      3. CUSTOM_CHECKLIST — admin-seeded checklist items for this trade/company

    Re-running this function replaces any previous review for the exhibit.
    Returns the new FinalReview (status=IN_PROGRESS until saved as COMPLETED).
    """
    if not exhibit.project:
        # Template exhibits have no project — nothing to check; return a clean review
        with transaction.atomic():
            exhibit.final_reviews.all().delete()
            review = FinalReview.objects.create(
                scope_exhibit=exhibit,
                initiated_by=user,
                status=FinalReview.Status.COMPLETED,
                completed_at=timezone.now(),
            )
        return review

    try:
        from projects.models import Trade
        trade = Trade.objects.get(project=exhibit.project, csi_trade=exhibit.csi_trade)
    except Trade.DoesNotExist:
        trade = None

    items = []

    # ------------------------------------------------------------------
    # Check 1: Open notes (this trade is the primary trade)
    # ------------------------------------------------------------------
    if trade:
        open_primary_notes = (
            Note.objects
            .filter(primary_trade=trade, status=Note.Status.OPEN)
            .select_related('primary_trade__csi_trade')
        )
        for note in open_primary_notes:
            items.append(FinalReviewItem(
                check_type=FinalReviewItem.CheckType.OPEN_NOTE,
                description=f'Unresolved {note.get_note_type_display().lower()}: "{note.text[:120]}"',
                status=FinalReviewItem.ItemStatus.WARNING,
            ))

        if not open_primary_notes.exists():
            items.append(FinalReviewItem(
                check_type=FinalReviewItem.CheckType.OPEN_NOTE,
                description='No open notes for this trade.',
                status=FinalReviewItem.ItemStatus.PASS,
            ))

    # ------------------------------------------------------------------
    # Check 2: Cross-trade notes from other trades that mention this trade
    # ------------------------------------------------------------------
    if trade:
        cross_trade_notes = (
            Note.objects
            .filter(related_trades=trade, status=Note.Status.OPEN)
            .exclude(primary_trade=trade)
            .select_related('primary_trade__csi_trade')
        )
        for note in cross_trade_notes:
            items.append(FinalReviewItem(
                check_type=FinalReviewItem.CheckType.CROSS_TRADE,
                description=(
                    f'Open cross-trade note from {note.primary_trade.csi_trade.name}: '
                    f'"{note.text[:120]}"'
                ),
                status=FinalReviewItem.ItemStatus.WARNING,
            ))

        if not cross_trade_notes.exists():
            items.append(FinalReviewItem(
                check_type=FinalReviewItem.CheckType.CROSS_TRADE,
                description='No unresolved cross-trade notes involving this trade.',
                status=FinalReviewItem.ItemStatus.PASS,
            ))

    # ------------------------------------------------------------------
    # Check 3: Custom checklist items for this trade + company
    # ------------------------------------------------------------------
    project_type = exhibit.project.project_type if exhibit.project else None
    checklist_qs = ChecklistItem.objects.filter(
        company=exhibit.company,
        csi_trade=exhibit.csi_trade,
    ).prefetch_related('project_type_tags')

    checklist_items = list(checklist_qs)

    for ci in checklist_items:
        tags = list(ci.project_type_tags.all())
        # Skip if item is scoped to specific project types that don't match
        if tags and project_type and project_type not in tags:
            continue
        items.append(FinalReviewItem(
            check_type=FinalReviewItem.CheckType.CUSTOM_CHECKLIST,
            description=ci.text,
            status=FinalReviewItem.ItemStatus.WARNING,
        ))

    if not any(i.check_type == FinalReviewItem.CheckType.CUSTOM_CHECKLIST for i in items):
        items.append(FinalReviewItem(
            check_type=FinalReviewItem.CheckType.CUSTOM_CHECKLIST,
            description='No custom checklist items configured for this trade.',
            status=FinalReviewItem.ItemStatus.PASS,
        ))

    # ------------------------------------------------------------------
    # Persist — replace any previous review atomically
    # ------------------------------------------------------------------
    with transaction.atomic():
        exhibit.final_reviews.all().delete()
        review = FinalReview.objects.create(
            scope_exhibit=exhibit,
            initiated_by=user,
            status=FinalReview.Status.COMPLETED,
            completed_at=timezone.now(),
        )
        for item in items:
            item.final_review = review
        FinalReviewItem.objects.bulk_create(items)

    return review
