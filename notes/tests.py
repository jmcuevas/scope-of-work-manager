import pytest
from django.urls import reverse
from django.utils import timezone

from core.factories import CompanyFactory, CSITradeFactory, PMUserFactory
from exhibits.factories import ScopeExhibitFactory
from notes.factories import NoteFactory
from projects.factories import ProjectFactory, TradeFactory

from .models import Note


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BACKEND = 'django.contrib.auth.backends.ModelBackend'


def _login(client, user):
    user.set_password('testpass123')
    user.save(update_fields=['password'])
    client.force_login(user, backend=_BACKEND)


def _make_project_with_trades(user, n=2):
    """Return a project + list of n trades, all scoped to user's company."""
    project = ProjectFactory(company=user.company)
    trades = [TradeFactory(project=project, csi_trade=CSITradeFactory()) for _ in range(n)]
    return project, trades


def _make_exhibit_for_trade(user, project, trade):
    return ScopeExhibitFactory(
        company=user.company,
        project=project,
        csi_trade=trade.csi_trade,
        created_by=user,
        last_edited_by=user,
    )


# ---------------------------------------------------------------------------
# Note creation
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_note_add_creates_note(client):
    user = PMUserFactory()
    project, trades = _make_project_with_trades(user)
    exhibit = _make_exhibit_for_trade(user, project, trades[0])
    _login(client, user)

    url = reverse('notes:note_add', kwargs={'exhibit_pk': exhibit.pk})
    response = client.post(url, {
        'text': 'Caulking is in glazing scope.',
        'note_type': Note.NoteType.SCOPE_CLARIFICATION,
        'primary_trade': trades[0].pk,
        'source': 'OAC meeting',
    })

    assert response.status_code == 200
    assert Note.objects.filter(text='Caulking is in glazing scope.').exists()


@pytest.mark.django_db
def test_note_add_saves_related_trades(client):
    user = PMUserFactory()
    project, trades = _make_project_with_trades(user)
    exhibit = _make_exhibit_for_trade(user, project, trades[0])
    _login(client, user)

    url = reverse('notes:note_add', kwargs={'exhibit_pk': exhibit.pk})
    client.post(url, {
        'text': 'Who carries dumpsters?',
        'note_type': Note.NoteType.OPEN_QUESTION,
        'primary_trade': trades[0].pk,
        'related_trades': [trades[1].pk],
    })

    note = Note.objects.get(text='Who carries dumpsters?')
    assert trades[1] in note.related_trades.all()


@pytest.mark.django_db
def test_note_add_sets_project_and_user(client):
    user = PMUserFactory()
    project, trades = _make_project_with_trades(user)
    exhibit = _make_exhibit_for_trade(user, project, trades[0])
    _login(client, user)

    url = reverse('notes:note_add', kwargs={'exhibit_pk': exhibit.pk})
    client.post(url, {
        'text': 'Test note.',
        'note_type': Note.NoteType.MEANS_METHODS,
        'primary_trade': trades[0].pk,
    })

    note = Note.objects.get(text='Test note.')
    assert note.project == project
    assert note.created_by == user


@pytest.mark.django_db
def test_note_add_requires_login(client):
    exhibit = ScopeExhibitFactory()
    url = reverse('notes:note_add', kwargs={'exhibit_pk': exhibit.pk})
    response = client.post(url, {'text': 'x', 'note_type': Note.NoteType.MEANS_METHODS})
    assert response.status_code == 302
    assert '/accounts/' in response['Location']


# ---------------------------------------------------------------------------
# Cross-trade visibility
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_note_appears_in_related_trade_sidebar(client):
    """Note tagged with related_trade=trade_b appears in trade_b's note_list."""
    user = PMUserFactory()
    project, trades = _make_project_with_trades(user)
    trade_a, trade_b = trades[0], trades[1]
    exhibit_b = _make_exhibit_for_trade(user, project, trade_b)

    # Create note primarily for trade_a, related to trade_b
    note = NoteFactory(
        project=project,
        primary_trade=trade_a,
        created_by=user,
    )
    note.related_trades.add(trade_b)

    _login(client, user)
    url = reverse('notes:note_list', kwargs={'exhibit_pk': exhibit_b.pk})
    response = client.get(url)

    assert response.status_code == 200
    assert note.text.encode() in response.content


