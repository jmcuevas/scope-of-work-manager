from django.contrib.auth.decorators import login_required
from django.db.models import F
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from ai_services.services import AIDisabledError, AIServiceError, chat_with_exhibit, check_exhibit_completeness, convert_note_to_scope, expand_scope_item, generate_chat_title, generate_scope_from_description, generate_scope_item, rewrite_scope_item, rewrite_section_items, section_ai_action
from django.conf import settings
from django.utils import timezone
from notes.forms import NoteForm
from notes.models import Note
from projects.models import Project, Trade

from .models import ExhibitSection, ScopeExhibit, ScopeItem
from .services import accept_ai_item, accept_all_pending, clone_exhibit, compute_exhibit_numbering, compute_section_numbering, create_blank_exhibit, flatten_section_items, indent_item, outdent_item, reject_ai_item, reject_all_pending, save_as_template


def _get_trade(project_pk, trade_pk, user):
    """Return (project, trade) both scoped to user's company."""
    project = get_object_or_404(Project, pk=project_pk, company=user.company)
    trade = get_object_or_404(Trade, pk=trade_pk, project=project)
    return project, trade


def _company_exhibit_or_404(pk, user):
    return get_object_or_404(ScopeExhibit, pk=pk, company=user.company)


# ---------------------------------------------------------------------------
# Entry flow
# ---------------------------------------------------------------------------

@login_required
def trade_scope_open(request, project_pk, trade_pk):
    project, trade = _get_trade(project_pk, trade_pk, request.user)
    exhibit = ScopeExhibit.objects.filter(
        project=project,
        csi_trade=trade.csi_trade,
        company=request.user.company,
    ).first()
    if exhibit:
        return redirect('exhibits:editor', pk=exhibit.pk)
    return redirect('exhibits:template_picker', project_pk=project_pk, trade_pk=trade_pk)


@login_required
def template_picker(request, project_pk, trade_pk):
    project, trade = _get_trade(project_pk, trade_pk, request.user)

    company = request.user.company
    csi_trade = trade.csi_trade

    templates = list(
        ScopeExhibit.objects.filter(
            company=company,
            csi_trade=csi_trade,
            is_template=True,
        ).select_related('project__project_type', 'created_by')
        .prefetch_related('sections')
    )

    past_exhibits = list(
        ScopeExhibit.objects.filter(
            company=company,
            csi_trade=csi_trade,
            is_template=False,
            status=ScopeExhibit.Status.FINALIZED,
        ).exclude(project=project)
        .select_related('project__project_type', 'created_by')
        .prefetch_related('sections')
        .order_by('-updated_at')
    )

    # Sort past exhibits: exact project type match first
    project_type_id = project.project_type_id
    past_exhibits.sort(
        key=lambda e: (0 if e.project and e.project.project_type_id == project_type_id else 1)
    )

    return render(request, 'exhibits/picker.html', {
        'project': project,
        'trade': trade,
        'templates': templates,
        'past_exhibits': past_exhibits,
    })


@login_required
@require_POST
def exhibit_start(request, project_pk, trade_pk):
    project, trade = _get_trade(project_pk, trade_pk, request.user)
    source = request.POST.get('source', 'blank')

    if source == 'blank':
        exhibit = create_blank_exhibit(trade, request.user)
    else:
        source_exhibit = _company_exhibit_or_404(source, request.user)
        exhibit = clone_exhibit(source_exhibit, trade, request.user)

    if trade.status == Trade.Status.NOT_STARTED:
        trade.status = Trade.Status.DRAFTING
        trade.save(update_fields=['status', 'updated_at'])

    return redirect('exhibits:editor', pk=exhibit.pk)


# ---------------------------------------------------------------------------
# Editor
# ---------------------------------------------------------------------------

@login_required
def exhibit_editor(request, pk):
    exhibit = _company_exhibit_or_404(pk, request.user)

    if request.method == 'POST':
        exhibit.scope_description = request.POST.get('scope_description', '')
        exhibit.last_edited_by = request.user
        exhibit.save(update_fields=['scope_description', 'last_edited_by', 'updated_at'])
        return redirect('exhibits:editor', pk=exhibit.pk)

    sections = list(exhibit.sections.order_by('order'))
    numbers, section_letters = compute_exhibit_numbering(exhibit)
    items_by_section = {}
    for section in sections:
        items_by_section[section.pk] = flatten_section_items(section)

    # Notes sidebar context
    notes = Note.objects.none()
    note_form = None
    current_trade = None
    if exhibit.project:
        try:
            current_trade = Trade.objects.get(project=exhibit.project, csi_trade=exhibit.csi_trade)
            from django.db.models import Q
            notes = (
                Note.objects
                .filter(project=exhibit.project)
                .filter(Q(primary_trade=current_trade) | Q(related_trades=current_trade))
                .select_related('primary_trade__csi_trade', 'created_by', 'resolved_by')
                .prefetch_related('related_trades__csi_trade')
                .distinct()
                .order_by('status', '-created_at')
            )
        except Trade.DoesNotExist:
            pass
        note_form = NoteForm(project=exhibit.project)

    latest_review = (
        exhibit.final_reviews
        .prefetch_related('items')
        .first()
    )

    return render(request, 'exhibits/editor.html', {
        'exhibit': exhibit,
        'sections': sections,
        'numbers': numbers,
        'section_letters': section_letters,
        'items_by_section': items_by_section,
        'notes': notes,
        'form': note_form,
        'current_trade': current_trade,
        'ai_enabled': settings.AI_ENABLED,
        'latest_review': latest_review,
        'item_note_counts': _item_note_counts(exhibit),
    })


# ---------------------------------------------------------------------------
# Section CRUD (HTMX — all return section_list partial)
# ---------------------------------------------------------------------------

def _item_note_counts(exhibit):
    """Return {item_pk: count} for all notes linked to items in this exhibit."""
    from notes.models import Note
    from django.db.models import Count
    rows = (
        Note.objects
        .filter(scope_item__section__scope_exhibit=exhibit)
        .values('scope_item_id')
        .annotate(count=Count('id'))
    )
    return {row['scope_item_id']: row['count'] for row in rows}


def _section_list_response(request, exhibit):
    sections = list(exhibit.sections.order_by('order'))
    numbers, section_letters = compute_exhibit_numbering(exhibit)
    items_by_section = {}
    for section in sections:
        items_by_section[section.pk] = flatten_section_items(section)
    return render(request, 'exhibits/partials/section_list.html', {
        'exhibit': exhibit,
        'sections': sections,
        'numbers': numbers,
        'section_letters': section_letters,
        'items_by_section': items_by_section,
        'ai_enabled': settings.AI_ENABLED,
        'item_note_counts': _item_note_counts(exhibit),
    })


