import pytest
from django.urls import reverse

from core.factories import CompanyFactory, PMUserFactory, CSITradeFactory
from projects.factories import ProjectFactory, TradeFactory
from projects.models import Trade

from .factories import ExhibitSectionFactory, ScopeExhibitFactory, ScopeItemFactory
from .models import ExhibitSection, ScopeExhibit, ScopeItem
from .services import (
    clone_exhibit,
    compute_section_numbering,
    create_blank_exhibit,
    flatten_section_items,
    indent_item,
    outdent_item,
    save_as_template,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BACKEND = 'django.contrib.auth.backends.ModelBackend'


def _login(client, user):
    # PMUserFactory uses skip_postgeneration_save=True, so the password hash
    # is not persisted. Save it first or session auth hash validation fails.
    user.set_password('testpass123')
    user.save(update_fields=['password'])
    client.force_login(user, backend=_BACKEND)


def _make_trade_with_exhibit(user):
    """Return (trade, exhibit) both belonging to user's company."""
    project = ProjectFactory(company=user.company)
    csi = CSITradeFactory()
    trade = TradeFactory(project=project, csi_trade=csi)
    exhibit = ScopeExhibitFactory(
        company=user.company,
        project=project,
        csi_trade=csi,
        created_by=user,
        last_edited_by=user,
    )
    return trade, exhibit


def _make_section_with_items(exhibit, n=3):
    section = ExhibitSectionFactory(scope_exhibit=exhibit)
    items = [ScopeItemFactory(section=section, order=i) for i in range(n)]
    return section, items


# ---------------------------------------------------------------------------
# Service: create_blank_exhibit
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestCreateBlankExhibit:
    def test_creates_five_sections(self):
        user = PMUserFactory()
        project = ProjectFactory(company=user.company)
        csi = CSITradeFactory()
        trade = TradeFactory(project=project, csi_trade=csi)
        exhibit = create_blank_exhibit(trade, user)
        assert exhibit.sections.count() == 5

    def test_exhibit_scoped_to_user_company(self):
        user = PMUserFactory()
        project = ProjectFactory(company=user.company)
        csi = CSITradeFactory()
        trade = TradeFactory(project=project, csi_trade=csi)
        exhibit = create_blank_exhibit(trade, user)
        assert exhibit.company == user.company

    def test_exhibit_is_not_template(self):
        user = PMUserFactory()
        project = ProjectFactory(company=user.company)
        csi = CSITradeFactory()
        trade = TradeFactory(project=project, csi_trade=csi)
        exhibit = create_blank_exhibit(trade, user)
        assert exhibit.is_template is False


# ---------------------------------------------------------------------------
# Service: clone_exhibit
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestCloneExhibit:
    def test_sections_and_items_copied(self):
        user = PMUserFactory()
        _, source = _make_trade_with_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=source)
        ScopeItemFactory(section=section, order=0)
        ScopeItemFactory(section=section, order=1)

        project2 = ProjectFactory(company=user.company)
        csi2 = CSITradeFactory()
        trade2 = TradeFactory(project=project2, csi_trade=csi2)
        clone = clone_exhibit(source, trade2, user)

        assert clone.sections.count() == source.sections.count()
        clone_section = clone.sections.first()
        assert clone_section.items.count() == 2

    def test_parent_fk_remapped(self):
        user = PMUserFactory()
        _, source = _make_trade_with_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=source)
        parent_item = ScopeItemFactory(section=section, order=0)
        child_item = ScopeItemFactory(section=section, parent=parent_item, level=1, order=0)

        project2 = ProjectFactory(company=user.company)
        csi2 = CSITradeFactory()
        trade2 = TradeFactory(project=project2, csi_trade=csi2)
        clone = clone_exhibit(source, trade2, user)

        clone_section = clone.sections.first()
        clone_items = list(clone_section.items.order_by('level', 'order'))
        clone_parent = next(i for i in clone_items if i.level == 0)
        clone_child = next(i for i in clone_items if i.level == 1)

        assert clone_child.parent_id == clone_parent.pk
        assert clone_child.parent_id != child_item.parent_id  # not the original pk


# ---------------------------------------------------------------------------
# Service: save_as_template
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestSaveAsTemplate:
    def test_is_template_true(self):
        user = PMUserFactory()
        _, exhibit = _make_trade_with_exhibit(user)
        template = save_as_template(exhibit, user)
        assert template.is_template is True

    def test_project_is_none(self):
        user = PMUserFactory()
        _, exhibit = _make_trade_with_exhibit(user)
        template = save_as_template(exhibit, user)
        assert template.project is None

    def test_sections_copied(self):
        user = PMUserFactory()
        _, exhibit = _make_trade_with_exhibit(user)
        ExhibitSectionFactory(scope_exhibit=exhibit)
        ExhibitSectionFactory(scope_exhibit=exhibit)
        template = save_as_template(exhibit, user)
        assert template.sections.count() == 2


