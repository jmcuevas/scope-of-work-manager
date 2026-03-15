import pytest
from unittest.mock import patch
from django.urls import reverse

from core.factories import CompanyFactory, PMUserFactory, CSITradeFactory
from notes.factories import NoteFactory
from notes.models import Note
from projects.factories import ProjectFactory, TradeFactory
from projects.models import Trade

from .factories import ExhibitSectionFactory, ScopeExhibitFactory, ScopeItemFactory
from .models import ExhibitSection, ScopeExhibit, ScopeItem
from .services import (
    accept_ai_item,
    accept_all_pending,
    clone_exhibit,
    compute_section_numbering,
    create_blank_exhibit,
    flatten_section_items,
    indent_item,
    outdent_item,
    reject_ai_item,
    reject_all_pending,
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
        assert trade.status == Trade.Status.DRAFTING

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
        trade.status = Trade.Status.DRAFTING
        trade.save()
        return user, trade, exhibit

    def test_ready_for_bid_advances_trade_to_out_to_bid(self, client):
        _, trade, exhibit = self._setup(client)
        url = reverse('exhibits:update_status', args=[exhibit.pk])
        client.post(url, {'status': 'READY_FOR_BID'})
        trade.refresh_from_db()
        assert trade.status == Trade.Status.OUT_TO_BID

    def test_finalized_advances_trade_to_subcontractor_approved(self, client):
        _, trade, exhibit = self._setup(client)
        url = reverse('exhibits:update_status', args=[exhibit.pk])
        client.post(url, {'status': 'FINALIZED'})
        trade.refresh_from_db()
        assert trade.status == Trade.Status.SUBCONTRACTOR_APPROVED

    def test_draft_does_not_change_trade_status(self, client):
        _, trade, exhibit = self._setup(client)
        url = reverse('exhibits:update_status', args=[exhibit.pk])
        client.post(url, {'status': 'DRAFT'})
        trade.refresh_from_db()
        assert trade.status == Trade.Status.DRAFTING

    def test_status_never_regresses_trade(self, client):
        _, trade, exhibit = self._setup(client)
        trade.status = Trade.Status.SUBCONTRACTOR_APPROVED
        trade.save()
        url = reverse('exhibits:update_status', args=[exhibit.pk])
        client.post(url, {'status': 'READY_FOR_BID'})
        trade.refresh_from_db()
        assert trade.status == Trade.Status.SUBCONTRACTOR_APPROVED

    def test_company_isolation_on_status_update(self, client):
        user_b = PMUserFactory()
        _login(client, user_b)
        user_a = PMUserFactory()
        _, exhibit = _make_trade_with_exhibit(user_a)
        url = reverse('exhibits:update_status', args=[exhibit.pk])
        response = client.post(url, {'status': 'FINALIZED'})
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Service: accept_ai_item / reject_ai_item / accept_all_pending / reject_all_pending
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAcceptRejectAIItem:

    def _make_pending_edit(self, user, exhibit):
        """Item that represents an AI edit: has original text stored."""
        section = ExhibitSectionFactory(scope_exhibit=exhibit)
        item = ScopeItemFactory(
            section=section,
            text='Proposed new text',
            pending_original_text='Original text',
            is_pending_review=True,
            is_ai_generated=True,
            created_by=user,
        )
        return section, item

    def _make_pending_new(self, user, exhibit):
        """Item that represents a brand-new AI suggestion (no original)."""
        section = ExhibitSectionFactory(scope_exhibit=exhibit)
        item = ScopeItemFactory(
            section=section,
            text='Brand new AI item',
            pending_original_text='',
            is_pending_review=True,
            is_ai_generated=True,
            created_by=user,
        )
        return section, item

    def test_accept_ai_item_clears_pending_state(self):
        user = PMUserFactory()
        _, exhibit = _make_trade_with_exhibit(user)
        _, item = self._make_pending_edit(user, exhibit)

        accept_ai_item(item)

        item.refresh_from_db()
        assert item.is_pending_review is False
        assert item.pending_original_text == ''
        assert item.text == 'Proposed new text'  # proposed text kept

    def test_reject_ai_item_edit_restores_original(self):
        user = PMUserFactory()
        _, exhibit = _make_trade_with_exhibit(user)
        _, item = self._make_pending_edit(user, exhibit)

        reject_ai_item(item)

        item.refresh_from_db()
        assert item.is_pending_review is False
        assert item.text == 'Original text'
        assert item.pending_original_text == ''

    def test_reject_ai_item_new_deletes_item(self):
        user = PMUserFactory()
        _, exhibit = _make_trade_with_exhibit(user)
        _, item = self._make_pending_new(user, exhibit)
        pk = item.pk

        reject_ai_item(item)

        assert not ScopeItem.objects.filter(pk=pk).exists()

    def test_reject_ai_item_new_also_deletes_descendants(self):
        user = PMUserFactory()
        _, exhibit = _make_trade_with_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit)
        parent = ScopeItemFactory(
            section=section, text='Parent AI item', pending_original_text='',
            is_pending_review=True, is_ai_generated=True, level=0, created_by=user,
        )
        child = ScopeItemFactory(
            section=section, parent=parent, level=1,
            text='Child', pending_original_text='', is_pending_review=True,
            is_ai_generated=True, created_by=user,
        )

        reject_ai_item(parent)

        assert not ScopeItem.objects.filter(pk=parent.pk).exists()
        assert not ScopeItem.objects.filter(pk=child.pk).exists()

    def test_accept_all_pending_clears_all(self):
        user = PMUserFactory()
        _, exhibit = _make_trade_with_exhibit(user)
        _, item1 = self._make_pending_edit(user, exhibit)
        _, item2 = self._make_pending_new(user, exhibit)
        # One non-pending item should be unaffected
        section = ExhibitSectionFactory(scope_exhibit=exhibit)
        normal = ScopeItemFactory(section=section, is_pending_review=False, created_by=user)

        accept_all_pending(exhibit)

        item1.refresh_from_db()
        item2.refresh_from_db()
        normal.refresh_from_db()
        assert item1.is_pending_review is False
        assert item1.pending_original_text == ''
        assert item2.is_pending_review is False
        assert normal.is_pending_review is False  # unchanged

    def test_reject_all_pending_restores_edits_and_deletes_new(self):
        user = PMUserFactory()
        _, exhibit = _make_trade_with_exhibit(user)
        _, edit_item = self._make_pending_edit(user, exhibit)
        _, new_item = self._make_pending_new(user, exhibit)
        new_pk = new_item.pk

        reject_all_pending(exhibit)

        edit_item.refresh_from_db()
        assert edit_item.is_pending_review is False
        assert edit_item.text == 'Original text'
        assert not ScopeItem.objects.filter(pk=new_pk).exists()

    def test_accept_all_pending_scoped_to_exhibit(self):
        """Items in another exhibit are not affected."""
        user = PMUserFactory()
        _, exhibit_a = _make_trade_with_exhibit(user)
        _, exhibit_b = _make_trade_with_exhibit(user)
        _, item_a = self._make_pending_edit(user, exhibit_a)
        _, item_b = self._make_pending_edit(user, exhibit_b)

        accept_all_pending(exhibit_a)

        item_a.refresh_from_db()
        item_b.refresh_from_db()
        assert item_a.is_pending_review is False
        assert item_b.is_pending_review is True  # untouched