@login_required
@require_POST
def section_add(request, pk):
    exhibit = _company_exhibit_or_404(pk, request.user)
    last_order = exhibit.sections.order_by('-order').values_list('order', flat=True).first() or -1
    ExhibitSection.objects.create(
        scope_exhibit=exhibit,
        name='New Section',
        order=last_order + 1,
    )
    return _section_list_response(request, exhibit)


@login_required
@require_POST
def section_rename(request, pk, section_pk):
    exhibit = _company_exhibit_or_404(pk, request.user)
    section = get_object_or_404(ExhibitSection, pk=section_pk, scope_exhibit=exhibit)
    name = request.POST.get('name', '').strip()
    if name:
        section.name = name
        section.save(update_fields=['name', 'updated_at'])
    return _section_list_response(request, exhibit)


@login_required
@require_POST
def section_delete(request, pk, section_pk):
    exhibit = _company_exhibit_or_404(pk, request.user)
    section = get_object_or_404(ExhibitSection, pk=section_pk, scope_exhibit=exhibit)
    section.delete()
    return _section_list_response(request, exhibit)


@login_required
@require_POST
def section_move(request, pk, section_pk):
    exhibit = _company_exhibit_or_404(pk, request.user)
    section = get_object_or_404(ExhibitSection, pk=section_pk, scope_exhibit=exhibit)
    direction = request.POST.get('direction')

    sections = list(exhibit.sections.order_by('order'))
    idx = next(i for i, s in enumerate(sections) if s.pk == section.pk)

    if direction == 'up' and idx > 0:
        neighbor = sections[idx - 1]
    elif direction == 'down' and idx < len(sections) - 1:
        neighbor = sections[idx + 1]
    else:
        return _section_list_response(request, exhibit)

    section.order, neighbor.order = neighbor.order, section.order
    ExhibitSection.objects.bulk_update([section, neighbor], ['order'])

    return _section_list_response(request, exhibit)


# ---------------------------------------------------------------------------
# Item CRUD (HTMX — target is item list within a section)
# ---------------------------------------------------------------------------

def _item_list_response(request, exhibit, section, edit_item_pk=None):
    items = flatten_section_items(section)
    numbers, _section_letters = compute_exhibit_numbering(exhibit)
    return render(request, 'exhibits/partials/item_list.html', {
        'exhibit': exhibit,
        'section': section,
        'items': items,
        'numbers': numbers,
        'item_note_counts': _item_note_counts(exhibit),
        'edit_item_pk': edit_item_pk,
    })


def _collect_descendant_ids(item):
    ids = [item.pk]
    for child in item.children.all():
        ids.extend(_collect_descendant_ids(child))
    return ids


@login_required
@require_POST
def item_add(request, pk, section_pk):
    exhibit = _company_exhibit_or_404(pk, request.user)
    section = get_object_or_404(ExhibitSection, pk=section_pk, scope_exhibit=exhibit)
    text = request.POST.get('text', '').strip()
    if not text:
        return _item_list_response(request, exhibit, section)

    from .services import parse_pasted_items, bulk_add_items
    parsed = parse_pasted_items(text)

    if len(parsed) > 1:
        bulk_add_items(section, parsed, request.user)
        response = _item_list_response(request, exhibit, section)
        response['HX-Trigger'] = 'pendingChanged'
        return response

    # Single item — current behavior (no pending review)
    last = section.items.order_by('-order').values_list('order', flat=True).first()
    last_order = last if last is not None else -1
    ScopeItem.objects.create(
        section=section,
        text=parsed[0]['text'] if parsed else text,
        level=0,
        parent=None,
        order=last_order + 1,
        created_by=request.user,
    )
    return _item_list_response(request, exhibit, section)


@login_required
def item_edit(request, pk, section_pk, item_pk):
    exhibit = _company_exhibit_or_404(pk, request.user)
    section = get_object_or_404(ExhibitSection, pk=section_pk, scope_exhibit=exhibit)
    item = get_object_or_404(ScopeItem, pk=item_pk, section=section)

    if request.method == 'POST':
        from django.http import HttpResponse
        text = request.POST.get('text', '').strip()
        if not text:
            item.delete()
            return HttpResponse('')
        item.text = text
        item.save(update_fields=['text', 'updated_at'])
        numbers, _sl = compute_exhibit_numbering(exhibit)
        return render(request, 'exhibits/partials/item.html', {
            'exhibit': exhibit,
            'section': section,
            'item': item,
            'numbers': numbers,
        })

    # GET — show edit form
    numbers, _sl = compute_exhibit_numbering(exhibit)
    return render(request, 'exhibits/partials/item_form.html', {
        'exhibit': exhibit,
        'section': section,
        'item': item,
        'numbers': numbers,
    })


@login_required
@require_POST
def item_delete(request, pk, section_pk, item_pk):
    exhibit = _company_exhibit_or_404(pk, request.user)
    section = get_object_or_404(ExhibitSection, pk=section_pk, scope_exhibit=exhibit)
    item = get_object_or_404(ScopeItem, pk=item_pk, section=section)
    ScopeItem.objects.filter(pk__in=_collect_descendant_ids(item)).delete()
    return _item_list_response(request, exhibit, section)


@login_required
@require_POST
def item_accept_ai(request, pk, section_pk, item_pk):
    exhibit = _company_exhibit_or_404(pk, request.user)
    section = get_object_or_404(ExhibitSection, pk=section_pk, scope_exhibit=exhibit)
    item = get_object_or_404(ScopeItem, pk=item_pk, section=section)
    accept_ai_item(item)
    response = _item_list_response(request, exhibit, section)
    response['HX-Trigger'] = 'pendingChanged'
    return response


@login_required
@require_POST
def item_reject_ai(request, pk, section_pk, item_pk):
    exhibit = _company_exhibit_or_404(pk, request.user)
    section = get_object_or_404(ExhibitSection, pk=section_pk, scope_exhibit=exhibit)
    item = get_object_or_404(ScopeItem, pk=item_pk, section=section)
    reject_ai_item(item)
    response = _item_list_response(request, exhibit, section)
    response['HX-Trigger'] = 'pendingChanged'
    return response


# ---------------------------------------------------------------------------
# Item hierarchy — stubs (implemented in subsequent steps)
# ---------------------------------------------------------------------------