@pytest.mark.django_db
def test_note_appears_in_primary_trade_sidebar(client):
    """Note with primary_trade=trade_a appears in trade_a's note_list."""
    user = PMUserFactory()
    project, trades = _make_project_with_trades(user)
    exhibit_a = _make_exhibit_for_trade(user, project, trades[0])

    note = NoteFactory(project=project, primary_trade=trades[0], created_by=user)

    _login(client, user)
    url = reverse('notes:note_list', kwargs={'exhibit_pk': exhibit_a.pk})
    response = client.get(url)

    assert response.status_code == 200
    assert note.text.encode() in response.content


@pytest.mark.django_db
def test_unrelated_note_not_in_sidebar(client):
    """Note for a different trade does not appear in this exhibit's sidebar."""
    user = PMUserFactory()
    project, trades = _make_project_with_trades(user, n=3)
    exhibit_a = _make_exhibit_for_trade(user, project, trades[0])

    # Note for trade_b only — no relation to trade_a
    other_note = NoteFactory(project=project, primary_trade=trades[2], created_by=user)

    _login(client, user)
    url = reverse('notes:note_list', kwargs={'exhibit_pk': exhibit_a.pk})
    response = client.get(url)

    assert other_note.text.encode() not in response.content


# ---------------------------------------------------------------------------
# Company isolation
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_note_list_company_isolation(client):
    """User cannot access note_list for another company's exhibit."""
    user = PMUserFactory()
    other_exhibit = ScopeExhibitFactory()  # different company
    _login(client, user)

    url = reverse('notes:note_list', kwargs={'exhibit_pk': other_exhibit.pk})
    response = client.get(url)

    assert response.status_code == 404


@pytest.mark.django_db
def test_note_resolve_company_isolation(client):
    """User cannot resolve a note from another company's project."""
    user = PMUserFactory()
    other_project = ProjectFactory()  # different company
    other_note = NoteFactory(project=other_project)
    _login(client, user)

    url = reverse('notes:note_resolve', kwargs={'pk': other_note.pk})
    response = client.post(url, {'resolution': 'hacked'})

    assert response.status_code == 404
    other_note.refresh_from_db()
    assert other_note.status == Note.Status.OPEN


# ---------------------------------------------------------------------------
# Note resolution
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_note_resolve_sets_fields(client):
    user = PMUserFactory()
    project, trades = _make_project_with_trades(user)
    note = NoteFactory(project=project, primary_trade=trades[0], created_by=user)
    _login(client, user)

    url = reverse('notes:note_resolve', kwargs={'pk': note.pk})
    response = client.post(url, {'resolution': 'Decided in OAC: GC carries dumpsters.'})

    assert response.status_code == 200
    note.refresh_from_db()
    assert note.status == Note.Status.RESOLVED
    assert note.resolution == 'Decided in OAC: GC carries dumpsters.'
    assert note.resolved_by == user
    assert note.resolved_at is not None


@pytest.mark.django_db
def test_note_resolve_without_resolution_text(client):
    """Resolution text is optional — resolve should still succeed."""
    user = PMUserFactory()
    project, trades = _make_project_with_trades(user)
    note = NoteFactory(project=project, primary_trade=trades[0], created_by=user)
    _login(client, user)

    url = reverse('notes:note_resolve', kwargs={'pk': note.pk})
    client.post(url, {'resolution': ''})

    note.refresh_from_db()
    assert note.status == Note.Status.RESOLVED


@pytest.mark.django_db
def test_note_resolve_dismiss_returns_empty(client):
    """dismiss=1 causes resolve to return empty response (for open questions page)."""
    user = PMUserFactory()
    project, trades = _make_project_with_trades(user)
    note = NoteFactory(project=project, primary_trade=trades[0], created_by=user)
    _login(client, user)

    url = reverse('notes:note_resolve', kwargs={'pk': note.pk})
    response = client.post(url, {'resolution': '', 'dismiss': '1'})

    assert response.status_code == 200
    assert response.content == b''


