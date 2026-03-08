from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from ai_services.services import AIDisabledError, AIServiceError, generate_scope_from_description, generate_scope_item
from django.conf import settings
from notes.forms import NoteForm
from notes.models import Note
from projects.models import Project, Trade

from .models import ExhibitSection, ScopeExhibit, ScopeItem
from .services import clone_exhibit, compute_section_numbering, create_blank_exhibit, flatten_section_items, indent_item, outdent_item, save_as_template


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
        trade.status = Trade.Status.SCOPE_IN_PROGRESS
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
    numbers = {}
    items_by_section = {}
    for section in sections:
        numbers.update(compute_section_numbering(section))
        items_by_section[section.pk] = flatten_section_items(section)

    # Notes sidebar context
    notes = Note.objects.none()
    note_form = None
    if exhibit.project:
        try:
            trade = Trade.objects.get(project=exhibit.project, csi_trade=exhibit.csi_trade)
            from django.db.models import Q
            notes = (
                Note.objects
                .filter(project=exhibit.project)
                .filter(Q(primary_trade=trade) | Q(related_trades=trade))
                .select_related('primary_trade__csi_trade', 'created_by', 'resolved_by')
                .prefetch_related('related_trades__csi_trade')
                .distinct()
                .order_by('status', '-created_at')
            )
        except Trade.DoesNotExist:
            pass
        note_form = NoteForm(project=exhibit.project)

    return render(request, 'exhibits/editor.html', {
        'exhibit': exhibit,
        'sections': sections,
        'numbers': numbers,
        'items_by_section': items_by_section,
        'notes': notes,
        'form': note_form,
        'ai_enabled': settings.AI_ENABLED,
    })


# ---------------------------------------------------------------------------
# Section CRUD (HTMX — all return section_list partial)
# ---------------------------------------------------------------------------

def _section_list_response(request, exhibit):
    sections = list(exhibit.sections.order_by('order'))
    numbers = {}
    items_by_section = {}
    for section in sections:
        numbers.update(compute_section_numbering(section))
        items_by_section[section.pk] = flatten_section_items(section)
    return render(request, 'exhibits/partials/section_list.html', {
        'exhibit': exhibit,
        'sections': sections,
        'numbers': numbers,
        'items_by_section': items_by_section,
        'ai_enabled': settings.AI_ENABLED,
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

def _item_list_response(request, exhibit, section):
    items = flatten_section_items(section)
    numbers = compute_section_numbering(section)
    return render(request, 'exhibits/partials/item_list.html', {
        'exhibit': exhibit,
        'section': section,
        'items': items,
        'numbers': numbers,
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
    last = section.items.order_by('-order').values_list('order', flat=True).first()
    last_order = last if last is not None else -1
    ScopeItem.objects.create(
        section=section,
        text=text,
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
        text = request.POST.get('text', '').strip()
        if text:
            item.text = text
            item.save(update_fields=['text', 'updated_at'])
        numbers = compute_section_numbering(section)
        return render(request, 'exhibits/partials/item.html', {
            'exhibit': exhibit,
            'section': section,
            'item': item,
            'numbers': numbers,
        })

    # GET — cancel returns display mode, otherwise edit form
    template = 'exhibits/partials/item_form.html'
    if request.GET.get('cancel'):
        template = 'exhibits/partials/item.html'
    numbers = compute_section_numbering(section)
    return render(request, template, {
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
                ScopeExhibit.Status.FINALIZED: Trade.Status.SUBCONTRACT_ISSUED,
            }
            trade_status_order = [
                Trade.Status.NOT_STARTED,
                Trade.Status.SCOPE_IN_PROGRESS,
                Trade.Status.OUT_TO_BID,
                Trade.Status.BIDS_RECEIVED,
                Trade.Status.SUBCONTRACT_ISSUED,
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

        items_to_create = []
        for i, item_data in enumerate(section_data.get('items', [])):
            text = item_data.get('text', '').strip()
            level = int(item_data.get('level', 0))
            if not text:
                continue
            items_to_create.append(ScopeItem(
                section=section,
                text=text,
                level=level,
                parent=None,
                order=next_order + i,
                is_ai_generated=True,
                created_by=request.user,
            ))

        if items_to_create:
            ScopeItem.objects.bulk_create(items_to_create)

    exhibit.last_edited_by = request.user
    exhibit.save(update_fields=['last_edited_by', 'updated_at'])

    messages.success(request, 'Scope generated. Review and edit the items below.')
    return _section_list_response(request, exhibit)


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

    text = exhibit_text or input_text
    last = section.items.order_by('-order').values_list('order', flat=True).first()
    last_order = last if last is not None else -1
    ScopeItem.objects.create(
        section=section,
        text=text,
        level=0,
        parent=None,
        order=last_order + 1,
        is_ai_generated=exhibit_text is not None,
        created_by=request.user,
    )
    return _item_list_response(request, exhibit, section)