@login_required
@require_POST
def item_move(request, pk, section_pk, item_pk, direction):
    exhibit = _company_exhibit_or_404(pk, request.user)
    section = get_object_or_404(ExhibitSection, pk=section_pk, scope_exhibit=exhibit)
    item = get_object_or_404(ScopeItem, pk=item_pk, section=section)

    siblings = list(
        ScopeItem.objects.filter(section=section, parent=item.parent).order_by('order')
    )
    idx = next(i for i, s in enumerate(siblings) if s.pk == item.pk)

    if direction == 'up' and idx > 0:
        siblings[idx - 1], siblings[idx] = siblings[idx], siblings[idx - 1]
    elif direction == 'down' and idx < len(siblings) - 1:
        siblings[idx], siblings[idx + 1] = siblings[idx + 1], siblings[idx]
    else:
        return _item_list_response(request, exhibit, section)

    for i, sibling in enumerate(siblings):
        sibling.order = i
    ScopeItem.objects.bulk_update(siblings, ['order'])

    return _item_list_response(request, exhibit, section)
@login_required
@require_POST
def item_indent(request, pk, section_pk, item_pk):
    exhibit = _company_exhibit_or_404(pk, request.user)
    section = get_object_or_404(ExhibitSection, pk=section_pk, scope_exhibit=exhibit)
    item = get_object_or_404(ScopeItem, pk=item_pk, section=section)
    indent_item(item)
    return _item_list_response(request, exhibit, section)


@login_required
@require_POST
def item_outdent(request, pk, section_pk, item_pk):
    exhibit = _company_exhibit_or_404(pk, request.user)
    section = get_object_or_404(ExhibitSection, pk=section_pk, scope_exhibit=exhibit)
    item = get_object_or_404(ScopeItem, pk=item_pk, section=section)
    outdent_item(item)
    return _item_list_response(request, exhibit, section)


@login_required
@require_POST
def item_insert_below(request, pk, section_pk, item_pk):
    exhibit = _company_exhibit_or_404(pk, request.user)
    section = get_object_or_404(ExhibitSection, pk=section_pk, scope_exhibit=exhibit)
    item = get_object_or_404(ScopeItem, pk=item_pk, section=section)

    # Save current item text before inserting
    text = request.POST.get('text', '').strip()
    if text:
        item.text = text
        item.save(update_fields=['text', 'updated_at'])

    # Shift all subsequent items down to make room
    ScopeItem.objects.filter(section=section, order__gt=item.order).update(order=F('order') + 1)

    # Insert new blank item immediately after, inheriting level and parent
    new_item = ScopeItem.objects.create(
        section=section,
        text='',
        level=item.level,
        parent=item.parent,
        order=item.order + 1,
        created_by=request.user,
    )

    return _item_list_response(request, exhibit, section, edit_item_pk=new_item.pk)


# ---------------------------------------------------------------------------
# Pending banner (AI review)
# ---------------------------------------------------------------------------

@login_required
def pending_banner(request, pk):
    exhibit = _company_exhibit_or_404(pk, request.user)
    pending_count = ScopeItem.objects.filter(
        section__scope_exhibit=exhibit,
        is_pending_review=True,
    ).count()
    return render(request, 'exhibits/partials/pending_banner.html', {
        'exhibit': exhibit,
        'pending_count': pending_count,
    })


@login_required
@require_POST
def accept_all_pending_view(request, pk):
    exhibit = _company_exhibit_or_404(pk, request.user)
    accept_all_pending(exhibit)
    response = _section_list_response(request, exhibit)
    response['HX-Trigger'] = 'pendingChanged'
    return response


@login_required
@require_POST
def reject_all_pending_view(request, pk):
    exhibit = _company_exhibit_or_404(pk, request.user)
    reject_all_pending(exhibit)
    response = _section_list_response(request, exhibit)
    response['HX-Trigger'] = 'pendingChanged'
    return response


@login_required
@require_POST
def exhibit_save_as_template(request, pk):
    exhibit = _company_exhibit_or_404(pk, request.user)
    save_as_template(exhibit, request.user)
    from django.contrib import messages
    messages.success(request, 'Saved as template. It will appear in the template picker for this trade.')
    return redirect('exhibits:editor', pk=exhibit.pk)
@login_required
@require_POST
def exhibit_update_status(request, pk):
    exhibit = _company_exhibit_or_404(pk, request.user)
    new_status = request.POST.get('status', '').strip()

    valid = [s.value for s in ScopeExhibit.Status]
    if new_status not in valid:
        return redirect('exhibits:editor', pk=exhibit.pk)

    exhibit.status = new_status
    exhibit.last_edited_by = request.user
    exhibit.save(update_fields=['status', 'last_edited_by', 'updated_at'])

    # Sync trade status (never regress)
    if exhibit.project:
        from projects.models import Trade
        trade = Trade.objects.filter(
            project=exhibit.project,
            csi_trade=exhibit.csi_trade,
        ).first()
        if trade:
            STATUS_SYNC = {
                ScopeExhibit.Status.READY_FOR_BID: Trade.Status.OUT_TO_BID,
                ScopeExhibit.Status.FINALIZED: Trade.Status.SUBCONTRACTOR_APPROVED,
            }
            trade_status_order = [
                Trade.Status.NOT_STARTED,
                Trade.Status.DRAFTING,
                Trade.Status.OUT_TO_BID,
                Trade.Status.BIDS_RECEIVED,
                Trade.Status.OWNER_REVIEW,
                Trade.Status.SUBCONTRACTOR_APPROVED,
            ]
            target_trade_status = STATUS_SYNC.get(new_status)
            if target_trade_status:
                current_idx = trade_status_order.index(trade.status)
                target_idx = trade_status_order.index(target_trade_status)
                if target_idx > current_idx:
                    trade.status = target_trade_status
                    trade.save(update_fields=['status', 'updated_at'])

    return redirect('exhibits:editor', pk=exhibit.pk)


# ---------------------------------------------------------------------------
# AI: Per-item rewrite and expand
# ---------------------------------------------------------------------------

@login_required
@require_POST
def item_rewrite(request, pk, section_pk, item_pk):
    exhibit = _company_exhibit_or_404(pk, request.user)
    section = get_object_or_404(ExhibitSection, pk=section_pk, scope_exhibit=exhibit)
    item = get_object_or_404(ScopeItem, pk=item_pk, section=section)

    instruction = request.POST.get('instruction', '').strip()
    try:
        proposed_text = rewrite_scope_item(item, exhibit, instruction=instruction)
    except (AIDisabledError, AIServiceError):
        proposed_text = None

    if proposed_text:
        item.pending_original_text = item.text
        item.text = proposed_text
        item.is_pending_review = True
        item.is_ai_generated = True
        item.save(update_fields=['text', 'pending_original_text', 'is_pending_review', 'is_ai_generated', 'updated_at'])

    numbers, _sl = compute_exhibit_numbering(exhibit)
    response = render(request, 'exhibits/partials/item.html', {
        'exhibit': exhibit,
        'section': section,
        'item': item,
        'numbers': numbers,
        'item_note_counts': _item_note_counts(exhibit),
        'ai_enabled': settings.AI_ENABLED,
    })
    if proposed_text:
        response['HX-Trigger'] = 'pendingChanged'
    return response