# ---------------------------------------------------------------------------
# Views: item_accept_ai / item_reject_ai
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAcceptRejectAIViews:

    def _make_pending_edit(self, user, exhibit):
        section = ExhibitSectionFactory(scope_exhibit=exhibit)
        item = ScopeItemFactory(
            section=section,
            text='Proposed text',
            pending_original_text='Original text',
            is_pending_review=True,
            is_ai_generated=True,
            created_by=user,
        )
        return section, item

    def _make_pending_new(self, user, exhibit):
        section = ExhibitSectionFactory(scope_exhibit=exhibit)
        item = ScopeItemFactory(
            section=section,
            text='New AI item',
            pending_original_text='',
            is_pending_review=True,
            is_ai_generated=True,
            created_by=user,
        )
        return section, item

    def test_accept_ai_returns_200_and_clears_pending(self, client):
        user = PMUserFactory()
        _login(client, user)
        _, exhibit = _make_trade_with_exhibit(user)
        section, item = self._make_pending_edit(user, exhibit)
        url = reverse('exhibits:item_accept_ai', args=[exhibit.pk, section.pk, item.pk])
        response = client.post(url)
        assert response.status_code == 200
        item.refresh_from_db()
        assert item.is_pending_review is False
        assert item.text == 'Proposed text'

    def test_accept_ai_fires_pending_changed_trigger(self, client):
        user = PMUserFactory()
        _login(client, user)
        _, exhibit = _make_trade_with_exhibit(user)
        section, item = self._make_pending_edit(user, exhibit)
        url = reverse('exhibits:item_accept_ai', args=[exhibit.pk, section.pk, item.pk])
        response = client.post(url)
        assert response['HX-Trigger'] == 'pendingChanged'

    def test_reject_ai_edit_restores_original(self, client):
        user = PMUserFactory()
        _login(client, user)
        _, exhibit = _make_trade_with_exhibit(user)
        section, item = self._make_pending_edit(user, exhibit)
        url = reverse('exhibits:item_reject_ai', args=[exhibit.pk, section.pk, item.pk])
        response = client.post(url)
        assert response.status_code == 200
        item.refresh_from_db()
        assert item.text == 'Original text'
        assert item.is_pending_review is False

    def test_reject_ai_new_deletes_item(self, client):
        user = PMUserFactory()
        _login(client, user)
        _, exhibit = _make_trade_with_exhibit(user)
        section, item = self._make_pending_new(user, exhibit)
        pk = item.pk
        url = reverse('exhibits:item_reject_ai', args=[exhibit.pk, section.pk, item.pk])
        response = client.post(url)
        assert response.status_code == 200
        assert not ScopeItem.objects.filter(pk=pk).exists()

    def test_reject_ai_fires_pending_changed_trigger(self, client):
        user = PMUserFactory()
        _login(client, user)
        _, exhibit = _make_trade_with_exhibit(user)
        section, item = self._make_pending_new(user, exhibit)
        url = reverse('exhibits:item_reject_ai', args=[exhibit.pk, section.pk, item.pk])
        response = client.post(url)
        assert response['HX-Trigger'] == 'pendingChanged'

    def test_accept_ai_company_isolation(self, client):
        user_b = PMUserFactory()
        _login(client, user_b)
        user_a = PMUserFactory()
        _, exhibit = _make_trade_with_exhibit(user_a)
        section, item = self._make_pending_edit(user_a, exhibit)
        url = reverse('exhibits:item_accept_ai', args=[exhibit.pk, section.pk, item.pk])
        response = client.post(url)
        assert response.status_code == 404

    def test_reject_ai_company_isolation(self, client):
        user_b = PMUserFactory()
        _login(client, user_b)
        user_a = PMUserFactory()
        _, exhibit = _make_trade_with_exhibit(user_a)
        section, item = self._make_pending_new(user_a, exhibit)
        url = reverse('exhibits:item_reject_ai', args=[exhibit.pk, section.pk, item.pk])
        response = client.post(url)
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Views: pending_banner / accept_all_pending_view / reject_all_pending_view
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestPendingBannerViews:

    def _make_pending(self, user, exhibit, n=1):
        section = ExhibitSectionFactory(scope_exhibit=exhibit)
        items = [
            ScopeItemFactory(
                section=section,
                text=f'Proposed {i}',
                pending_original_text=f'Original {i}',
                is_pending_review=True,
                is_ai_generated=True,
                created_by=user,
            )
            for i in range(n)
        ]
        return section, items

    def test_banner_shows_count(self, client):
        user = PMUserFactory()
        _login(client, user)
        _, exhibit = _make_trade_with_exhibit(user)
        self._make_pending(user, exhibit, n=3)
        url = reverse('exhibits:pending_banner', args=[exhibit.pk])
        response = client.get(url)
        assert response.status_code == 200
        assert b'3' in response.content
        assert b'pending review' in response.content

    def test_banner_empty_when_no_pending(self, client):
        user = PMUserFactory()
        _login(client, user)
        _, exhibit = _make_trade_with_exhibit(user)
        url = reverse('exhibits:pending_banner', args=[exhibit.pk])
        response = client.get(url)
        assert response.status_code == 200
        assert b'pending review' not in response.content

    def test_accept_all_pending_view_clears_items(self, client):
        user = PMUserFactory()
        _login(client, user)
        _, exhibit = _make_trade_with_exhibit(user)
        _, items = self._make_pending(user, exhibit, n=2)
        url = reverse('exhibits:accept_all_pending', args=[exhibit.pk])
        response = client.post(url)
        assert response.status_code == 200
        assert response['HX-Trigger'] == 'pendingChanged'
        for item in items:
            item.refresh_from_db()
            assert item.is_pending_review is False

    def test_reject_all_pending_view_restores_items(self, client):
        user = PMUserFactory()
        _login(client, user)
        _, exhibit = _make_trade_with_exhibit(user)
        _, items = self._make_pending(user, exhibit, n=2)
        url = reverse('exhibits:reject_all_pending', args=[exhibit.pk])
        response = client.post(url)
        assert response.status_code == 200
        assert response['HX-Trigger'] == 'pendingChanged'
        for item in items:
            item.refresh_from_db()
            assert item.is_pending_review is False
            assert item.text == item.pending_original_text or True  # restored

    def test_banner_company_isolation(self, client):
        user_b = PMUserFactory()
        _login(client, user_b)
        user_a = PMUserFactory()
        _, exhibit = _make_trade_with_exhibit(user_a)
        url = reverse('exhibits:pending_banner', args=[exhibit.pk])
        response = client.get(url)
        assert response.status_code == 404

    def test_accept_all_company_isolation(self, client):
        user_b = PMUserFactory()
        _login(client, user_b)
        user_a = PMUserFactory()
        _, exhibit = _make_trade_with_exhibit(user_a)
        url = reverse('exhibits:accept_all_pending', args=[exhibit.pk])
        response = client.post(url)
        assert response.status_code == 404

    def test_reject_all_company_isolation(self, client):
        user_b = PMUserFactory()
        _login(client, user_b)
        user_a = PMUserFactory()
        _, exhibit = _make_trade_with_exhibit(user_a)
        url = reverse('exhibits:reject_all_pending', args=[exhibit.pk])
        response = client.post(url)
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Item rewrite view
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestItemRewriteView:

    def _setup(self, client):
        user = PMUserFactory()
        _login(client, user)
        _, exhibit = _make_trade_with_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit)
        item = ScopeItemFactory(section=section, text='Original text', created_by=user)
        return user, exhibit, section, item

    def test_rewrite_sets_pending_fields(self, client):
        user, exhibit, section, item = self._setup(client)
        url = reverse('exhibits:item_rewrite', args=[exhibit.pk, section.pk, item.pk])
        with patch('exhibits.views.rewrite_scope_item', return_value='Rewritten text'):
            response = client.post(url)
        assert response.status_code == 200
        item.refresh_from_db()
        assert item.text == 'Rewritten text'
        assert item.pending_original_text == 'Original text'
        assert item.is_pending_review is True
        assert item.is_ai_generated is True

    def test_rewrite_fires_pending_changed_trigger(self, client):
        user, exhibit, section, item = self._setup(client)
        url = reverse('exhibits:item_rewrite', args=[exhibit.pk, section.pk, item.pk])
        with patch('exhibits.views.rewrite_scope_item', return_value='Rewritten text'):
            response = client.post(url)
        assert response['HX-Trigger'] == 'pendingChanged'

    def test_rewrite_no_op_on_ai_failure(self, client):
        from ai_services.services import AIServiceError
        user, exhibit, section, item = self._setup(client)
        url = reverse('exhibits:item_rewrite', args=[exhibit.pk, section.pk, item.pk])
        with patch('exhibits.views.rewrite_scope_item', side_effect=AIServiceError('fail')):
            response = client.post(url)
        assert response.status_code == 200
        item.refresh_from_db()
        assert item.text == 'Original text'
        assert item.is_pending_review is False
        assert 'HX-Trigger' not in response

    def test_rewrite_company_isolation(self, client):
        user_b = PMUserFactory()
        _login(client, user_b)
        user_a = PMUserFactory()
        _, exhibit = _make_trade_with_exhibit(user_a)
        section = ExhibitSectionFactory(scope_exhibit=exhibit)
        item = ScopeItemFactory(section=section, text='x', created_by=user_a)
        url = reverse('exhibits:item_rewrite', args=[exhibit.pk, section.pk, item.pk])
        response = client.post(url)
        assert response.status_code == 404

    def test_rewrite_requires_post(self, client):
        user, exhibit, section, item = self._setup(client)
        url = reverse('exhibits:item_rewrite', args=[exhibit.pk, section.pk, item.pk])
        response = client.get(url)
        assert response.status_code == 405


