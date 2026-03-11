from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from exhibits.models import ScopeExhibit

from .models import FinalReview, FinalReviewItem
from .services import generate_final_review


def _get_exhibit(pk, user):
    return get_object_or_404(ScopeExhibit, pk=pk, company=user.company)


def _review_panel_response(request, exhibit):
    review = exhibit.final_reviews.prefetch_related('items').first()
    return render(request, 'reviews/partials/review_panel.html', {
        'exhibit': exhibit,
        'review': review,
    })


@login_required
@require_POST
def run_review(request, exhibit_pk):
    exhibit = _get_exhibit(exhibit_pk, request.user)
    generate_final_review(exhibit, request.user)
    return _review_panel_response(request, exhibit)


@login_required
def review_item_respond(request, exhibit_pk, item_pk):
    exhibit = _get_exhibit(exhibit_pk, request.user)
    item = get_object_or_404(
        FinalReviewItem,
        pk=item_pk,
        final_review__scope_exhibit=exhibit,
    )
    if request.method == 'GET':
        # Edit mode — return the item with the response form pre-filled
        return render(request, 'reviews/partials/review_item.html', {
            'exhibit': exhibit,
            'item': item,
            'edit_mode': True,
        })
    response_text = request.POST.get('pm_response', '').strip()
    item.pm_response = response_text
    item.reviewed_at = timezone.now() if response_text else None
    item.save(update_fields=['pm_response', 'reviewed_at'])
    return render(request, 'reviews/partials/review_item.html', {
        'exhibit': exhibit,
        'item': item,
    })