@login_required
@require_POST
def item_expand(request, pk, section_pk, item_pk):
    exhibit = _company_exhibit_or_404(pk, request.user)
    section = get_object_or_404(ExhibitSection, pk=section_pk, scope_exhibit=exhibit)
    item = get_object_or_404(ScopeItem, pk=item_pk, section=section)

    try:
        child_items = expand_scope_item(item, exhibit)
    except (AIDisabledError, AIServiceError):
        child_items = None

    if child_items:
        last = (
            ScopeItem.objects.filter(section=section, parent=item)
            .order_by('-order')
            .values_list('order', flat=True)
            .first()
        )
        next_order = (last + 1) if last is not None else 0
        ScopeItem.objects.bulk_create([
            ScopeItem(
                section=section,
                parent=item,
                level=entry['level'],
                text=entry['text'],
                order=next_order + i,
                is_ai_generated=True,
                is_pending_review=True,
                created_by=request.user,
            )
            for i, entry in enumerate(child_items)
        ])

    response = _item_list_response(request, exhibit, section)
    if child_items:
        response['HX-Trigger'] = 'pendingChanged'
    return response


# ---------------------------------------------------------------------------
# AI: Section-level AI action (unified — add, edit, delete based on prompt)
# ---------------------------------------------------------------------------

@login_required
@require_POST
def section_ai(request, pk, section_pk):
    """Handle a free-form AI instruction scoped to a single section."""
    exhibit = _company_exhibit_or_404(pk, request.user)
    section = get_object_or_404(ExhibitSection, pk=section_pk, scope_exhibit=exhibit)

    instruction = request.POST.get('instruction', '').strip()
    if not instruction:
        return _item_list_response(request, exhibit, section)

    try:
        changes = section_ai_action(section, exhibit, instruction)
    except (AIDisabledError, AIServiceError):
        changes = None

    if changes:
        applied, _ = _apply_proposed_changes(exhibit, changes, request.user)
        if applied:
            response = _item_list_response(request, exhibit, section)
            response['HX-Trigger'] = 'pendingChanged'
            return response

    return _item_list_response(request, exhibit, section)


# ---------------------------------------------------------------------------
# AI: Bulk section rewrite (kept for direct API use)
# ---------------------------------------------------------------------------

@login_required
@require_POST
def section_rewrite(request, pk, section_pk):
    exhibit = _company_exhibit_or_404(pk, request.user)
    section = get_object_or_404(ExhibitSection, pk=section_pk, scope_exhibit=exhibit)

    instruction = request.POST.get('instruction', '').strip()
    if not instruction:
        return _item_list_response(request, exhibit, section)

    try:
        rewrites = rewrite_section_items(section, exhibit, instruction)
    except (AIDisabledError, AIServiceError):
        rewrites = None

    if rewrites:
        for entry in rewrites:
            try:
                item = ScopeItem.objects.get(pk=entry['pk'], section=section)
                item.pending_original_text = item.text
                item.text = entry['exhibit_text']
                item.is_pending_review = True
                item.is_ai_generated = True
                item.save(update_fields=[
                    'text', 'pending_original_text',
                    'is_pending_review', 'is_ai_generated', 'updated_at',
                ])
            except ScopeItem.DoesNotExist:
                continue

    response = _item_list_response(request, exhibit, section)
    if rewrites:
        response['HX-Trigger'] = 'pendingChanged'
    return response


# ---------------------------------------------------------------------------
# AI: Note-to-scope conversion
# ---------------------------------------------------------------------------