# ---------------------------------------------------------------------------
# Open questions
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_open_questions_view_only_shows_open_questions(client):
    user = PMUserFactory()
    project, trades = _make_project_with_trades(user)

    oq = NoteFactory(
        project=project, primary_trade=trades[0], created_by=user,
        note_type=Note.NoteType.OPEN_QUESTION, status=Note.Status.OPEN,
    )
    clarification = NoteFactory(
        project=project, primary_trade=trades[0], created_by=user,
        note_type=Note.NoteType.SCOPE_CLARIFICATION, status=Note.Status.OPEN,
    )
    resolved_oq = NoteFactory(
        project=project, primary_trade=trades[0], created_by=user,
        note_type=Note.NoteType.OPEN_QUESTION, status=Note.Status.RESOLVED,
    )

    _login(client, user)
    url = reverse('notes:open_questions', kwargs={'project_pk': project.pk})
    response = client.get(url)

    assert response.status_code == 200
    assert oq.text.encode() in response.content
    assert clarification.text.encode() not in response.content
    assert resolved_oq.text.encode() not in response.content


@pytest.mark.django_db
def test_open_questions_company_isolation(client):
    user = PMUserFactory()
    other_project = ProjectFactory()
    _login(client, user)

    url = reverse('notes:open_questions', kwargs={'project_pk': other_project.pk})
    response = client.get(url)

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Dashboard open question count
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_dashboard_shows_open_question_badge(client):
    user = PMUserFactory()
    project, trades = _make_project_with_trades(user)
    NoteFactory(
        project=project, primary_trade=trades[0], created_by=user,
        note_type=Note.NoteType.OPEN_QUESTION, status=Note.Status.OPEN,
    )
    _login(client, user)

    url = reverse('projects:dashboard', kwargs={'pk': project.pk})
    response = client.get(url)

    assert response.status_code == 200
    assert b'Open Questions' in response.content


@pytest.mark.django_db
def test_dashboard_no_badge_when_no_open_questions(client):
    user = PMUserFactory()
    project, trades = _make_project_with_trades(user)
    # Only a resolved open question — no badge should show
    NoteFactory(
        project=project, primary_trade=trades[0], created_by=user,
        note_type=Note.NoteType.OPEN_QUESTION, status=Note.Status.RESOLVED,
    )
    _login(client, user)

    url = reverse('projects:dashboard', kwargs={'pk': project.pk})
    response = client.get(url)

    assert b'Open Questions' not in response.content


@pytest.mark.django_db
def test_dashboard_open_question_count_matches_db(client):
    user = PMUserFactory()
    project, trades = _make_project_with_trades(user)
    for _ in range(3):
        NoteFactory(
            project=project, primary_trade=trades[0], created_by=user,
            note_type=Note.NoteType.OPEN_QUESTION, status=Note.Status.OPEN,
        )
    _login(client, user)

    url = reverse('projects:dashboard', kwargs={'pk': project.pk})
    response = client.get(url)

    assert b'3' in response.content


# ---------------------------------------------------------------------------
# Auth guards
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_note_list_requires_login(client):
    exhibit = ScopeExhibitFactory()
    url = reverse('notes:note_list', kwargs={'exhibit_pk': exhibit.pk})
    response = client.get(url)
    assert response.status_code == 302
    assert '/accounts/' in response['Location']


@pytest.mark.django_db
def test_note_resolve_requires_login(client):
    note = NoteFactory()
    url = reverse('notes:note_resolve', kwargs={'pk': note.pk})
    response = client.post(url, {'resolution': ''})
    assert response.status_code == 302
    assert '/accounts/' in response['Location']


@pytest.mark.django_db
def test_open_questions_requires_login(client):
    project = ProjectFactory()
    url = reverse('notes:open_questions', kwargs={'project_pk': project.pk})
    response = client.get(url)
    assert response.status_code == 302
    assert '/accounts/' in response['Location']
