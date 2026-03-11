from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from .models import Project, Trade
from .forms import ProjectForm, TradeForm


def company_project_or_404(pk, user):
    return get_object_or_404(Project, pk=pk, company=user.company)


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


def _build_status_counts(project):
    trades = project.trades.all()
    counts = {s.value: 0 for s in Trade.Status}
    for t in trades:
        if t.status in counts:
            counts[t.status] += 1
    return counts, trades.count()


@login_required
def trade_update_status(request, pk, trade_pk):
    project = company_project_or_404(pk, request.user)
    trade = get_object_or_404(Trade, pk=trade_pk, project=project)
    new_status = request.POST.get('status')
    if new_status in Trade.Status.values:
        trade.status = new_status
        trade.save()
    from core.models import User
    company_users = User.objects.filter(company=request.user.company).order_by('first_name', 'email')
    response = render(request, 'projects/partials/trade_row.html', {'trade': trade, 'company_users': company_users})
    response['HX-Trigger'] = 'statsChanged'
    return response


@login_required
def project_stats(request, pk):
    project = company_project_or_404(pk, request.user)
    status_counts, total_trades = _build_status_counts(project)
    return render(request, 'projects/partials/stats_bar.html', {
        'project': project,
        'status_counts': status_counts,
        'total_trades': total_trades,
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
    company_users = User.objects.filter(company=request.user.company).order_by('first_name', 'email')
    return render(request, 'projects/partials/trade_row.html', {'trade': trade, 'company_users': company_users})


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
    from core.models import User
    from notes.models import Note
    project = company_project_or_404(pk, request.user)
    trades = (
        project.trades
        .select_related('csi_trade', 'assigned_to')
        .order_by('order', 'csi_trade__csi_code')
    )
    company_users = User.objects.filter(company=request.user.company).order_by('first_name', 'email')

    # Stats
    from .models import Trade as TradeModel
    status_counts = {s.value: 0 for s in TradeModel.Status}
    for trade in trades:
        if trade.status in status_counts:
            status_counts[trade.status] += 1

    open_question_count = Note.objects.filter(
        project=project,
        note_type=Note.NoteType.OPEN_QUESTION,
        status=Note.Status.OPEN,
    ).count()

    return render(request, 'projects/dashboard.html', {
        'project': project,
        'trades': trades,
        'status_counts': status_counts,
        'total_trades': trades.count(),
        'company_users': company_users,
        'open_question_count': open_question_count,
    })