@login_required
@require_POST
def note_to_scope_ai(request, pk, note_pk):
    """Convert a note to a scope item using AI, with overlap check."""
    exhibit = _company_exhibit_or_404(pk, request.user)
    note = get_object_or_404(
        Note, pk=note_pk, project=exhibit.project, project__company=request.user.company,
    )

    if note.status != Note.Status.OPEN:
        from django.http import HttpResponse
        return HttpResponse(
            '<div class="text-xs text-red-500 p-2">This note is already resolved.</div>'
        )

    # edit_item_pk = rewrite an existing item incorporating the note (used by "Edit Existing Item")
    edit_item_pk = request.POST.get('edit_item_pk')
    if edit_item_pk:
        try:
            item = ScopeItem.objects.get(pk=edit_item_pk, section__scope_exhibit=exhibit)
        except ScopeItem.DoesNotExist:
            from django.http import HttpResponse
            return HttpResponse(
                '<div class="text-xs text-red-500 p-2">Item not found.</div>'
            )
        instruction = f'Incorporate this note into the item: {note.text}'
        if note.resolution:
            instruction += f' (Resolution: {note.resolution})'
        try:
            proposed_text = rewrite_scope_item(item, exhibit, instruction=instruction)
        except (AIDisabledError, AIServiceError):
            proposed_text = None

        if proposed_text:
            item.pending_original_text = item.text
            item.text = proposed_text
            item.is_pending_review = True
            item.is_ai_generated = True
            item.save(update_fields=[
                'text', 'pending_original_text',
                'is_pending_review', 'is_ai_generated', 'updated_at',
            ])

        # Resolve the note
        note.scope_item = item
        note.status = Note.Status.RESOLVED
        numbers, _sl = compute_exhibit_numbering(exhibit)
        item_ref = numbers.get(item.pk, '')
        note.resolution = f'Incorporated into scope item {item_ref} by AI'
        note.resolved_by = request.user
        note.resolved_at = timezone.now()
        note.save(update_fields=[
            'scope_item', 'status', 'resolution',
            'resolved_by', 'resolved_at', 'updated_at',
        ])

        # Return updated note card
        note.refresh_from_db()
        notes_qs = Note.objects.filter(pk=note.pk).select_related(
            'primary_trade__csi_trade', 'created_by', 'resolved_by', 'scope_item__section',
        ).prefetch_related('related_trades__csi_trade')
        note = notes_qs.first()
        from exhibits.services import compute_section_numbering as _csn2
        note_numbers = {}
        if note.scope_item:
            note_numbers = _csn2(note.scope_item.section)
        response = render(request, 'notes/partials/note_card.html', {
            'note': note,
            'exhibit': exhibit,
            'numbers': note_numbers,
            'ai_enabled': settings.AI_ENABLED,
        })
        response['HX-Trigger'] = 'pendingChanged'
        return response

    # skip_overlap=1 bypasses the AI overlap check (used by "Add New Anyway" button)
    skip_overlap = request.POST.get('skip_overlap')
    if skip_overlap:
        result = None
        # Go straight to generation using generate_scope_item
        section_pk = request.POST.get('section_pk')
        section = None
        if section_pk:
            try:
                section = ExhibitSection.objects.get(pk=section_pk, scope_exhibit=exhibit)
            except ExhibitSection.DoesNotExist:
                pass
        if not section:
            section = exhibit.sections.order_by('order').first()

        if section:
            try:
                exhibit_text = generate_scope_item(note.text, exhibit, section)
            except (AIDisabledError, AIServiceError):
                exhibit_text = None

            text = exhibit_text or note.text
            last = section.items.order_by('-order').values_list('order', flat=True).first()
            last_order = last if last is not None else -1
            item = ScopeItem.objects.create(
                section=section,
                text=text,
                original_input=note.text,
                level=0,
                parent=None,
                order=last_order + 1,
                is_ai_generated=exhibit_text is not None,
                is_pending_review=exhibit_text is not None,
                created_by=request.user,
            )
            numbers, _sl = compute_exhibit_numbering(exhibit)
            item_ref = numbers.get(item.pk, '')
            note.scope_item = item
            note.status = Note.Status.RESOLVED
            note.resolution = f'Converted to scope item {item_ref} by AI'
            note.resolved_by = request.user
            note.resolved_at = timezone.now()
            note.save(update_fields=[
                'scope_item', 'status', 'resolution',
                'resolved_by', 'resolved_at', 'updated_at',
            ])

        # Return updated note card
        note.refresh_from_db()
        notes_qs = Note.objects.filter(pk=note.pk).select_related(
            'primary_trade__csi_trade', 'created_by', 'resolved_by', 'scope_item__section',
        ).prefetch_related('related_trades__csi_trade')
        note = notes_qs.first()
        from exhibits.services import compute_section_numbering as _csn
        note_numbers = {}
        if note.scope_item:
            note_numbers = _csn(note.scope_item.section)
        response = render(request, 'notes/partials/note_card.html', {
            'note': note,
            'exhibit': exhibit,
            'numbers': note_numbers,
            'ai_enabled': settings.AI_ENABLED,
        })
        response['HX-Trigger'] = 'pendingChanged'
        return response

    instruction = request.POST.get('instruction', '').strip()
    try:
        result = convert_note_to_scope(note, exhibit, instruction=instruction)
    except (AIDisabledError, AIServiceError):
        result = None

    if result is None:
        from django.http import HttpResponse
        return HttpResponse(
            '<div class="text-xs text-red-500 p-2">AI conversion failed. Please try again.</div>'
        )

    if result['status'] == 'overlap':
        # Find the overlapping item's ref number
        numbers, _sl = compute_exhibit_numbering(exhibit)
        overlap_pk = result.get('overlap_item_pk')
        overlap_ref = numbers.get(overlap_pk, '')
        overlap_item = None
        if overlap_pk:
            try:
                overlap_item = ScopeItem.objects.get(pk=overlap_pk, section__scope_exhibit=exhibit)
            except ScopeItem.DoesNotExist:
                pass

        # Fallback section for "Add New Anyway" when overlap_item is None
        fallback_section = exhibit.sections.order_by('order').first()
        fallback_section_pk = fallback_section.pk if fallback_section else ''

        return render(request, 'exhibits/partials/note_overlap.html', {
            'exhibit': exhibit,
            'note': note,
            'overlap_item': overlap_item,
            'overlap_ref': overlap_ref,
            'explanation': result.get('explanation', ''),
            'fallback_section_pk': fallback_section_pk,
        })

    # status == 'created'
    section_name = result['section_name']
    sections = {s.name.lower(): s for s in exhibit.sections.all()}
    section = sections.get(section_name.lower())
    if not section:
        # Fallback to first section
        section = exhibit.sections.order_by('order').first()

    if section:
        last = section.items.order_by('-order').values_list('order', flat=True).first()
        last_order = last if last is not None else -1
        item = ScopeItem.objects.create(
            section=section,
            text=result['exhibit_text'],
            original_input=note.text,
            level=0,
            parent=None,
            order=last_order + 1,
            is_ai_generated=True,
            is_pending_review=True,
            created_by=request.user,
        )
        # Link note to item and auto-resolve
        numbers, _sl = compute_exhibit_numbering(exhibit)
        item_ref = numbers.get(item.pk, '')
        note.scope_item = item
        note.status = Note.Status.RESOLVED
        note.resolution = f'Converted to scope item {item_ref} by AI'
        note.resolved_by = request.user
        note.resolved_at = timezone.now()
        note.save(update_fields=[
            'scope_item', 'status', 'resolution',
            'resolved_by', 'resolved_at', 'updated_at',
        ])

    # Return updated note card
    notes = Note.objects.filter(pk=note.pk).select_related(
        'primary_trade__csi_trade', 'created_by', 'resolved_by', 'scope_item__section',
    ).prefetch_related('related_trades__csi_trade')
    note = notes.first()
    from exhibits.services import compute_section_numbering
    note_numbers = {}
    if note.scope_item:
        note_numbers = compute_section_numbering(note.scope_item.section)
    response = render(request, 'notes/partials/note_card.html', {
        'note': note,
        'exhibit': exhibit,
        'numbers': note_numbers,
        'ai_enabled': settings.AI_ENABLED,
    })
    response['HX-Trigger'] = 'pendingChanged'
    return response


# ---------------------------------------------------------------------------
# AI: Generate full scope from description
# ---------------------------------------------------------------------------

