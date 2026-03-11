import pytest
from django.urls import reverse

from core.factories import CSITradeFactory, CompanyFactory, PMUserFactory
from exhibits.factories import ExhibitSectionFactory, ScopeExhibitFactory
from notes.factories import NoteFactory
from projects.factories import ProjectFactory, TradeFactory

from .factories import ChecklistItemFactory, FinalReviewFactory, FinalReviewItemFactory
from .models import FinalReview, FinalReviewItem
from .services import generate_final_review


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BACKEND = 'django.contrib.auth.backends.ModelBackend'


def _login(client, user):
    user.set_password('testpass123')
    user.save(update_fields=['password'])
    client.force_login(user, backend=_BACKEND)


def _make_exhibit(user):
    project = ProjectFactory(company=user.company)
    csi = CSITradeFactory()
    trade = TradeFactory(project=project, csi_trade=csi)
    exhibit = ScopeExhibitFactory(
        company=user.company,
        project=project,
        csi_trade=csi,
        created_by=user,
        last_edited_by=user,
    )
    return exhibit, trade


# ---------------------------------------------------------------------------
# Service: generate_final_review — open notes check
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestOpenNotesCheck:
    def test_open_note_creates_warning_item(self):
        user = PMUserFactory()
        exhibit, trade = _make_exhibit(user)
        NoteFactory(
            project=exhibit.project,
            primary_trade=trade,
            status='OPEN',
            created_by=user,
        )
        review = generate_final_review(exhibit, user)
        items = list(review.items.filter(check_type=FinalReviewItem.CheckType.OPEN_NOTE))
        assert any(i.status == FinalReviewItem.ItemStatus.WARNING for i in items)

    def test_no_open_notes_creates_pass_item(self):
        user = PMUserFactory()
        exhibit, trade = _make_exhibit(user)
        # No notes created
        review = generate_final_review(exhibit, user)
        items = list(review.items.filter(check_type=FinalReviewItem.CheckType.OPEN_NOTE))
        assert any(i.status == FinalReviewItem.ItemStatus.PASS for i in items)

    def test_resolved_note_does_not_trigger_warning(self):
        user = PMUserFactory()
        exhibit, trade = _make_exhibit(user)
        NoteFactory(
            project=exhibit.project,
            primary_trade=trade,
            status='RESOLVED',
            created_by=user,
        )
        review = generate_final_review(exhibit, user)
        items = list(review.items.filter(check_type=FinalReviewItem.CheckType.OPEN_NOTE))
        assert all(i.status == FinalReviewItem.ItemStatus.PASS for i in items)


# ---------------------------------------------------------------------------
# Service: generate_final_review — cross-trade notes check
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestCrossTradeCheck:
    def test_cross_trade_open_note_creates_warning(self):
        user = PMUserFactory()
        exhibit, trade = _make_exhibit(user)

        # Note from a DIFFERENT trade that mentions this trade as related
        other_csi = CSITradeFactory()
        other_trade = TradeFactory(project=exhibit.project, csi_trade=other_csi)
        note = NoteFactory(
            project=exhibit.project,
            primary_trade=other_trade,
            status='OPEN',
            created_by=user,
        )
        note.related_trades.add(trade)

        review = generate_final_review(exhibit, user)
        items = list(review.items.filter(check_type=FinalReviewItem.CheckType.CROSS_TRADE))
        assert any(i.status == FinalReviewItem.ItemStatus.WARNING for i in items)

    def test_no_cross_trade_notes_creates_pass(self):
        user = PMUserFactory()
        exhibit, trade = _make_exhibit(user)
        review = generate_final_review(exhibit, user)
        items = list(review.items.filter(check_type=FinalReviewItem.CheckType.CROSS_TRADE))
        assert any(i.status == FinalReviewItem.ItemStatus.PASS for i in items)

    def test_primary_trade_notes_not_counted_as_cross_trade(self):
        user = PMUserFactory()
        exhibit, trade = _make_exhibit(user)
        # Note where THIS trade is primary AND related — should NOT appear as cross-trade
        note = NoteFactory(
            project=exhibit.project,
            primary_trade=trade,
            status='OPEN',
            created_by=user,
        )
        note.related_trades.add(trade)
        review = generate_final_review(exhibit, user)
        cross_items = list(
            review.items.filter(
                check_type=FinalReviewItem.CheckType.CROSS_TRADE,
                status=FinalReviewItem.ItemStatus.WARNING,
            )
        )
        assert len(cross_items) == 0


