from urllib.parse import urlencode

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from .models import Project, Trade
from .forms import ProjectForm, TradeForm


def company_project_or_404(pk, user):
    return get_object_or_404(Project, pk=pk, company=user.company)


# ---------------------------------------------------------------------------
# Filtering / sorting / grouping helpers
# ---------------------------------------------------------------------------

SORT_FIELD_MAP = {
    'trade': 'csi_trade__csi_code',
    'budget': 'budget',
    'status': 'status',
    'assigned_to': 'assigned_to__first_name',
}


def _apply_trade_filters(trades, status_filters, assigned_to_filters):
    if status_filters:
        trades = trades.filter(status__in=status_filters)
    if assigned_to_filters:
        from django.db.models import Q
        q = Q()
        pks = [v for v in assigned_to_filters if v != 'unassigned']
        if pks:
            q |= Q(assigned_to_id__in=pks)
        if 'unassigned' in assigned_to_filters:
            q |= Q(assigned_to__isnull=True)
        trades = trades.filter(q)
    return trades


def _apply_trade_sort(trades, sort_by, sort_dir):
    field = SORT_FIELD_MAP.get(sort_by, 'order')
    if sort_dir == 'desc':
        field = f'-{field}'
    return trades.order_by(field)


def _build_trade_groups(trades, group_by):
    from collections import OrderedDict
    groups = OrderedDict()
    if group_by == 'status':
        for s in Trade.Status:
            groups[s.label] = []
        for trade in trades:
            groups[Trade.Status(trade.status).label].append(trade)
        return {k: v for k, v in groups.items() if v}
    elif group_by == 'assigned_to':
        for trade in trades:
            if trade.assigned_to:
                key = trade.assigned_to.get_full_name() or trade.assigned_to.email
            else:
                key = 'Unassigned'
            groups.setdefault(key, []).append(trade)
    return groups


def _build_sort_urls(base_url, filter_params, sort_by, sort_dir):
    """Return a dict of {field: url} with toggled sort for each sortable column."""
    urls = {}
    for field in ['trade', 'budget', 'status', 'assigned_to']:
        params = dict(filter_params)  # shallow copy; lists preserved
        params['sort'] = field
        params['dir'] = 'desc' if (sort_by == field and sort_dir == 'asc') else 'asc'
        urls[field] = base_url + '?' + urlencode(params, doseq=True)
    return urls


def _dashboard_context(request, project):
    """Build the shared context dict for the buyout dashboard."""
    from core.models import User

    # Parse filter/sort/group params
    status_filters = [s for s in request.GET.getlist('status') if s]
    assigned_to_filters = [s for s in request.GET.getlist('assigned_to') if s]
    sort_by = request.GET.get('sort', '')
    sort_dir = request.GET.get('dir', 'asc')
    group_by = request.GET.get('group', '')

    trades = (
        project.trades
        .select_related('csi_trade', 'assigned_to')
    )
    trades = _apply_trade_filters(trades, status_filters, assigned_to_filters)
    if sort_by:
        trades = _apply_trade_sort(trades, sort_by, sort_dir)
    else:
        trades = trades.order_by('order', 'csi_trade__csi_code')

    # Status counts from filtered set
    status_counts = {s.value: 0 for s in Trade.Status}
    for trade in trades:
        if trade.status in status_counts:
            status_counts[trade.status] += 1

    trade_groups = _build_trade_groups(trades, group_by) if group_by else None

    company_users = User.objects.filter(company=request.user.company).order_by('first_name', 'email')

    # Build params dict for sort URL generation (excludes sort/dir, added by helper)
    filter_params = {}
    if status_filters:
        filter_params['status'] = status_filters
    if assigned_to_filters:
        filter_params['assigned_to'] = assigned_to_filters
    if group_by:
        filter_params['group'] = group_by

    sort_urls = _build_sort_urls(request.path, filter_params, sort_by, sort_dir)

    # Labels for active filter chips
    active_status_filter_items = [
        {'value': s, 'label': Trade.Status(s).label}
        for s in status_filters
        if s in Trade.Status.values
    ]
    active_assigned_to_filter_items = []
    for v in assigned_to_filters:
        if v == 'unassigned':
            active_assigned_to_filter_items.append({'value': 'unassigned', 'label': 'Unassigned'})
        else:
            matched = company_users.filter(pk=v).first()
            if matched:
                active_assigned_to_filter_items.append({'value': v, 'label': matched.get_full_name() or matched.email})

    return {
        'project': project,
        'trades': trades,
        'trade_groups': trade_groups,
        'status_counts': status_counts,
        'total_trades': trades.count(),
        'company_users': company_users,
        # Filter state (for template rendering)
        'active_status_filters': status_filters,
        'active_assigned_to_filters': assigned_to_filters,
        'sort_by': sort_by,
        'sort_dir': sort_dir,
        'group_by': group_by,
        'sort_urls': sort_urls,
        'active_status_filter_items': active_status_filter_items,
        'active_assigned_to_filter_items': active_assigned_to_filter_items,
        'trade_status_choices': Trade.Status.choices,
        'stats_query_string': urlencode(
            {k: v for k, v in [('status', status_filters), ('assigned_to', assigned_to_filters)] if v},
            doseq=True,
        ),
    }