@login_required
@require_POST
def exhibit_generate_scope(request, pk):
    from django.contrib import messages
    exhibit = _company_exhibit_or_404(pk, request.user)

    try:
        result = generate_scope_from_description(exhibit)
    except (AIDisabledError, AIServiceError) as e:
        messages.error(request, f'AI generation failed: {e}')
        return _section_list_response(request, exhibit)

    if result is None:
        messages.error(request, 'AI returned an unexpected response. Please try again.')
        return _section_list_response(request, exhibit)

    # Match returned section names to existing sections (case-insensitive)
    sections = {s.name.lower(): s for s in exhibit.sections.all()}

    for section_data in result.get('scope_items', []):
        section_name = section_data.get('section_name', '').strip()
        section = sections.get(section_name.lower())
        if not section:
            continue  # Skip sections that don't exist in the exhibit

        # Append after any existing items
        last = section.items.order_by('-order').values_list('order', flat=True).first()
        next_order = (last + 1) if last is not None else 0

        parent_at_level = {}  # level -> last created ScopeItem at that level
        order_offset = 0
        for item_data in section_data.get('items', []):
            text = item_data.get('text', '').strip()
            level = int(item_data.get('level', 0))
            if not text:
                continue
            parent = parent_at_level.get(level - 1) if level > 0 else None
            item = ScopeItem.objects.create(
                section=section,
                text=text,
                level=level,
                parent=parent,
                order=next_order + order_offset,
                is_ai_generated=True,
                is_pending_review=True,
                created_by=request.user,
            )
            parent_at_level[level] = item
            order_offset += 1

    exhibit.last_edited_by = request.user
    exhibit.save(update_fields=['last_edited_by', 'updated_at'])

    messages.success(request, 'Scope generated — review and accept or reject each suggestion.')
    response = _section_list_response(request, exhibit)
    response['HX-Trigger'] = 'pendingChanged'
    return response


# ---------------------------------------------------------------------------
# AI: Generate a single scope item from plain-language input
# ---------------------------------------------------------------------------

@login_required
@require_POST
def item_generate(request, pk, section_pk):
    exhibit = _company_exhibit_or_404(pk, request.user)
    section = get_object_or_404(ExhibitSection, pk=section_pk, scope_exhibit=exhibit)

    input_text = request.POST.get('text', '').strip()
    if not input_text:
        return _item_list_response(request, exhibit, section)

    try:
        exhibit_text = generate_scope_item(input_text, exhibit, section)
    except (AIDisabledError, AIServiceError):
        # Fall back to saving the raw input as a plain item
        exhibit_text = None

    ai_succeeded = exhibit_text is not None
    text = exhibit_text or input_text
    last = section.items.order_by('-order').values_list('order', flat=True).first()
    last_order = last if last is not None else -1
    ScopeItem.objects.create(
        section=section,
        text=text,
        original_input=input_text,
        level=0,
        parent=None,
        order=last_order + 1,
        is_ai_generated=ai_succeeded,
        is_pending_review=ai_succeeded,
        created_by=request.user,
    )
    response = _item_list_response(request, exhibit, section)
    if ai_succeeded:
        response['HX-Trigger'] = 'pendingChanged'
    return response


# ---------------------------------------------------------------------------
# AI panel (right pane tab)
# ---------------------------------------------------------------------------

def _ai_panel_context(exhibit, item_pk=None, suggestions=None, error=None):
    """Build the context dict for the ai_panel partial."""
    sections = list(exhibit.sections.prefetch_related('items').order_by('order'))

    selected_item = None
    if item_pk:
        try:
            selected_item = ScopeItem.objects.select_related('section').get(
                pk=item_pk, section__scope_exhibit=exhibit
            )
        except ScopeItem.DoesNotExist:
            pass

    # All notes for this exhibit's trade (for context chip picker)
    notes = []
    if exhibit.project:
        from django.db.models import Q
        trade = exhibit.project.trades.filter(csi_trade=exhibit.csi_trade).first()
        if trade:
            notes = list(
                Note.objects.filter(
                    Q(primary_trade=trade) | Q(related_trades=trade),
                ).distinct().order_by('-created_at').select_related('primary_trade__csi_trade')
            )

    # Attach matching section object to each suggestion
    if suggestions is not None:
        section_by_name = {s.name.lower(): s for s in sections}
        for gap in suggestions:
            gap['section'] = section_by_name.get(gap.get('section_name', '').lower())

    return {
        'exhibit': exhibit,
        'sections': sections,
        'selected_item': selected_item,
        'suggestions': suggestions,
        'notes': notes,
        'error': error,
        'ai_enabled': settings.AI_ENABLED,
    }


@login_required
def ai_panel(request, pk):
    exhibit = _company_exhibit_or_404(pk, request.user)
    item_pk = request.GET.get('item_pk')
    ctx = _ai_panel_context(exhibit, item_pk=item_pk)
    return render(request, 'exhibits/partials/ai_panel.html', ctx)


@login_required
@require_POST
def exhibit_check_completeness(request, pk):
    exhibit = _company_exhibit_or_404(pk, request.user)
    suggestions = None
    error = None
    try:
        suggestions = check_exhibit_completeness(exhibit)
    except AIDisabledError:
        error = 'AI is disabled.'
        suggestions = []
    except AIServiceError as e:
        error = str(e)
        suggestions = []
    ctx = _ai_panel_context(exhibit, suggestions=suggestions, error=error)
    return render(request, 'exhibits/partials/completeness_results.html', ctx)


@login_required
@require_POST
def note_to_scope_item(request, pk, note_pk):
    """Convert an open question note into a pending scope item."""
    exhibit = _company_exhibit_or_404(pk, request.user)
    note = get_object_or_404(
        Note, pk=note_pk, project=exhibit.project, project__company=request.user.company
    )
    section_pk = request.POST.get('section_pk')
    section = get_object_or_404(ExhibitSection, pk=section_pk, scope_exhibit=exhibit)

    try:
        exhibit_text = generate_scope_item(note.text, exhibit, section)
    except (AIDisabledError, AIServiceError):
        exhibit_text = None

    ai_succeeded = exhibit_text is not None
    text = exhibit_text or note.text
    last = section.items.order_by('-order').values_list('order', flat=True).first()
    last_order = last if last is not None else -1
    item = ScopeItem.objects.create(
        section=section,
        text=text,
        original_input=note.text,
        level=0,
        order=last_order + 1,
        is_ai_generated=ai_succeeded,
        is_pending_review=ai_succeeded,
        created_by=request.user,
    )
    note.scope_item = item
    note.save(update_fields=['scope_item', 'updated_at'])

    response = _section_list_response(request, exhibit)
    if ai_succeeded:
        response['HX-Trigger'] = 'pendingChanged'
    return response


@login_required
@require_POST
def add_gap_item(request, pk, section_pk):
    """Add a suggested gap item from the completeness check as a pending scope item."""
    exhibit = _company_exhibit_or_404(pk, request.user)
    section = get_object_or_404(ExhibitSection, pk=section_pk, scope_exhibit=exhibit)
    text = request.POST.get('text', '').strip()
    if not text:
        return _item_list_response(request, exhibit, section)

    last = section.items.order_by('-order').values_list('order', flat=True).first()
    last_order = last if last is not None else -1
    ScopeItem.objects.create(
        section=section,
        text=text,
        level=0,
        order=last_order + 1,
        is_ai_generated=True,
        is_pending_review=True,
        created_by=request.user,
    )
    response = _item_list_response(request, exhibit, section)
    response['HX-Trigger'] = 'pendingChanged'
    return response


