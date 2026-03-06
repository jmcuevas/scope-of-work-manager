from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from exhibits.models import ScopeExhibit

from .services import generate_exhibit_pdf, safe_filename


@login_required
def exhibit_pdf_download(request, pk):
    exhibit = get_object_or_404(ScopeExhibit, pk=pk, company=request.user.company)
    pdf_bytes = generate_exhibit_pdf(exhibit)
    filename = safe_filename(exhibit)
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