def _inline_update_response(request, trade, project):
    """
    After an inline status/assignment update, return either:
    - The grouped table body (when group_by is active)
    - The single trade row (flat mode)
    """
    from core.models import User

    group_by = request.POST.get('group_by', '')
    sort_by = request.POST.get('sort_by', '')
    sort_dir = request.POST.get('sort_dir', 'asc')
    filter_status_raw = request.POST.get('filter_status', '')
    filter_assigned_to_raw = request.POST.get('filter_assigned_to', '')

    company_users = User.objects.filter(company=project.company).order_by('first_name', 'email')

    if group_by:
        # Rebuild filtered/sorted/grouped trades and return full table body
        status_filters = [s for s in filter_status_raw.split(',') if s]
        assigned_to_filters = [s for s in filter_assigned_to_raw.split(',') if s]
        trades = project.trades.select_related('csi_trade', 'assigned_to')
        trades = _apply_trade_filters(trades, status_filters, assigned_to_filters)
        if sort_by:
            trades = _apply_trade_sort(trades, sort_by, sort_dir)
        else:
            trades = trades.order_by('order', 'csi_trade__csi_code')
        trade_groups = _build_trade_groups(trades, group_by)
        ctx = {
            'project': project,
            'trades': trades,
            'trade_groups': trade_groups,
            'company_users': company_users,
            'active_status_filters': status_filters,
            'active_assigned_to_filters': assigned_to_filters,
            'sort_by': sort_by,
            'sort_dir': sort_dir,
            'group_by': group_by,
        }
        response = render(request, 'projects/partials/trades_table_body.html', ctx)
        response['HX-Trigger'] = 'statsChanged'
        return response

    # Flat mode: return single row
    assigned_to_filters = [s for s in filter_assigned_to_raw.split(',') if s]
    ctx = {
        'trade': trade,
        'company_users': company_users,
        'group_by': group_by,
        'sort_by': sort_by,
        'sort_dir': sort_dir,
        'active_status_filters': [],
        'active_assigned_to_filters': assigned_to_filters,
    }
    response = render(request, 'projects/partials/trade_row.html', ctx)
    response['HX-Trigger'] = 'statsChanged'
    return response


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------

@login_required
def project_list(request):
    projects = (
        Project.objects
        .filter(company=request.user.company)
        .select_related('project_type', 'created_by')
        .annotate(trade_count=Count('trades'))
        .order_by('-created_at')
    )
    return render(request, 'projects/list.html', {'projects': projects})


@login_required
def project_create(request):
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.company = request.user.company
            project.created_by = request.user
            project.save()
            return redirect('projects:dashboard', pk=project.pk)
    else:
        form = ProjectForm()
    return render(request, 'projects/form.html', {'form': form, 'action': 'Create'})


@login_required
def trade_import(request, pk):
    project = company_project_or_404(pk, request.user)
    return render(request, 'projects/trade_import.html', {'project': project})


@login_required
def trade_add(request, pk):
    project = company_project_or_404(pk, request.user)
    if request.method == 'POST':
        form = TradeForm(request.POST, project=project)
        if form.is_valid():
            trade = form.save(commit=False)
            trade.project = project
            trade.order = project.trades.count()
            trade.save()
            return redirect('projects:dashboard', pk=project.pk)
    else:
        form = TradeForm(project=project)
    return render(request, 'projects/trade_add.html', {'project': project, 'form': form})


@login_required
def trade_update_status(request, pk, trade_pk):
    project = company_project_or_404(pk, request.user)
    trade = get_object_or_404(Trade, pk=trade_pk, project=project)
    new_status = request.POST.get('status')
    if new_status in Trade.Status.values:
        trade.status = new_status
        trade.save()
    return _inline_update_response(request, trade, project)


@login_required
def project_stats(request, pk):
    project = company_project_or_404(pk, request.user)
    status_filters = [s for s in request.GET.getlist('status') if s]
    assigned_to_filters = [s for s in request.GET.getlist('assigned_to') if s]

    trades = project.trades.all()
    trades = _apply_trade_filters(trades, status_filters, assigned_to_filters)

    status_counts = {s.value: 0 for s in Trade.Status}
    for trade in trades:
        if trade.status in status_counts:
            status_counts[trade.status] += 1

    qs = urlencode(
        {k: v for k, v in [('status', status_filters), ('assigned_to', assigned_to_filters)] if v},
        doseq=True,
    )
    return render(request, 'projects/partials/stats_bar.html', {
        'project': project,
        'status_counts': status_counts,
        'total_trades': trades.count(),
        'active_status_filters': status_filters,
        'active_assigned_to_filters': assigned_to_filters,
        'stats_query_string': qs,
    })


@login_required
def trade_update_assign(request, pk, trade_pk):
    from core.models import User
    project = company_project_or_404(pk, request.user)
    trade = get_object_or_404(Trade, pk=trade_pk, project=project)
    user_id = request.POST.get('assigned_to')
    if user_id:
        trade.assigned_to = get_object_or_404(User, pk=user_id, company=request.user.company)
    else:
        trade.assigned_to = None
    trade.save()
    return _inline_update_response(request, trade, project)


@login_required
def project_edit(request, pk):
    project = company_project_or_404(pk, request.user)
    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            return redirect('projects:dashboard', pk=project.pk)
    else:
        form = ProjectForm(instance=project)
    return render(request, 'projects/form.html', {
        'form': form,
        'action': 'Edit',
        'project': project,
    })


@login_required
def project_dashboard(request, pk):
    from notes.models import Note
    project = company_project_or_404(pk, request.user)
    context = _dashboard_context(request, project)
    context['open_question_count'] = Note.objects.filter(
        project=project,
        status=Note.Status.OPEN,
    ).count()

    if request.headers.get('HX-Request'):
        return render(request, 'projects/partials/dashboard_content.html', context)
    return render(request, 'projects/dashboard.html', context)