# ---------------------------------------------------------------------------
# Section list (GET endpoint for HTMX refresh)
# ---------------------------------------------------------------------------

@login_required
def section_list(request, pk):
    exhibit = _company_exhibit_or_404(pk, request.user)
    return _section_list_response(request, exhibit)


# ---------------------------------------------------------------------------
# AI chat overlay
# ---------------------------------------------------------------------------

def _apply_proposed_changes(exhibit, changes, user):
    """
    Apply Claude's proposed add/edit/delete actions as pending scope items.
    Returns (applied_count, applied_pks) — count and list of affected item PKs.
    """
    applied = 0
    applied_pks = []
    section_by_name = {
        s.name.lower(): s
        for s in exhibit.sections.prefetch_related('items').order_by('order')
    }

    for change in changes:
        action = change.get('action')

        if action == 'add':
            section_name = change.get('section_name', '').strip()
            text = change.get('text', '').strip()
            level = int(change.get('level', 0))
            section = section_by_name.get(section_name.lower())
            if section and text:
                parent = None
                if level > 0:
                    parent_pk = change.get('parent_item_pk')
                    if parent_pk:
                        try:
                            parent = ScopeItem.objects.get(pk=parent_pk, section=section)
                        except ScopeItem.DoesNotExist:
                            parent = None
                    # Fallback: last item at parent level in section
                    if parent is None:
                        parent = section.items.filter(level=level - 1).order_by('-order').first()
                # Order scoped to siblings (same parent)
                sibling_last = (
                    section.items.filter(parent=parent)
                    .order_by('-order')
                    .values_list('order', flat=True)
                    .first()
                )
                next_order = (sibling_last + 1) if sibling_last is not None else 0
                item = ScopeItem.objects.create(
                    section=section,
                    text=text,
                    level=level,
                    parent=parent,
                    order=next_order,
                    is_ai_generated=True,
                    is_pending_review=True,
                    created_by=user,
                )
                applied += 1
                applied_pks.append(item.pk)

        elif action == 'edit':
            item_pk = change.get('target_item_pk')
            text = change.get('text', '').strip()
            if item_pk and text:
                try:
                    item = ScopeItem.objects.get(pk=item_pk, section__scope_exhibit=exhibit)
                    item.pending_original_text = item.text
                    item.text = text
                    item.is_pending_review = True
                    item.is_ai_generated = True
                    item.save(update_fields=['text', 'pending_original_text', 'is_pending_review', 'is_ai_generated', 'updated_at'])
                    applied += 1
                    applied_pks.append(item.pk)
                except ScopeItem.DoesNotExist:
                    pass

        elif action == 'delete':
            item_pk = change.get('target_item_pk')
            if item_pk:
                try:
                    item = ScopeItem.objects.get(pk=item_pk, section__scope_exhibit=exhibit)
                    item.is_pending_review = True
                    item.pending_delete = True
                    item.save(update_fields=['is_pending_review', 'pending_delete', 'updated_at'])
                    applied += 1
                    applied_pks.append(item.pk)
                except ScopeItem.DoesNotExist:
                    pass

        elif action == 'convert_note':
            note_pk = change.get('note_pk')
            section_name = change.get('section_name', '').strip()
            text = change.get('text', '').strip()
            level = int(change.get('level', 0))
            section = section_by_name.get(section_name.lower())
            if note_pk and section and text:
                try:
                    note = Note.objects.get(
                        pk=note_pk, project=exhibit.project,
                        project__company=exhibit.company,
                    )
                    if note.status != Note.Status.OPEN:
                        continue
                    # Create pending scope item
                    sibling_last = (
                        section.items.filter(parent=None)
                        .order_by('-order')
                        .values_list('order', flat=True)
                        .first()
                    )
                    next_order = (sibling_last + 1) if sibling_last is not None else 0
                    item = ScopeItem.objects.create(
                        section=section,
                        text=text,
                        level=level,
                        parent=None,
                        order=next_order,
                        is_ai_generated=True,
                        is_pending_review=True,
                        original_input=note.text,
                        created_by=user,
                    )
                    # Link and resolve the note
                    note.scope_item = item
                    note.status = Note.Status.RESOLVED
                    note.resolution = 'Converted to scope item by AI'
                    note.resolved_by = user
                    note.resolved_at = timezone.now()
                    note.save(update_fields=[
                        'scope_item', 'status', 'resolution',
                        'resolved_by', 'resolved_at', 'updated_at',
                    ])
                    applied += 1
                    applied_pks.append(item.pk)
                except Note.DoesNotExist:
                    pass

    return applied, applied_pks


@login_required
def ai_chat(request, pk):
    exhibit = _company_exhibit_or_404(pk, request.user)
    from ai_services.models import ChatSession
    session = ChatSession.objects.filter(exhibit=exhibit, user=request.user).first()
    messages = list(session.messages.order_by('created_at')) if session else []
    ctx = _ai_panel_context(exhibit)
    ctx['messages'] = messages
    ctx['session'] = session
    ctx['sessions'] = ChatSession.objects.filter(exhibit=exhibit, user=request.user).order_by('-updated_at')
    return render(request, 'exhibits/partials/chat_side_panel.html', ctx)


@login_required
@require_POST
def ai_chat_new(request, pk):
    """Show a fresh empty chat panel — session is created lazily on first send."""
    from ai_services.models import ChatSession
    exhibit = _company_exhibit_or_404(pk, request.user)
    ctx = _ai_panel_context(exhibit)
    ctx['messages'] = []
    ctx['session'] = None
    ctx['sessions'] = ChatSession.objects.filter(exhibit=exhibit, user=request.user).order_by('-updated_at')
    return render(request, 'exhibits/partials/chat_side_panel.html', ctx)


@login_required
def ai_chat_switch(request, pk, session_pk):
    """Load a specific chat session (must belong to request.user)."""
    from ai_services.models import ChatSession
    exhibit = _company_exhibit_or_404(pk, request.user)
    session = get_object_or_404(ChatSession, pk=session_pk, exhibit=exhibit, user=request.user)
    messages = list(session.messages.order_by('created_at'))
    ctx = _ai_panel_context(exhibit)
    ctx['messages'] = messages
    ctx['session'] = session
    ctx['sessions'] = ChatSession.objects.filter(exhibit=exhibit, user=request.user).order_by('-updated_at')
    return render(request, 'exhibits/partials/chat_side_panel.html', ctx)