# ---------------------------------------------------------------------------
# Service: compute_section_numbering
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestComputeSectionNumbering:
    def test_flat_items(self):
        section = ExhibitSectionFactory()
        a = ScopeItemFactory(section=section, order=0)
        b = ScopeItemFactory(section=section, order=1)
        c = ScopeItemFactory(section=section, order=2)
        numbers = compute_section_numbering(section)
        assert numbers[a.pk] == '1'
        assert numbers[b.pk] == '2'
        assert numbers[c.pk] == '3'

    def test_nested_items(self):
        section = ExhibitSectionFactory()
        parent = ScopeItemFactory(section=section, order=0)
        child1 = ScopeItemFactory(section=section, parent=parent, level=1, order=0)
        child2 = ScopeItemFactory(section=section, parent=parent, level=1, order=1)
        grandchild = ScopeItemFactory(section=section, parent=child1, level=2, order=0)
        numbers = compute_section_numbering(section)
        assert numbers[parent.pk] == '1'
        assert numbers[child1.pk] == '1.1'
        assert numbers[child2.pk] == '1.2'
        assert numbers[grandchild.pk] == '1.1.1'


# ---------------------------------------------------------------------------
# Service: flatten_section_items
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestFlattenSectionItems:
    def test_dfs_order(self):
        section = ExhibitSectionFactory()
        a = ScopeItemFactory(section=section, order=0)
        b = ScopeItemFactory(section=section, order=1)
        child_a = ScopeItemFactory(section=section, parent=a, level=1, order=0)
        result = flatten_section_items(section)
        pks = [i.pk for i in result]
        assert pks == [a.pk, child_a.pk, b.pk]


# ---------------------------------------------------------------------------
# Service: indent_item / outdent_item
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestIndentItem:
    def test_indent_sets_parent(self):
        section = ExhibitSectionFactory()
        a = ScopeItemFactory(section=section, order=0)
        b = ScopeItemFactory(section=section, order=1)
        indent_item(b)
        b.refresh_from_db()
        assert b.parent_id == a.pk
        assert b.level == 1

    def test_indent_first_item_is_noop(self):
        section = ExhibitSectionFactory()
        a = ScopeItemFactory(section=section, order=0)
        indent_item(a)
        a.refresh_from_db()
        assert a.parent is None
        assert a.level == 0

    def test_indent_cascades_level_to_descendants(self):
        section = ExhibitSectionFactory()
        a = ScopeItemFactory(section=section, order=0)
        b = ScopeItemFactory(section=section, order=1)
        child_b = ScopeItemFactory(section=section, parent=b, level=1, order=0)
        indent_item(b)
        child_b.refresh_from_db()
        assert child_b.level == 2


@pytest.mark.django_db
class TestOutdentItem:
    def test_outdent_moves_to_grandparent(self):
        section = ExhibitSectionFactory()
        a = ScopeItemFactory(section=section, order=0)
        b = ScopeItemFactory(section=section, parent=a, level=1, order=0)
        outdent_item(b)
        b.refresh_from_db()
        assert b.parent is None
        assert b.level == 0

    def test_outdent_top_level_is_noop(self):
        section = ExhibitSectionFactory()
        a = ScopeItemFactory(section=section, order=0)
        outdent_item(a)
        a.refresh_from_db()
        assert a.parent is None

    def test_outdent_inserts_after_old_parent(self):
        section = ExhibitSectionFactory()
        a = ScopeItemFactory(section=section, order=0)
        b = ScopeItemFactory(section=section, order=1)
        child_a = ScopeItemFactory(section=section, parent=a, level=1, order=0)
        outdent_item(child_a)
        flat = flatten_section_items(section)
        pks = [i.pk for i in flat]
        assert pks.index(a.pk) < pks.index(child_a.pk) < pks.index(b.pk)

    def test_outdent_cascades_level_to_descendants(self):
        section = ExhibitSectionFactory()
        a = ScopeItemFactory(section=section, order=0)
        b = ScopeItemFactory(section=section, parent=a, level=1, order=0)
        grandchild = ScopeItemFactory(section=section, parent=b, level=2, order=0)
        outdent_item(b)
        grandchild.refresh_from_db()
        assert grandchild.level == 1


