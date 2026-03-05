from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from .models import Project
from .forms import ProjectForm


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
    return render(request, 'projects/trade_add.html', {'project': project})


@login_required
def trade_update_status(request, pk, trade_pk):
    pass


@login_required
def trade_update_assign(request, pk, trade_pk):
    pass


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
    project = company_project_or_404(pk, request.user)
    trades = (
        project.trades
        .select_related('csi_trade', 'assigned_to')
        .order_by('order', 'csi_trade__csi_code')
    )

    # Stats
    from .models import Trade as TradeModel
    status_counts = {s.value: 0 for s in TradeModel.Status}
    for trade in trades:
        status_counts[trade.status] += 1

    return render(request, 'projects/dashboard.html', {
        'project': project,
        'trades': trades,
        'status_counts': status_counts,
        'total_trades': trades.count(),
    })
