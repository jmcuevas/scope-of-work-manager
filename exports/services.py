import re
from datetime import date

from django.template.loader import render_to_string

from exhibits.services import compute_section_numbering, flatten_section_items


def generate_exhibit_pdf(exhibit):
    """Render exhibit as HTML and convert to PDF bytes via WeasyPrint."""
    import weasyprint  # lazy import — system libs may not be present at startup

    sections = list(exhibit.sections.order_by('order'))
    sections_data = []
    for section in sections:
        items = flatten_section_items(section)
        numbers = compute_section_numbering(section)
        sections_data.append({
            'section': section,
            'items': items,
            'numbers': numbers,
        })

    html_string = render_to_string('exports/exhibit_pdf.html', {
        'exhibit': exhibit,
        'sections_data': sections_data,
        'export_date': date.today(),
    })

    return weasyprint.HTML(string=html_string).write_pdf()


def safe_filename(exhibit):
    """Build a filesystem-safe PDF filename for the exhibit."""
    parts = [
        'ExhibitA',
        exhibit.csi_trade.csi_code,
        exhibit.csi_trade.name,
    ]
    if exhibit.project:
        parts.append(exhibit.project.name)

    raw = '_'.join(parts)
    safe = re.sub(r'[^\w\-]', '_', raw)
    safe = re.sub(r'_+', '_', safe).strip('_')
    return f'{safe}.pdf'