# ---------------------------------------------------------------------------
# Entry flow views
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestTradesScopeOpen:
    def test_redirects_to_editor_if_exhibit_exists(self, client):
        user = PMUserFactory()
        _login(client, user)
        trade, exhibit = _make_trade_with_exhibit(user)
        url = reverse('exhibits:trade_scope_open', args=[trade.project.pk, trade.pk])
        response = client.get(url)
        assert response.status_code == 302
        assert str(exhibit.pk) in response['Location']

    def test_redirects_to_picker_if_no_exhibit(self, client):
        user = PMUserFactory()
        _login(client, user)
        project = ProjectFactory(company=user.company)
        csi = CSITradeFactory()
        trade = TradeFactory(project=project, csi_trade=csi)
        url = reverse('exhibits:trade_scope_open', args=[project.pk, trade.pk])
        response = client.get(url)
        assert response.status_code == 302
        assert 'pick' in response['Location']


@pytest.mark.django_db
class TestExhibitStart:
    def test_sets_trade_to_scope_in_progress(self, client):
        user = PMUserFactory()
        _login(client, user)
        project = ProjectFactory(company=user.company)
        csi = CSITradeFactory()
        trade = TradeFactory(project=project, csi_trade=csi, status=Trade.Status.NOT_STARTED)
        url = reverse('exhibits:exhibit_start', args=[project.pk, trade.pk])
        client.post(url, {'source': 'blank'})
        trade.refresh_from_db()
        assert trade.status == Trade.Status.SCOPE_IN_PROGRESS

    def test_company_isolation(self, client):
        user_a = PMUserFactory()
        user_b = PMUserFactory()
        _login(client, user_b)
        project = ProjectFactory(company=user_a.company)
        csi = CSITradeFactory()
        trade = TradeFactory(project=project, csi_trade=csi)
        url = reverse('exhibits:exhibit_start', args=[project.pk, trade.pk])
        response = client.post(url, {'source': 'blank'})
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Section CRUD views
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestSectionCRUD:
    def test_section_add(self, client):
        user = PMUserFactory()
        _login(client, user)
        _, exhibit = _make_trade_with_exhibit(user)
        url = reverse('exhibits:section_add', args=[exhibit.pk])
        client.post(url)
        assert exhibit.sections.count() == 1

    def test_section_rename(self, client):
        user = PMUserFactory()
        _login(client, user)
        _, exhibit = _make_trade_with_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit)
        url = reverse('exhibits:section_rename', args=[exhibit.pk, section.pk])
        client.post(url, {'name': 'Renamed'})
        section.refresh_from_db()
        assert section.name == 'Renamed'

    def test_section_delete_cascades_items(self, client):
        user = PMUserFactory()
        _login(client, user)
        _, exhibit = _make_trade_with_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit)
        ScopeItemFactory(section=section)
        url = reverse('exhibits:section_delete', args=[exhibit.pk, section.pk])
        client.post(url)
        assert not ExhibitSection.objects.filter(pk=section.pk).exists()
        assert ScopeItem.objects.filter(section=section).count() == 0

    def test_section_move_swaps_order(self, client):
        user = PMUserFactory()
        _login(client, user)
        _, exhibit = _make_trade_with_exhibit(user)
        s1 = ExhibitSectionFactory(scope_exhibit=exhibit, order=0)
        s2 = ExhibitSectionFactory(scope_exhibit=exhibit, order=1)
        url = reverse('exhibits:section_move', args=[exhibit.pk, s1.pk])
        client.post(url, {'direction': 'down'})
        s1.refresh_from_db()
        s2.refresh_from_db()
        assert s1.order > s2.order


# ---------------------------------------------------------------------------
# Item CRUD views
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestItemCRUD:
    def test_item_add(self, client):
        user = PMUserFactory()
        _login(client, user)
        _, exhibit = _make_trade_with_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit)
        url = reverse('exhibits:item_add', args=[exhibit.pk, section.pk])
        client.post(url, {'text': 'Provide and install ductwork'})
        assert section.items.count() == 1

    def test_item_add_sequential_orders(self, client):
        user = PMUserFactory()
        _login(client, user)
        _, exhibit = _make_trade_with_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit)
        url = reverse('exhibits:item_add', args=[exhibit.pk, section.pk])
        client.post(url, {'text': 'Item A'})
        client.post(url, {'text': 'Item B'})
        client.post(url, {'text': 'Item C'})
        orders = list(section.items.order_by('order').values_list('order', flat=True))
        assert orders == list(range(len(orders)))

    def test_item_edit(self, client):
        user = PMUserFactory()
        _login(client, user)
        _, exhibit = _make_trade_with_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit)
        item = ScopeItemFactory(section=section)
        url = reverse('exhibits:item_edit', args=[exhibit.pk, section.pk, item.pk])
        client.post(url, {'text': 'Updated text'})
        item.refresh_from_db()
        assert item.text == 'Updated text'

    def test_item_delete_removes_descendants(self, client):
        user = PMUserFactory()
        _login(client, user)
        _, exhibit = _make_trade_with_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit)
        parent = ScopeItemFactory(section=section, order=0)
        child = ScopeItemFactory(section=section, parent=parent, level=1, order=0)
        url = reverse('exhibits:item_delete', args=[exhibit.pk, section.pk, parent.pk])
        client.post(url)
        assert not ScopeItem.objects.filter(pk__in=[parent.pk, child.pk]).exists()