# ---------------------------------------------------------------------------
# Service: generate_final_review — custom checklist check
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestCustomChecklistCheck:
    def test_matching_checklist_item_creates_warning(self):
        user = PMUserFactory()
        exhibit, trade = _make_exhibit(user)
        ChecklistItemFactory(
            company=user.company,
            csi_trade=exhibit.csi_trade,
            created_by=user,
        )
        review = generate_final_review(exhibit, user)
        items = list(review.items.filter(check_type=FinalReviewItem.CheckType.CUSTOM_CHECKLIST))
        assert any(i.status == FinalReviewItem.ItemStatus.WARNING for i in items)

    def test_no_checklist_items_creates_pass(self):
        user = PMUserFactory()
        exhibit, trade = _make_exhibit(user)
        review = generate_final_review(exhibit, user)
        items = list(review.items.filter(check_type=FinalReviewItem.CheckType.CUSTOM_CHECKLIST))
        assert any(i.status == FinalReviewItem.ItemStatus.PASS for i in items)

    def test_checklist_item_for_other_company_not_included(self):
        user = PMUserFactory()
        exhibit, trade = _make_exhibit(user)
        other_user = PMUserFactory()  # different company
        ChecklistItemFactory(
            company=other_user.company,
            csi_trade=exhibit.csi_trade,
            created_by=other_user,
        )
        review = generate_final_review(exhibit, user)
        warning_items = list(
            review.items.filter(
                check_type=FinalReviewItem.CheckType.CUSTOM_CHECKLIST,
                status=FinalReviewItem.ItemStatus.WARNING,
            )
        )
        assert len(warning_items) == 0


# ---------------------------------------------------------------------------
# Service: re-running replaces previous review
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestReviewReplacement:
    def test_rerunning_replaces_previous_review(self):
        user = PMUserFactory()
        exhibit, trade = _make_exhibit(user)
        first_review = generate_final_review(exhibit, user)
        second_review = generate_final_review(exhibit, user)
        assert FinalReview.objects.filter(scope_exhibit=exhibit).count() == 1
        assert FinalReview.objects.filter(scope_exhibit=exhibit).first().pk == second_review.pk

    def test_review_status_is_completed(self):
        user = PMUserFactory()
        exhibit, trade = _make_exhibit(user)
        review = generate_final_review(exhibit, user)
        assert review.status == FinalReview.Status.COMPLETED
        assert review.completed_at is not None


# ---------------------------------------------------------------------------
# View: run_review
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestRunReviewView:
    def test_returns_200_and_review_panel(self, client):
        user = PMUserFactory()
        _login(client, user)
        exhibit, trade = _make_exhibit(user)
        url = reverse('reviews:run', kwargs={'exhibit_pk': exhibit.pk})
        response = client.post(url)
        assert response.status_code == 200
        assert b'review-panel' in response.content

    def test_creates_final_review_record(self, client):
        user = PMUserFactory()
        _login(client, user)
        exhibit, trade = _make_exhibit(user)
        url = reverse('reviews:run', kwargs={'exhibit_pk': exhibit.pk})
        client.post(url)
        assert FinalReview.objects.filter(scope_exhibit=exhibit).count() == 1

    def test_rejects_other_company_exhibit(self, client):
        user = PMUserFactory()
        _login(client, user)
        other_exhibit = ScopeExhibitFactory()  # different company
        url = reverse('reviews:run', kwargs={'exhibit_pk': other_exhibit.pk})
        response = client.post(url)
        assert response.status_code == 404

    def test_requires_login(self, client):
        exhibit = ScopeExhibitFactory()
        url = reverse('reviews:run', kwargs={'exhibit_pk': exhibit.pk})
        response = client.post(url)
        assert response.status_code == 302


# ---------------------------------------------------------------------------
# View: review_item_respond
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestReviewItemRespondView:
    def _make_item(self, user):
        exhibit, trade = _make_exhibit(user)
        review = FinalReviewFactory(scope_exhibit=exhibit, initiated_by=user)
        item = FinalReviewItemFactory(
            final_review=review,
            status=FinalReviewItem.ItemStatus.WARNING,
        )
        return exhibit, item

    def test_saves_pm_response(self, client):
        user = PMUserFactory()
        _login(client, user)
        exhibit, item = self._make_item(user)
        url = reverse('reviews:item_respond', kwargs={'exhibit_pk': exhibit.pk, 'item_pk': item.pk})
        response = client.post(url, {'pm_response': 'Confirmed with sub.'})
        assert response.status_code == 200
        item.refresh_from_db()
        assert item.pm_response == 'Confirmed with sub.'
        assert item.reviewed_at is not None

    def test_clears_response_when_empty(self, client):
        user = PMUserFactory()
        _login(client, user)
        exhibit, item = self._make_item(user)
        item.pm_response = 'Old note'
        item.save()
        url = reverse('reviews:item_respond', kwargs={'exhibit_pk': exhibit.pk, 'item_pk': item.pk})
        client.post(url, {'pm_response': ''})
        item.refresh_from_db()
        assert item.pm_response == ''
        assert item.reviewed_at is None

    def test_rejects_other_company_exhibit(self, client):
        user = PMUserFactory()
        _login(client, user)
        other_user = PMUserFactory()
        other_exhibit, _ = _make_exhibit(other_user)
        other_review = FinalReviewFactory(scope_exhibit=other_exhibit, initiated_by=other_user)
        other_item = FinalReviewItemFactory(final_review=other_review)
        url = reverse('reviews:item_respond', kwargs={'exhibit_pk': other_exhibit.pk, 'item_pk': other_item.pk})
        response = client.post(url, {'pm_response': 'hack'})
        assert response.status_code == 404
