from django.shortcuts import render
from django.contrib.auth.decorators import login_required


@login_required
def project_list(request):
    return render(request, 'projects/list.html')
