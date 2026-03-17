from django.contrib.auth.decorators import login_required
from django.db import models
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from exhibits.models import ScopeExhibit
from projects.models import Project

from exhibits.services import compute_section_numbering
from .forms import NoteForm
from .models import Note


def _current_trade(exhibit):
    """Return the Trade for this exhibit's project+csi_trade, or None."""
    if not exhibit.project:
        return None
    from projects.models import Trade
    try:
        return Trade.objects.get(project=exhibit.project, csi_trade=exhibit.csi_trade)
    except Trade.DoesNotExist:
        return None


def _item_numbers_for_notes(notes):
    """Build {item_pk: number_string} for all notes that reference a scope item."""
    numbers = {}
    seen_sections = set()
    for note in notes:
        if note.scope_item_id and note.scope_item.section_id not in seen_sections:
            seen_sections.add(note.scope_item.section_id)
            numbers.update(compute_section_numbering(note.scope_item.section))
    return numbers


def _get_exhibit(exhibit_pk, user):
    return get_object_or_404(ScopeExhibit, pk=exhibit_pk, company=user.company)


def _get_note(pk, user):
    return get_object_or_404(Note, pk=pk, project__company=user.company)


def _notes_for_exhibit(exhibit):
    """All notes visible in this exhibit's sidebar: primary or related trade match."""
    from projects.models import Trade
    try:
        trade = Trade.objects.get(project=exhibit.project, csi_trade=exhibit.csi_trade)
    except Trade.DoesNotExist:
        return Note.objects.none()
    return (
        Note.objects
        .filter(project=exhibit.project)
        .filter(
            models.Q(primary_trade=trade) | models.Q(related_trades=trade)
        )
        .select_related('primary_trade__csi_trade', 'created_by', 'resolved_by',
                        'scope_item__section')
        .prefetch_related('related_trades__csi_trade')
        .distinct()
        .order_by('status', '-created_at')
    )


# ---------------------------------------------------------------------------
# Note list (sidebar partial)
# ---------------------------------------------------------------------------

@login_required
def note_list(request, exhibit_pk):
    exhibit = _get_exhibit(exhibit_pk, request.user)
    notes = _notes_for_exhibit(exhibit)
    project_trades = exhibit.project.trades.select_related('csi_trade') if exhibit.project else []
    form = NoteForm(project=exhibit.project)
    return render(request, 'notes/partials/note_list.html', {
        'exhibit': exhibit,
        'notes': notes,
        'form': form,
        'project_trades': project_trades,
        'numbers': _item_numbers_for_notes(notes),
        'current_trade': _current_trade(exhibit),
    })


# ---------------------------------------------------------------------------
# Note add
# ---------------------------------------------------------------------------

@login_required
@require_POST
def note_add(request, exhibit_pk):
    exhibit = _get_exhibit(exhibit_pk, request.user)
    form = NoteForm(request.POST, project=exhibit.project)
    if form.is_valid():
        note = form.save(commit=False)
        note.project = exhibit.project
        note.created_by = request.user
        scope_item_id = request.POST.get('scope_item_id')
        if scope_item_id:
            from exhibits.models import ScopeItem
            try:
                note.scope_item = ScopeItem.objects.get(
                    pk=scope_item_id,
                    section__scope_exhibit__company=request.user.company,
                )
            except ScopeItem.DoesNotExist:
                pass
        note.save()
        form.save_m2m()
    # Always return the refreshed notes list (even on invalid — keeps UX simple)
    notes = _notes_for_exhibit(exhibit)
    fresh_form = NoteForm(project=exhibit.project)
    return render(request, 'notes/partials/note_list.html', {
        'exhibit': exhibit,
        'notes': notes,
        'form': fresh_form,
        'numbers': _item_numbers_for_notes(notes),
        'current_trade': _current_trade(exhibit),
    })


# ---------------------------------------------------------------------------
# Note resolve
# ---------------------------------------------------------------------------

@login_required
@require_POST
def note_resolve(request, pk):
    from django.http import HttpResponse
    from django.utils import timezone
    note = _get_note(pk, request.user)
    resolution = request.POST.get('resolution', '').strip()
    note.status = Note.Status.RESOLVED
    note.resolution = resolution
    note.resolved_by = request.user
    note.resolved_at = timezone.now()
    note.save(update_fields=['status', 'resolution', 'resolved_by', 'resolved_at', 'updated_at'])
    # dismiss=1 means the caller wants the element removed (open questions page)
    if request.POST.get('dismiss'):
        return HttpResponse('')
    return render(request, 'notes/partials/note_card.html', {'note': note})


# ---------------------------------------------------------------------------
# Note edit
# ---------------------------------------------------------------------------

@login_required
def note_edit(request, pk):
    note = _get_note(pk, request.user)
    if request.method == 'POST':
        form = NoteForm(request.POST, instance=note, project=note.project)
        if form.is_valid():
            form.save()
            return render(request, 'notes/partials/note_card.html', {'note': note})
    else:
        if request.GET.get('cancel'):
            return render(request, 'notes/partials/note_card.html', {'note': note})
        form = NoteForm(instance=note, project=note.project)
    return render(request, 'notes/partials/note_edit_form.html', {
        'note': note,
        'form': form,
    })


# ---------------------------------------------------------------------------
# Open questions (project-level)
# ---------------------------------------------------------------------------

@login_required
def open_questions(request, project_pk):
    from django.db.models import Q
    project = get_object_or_404(Project, pk=project_pk, company=request.user.company)
    trades = project.trades.select_related('csi_trade').order_by('csi_trade__csi_code')

    qs = (
        Note.objects
        .filter(project=project, status=Note.Status.OPEN)
        .select_related('primary_trade__csi_trade', 'created_by')
        .prefetch_related('related_trades__csi_trade')
        .order_by('-created_at')
    )

    selected_trade_pks = request.GET.getlist('trade')
    if selected_trade_pks:
        qs = qs.filter(
            Q(primary_trade__pk__in=selected_trade_pks) | Q(related_trades__pk__in=selected_trade_pks)
        ).distinct()

    form = NoteForm(project=project)
    return render(request, 'notes/open_questions.html', {
        'project': project,
        'notes': qs,
        'trades': trades,
        'selected_trade_pks': selected_trade_pks,
        'form': form,
    })


@login_required
@require_POST
def note_add_project(request, project_pk):
    project = get_object_or_404(Project, pk=project_pk, company=request.user.company)
    form = NoteForm(request.POST, project=project)
    if form.is_valid():
        note = form.save(commit=False)
        note.project = project
        note.created_by = request.user
        note.save()
        form.save_m2m()
    return redirect('notes:open_notes', project_pk=project.pk)