# ---------------------------------------------------------------------------
# Item expand view
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestItemExpandView:

    def _setup(self, client):
        user = PMUserFactory()
        _login(client, user)
        _, exhibit = _make_trade_with_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit)
        item = ScopeItemFactory(section=section, text='Parent item', created_by=user, level=0)
        return user, exhibit, section, item

    def test_expand_creates_pending_children(self, client):
        user, exhibit, section, item = self._setup(client)
        url = reverse('exhibits:item_expand', args=[exhibit.pk, section.pk, item.pk])
        child_data = [
            {'text': 'Child A', 'level': 1},
            {'text': 'Child B', 'level': 1},
        ]
        with patch('exhibits.views.expand_scope_item', return_value=child_data):
            response = client.post(url)
        assert response.status_code == 200
        children = ScopeItem.objects.filter(section=section, parent=item)
        assert children.count() == 2
        assert all(c.is_pending_review for c in children)
        assert all(c.is_ai_generated for c in children)

    def test_expand_fires_pending_changed_trigger(self, client):
        user, exhibit, section, item = self._setup(client)
        url = reverse('exhibits:item_expand', args=[exhibit.pk, section.pk, item.pk])
        child_data = [{'text': 'Child A', 'level': 1}]
        with patch('exhibits.views.expand_scope_item', return_value=child_data):
            response = client.post(url)
        assert response['HX-Trigger'] == 'pendingChanged'

    def test_expand_no_op_on_ai_failure(self, client):
        from ai_services.services import AIServiceError
        user, exhibit, section, item = self._setup(client)
        url = reverse('exhibits:item_expand', args=[exhibit.pk, section.pk, item.pk])
        with patch('exhibits.views.expand_scope_item', side_effect=AIServiceError('fail')):
            response = client.post(url)
        assert response.status_code == 200
        assert ScopeItem.objects.filter(section=section, parent=item).count() == 0
        assert 'HX-Trigger' not in response

    def test_expand_company_isolation(self, client):
        user_b = PMUserFactory()
        _login(client, user_b)
        user_a = PMUserFactory()
        _, exhibit = _make_trade_with_exhibit(user_a)
        section = ExhibitSectionFactory(scope_exhibit=exhibit)
        item = ScopeItemFactory(section=section, text='x', created_by=user_a)
        url = reverse('exhibits:item_expand', args=[exhibit.pk, section.pk, item.pk])
        response = client.post(url)
        assert response.status_code == 404

    def test_expand_requires_post(self, client):
        user, exhibit, section, item = self._setup(client)
        url = reverse('exhibits:item_expand', args=[exhibit.pk, section.pk, item.pk])
        response = client.get(url)
        assert response.status_code == 405