@login_required
def ai_chat_sessions(request, pk):
    """Return HTMX partial with the session list for the current user+exhibit."""
    from ai_services.models import ChatSession
    exhibit = _company_exhibit_or_404(pk, request.user)
    sessions = ChatSession.objects.filter(exhibit=exhibit, user=request.user).order_by('-updated_at')
    session_pk = request.GET.get('active')
    return render(request, 'exhibits/partials/chat_session_list.html', {
        'exhibit': exhibit,
        'sessions': sessions,
        'active_session_pk': int(session_pk) if session_pk else None,
    })


def _session_title_context(exhibit, session, user):
    from ai_services.models import ChatSession
    return {
        'exhibit': exhibit,
        'session': session,
        'sessions': ChatSession.objects.filter(exhibit=exhibit, user=user).order_by('-updated_at'),
    }


@login_required
def ai_chat_session_title(request, pk, session_pk):
    """Return the session title area partial (used for rename cancel / restore)."""
    exhibit = _company_exhibit_or_404(pk, request.user)
    from ai_services.models import ChatSession
    session = get_object_or_404(ChatSession, pk=session_pk, exhibit=exhibit, user=request.user)
    return render(request, 'exhibits/partials/chat_session_title_area.html',
                  _session_title_context(exhibit, session, request.user))


@login_required
def ai_chat_rename_form(request, pk, session_pk):
    """Return inline rename form that replaces the session title area."""
    exhibit = _company_exhibit_or_404(pk, request.user)
    from ai_services.models import ChatSession
    session = get_object_or_404(ChatSession, pk=session_pk, exhibit=exhibit, user=request.user)
    return render(request, 'exhibits/partials/chat_session_rename_form.html',
                  {'exhibit': exhibit, 'session': session})


@login_required
@require_POST
def ai_chat_rename(request, pk, session_pk):
    """Save new session title, return updated title area partial."""
    exhibit = _company_exhibit_or_404(pk, request.user)
    from ai_services.models import ChatSession
    session = get_object_or_404(ChatSession, pk=session_pk, exhibit=exhibit, user=request.user)
    title = request.POST.get('title', '').strip()[:200]
    session.title = title
    session.save(update_fields=['title'])
    return render(request, 'exhibits/partials/chat_session_title_area.html',
                  _session_title_context(exhibit, session, request.user))


@login_required
@require_POST
def ai_chat_delete(request, pk, session_pk):
    """Delete the session, load the next most recent session or empty state."""
    exhibit = _company_exhibit_or_404(pk, request.user)
    from ai_services.models import ChatSession
    session = get_object_or_404(ChatSession, pk=session_pk, exhibit=exhibit, user=request.user)
    session.delete()
    next_session = ChatSession.objects.filter(exhibit=exhibit, user=request.user).order_by('-updated_at').first()
    messages = list(next_session.messages.order_by('created_at')) if next_session else []
    ctx = _ai_panel_context(exhibit)
    ctx['messages'] = messages
    ctx['session'] = next_session
    ctx['sessions'] = ChatSession.objects.filter(exhibit=exhibit, user=request.user).order_by('-updated_at')
    return render(request, 'exhibits/partials/chat_side_panel.html', ctx)


@login_required
@require_POST
def ai_chat_send(request, pk):
    from ai_services.models import ChatMessage, ChatSession

    exhibit = _company_exhibit_or_404(pk, request.user)
    user_message = request.POST.get('message', '').strip()

    if not user_message:
        from django.http import HttpResponse
        return HttpResponse('')

    # Build context prefix from selected chips
    context_section_pks = request.POST.getlist('context_section_pks')
    context_note_pks = request.POST.getlist('context_note_pks')
    context_parts = []
    if context_section_pks:
        for s in ExhibitSection.objects.filter(pk__in=context_section_pks, scope_exhibit=exhibit).order_by('order'):
            context_parts.append(f'Section "{s.name}"')
    if context_note_pks and exhibit.project:
        for n in Note.objects.filter(pk__in=context_note_pks, project=exhibit.project):
            context_parts.append(f'Note: "{n.text[:300]}"')
    if context_parts:
        user_message = '[Context: ' + '; '.join(context_parts) + ']\n\n' + user_message

    # Route to session — create lazily on first send if no session exists yet
    session_pk = request.POST.get('session_pk')
    new_session_pk = None
    if session_pk:
        session = get_object_or_404(ChatSession, pk=session_pk, exhibit=exhibit, user=request.user)
    else:
        session = ChatSession.objects.create(exhibit=exhibit, user=request.user)
        new_session_pk = session.pk

    # Save user message
    ChatMessage.objects.create(
        session=session, role=ChatMessage.Role.USER,
        content=user_message, user=request.user,
    )

    # Build conversation from DB
    conversation = list(
        session.messages.order_by('created_at').values_list('role', 'content')
    )
    conversation = [{'role': role, 'content': content} for role, content in conversation]

    assistant_message = None
    changes_applied_pks = []
    error = False

    try:
        result = chat_with_exhibit(exhibit, conversation)
        if result:
            assistant_message = result.get('message', '').strip()
            proposed_changes = result.get('proposed_changes', [])
            if proposed_changes:
                _count, changes_applied_pks = _apply_proposed_changes(exhibit, proposed_changes, request.user)
    except (AIDisabledError, AIServiceError) as e:
        assistant_message = f'Sorry, I ran into an error: {e}'
        error = True

    changes_applied = len(changes_applied_pks)

    if not assistant_message:
        if changes_applied:
            assistant_message = f'Done — {changes_applied} change{"s" if changes_applied != 1 else ""} proposed for your review.'
        else:
            assistant_message = 'Sorry, I could not generate a response. Please try again.'

    # Save assistant message
    ChatMessage.objects.create(
        session=session, role=ChatMessage.Role.ASSISTANT,
        content=assistant_message,
        changes_applied_pks=changes_applied_pks,
    )

    # Auto-title the session from the first user message (once only)
    if not session.title:
        session.title = generate_chat_title(user_message)
        session.save(update_fields=['title', 'updated_at'])

    ctx = {
        'user_message': user_message,
        'assistant_message': assistant_message,
        'changes_applied': changes_applied,
        'changes_applied_pks': changes_applied_pks,
        'error': error,
        'new_session_pk': new_session_pk,
    }
    if new_session_pk:
        ctx.update(_session_title_context(exhibit, session, request.user))
    response = render(request, 'exhibits/partials/ai_chat_messages.html', ctx)
    if changes_applied:
        response['HX-Trigger'] = 'pendingChanged'
    return response
