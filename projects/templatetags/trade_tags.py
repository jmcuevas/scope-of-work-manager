from django import template

register = template.Library()

STATUS_CLASSES = {
    'NOT_STARTED':           'bg-gray-100 text-gray-600',
    'DRAFTING':              'bg-blue-100 text-blue-700',
    'OUT_TO_BID':            'bg-yellow-100 text-yellow-700',
    'BIDS_RECEIVED':         'bg-orange-100 text-orange-700',
    'OWNER_REVIEW':          'bg-purple-100 text-purple-700',
    'SUBCONTRACTOR_APPROVED': 'bg-green-100 text-green-700',
}


@register.filter
def status_badge_class(status):
    return STATUS_CLASSES.get(status, 'bg-gray-100 text-gray-600')