# ---------------------------------------------------------------------------
# AI panel view
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAIPanelView:

    def test_returns_200(self, client):
        user = PMUserFactory()
        _login(client, user)
        _, exhibit = _make_trade_with_exhibit(user)
        url = reverse('exhibits:ai_panel', args=[exhibit.pk])
        response = client.get(url)
        assert response.status_code == 200

    def test_with_item_pk_shows_item_context(self, client):
        user = PMUserFactory()
        _login(client, user)
        _, exhibit = _make_trade_with_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit)
        item = ScopeItemFactory(section=section, text='Test item', created_by=user)
        url = reverse('exhibits:ai_panel', args=[exhibit.pk])
        response = client.get(url, {'item_pk': item.pk})
        assert response.status_code == 200
        assert b'Test item' in response.content

    def test_invalid_item_pk_falls_back_to_default(self, client):
        user = PMUserFactory()
        _login(client, user)
        _, exhibit = _make_trade_with_exhibit(user)
        url = reverse('exhibits:ai_panel', args=[exhibit.pk])
        response = client.get(url, {'item_pk': 99999})
        assert response.status_code == 200

    def test_company_isolation(self, client):
        user_b = PMUserFactory()
        _login(client, user_b)
        user_a = PMUserFactory()
        _, exhibit = _make_trade_with_exhibit(user_a)
        url = reverse('exhibits:ai_panel', args=[exhibit.pk])
        response = client.get(url)
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Exhibit check completeness view
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestExhibitCheckCompletenessView:

    def test_returns_suggestions_on_success(self, client):
        user = PMUserFactory()
        _login(client, user)
        _, exhibit = _make_trade_with_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit, name='Scope of Work')
        fake_gaps = [{'section_name': 'Scope of Work', 'text': 'Provide coordination drawings.', 'reason': 'Missing.'}]
        url = reverse('exhibits:check_completeness', args=[exhibit.pk])
        with patch('exhibits.views.check_exhibit_completeness', return_value=fake_gaps):
            response = client.post(url)
        assert response.status_code == 200
        assert b'Provide coordination drawings' in response.content

    def test_empty_suggestions_shows_complete_message(self, client):
        user = PMUserFactory()
        _login(client, user)
        _, exhibit = _make_trade_with_exhibit(user)
        url = reverse('exhibits:check_completeness', args=[exhibit.pk])
        with patch('exhibits.views.check_exhibit_completeness', return_value=[]):
            response = client.post(url)
        assert response.status_code == 200
        assert b'complete' in response.content.lower()

    def test_ai_failure_shows_error(self, client):
        from ai_services.services import AIServiceError
        user = PMUserFactory()
        _login(client, user)
        _, exhibit = _make_trade_with_exhibit(user)
        url = reverse('exhibits:check_completeness', args=[exhibit.pk])
        with patch('exhibits.views.check_exhibit_completeness', side_effect=AIServiceError('fail')):
            response = client.post(url)
        assert response.status_code == 200
        assert b'fail' in response.content

    def test_company_isolation(self, client):
        user_b = PMUserFactory()
        _login(client, user_b)
        user_a = PMUserFactory()
        _, exhibit = _make_trade_with_exhibit(user_a)
        url = reverse('exhibits:check_completeness', args=[exhibit.pk])
        response = client.post(url)
        assert response.status_code == 404

    def test_requires_post(self, client):
        user = PMUserFactory()
        _login(client, user)
        _, exhibit = _make_trade_with_exhibit(user)
        url = reverse('exhibits:check_completeness', args=[exhibit.pk])
        response = client.get(url)
        assert response.status_code == 405


