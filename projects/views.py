from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from .models import Project


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
    # Placeholder — built in next step
    pass


@login_required
def project_dashboard(request, pk):
    project = company_project_or_404(pk, request.user)
    return render(request, 'projects/dashboard.html', {'project': project})


@login_required
def project_edit(request, pk):
    project = company_project_or_404(pk, request.user)
    return render(request, 'projects/edit.html', {'project': project})
