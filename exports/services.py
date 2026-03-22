import re
from datetime import date

from django.template.loader import render_to_string

from exhibits.services import compute_exhibit_numbering, flatten_section_items


def generate_exhibit_pdf(exhibit):
    """Render exhibit as HTML and convert to PDF bytes via WeasyPrint."""
    import weasyprint  # lazy import — system libs may not be present at startup

    sections = list(exhibit.sections.order_by('order'))
    numbers, section_letters = compute_exhibit_numbering(exhibit)
    sections_data = []
    for section in sections:
        items = flatten_section_items(section)
        sections_data.append({
            'section': section,
            'items': items,
            'numbers': numbers,
            'section_letter': section_letters.get(section.pk, ''),
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
