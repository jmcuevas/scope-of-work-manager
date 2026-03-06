import pytest
from django.urls import reverse

from core.factories import CompanyFactory, PMUserFactory
from exhibits.factories import ExhibitSectionFactory, ScopeExhibitFactory, ScopeItemFactory

from .services import generate_exhibit_pdf, safe_filename


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BACKEND = 'django.contrib.auth.backends.ModelBackend'


def _login(client, user):
    user.set_password('testpass123')
    user.save(update_fields=['password'])
    client.force_login(user, backend=_BACKEND)


# ---------------------------------------------------------------------------
# Service tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_generate_exhibit_pdf_returns_bytes():
    exhibit = ScopeExhibitFactory()
    section = ExhibitSectionFactory(scope_exhibit=exhibit, order=0)
    ScopeItemFactory(section=section, text='Supply and install all HVAC equipment.', level=0, order=0)
    ScopeItemFactory(section=section, text='Provide commissioning.', level=0, order=1)

    result = generate_exhibit_pdf(exhibit)

    assert isinstance(result, bytes)
    assert len(result) > 0


@pytest.mark.django_db
def test_generate_exhibit_pdf_with_nested_items():
    exhibit = ScopeExhibitFactory()
    section = ExhibitSectionFactory(scope_exhibit=exhibit, order=0)
    parent = ScopeItemFactory(section=section, text='General HVAC work.', level=0, order=0)
    ScopeItemFactory(section=section, parent=parent, text='Ductwork.', level=1, order=0)
    ScopeItemFactory(section=section, parent=parent, text='Equipment.', level=1, order=1)

    result = generate_exhibit_pdf(exhibit)

    assert isinstance(result, bytes)
    assert len(result) > 0


@pytest.mark.django_db
def test_generate_exhibit_pdf_with_scope_description():
    exhibit = ScopeExhibitFactory(scope_description='Full mechanical scope for lab buildout.')
    section = ExhibitSectionFactory(scope_exhibit=exhibit, order=0)
    ScopeItemFactory(section=section, order=0)

    result = generate_exhibit_pdf(exhibit)

    assert isinstance(result, bytes)
    assert len(result) > 0


@pytest.mark.django_db
def test_generate_exhibit_pdf_empty_sections():
    """Exhibit with sections but no items should still produce a PDF."""
    exhibit = ScopeExhibitFactory()
    ExhibitSectionFactory(scope_exhibit=exhibit, order=0)
    ExhibitSectionFactory(scope_exhibit=exhibit, order=1)

    result = generate_exhibit_pdf(exhibit)

    assert isinstance(result, bytes)
    assert len(result) > 0


@pytest.mark.django_db
def test_safe_filename_contains_trade_and_project():
    exhibit = ScopeExhibitFactory()
    filename = safe_filename(exhibit)

    assert filename.endswith('.pdf')
    assert 'ExhibitA' in filename
    # CSI code and trade name are present (spaces → underscores)
    csi = exhibit.csi_trade.csi_code.replace(' ', '_')
    assert csi in filename


@pytest.mark.django_db
def test_safe_filename_no_special_chars():
    exhibit = ScopeExhibitFactory()
    filename = safe_filename(exhibit)
    # Only alphanumeric, underscore, hyphen, and .pdf extension allowed
    import re
    assert re.match(r'^[\w\-]+\.pdf$', filename), f"Unsafe filename: {filename}"


# ---------------------------------------------------------------------------
# Download view tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_pdf_download_returns_200_with_correct_headers(client):
    user = PMUserFactory()
    exhibit = ScopeExhibitFactory(company=user.company)
    ExhibitSectionFactory(scope_exhibit=exhibit, order=0)
    _login(client, user)

    url = reverse('exports:exhibit_pdf', kwargs={'pk': exhibit.pk})
    response = client.get(url)

    assert response.status_code == 200
    assert response['Content-Type'] == 'application/pdf'
    assert 'attachment' in response['Content-Disposition']
    assert '.pdf' in response['Content-Disposition']


@pytest.mark.django_db
def test_pdf_download_filename_contains_trade_name(client):
    user = PMUserFactory()
    exhibit = ScopeExhibitFactory(company=user.company)
    ExhibitSectionFactory(scope_exhibit=exhibit, order=0)
    _login(client, user)

    url = reverse('exports:exhibit_pdf', kwargs={'pk': exhibit.pk})
    response = client.get(url)

    disposition = response['Content-Disposition']
    assert exhibit.csi_trade.csi_code.replace(' ', '_') in disposition or \
           exhibit.csi_trade.name.replace(' ', '_') in disposition


@pytest.mark.django_db
def test_pdf_download_company_isolation(client):
    """User cannot download another company's exhibit."""
    user = PMUserFactory()
    other_company = CompanyFactory()
    exhibit = ScopeExhibitFactory(company=other_company)
    _login(client, user)

    url = reverse('exports:exhibit_pdf', kwargs={'pk': exhibit.pk})
    response = client.get(url)

    assert response.status_code == 404


@pytest.mark.django_db
def test_pdf_download_requires_login(client):
    exhibit = ScopeExhibitFactory()
    url = reverse('exports:exhibit_pdf', kwargs={'pk': exhibit.pk})
    response = client.get(url)
    assert response.status_code == 302
    assert '/accounts/' in response['Location']


# ---------------------------------------------------------------------------
# Multi-section smoke test
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_pdf_multi_section_exhibit(client):
    """Five sections with items each — simulates a realistic exhibit."""
    user = PMUserFactory()
    exhibit = ScopeExhibitFactory(company=user.company)

    section_names = [
        'General Conditions', 'Scope of Work',
        'Specific Inclusions', 'Specific Exclusions', 'Clarifications',
    ]
    for i, name in enumerate(section_names):
        section = ExhibitSectionFactory(scope_exhibit=exhibit, name=name, order=i)
        for j in range(4):
            ScopeItemFactory(section=section, level=0, order=j)

    _login(client, user)
    url = reverse('exports:exhibit_pdf', kwargs={'pk': exhibit.pk})
    response = client.get(url)

    assert response.status_code == 200
    assert response['Content-Type'] == 'application/pdf'
    assert len(response.content) > 0