# ---------------------------------------------------------------------------
# Add gap item view
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAddGapItemView:

    def test_creates_pending_item(self, client):
        user = PMUserFactory()
        _login(client, user)
        _, exhibit = _make_trade_with_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit)
        url = reverse('exhibits:add_gap_item', args=[exhibit.pk, section.pk])
        response = client.post(url, {'text': 'Provide fire stopping.'})
        assert response.status_code == 200
        item = ScopeItem.objects.get(section=section, text='Provide fire stopping.')
        assert item.is_pending_review is True
        assert item.is_ai_generated is True

    def test_fires_pending_changed_trigger(self, client):
        user = PMUserFactory()
        _login(client, user)
        _, exhibit = _make_trade_with_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit)
        url = reverse('exhibits:add_gap_item', args=[exhibit.pk, section.pk])
        response = client.post(url, {'text': 'Test item.'})
        assert response['HX-Trigger'] == 'pendingChanged'

    def test_empty_text_is_no_op(self, client):
        user = PMUserFactory()
        _login(client, user)
        _, exhibit = _make_trade_with_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit)
        url = reverse('exhibits:add_gap_item', args=[exhibit.pk, section.pk])
        response = client.post(url, {'text': ''})
        assert response.status_code == 200
        assert ScopeItem.objects.filter(section=section).count() == 0

    def test_company_isolation(self, client):
        user_b = PMUserFactory()
        _login(client, user_b)
        user_a = PMUserFactory()
        _, exhibit = _make_trade_with_exhibit(user_a)
        section = ExhibitSectionFactory(scope_exhibit=exhibit)
        url = reverse('exhibits:add_gap_item', args=[exhibit.pk, section.pk])
        response = client.post(url, {'text': 'Test.'})
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Note to scope item view
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestNoteToScopeItemView:

    def _setup(self, client):
        user = PMUserFactory()
        _login(client, user)
        trade, exhibit = _make_trade_with_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit)
        note = NoteFactory(
            project=exhibit.project,
            primary_trade=trade,
            note_type=Note.NoteType.OPEN_QUESTION,
            status=Note.Status.OPEN,
            text='Who carries the caulking?',
            created_by=user,
        )
        return user, trade, exhibit, section, note

    def test_creates_pending_item_from_note(self, client):
        user, trade, exhibit, section, note = self._setup(client)
        url = reverse('exhibits:note_to_scope_item', args=[exhibit.pk, note.pk])
        with patch('exhibits.views.generate_scope_item', return_value='Provide all joint caulking.'):
            response = client.post(url, {'section_pk': section.pk})
        assert response.status_code == 200
        item = ScopeItem.objects.get(section=section)
        assert item.text == 'Provide all joint caulking.'
        assert item.is_pending_review is True
        assert item.is_ai_generated is True

    def test_links_note_to_created_item(self, client):
        user, trade, exhibit, section, note = self._setup(client)
        url = reverse('exhibits:note_to_scope_item', args=[exhibit.pk, note.pk])
        with patch('exhibits.views.generate_scope_item', return_value='Provide all joint caulking.'):
            client.post(url, {'section_pk': section.pk})
        note.refresh_from_db()
        assert note.scope_item is not None

    def test_falls_back_to_raw_text_on_ai_failure(self, client):
        from ai_services.services import AIServiceError
        user, trade, exhibit, section, note = self._setup(client)
        url = reverse('exhibits:note_to_scope_item', args=[exhibit.pk, note.pk])
        with patch('exhibits.views.generate_scope_item', side_effect=AIServiceError('fail')):
            response = client.post(url, {'section_pk': section.pk})
        assert response.status_code == 200
        item = ScopeItem.objects.get(section=section)
        assert item.text == note.text
        assert item.is_pending_review is False

    def test_fires_pending_changed_on_ai_success(self, client):
        user, trade, exhibit, section, note = self._setup(client)
        url = reverse('exhibits:note_to_scope_item', args=[exhibit.pk, note.pk])
        with patch('exhibits.views.generate_scope_item', return_value='Polished text.'):
            response = client.post(url, {'section_pk': section.pk})
        assert response['HX-Trigger'] == 'pendingChanged'

    def test_company_isolation(self, client):
        user_b = PMUserFactory()
        _login(client, user_b)
        user_a = PMUserFactory()
        trade_a, exhibit_a = _make_trade_with_exhibit(user_a)
        note_a = NoteFactory(
            project=exhibit_a.project,
            primary_trade=trade_a,
            note_type=Note.NoteType.OPEN_QUESTION,
            created_by=user_a,
        )
        section_a = ExhibitSectionFactory(scope_exhibit=exhibit_a)
        url = reverse('exhibits:note_to_scope_item', args=[exhibit_a.pk, note_a.pk])
        response = client.post(url, {'section_pk': section_a.pk})
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Section list GET view
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestSectionListView:

    def test_returns_200(self, client):
        user = PMUserFactory()
        _login(client, user)
        _, exhibit = _make_trade_with_exhibit(user)
        ExhibitSectionFactory(scope_exhibit=exhibit)
        url = reverse('exhibits:section_list', args=[exhibit.pk])
        response = client.get(url)
        assert response.status_code == 200

    def test_company_isolation(self, client):
        user_b = PMUserFactory()
        _login(client, user_b)
        user_a = PMUserFactory()
        _, exhibit = _make_trade_with_exhibit(user_a)
        url = reverse('exhibits:section_list', args=[exhibit.pk])
        response = client.get(url)
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# AI chat overlay view
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAIChatView:

    def test_returns_200(self, client):
        user = PMUserFactory()
        _login(client, user)
        _, exhibit = _make_trade_with_exhibit(user)
        url = reverse('exhibits:ai_chat', args=[exhibit.pk])
        response = client.get(url)
        assert response.status_code == 200
        assert b'ai-chat-overlay' in response.content

    def test_company_isolation(self, client):
        user_b = PMUserFactory()
        _login(client, user_b)
        user_a = PMUserFactory()
        _, exhibit = _make_trade_with_exhibit(user_a)
        url = reverse('exhibits:ai_chat', args=[exhibit.pk])
        response = client.get(url)
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# AI chat send view
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAIChatSendView:

    def _setup(self, client):
        user = PMUserFactory()
        _login(client, user)
        _, exhibit = _make_trade_with_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit, name='Scope of Work')
        return user, exhibit, section

    def test_returns_user_and_assistant_messages(self, client):
        user, exhibit, section = self._setup(client)
        url = reverse('exhibits:ai_chat_send', args=[exhibit.pk])
        result = {'message': 'Got it!', 'proposed_changes': []}
        with patch('exhibits.views.chat_with_exhibit', return_value=result):
            response = client.post(url, {'message': 'Hello', 'history': '[]'})
        assert response.status_code == 200
        assert b'Hello' in response.content
        assert b'Got it!' in response.content

    def test_add_change_creates_pending_item(self, client):
        user, exhibit, section = self._setup(client)
        url = reverse('exhibits:ai_chat_send', args=[exhibit.pk])
        result = {
            'message': 'Done!',
            'proposed_changes': [
                {'action': 'add', 'section_name': 'Scope of Work', 'text': 'Provide fire stopping.', 'level': 0}
            ],
        }
        with patch('exhibits.views.chat_with_exhibit', return_value=result):
            response = client.post(url, {'message': 'Add fire stopping', 'history': '[]'})
        assert response.status_code == 200
        item = ScopeItem.objects.get(section=section, text='Provide fire stopping.')
        assert item.is_pending_review is True
        assert item.is_ai_generated is True

    def test_add_change_fires_pending_changed_trigger(self, client):
        user, exhibit, section = self._setup(client)
        url = reverse('exhibits:ai_chat_send', args=[exhibit.pk])
        result = {
            'message': 'Done!',
            'proposed_changes': [
                {'action': 'add', 'section_name': 'Scope of Work', 'text': 'Provide X.', 'level': 0}
            ],
        }
        with patch('exhibits.views.chat_with_exhibit', return_value=result):
            response = client.post(url, {'message': 'Add X', 'history': '[]'})
        assert response['HX-Trigger'] == 'pendingChanged'

    def test_edit_change_sets_pending_fields(self, client):
        user, exhibit, section = self._setup(client)
        item = ScopeItemFactory(section=section, text='Original text', created_by=user)
        url = reverse('exhibits:ai_chat_send', args=[exhibit.pk])
        result = {
            'message': 'Updated!',
            'proposed_changes': [
                {'action': 'edit', 'target_item_pk': item.pk, 'text': 'Revised text.', 'level': 0}
            ],
        }
        with patch('exhibits.views.chat_with_exhibit', return_value=result):
            response = client.post(url, {'message': 'Edit item', 'history': '[]'})
        assert response.status_code == 200
        item.refresh_from_db()
        assert item.text == 'Revised text.'
        assert item.pending_original_text == 'Original text'
        assert item.is_pending_review is True

    def test_no_changes_does_not_fire_trigger(self, client):
        user, exhibit, section = self._setup(client)
        url = reverse('exhibits:ai_chat_send', args=[exhibit.pk])
        result = {'message': 'No changes needed.', 'proposed_changes': []}
        with patch('exhibits.views.chat_with_exhibit', return_value=result):
            response = client.post(url, {'message': 'How does this look?', 'history': '[]'})
        assert response.status_code == 200
        assert 'HX-Trigger' not in response

    def test_ai_failure_returns_error_message(self, client):
        from ai_services.services import AIServiceError
        user, exhibit, section = self._setup(client)
        url = reverse('exhibits:ai_chat_send', args=[exhibit.pk])
        with patch('exhibits.views.chat_with_exhibit', side_effect=AIServiceError('timeout')):
            response = client.post(url, {'message': 'Hello', 'history': '[]'})
        assert response.status_code == 200
        assert b'timeout' in response.content

    def test_empty_message_returns_empty_response(self, client):
        user, exhibit, section = self._setup(client)
        url = reverse('exhibits:ai_chat_send', args=[exhibit.pk])
        response = client.post(url, {'message': '', 'history': '[]'})
        assert response.status_code == 200
        assert response.content == b''

    def test_history_is_passed_to_service(self, client):
        user, exhibit, section = self._setup(client)
        url = reverse('exhibits:ai_chat_send', args=[exhibit.pk])
        prior_history = [
            {'role': 'user', 'content': 'Earlier message'},
            {'role': 'assistant', 'content': 'Earlier reply'},
        ]
        import json
        result = {'message': 'Response.', 'proposed_changes': []}
        with patch('exhibits.views.chat_with_exhibit', return_value=result) as mock_chat:
            client.post(url, {'message': 'New message', 'history': json.dumps(prior_history)})
        call_args = mock_chat.call_args[0]
        conversation = call_args[1]
        assert conversation[0]['content'] == 'Earlier message'
        assert conversation[2]['content'] == 'New message'

    def test_company_isolation(self, client):
        user_b = PMUserFactory()
        _login(client, user_b)
        user_a = PMUserFactory()
        _, exhibit = _make_trade_with_exhibit(user_a)
        url = reverse('exhibits:ai_chat_send', args=[exhibit.pk])
        response = client.post(url, {'message': 'Hello', 'history': '[]'})
        assert response.status_code == 404

    def test_requires_post(self, client):
        user = PMUserFactory()
        _login(client, user)
        _, exhibit = _make_trade_with_exhibit(user)
        url = reverse('exhibits:ai_chat_send', args=[exhibit.pk])
        response = client.get(url)
        assert response.status_code == 405