# ---------------------------------------------------------------------------
# Item reorder views
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestItemMove:
    def test_move_up_swaps_siblings(self, client):
        user = PMUserFactory()
        _login(client, user)
        _, exhibit = _make_trade_with_exhibit(user)
        section, (a, b, c) = _make_section_with_items(exhibit)
        url = reverse('exhibits:item_move', args=[exhibit.pk, section.pk, b.pk, 'up'])
        client.post(url)
        a.refresh_from_db()
        b.refresh_from_db()
        assert b.order < a.order

    def test_move_down_swaps_siblings(self, client):
        user = PMUserFactory()
        _login(client, user)
        _, exhibit = _make_trade_with_exhibit(user)
        section, (a, b, c) = _make_section_with_items(exhibit)
        url = reverse('exhibits:item_move', args=[exhibit.pk, section.pk, b.pk, 'down'])
        client.post(url)
        b.refresh_from_db()
        c.refresh_from_db()
        assert b.order > c.order

    def test_move_up_first_item_is_noop(self, client):
        user = PMUserFactory()
        _login(client, user)
        _, exhibit = _make_trade_with_exhibit(user)
        section, (a, b, c) = _make_section_with_items(exhibit)
        original_order = a.order
        url = reverse('exhibits:item_move', args=[exhibit.pk, section.pk, a.pk, 'up'])
        client.post(url)
        a.refresh_from_db()
        assert a.order == original_order

    def test_move_down_last_item_is_noop(self, client):
        user = PMUserFactory()
        _login(client, user)
        _, exhibit = _make_trade_with_exhibit(user)
        section, (a, b, c) = _make_section_with_items(exhibit)
        original_order = c.order
        url = reverse('exhibits:item_move', args=[exhibit.pk, section.pk, c.pk, 'down'])
        client.post(url)
        c.refresh_from_db()
        assert c.order == original_order


# ---------------------------------------------------------------------------
# Status transitions
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestExhibitStatusTransitions:
    def _setup(self, client):
        user = PMUserFactory()
        _login(client, user)
        trade, exhibit = _make_trade_with_exhibit(user)
        trade.status = Trade.Status.SCOPE_IN_PROGRESS
        trade.save()
        return user, trade, exhibit

    def test_ready_for_bid_advances_trade_to_out_to_bid(self, client):
        _, trade, exhibit = self._setup(client)
        url = reverse('exhibits:update_status', args=[exhibit.pk])
        client.post(url, {'status': 'READY_FOR_BID'})
        trade.refresh_from_db()
        assert trade.status == Trade.Status.OUT_TO_BID

    def test_finalized_advances_trade_to_subcontract_issued(self, client):
        _, trade, exhibit = self._setup(client)
        url = reverse('exhibits:update_status', args=[exhibit.pk])
        client.post(url, {'status': 'FINALIZED'})
        trade.refresh_from_db()
        assert trade.status == Trade.Status.SUBCONTRACT_ISSUED

    def test_draft_does_not_change_trade_status(self, client):
        _, trade, exhibit = self._setup(client)
        url = reverse('exhibits:update_status', args=[exhibit.pk])
        client.post(url, {'status': 'DRAFT'})
        trade.refresh_from_db()
        assert trade.status == Trade.Status.SCOPE_IN_PROGRESS

    def test_status_never_regresses_trade(self, client):
        _, trade, exhibit = self._setup(client)
        trade.status = Trade.Status.SUBCONTRACT_ISSUED
        trade.save()
        url = reverse('exhibits:update_status', args=[exhibit.pk])
        client.post(url, {'status': 'READY_FOR_BID'})
        trade.refresh_from_db()
        assert trade.status == Trade.Status.SUBCONTRACT_ISSUED

    def test_company_isolation_on_status_update(self, client):
        user_b = PMUserFactory()
        _login(client, user_b)
        user_a = PMUserFactory()
        _, exhibit = _make_trade_with_exhibit(user_a)
        url = reverse('exhibits:update_status', args=[exhibit.pk])
        response = client.post(url, {'status': 'FINALIZED'})
        assert response.status_code == 404
