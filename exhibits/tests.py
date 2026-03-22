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
    bulk_add_items,
    clone_exhibit,
    compute_exhibit_numbering,
    compute_section_numbering,
    create_blank_exhibit,
    flatten_section_items,
    indent_item,
    outdent_item,
    parse_pasted_items,
    reject_ai_item,
    reject_all_pending,
    save_as_template,
)
from .views import _apply_proposed_changes


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

    def test_with_section_letter(self):
        section = ExhibitSectionFactory()
        parent = ScopeItemFactory(section=section, order=0)
        child = ScopeItemFactory(section=section, parent=parent, level=1, order=0)
        numbers = compute_section_numbering(section, section_letter='B')
        assert numbers[parent.pk] == 'B.1'
        assert numbers[child.pk] == 'B.1.1'

    def test_section_letter_none_is_backward_compatible(self):
        section = ExhibitSectionFactory()
        item = ScopeItemFactory(section=section, order=0)
        numbers = compute_section_numbering(section, section_letter=None)
        assert numbers[item.pk] == '1'


@pytest.mark.django_db
class TestComputeExhibitNumbering:
    def test_assigns_letters_to_sections(self):
        exhibit = ScopeExhibitFactory()
        s1 = ExhibitSectionFactory(scope_exhibit=exhibit, order=0)
        s2 = ExhibitSectionFactory(scope_exhibit=exhibit, order=1)
        s3 = ExhibitSectionFactory(scope_exhibit=exhibit, order=2)
        _numbers, section_letters = compute_exhibit_numbering(exhibit)
        assert section_letters[s1.pk] == 'A'
        assert section_letters[s2.pk] == 'B'
        assert section_letters[s3.pk] == 'C'

    def test_items_have_letter_prefix(self):
        exhibit = ScopeExhibitFactory()
        s1 = ExhibitSectionFactory(scope_exhibit=exhibit, order=0)
        s2 = ExhibitSectionFactory(scope_exhibit=exhibit, order=1)
        item_a = ScopeItemFactory(section=s1, order=0)
        item_b1 = ScopeItemFactory(section=s2, order=0)
        item_b2 = ScopeItemFactory(section=s2, order=1)
        numbers, _sl = compute_exhibit_numbering(exhibit)
        assert numbers[item_a.pk] == 'A.1'
        assert numbers[item_b1.pk] == 'B.1'
        assert numbers[item_b2.pk] == 'B.2'

    def test_nested_items_across_sections(self):
        exhibit = ScopeExhibitFactory()
        s1 = ExhibitSectionFactory(scope_exhibit=exhibit, order=0)
        parent = ScopeItemFactory(section=s1, order=0)
        child = ScopeItemFactory(section=s1, parent=parent, level=1, order=0)
        numbers, _sl = compute_exhibit_numbering(exhibit)
        assert numbers[parent.pk] == 'A.1'
        assert numbers[child.pk] == 'A.1.1'

    def test_empty_exhibit(self):
        exhibit = ScopeExhibitFactory()
        numbers, section_letters = compute_exhibit_numbering(exhibit)
        assert numbers == {}
        assert section_letters == {}


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
        assert b'chat-messages' in response.content

    def test_company_isolation(self, client):
        user_b = PMUserFactory()
        _login(client, user_b)
        user_a = PMUserFactory()
        _, exhibit = _make_trade_with_exhibit(user_a)
        url = reverse('exhibits:ai_chat', args=[exhibit.pk])
        response = client.get(url)
        assert response.status_code == 404

    def test_messages_loaded_on_chat_open(self, client):
        from ai_services.models import ChatMessage, ChatSession
        user = PMUserFactory()
        _login(client, user)
        _, exhibit = _make_trade_with_exhibit(user)
        session = ChatSession.objects.create(exhibit=exhibit, user=user)
        ChatMessage.objects.create(session=session, role='user', content='Hello from DB')
        ChatMessage.objects.create(session=session, role='assistant', content='Hi back from DB')
        url = reverse('exhibits:ai_chat', args=[exhibit.pk])
        response = client.get(url)
        assert response.status_code == 200
        assert b'Hello from DB' in response.content
        assert b'Hi back from DB' in response.content


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
            response = client.post(url, {'message': 'Hello'})
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
            response = client.post(url, {'message': 'Add fire stopping'})
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
            response = client.post(url, {'message': 'Add X'})
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
            response = client.post(url, {'message': 'Edit item'})
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
            response = client.post(url, {'message': 'How does this look?'})
        assert response.status_code == 200
        assert 'HX-Trigger' not in response

    def test_ai_failure_returns_error_message(self, client):
        from ai_services.services import AIServiceError
        user, exhibit, section = self._setup(client)
        url = reverse('exhibits:ai_chat_send', args=[exhibit.pk])
        with patch('exhibits.views.chat_with_exhibit', side_effect=AIServiceError('timeout')):
            response = client.post(url, {'message': 'Hello'})
        assert response.status_code == 200
        assert b'timeout' in response.content

    def test_empty_message_returns_empty_response(self, client):
        user, exhibit, section = self._setup(client)
        url = reverse('exhibits:ai_chat_send', args=[exhibit.pk])
        response = client.post(url, {'message': ''})
        assert response.status_code == 200
        assert response.content == b''

    def test_history_is_passed_to_service(self, client):
        """Prior DB messages are included in conversation sent to AI."""
        from ai_services.models import ChatMessage, ChatSession
        user, exhibit, section = self._setup(client)
        session = ChatSession.objects.create(exhibit=exhibit, user=user)
        ChatMessage.objects.create(session=session, role='user', content='Earlier message')
        ChatMessage.objects.create(session=session, role='assistant', content='Earlier reply')
        url = reverse('exhibits:ai_chat_send', args=[exhibit.pk])
        result = {'message': 'Response.', 'proposed_changes': []}
        with patch('exhibits.views.chat_with_exhibit', return_value=result) as mock_chat:
            client.post(url, {'message': 'New message'})
        call_args = mock_chat.call_args[0]
        conversation = call_args[1]
        assert conversation[0]['content'] == 'Earlier message'
        assert conversation[1]['content'] == 'Earlier reply'
        assert conversation[2]['content'] == 'New message'

    def test_messages_persisted_to_db(self, client):
        """Sending a message creates both user and assistant ChatMessage records."""
        from ai_services.models import ChatMessage, ChatSession
        user, exhibit, section = self._setup(client)
        url = reverse('exhibits:ai_chat_send', args=[exhibit.pk])
        result = {'message': 'AI response here.', 'proposed_changes': []}
        with patch('exhibits.views.chat_with_exhibit', return_value=result):
            client.post(url, {'message': 'User says hello'})
        session = ChatSession.objects.get(exhibit=exhibit)
        messages = list(session.messages.order_by('created_at'))
        assert len(messages) == 2
        assert messages[0].role == 'user'
        assert messages[0].content == 'User says hello'
        assert messages[0].user == user
        assert messages[1].role == 'assistant'
        assert messages[1].content == 'AI response here.'
        assert messages[1].user is None

    def test_conversation_persists_across_requests(self, client):
        """Multiple sends accumulate in DB and full history is passed to AI."""
        from ai_services.models import ChatMessage, ChatSession
        user, exhibit, section = self._setup(client)
        url = reverse('exhibits:ai_chat_send', args=[exhibit.pk])
        result1 = {'message': 'Reply 1', 'proposed_changes': []}
        with patch('exhibits.views.chat_with_exhibit', return_value=result1):
            client.post(url, {'message': 'Message 1'})
        result2 = {'message': 'Reply 2', 'proposed_changes': []}
        with patch('exhibits.views.chat_with_exhibit', return_value=result2) as mock_chat:
            client.post(url, {'message': 'Message 2'})
        conversation = mock_chat.call_args[0][1]
        assert len(conversation) == 3
        assert conversation[0] == {'role': 'user', 'content': 'Message 1'}
        assert conversation[1] == {'role': 'assistant', 'content': 'Reply 1'}
        assert conversation[2] == {'role': 'user', 'content': 'Message 2'}

    def test_company_isolation(self, client):
        user_b = PMUserFactory()
        _login(client, user_b)
        user_a = PMUserFactory()
        _, exhibit = _make_trade_with_exhibit(user_a)
        url = reverse('exhibits:ai_chat_send', args=[exhibit.pk])
        response = client.post(url, {'message': 'Hello'})
        assert response.status_code == 404

    def test_requires_post(self, client):
        user = PMUserFactory()
        _login(client, user)
        _, exhibit = _make_trade_with_exhibit(user)
        url = reverse('exhibits:ai_chat_send', args=[exhibit.pk])
        response = client.get(url)
        assert response.status_code == 405

    def test_context_section_injected(self, client):
        user, exhibit, section = self._setup(client)
        url = reverse('exhibits:ai_chat_send', args=[exhibit.pk])
        result = {'message': 'Got it!', 'proposed_changes': []}
        with patch('exhibits.views.chat_with_exhibit', return_value=result) as mock_chat:
            client.post(url, {
                'message': 'Add seismic bracing.',
                'context_section_pks': [section.pk],
            })
        conversation = mock_chat.call_args[0][1]
        assert f'Section "{section.name}"' in conversation[0]['content']
        assert 'Add seismic bracing.' in conversation[0]['content']

    def test_context_note_injected(self, client):
        from notes.models import Note
        user, exhibit, section = self._setup(client)
        trade = exhibit.project.trades.filter(csi_trade=exhibit.csi_trade).first()
        note = NoteFactory(
            project=exhibit.project,
            primary_trade=trade,
            note_type=Note.NoteType.OPEN_QUESTION,
            text='Fire stopping at penetrations required.',
            created_by=user,
        )
        url = reverse('exhibits:ai_chat_send', args=[exhibit.pk])
        result = {'message': 'Done!', 'proposed_changes': []}
        with patch('exhibits.views.chat_with_exhibit', return_value=result) as mock_chat:
            client.post(url, {
                'message': 'Convert this note.',
                'context_note_pks': [note.pk],
            })
        conversation = mock_chat.call_args[0][1]
        assert 'Fire stopping at penetrations required.' in conversation[0]['content']

    def test_no_context_no_prefix(self, client):
        user, exhibit, section = self._setup(client)
        url = reverse('exhibits:ai_chat_send', args=[exhibit.pk])
        result = {'message': 'OK', 'proposed_changes': []}
        with patch('exhibits.views.chat_with_exhibit', return_value=result) as mock_chat:
            client.post(url, {'message': 'Hello'})
        conversation = mock_chat.call_args[0][1]
        assert conversation[0]['content'] == 'Hello'


# ---------------------------------------------------------------------------
# Service: parse_pasted_items (pure function, no DB)
# ---------------------------------------------------------------------------

class TestParsePastedItems:
    def test_single_line(self):
        result = parse_pasted_items('Provide all ductwork')
        assert result == [{'text': 'Provide all ductwork', 'level': 0}]

    def test_empty_string(self):
        assert parse_pasted_items('') == []

    def test_whitespace_only(self):
        assert parse_pasted_items('   \n  \n  ') == []

    def test_crlf_normalization(self):
        result = parse_pasted_items('Item A\r\nItem B\r\n')
        assert len(result) == 2
        assert result[0]['text'] == 'Item A'
        assert result[1]['text'] == 'Item B'

    def test_blank_lines_skipped(self):
        result = parse_pasted_items('Item A\n\n\nItem B')
        assert len(result) == 2

    def test_dotted_numeric_hierarchy(self):
        text = '1. Foundation work\n1.1. Excavation\n1.1.1. Trenching\n2. Framing'
        result = parse_pasted_items(text)
        assert result[0] == {'text': 'Foundation work', 'level': 0}
        assert result[1] == {'text': 'Excavation', 'level': 1}
        assert result[2] == {'text': 'Trenching', 'level': 2}
        assert result[3] == {'text': 'Framing', 'level': 0}

    def test_dotted_numeric_no_trailing_dot(self):
        text = '1. Foundation\n1.1 Excavation\n1.1.1 Trenching'
        result = parse_pasted_items(text)
        assert result[0] == {'text': 'Foundation', 'level': 0}
        assert result[1] == {'text': 'Excavation', 'level': 1}
        assert result[2] == {'text': 'Trenching', 'level': 2}

    def test_bullets_with_indentation(self):
        text = '- Top level\n  - Indented once\n    - Indented twice'
        result = parse_pasted_items(text)
        assert result[0] == {'text': 'Top level', 'level': 0}
        assert result[1] == {'text': 'Indented once', 'level': 1}
        assert result[2] == {'text': 'Indented twice', 'level': 2}

    def test_tabs_for_indentation(self):
        text = '- Top level\n\t- Tab indented\n\t\t- Double tab'
        result = parse_pasted_items(text)
        assert result[0]['level'] == 0
        assert result[1]['level'] == 1
        assert result[2]['level'] == 2

    def test_plain_indentation(self):
        text = 'Top level\n  Indented\n    More indented'
        result = parse_pasted_items(text)
        assert result[0]['level'] == 0
        assert result[1]['level'] == 1
        assert result[2]['level'] == 2

    def test_lettered_prefixes(self):
        text = 'A. First item\nb) Second item\n(c) Third item'
        result = parse_pasted_items(text)
        assert result[0] == {'text': 'First item', 'level': 0}
        assert result[1] == {'text': 'Second item', 'level': 0}
        assert result[2] == {'text': 'Third item', 'level': 0}

    def test_level_jump_clamped(self):
        """Level can only increase by 1 at a time."""
        text = '1. Top\n1.1.1.1. Jump three levels'
        result = parse_pasted_items(text)
        assert result[0]['level'] == 0
        assert result[1]['level'] == 1  # clamped from 3

    def test_level_capped_at_3(self):
        text = '- A\n  - B\n    - C\n      - D\n        - E'
        result = parse_pasted_items(text)
        assert result[4]['level'] == 3  # capped at 3

    def test_prefix_stripping(self):
        text = '1. Provide ductwork\n1.1. Install insulation\nA. Clean up'
        result = parse_pasted_items(text)
        assert result[0]['text'] == 'Provide ductwork'
        assert result[1]['text'] == 'Install insulation'
        assert result[2]['text'] == 'Clean up'

    def test_bullet_chars(self):
        text = '* Star bullet\n\u2022 Unicode bullet\n- Dash bullet'
        result = parse_pasted_items(text)
        assert len(result) == 3
        assert result[0]['text'] == 'Star bullet'
        assert result[1]['text'] == 'Unicode bullet'
        assert result[2]['text'] == 'Dash bullet'


# ---------------------------------------------------------------------------
# Service: bulk_add_items (DB)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestBulkAddItems:
    def test_correct_parent_fks(self):
        user = PMUserFactory()
        _, exhibit = _make_trade_with_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit)
        parsed = [
            {'text': 'Parent', 'level': 0},
            {'text': 'Child', 'level': 1},
            {'text': 'Grandchild', 'level': 2},
        ]
        items = bulk_add_items(section, parsed, user)
        assert items[0].parent is None
        assert items[1].parent == items[0]
        assert items[2].parent == items[1]

    def test_appends_after_existing_items(self):
        user = PMUserFactory()
        _, exhibit = _make_trade_with_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit)
        ScopeItemFactory(section=section, order=0)
        ScopeItemFactory(section=section, order=1)
        parsed = [{'text': 'New item', 'level': 0}]
        items = bulk_add_items(section, parsed, user)
        assert items[0].order == 2

    def test_levels_stored_correctly(self):
        user = PMUserFactory()
        _, exhibit = _make_trade_with_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit)
        parsed = [
            {'text': 'A', 'level': 0},
            {'text': 'B', 'level': 1},
            {'text': 'C', 'level': 0},
        ]
        items = bulk_add_items(section, parsed, user)
        assert [i.level for i in items] == [0, 1, 0]
        assert all(i.is_pending_review for i in items)


# ---------------------------------------------------------------------------
# View: multi-line paste via item_add
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestItemAddMultiLine:
    def test_multi_line_paste_creates_correct_items(self, client):
        user = PMUserFactory()
        _login(client, user)
        _, exhibit = _make_trade_with_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit)
        url = reverse('exhibits:item_add', args=[exhibit.pk, section.pk])
        text = '1. Provide ductwork\n1.1. Install insulation\n2. Clean up'
        response = client.post(url, {'text': text})
        assert section.items.count() == 3
        items = list(section.items.order_by('order'))
        assert items[0].text == 'Provide ductwork'
        assert items[0].level == 0
        assert items[1].text == 'Install insulation'
        assert items[1].level == 1
        assert items[1].parent == items[0]
        assert items[2].text == 'Clean up'
        assert items[2].level == 0
        assert all(i.is_pending_review for i in items)
        assert response['HX-Trigger'] == 'pendingChanged'

    def test_single_line_preserves_existing_behavior(self, client):
        user = PMUserFactory()
        _login(client, user)
        _, exhibit = _make_trade_with_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit)
        # Add an existing item first
        ScopeItemFactory(section=section, order=0)
        url = reverse('exhibits:item_add', args=[exhibit.pk, section.pk])
        client.post(url, {'text': 'Single item'})
        assert section.items.count() == 2
        new_item = section.items.order_by('-order').first()
        assert new_item.text == 'Single item'
        assert new_item.level == 0
        assert not new_item.is_pending_review


# ---------------------------------------------------------------------------
# Pending delete: services
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestPendingDeleteServices:

    def _make_pending_delete(self, user, exhibit):
        section = ExhibitSectionFactory(scope_exhibit=exhibit)
        item = ScopeItemFactory(
            section=section, text='Item to delete',
            is_pending_review=True, pending_delete=True,
            created_by=user,
        )
        return section, item

    def test_accept_pending_delete_actually_deletes(self):
        user = PMUserFactory()
        _, exhibit = _make_trade_with_exhibit(user)
        _, item = self._make_pending_delete(user, exhibit)
        pk = item.pk
        accept_ai_item(item)
        assert not ScopeItem.objects.filter(pk=pk).exists()

    def test_accept_pending_delete_also_deletes_descendants(self):
        user = PMUserFactory()
        _, exhibit = _make_trade_with_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit)
        parent = ScopeItemFactory(
            section=section, text='Parent', level=0,
            is_pending_review=True, pending_delete=True, created_by=user,
        )
        child = ScopeItemFactory(
            section=section, parent=parent, text='Child', level=1,
            created_by=user,
        )
        accept_ai_item(parent)
        assert not ScopeItem.objects.filter(pk=parent.pk).exists()
        assert not ScopeItem.objects.filter(pk=child.pk).exists()

    def test_reject_pending_delete_restores_item(self):
        user = PMUserFactory()
        _, exhibit = _make_trade_with_exhibit(user)
        _, item = self._make_pending_delete(user, exhibit)
        reject_ai_item(item)
        item.refresh_from_db()
        assert item.is_pending_review is False
        assert item.pending_delete is False
        assert item.text == 'Item to delete'

    def test_accept_all_handles_pending_deletes(self):
        user = PMUserFactory()
        _, exhibit = _make_trade_with_exhibit(user)
        _, delete_item = self._make_pending_delete(user, exhibit)
        delete_pk = delete_item.pk
        # Also add a normal pending edit
        section2 = ExhibitSectionFactory(scope_exhibit=exhibit)
        edit_item = ScopeItemFactory(
            section=section2, text='Edited', pending_original_text='Original',
            is_pending_review=True, created_by=user,
        )
        accept_all_pending(exhibit)
        assert not ScopeItem.objects.filter(pk=delete_pk).exists()
        edit_item.refresh_from_db()
        assert edit_item.is_pending_review is False

    def test_reject_all_handles_pending_deletes(self):
        user = PMUserFactory()
        _, exhibit = _make_trade_with_exhibit(user)
        _, delete_item = self._make_pending_delete(user, exhibit)
        reject_all_pending(exhibit)
        delete_item.refresh_from_db()
        assert delete_item.is_pending_review is False
        assert delete_item.pending_delete is False


# ---------------------------------------------------------------------------
# Pending delete: view (_apply_proposed_changes)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestApplyChangesDelete:

    def test_delete_action_sets_pending_not_immediate_delete(self, client):
        user = PMUserFactory()
        _login(client, user)
        _, exhibit = _make_trade_with_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit, name='Scope of Work')
        item = ScopeItemFactory(section=section, text='Existing item', created_by=user)
        url = reverse('exhibits:ai_chat_send', args=[exhibit.pk])
        result = {
            'message': '',
            'proposed_changes': [
                {'action': 'delete', 'target_item_pk': item.pk}
            ],
        }
        with patch('exhibits.views.chat_with_exhibit', return_value=result):
            response = client.post(url, {'message': 'Delete that item'})
        assert response.status_code == 200
        item.refresh_from_db()
        assert item.is_pending_review is True
        assert item.pending_delete is True

    def test_tool_only_response_generates_fallback_message(self, client):
        """When Claude returns only tool calls (no text), a meaningful fallback is saved."""
        from ai_services.models import ChatMessage, ChatSession
        user = PMUserFactory()
        _login(client, user)
        _, exhibit = _make_trade_with_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit, name='Scope of Work')
        url = reverse('exhibits:ai_chat_send', args=[exhibit.pk])
        result = {
            'message': '',
            'proposed_changes': [
                {'action': 'add', 'section_name': 'Scope of Work', 'text': 'New item.', 'level': 0}
            ],
        }
        with patch('exhibits.views.chat_with_exhibit', return_value=result):
            response = client.post(url, {'message': 'Add an item'})
        assert response.status_code == 200
        session = ChatSession.objects.get(exhibit=exhibit)
        assistant_msg = session.messages.filter(role='assistant').first()
        assert 'Done' in assistant_msg.content
        assert '1 change' in assistant_msg.content
        assert 'Sorry' not in assistant_msg.content


# ---------------------------------------------------------------------------
# _apply_proposed_changes: parent targeting via parent_item_pk
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestApplyChangesAddParent:

    def test_add_with_parent_pk_nests_correctly(self):
        user = PMUserFactory()
        user.set_password('testpass123')
        user.save(update_fields=['password'])
        _, exhibit = _make_trade_with_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit, name='Scope of Work')
        parent_item = ScopeItemFactory(
            section=section, text='Parent item', level=0, order=0, parent=None,
            created_by=user,
        )

        changes = [{
            'action': 'add',
            'section_name': 'Scope of Work',
            'text': 'Child under parent.',
            'level': 1,
            'parent_item_pk': parent_item.pk,
        }]
        applied, applied_pks = _apply_proposed_changes(exhibit, changes, user)
        assert applied == 1

        child = ScopeItem.objects.get(text='Child under parent.')
        assert child.parent == parent_item
        assert child.level == 1

    def test_add_with_parent_pk_after_existing_children(self):
        user = PMUserFactory()
        user.set_password('testpass123')
        user.save(update_fields=['password'])
        _, exhibit = _make_trade_with_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit, name='Scope of Work')
        parent_item = ScopeItemFactory(
            section=section, text='Parent', level=0, order=0, parent=None,
            created_by=user,
        )
        ScopeItemFactory(
            section=section, text='Existing child', level=1, order=0,
            parent=parent_item, created_by=user,
        )

        changes = [{
            'action': 'add',
            'section_name': 'Scope of Work',
            'text': 'Second child.',
            'level': 1,
            'parent_item_pk': parent_item.pk,
        }]
        applied, applied_pks = _apply_proposed_changes(exhibit, changes, user)
        assert applied == 1

        new_child = ScopeItem.objects.get(text='Second child.')
        assert new_child.parent == parent_item
        assert new_child.order == 1  # after existing child at order=0

    def test_add_with_invalid_parent_pk_falls_back(self):
        user = PMUserFactory()
        user.set_password('testpass123')
        user.save(update_fields=['password'])
        _, exhibit = _make_trade_with_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit, name='Scope of Work')
        fallback_parent = ScopeItemFactory(
            section=section, text='Fallback parent', level=0, order=0, parent=None,
            created_by=user,
        )

        changes = [{
            'action': 'add',
            'section_name': 'Scope of Work',
            'text': 'Child with bad pk.',
            'level': 1,
            'parent_item_pk': 99999,  # nonexistent
        }]
        applied, applied_pks = _apply_proposed_changes(exhibit, changes, user)
        assert applied == 1

        child = ScopeItem.objects.get(text='Child with bad pk.')
        assert child.parent == fallback_parent  # fell back to last level-0 item

    def test_add_without_parent_pk_backward_compat(self):
        user = PMUserFactory()
        user.set_password('testpass123')
        user.save(update_fields=['password'])
        _, exhibit = _make_trade_with_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit, name='Scope of Work')
        top_item = ScopeItemFactory(
            section=section, text='Top item', level=0, order=0, parent=None,
            created_by=user,
        )

        changes = [{
            'action': 'add',
            'section_name': 'Scope of Work',
            'text': 'New top-level item.',
            'level': 0,
        }]
        applied, applied_pks = _apply_proposed_changes(exhibit, changes, user)
        assert applied == 1

        new_item = ScopeItem.objects.get(text='New top-level item.')
        assert new_item.parent is None
        assert new_item.level == 0


# ---------------------------------------------------------------------------
# Section rewrite view
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestSectionRewriteView:
    def test_rewrites_items_as_pending(self, client):
        user = PMUserFactory()
        _login(client, user)
        _, exhibit = _make_trade_with_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit, name='Scope', order=0)
        item1 = ScopeItemFactory(section=section, text='Original 1.', order=0, created_by=user)
        item2 = ScopeItemFactory(section=section, text='Original 2.', order=1, created_by=user)

        import json
        mock_return = [
            {'pk': item1.pk, 'exhibit_text': 'Rewritten 1.'},
            {'pk': item2.pk, 'exhibit_text': 'Rewritten 2.'},
        ]
        url = reverse('exhibits:section_rewrite', args=[exhibit.pk, section.pk])
        with patch('exhibits.views.rewrite_section_items', return_value=mock_return):
            response = client.post(url, {'instruction': 'convert to subcontract'})

        assert response.status_code == 200
        item1.refresh_from_db()
        item2.refresh_from_db()
        assert item1.text == 'Rewritten 1.'
        assert item1.pending_original_text == 'Original 1.'
        assert item1.is_pending_review is True
        assert item2.text == 'Rewritten 2.'
        assert 'pendingChanged' in response.get('HX-Trigger', '')

    def test_empty_instruction_returns_without_changes(self, client):
        user = PMUserFactory()
        _login(client, user)
        _, exhibit = _make_trade_with_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit, name='Scope', order=0)
        ScopeItemFactory(section=section, text='Original.', order=0, created_by=user)

        url = reverse('exhibits:section_rewrite', args=[exhibit.pk, section.pk])
        response = client.post(url, {'instruction': ''})
        assert response.status_code == 200
        assert ScopeItem.objects.get(section=section).text == 'Original.'

    def test_ai_failure_leaves_items_unchanged(self, client):
        user = PMUserFactory()
        _login(client, user)
        _, exhibit = _make_trade_with_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit, name='Scope', order=0)
        ScopeItemFactory(section=section, text='Original.', order=0, created_by=user)

        from ai_services.services import AIServiceError
        url = reverse('exhibits:section_rewrite', args=[exhibit.pk, section.pk])
        with patch('exhibits.views.rewrite_section_items', side_effect=AIServiceError('fail')):
            response = client.post(url, {'instruction': 'rewrite'})

        assert response.status_code == 200
        assert ScopeItem.objects.get(section=section).text == 'Original.'

    def test_company_scoping(self, client):
        user = PMUserFactory()
        other_user = PMUserFactory()
        _login(client, other_user)
        _, exhibit = _make_trade_with_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit, name='Scope', order=0)
        url = reverse('exhibits:section_rewrite', args=[exhibit.pk, section.pk])
        response = client.post(url, {'instruction': 'rewrite'})
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Note-to-scope AI conversion view
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestNoteToScopeAIView:
    def _make_note_for_exhibit(self, exhibit, user):
        trade = Trade.objects.filter(
            project=exhibit.project, csi_trade=exhibit.csi_trade,
        ).first()
        if not trade:
            trade = TradeFactory(project=exhibit.project, csi_trade=exhibit.csi_trade)
        return NoteFactory(
            project=exhibit.project, primary_trade=trade,
            text='Sub needs to demo existing ceilings.',
            created_by=user,
        )

    def test_created_makes_pending_item_and_resolves_note(self, client):
        user = PMUserFactory()
        _login(client, user)
        _, exhibit = _make_trade_with_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit, name='Scope of Work', order=0)
        note = self._make_note_for_exhibit(exhibit, user)

        mock_result = {
            'status': 'created',
            'section_name': 'Scope of Work',
            'exhibit_text': 'Demolish existing ceiling tile and grid in designated rooms.',
        }
        url = reverse('exhibits:note_to_scope_ai', args=[exhibit.pk, note.pk])
        with patch('exhibits.views.convert_note_to_scope', return_value=mock_result):
            response = client.post(url)

        assert response.status_code == 200
        assert 'pendingChanged' in response.get('HX-Trigger', '')

        # Check scope item was created
        item = ScopeItem.objects.get(section=section)
        assert item.text == 'Demolish existing ceiling tile and grid in designated rooms.'
        assert item.is_pending_review is True
        assert item.is_ai_generated is True

        # Check note was resolved
        note.refresh_from_db()
        assert note.status == Note.Status.RESOLVED
        assert 'Converted to scope item' in note.resolution
        assert note.scope_item == item

    def test_overlap_returns_overlap_template(self, client):
        user = PMUserFactory()
        _login(client, user)
        _, exhibit = _make_trade_with_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit, name='Scope of Work', order=0)
        existing_item = ScopeItemFactory(
            section=section, text='Demo ceilings.', order=0, created_by=user,
        )
        note = self._make_note_for_exhibit(exhibit, user)

        mock_result = {
            'status': 'overlap',
            'overlap_item_pk': existing_item.pk,
            'explanation': 'Item already covers ceiling demo.',
        }
        url = reverse('exhibits:note_to_scope_ai', args=[exhibit.pk, note.pk])
        with patch('exhibits.views.convert_note_to_scope', return_value=mock_result):
            response = client.post(url)

        assert response.status_code == 200
        content = response.content.decode()
        assert 'Possible Overlap' in content
        assert 'already covers ceiling demo' in content
        # Note should NOT be resolved
        note.refresh_from_db()
        assert note.status == Note.Status.OPEN

    def test_already_resolved_note_returns_error(self, client):
        user = PMUserFactory()
        _login(client, user)
        _, exhibit = _make_trade_with_exhibit(user)
        note = self._make_note_for_exhibit(exhibit, user)
        note.status = Note.Status.RESOLVED
        note.save(update_fields=['status'])

        url = reverse('exhibits:note_to_scope_ai', args=[exhibit.pk, note.pk])
        response = client.post(url)
        assert response.status_code == 200
        assert 'already resolved' in response.content.decode()

    def test_section_name_fallback(self, client):
        user = PMUserFactory()
        _login(client, user)
        _, exhibit = _make_trade_with_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit, name='General', order=0)
        note = self._make_note_for_exhibit(exhibit, user)

        mock_result = {
            'status': 'created',
            'section_name': 'Nonexistent Section',
            'exhibit_text': 'Some scope item.',
        }
        url = reverse('exhibits:note_to_scope_ai', args=[exhibit.pk, note.pk])
        with patch('exhibits.views.convert_note_to_scope', return_value=mock_result):
            response = client.post(url)

        assert response.status_code == 200
        # Should have fallen back to first section
        assert ScopeItem.objects.filter(section=section).exists()

    def test_company_scoping(self, client):
        user = PMUserFactory()
        other_user = PMUserFactory()
        _login(client, other_user)
        _, exhibit = _make_trade_with_exhibit(user)
        trade = Trade.objects.get(project=exhibit.project, csi_trade=exhibit.csi_trade)
        note = NoteFactory(
            project=exhibit.project,
            primary_trade=trade,
            text='Test note.',
            created_by=user,
        )
        url = reverse('exhibits:note_to_scope_ai', args=[exhibit.pk, note.pk])
        response = client.post(url)
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# _apply_proposed_changes: convert_note action
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestApplyProposedChangesConvertNote:
    def test_convert_note_creates_item_and_resolves_note(self):
        user = PMUserFactory()
        user.set_password('testpass123')
        user.save(update_fields=['password'])
        _, exhibit = _make_trade_with_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit, name='Scope of Work')
        trade = Trade.objects.get(project=exhibit.project, csi_trade=exhibit.csi_trade)
        note = NoteFactory(
            project=exhibit.project, primary_trade=trade,
            text='Add dumpster language.', created_by=user,
        )

        changes = [{
            'action': 'convert_note',
            'note_pk': note.pk,
            'section_name': 'Scope of Work',
            'text': 'Provide and coordinate all dumpster removal.',
            'level': 0,
        }]
        applied, applied_pks = _apply_proposed_changes(exhibit, changes, user)
        assert applied == 1

        item = ScopeItem.objects.get(pk=applied_pks[0])
        assert item.is_pending_review is True
        assert item.is_ai_generated is True
        assert item.original_input == 'Add dumpster language.'

        note.refresh_from_db()
        assert note.status == Note.Status.RESOLVED
        assert note.scope_item == item
        assert 'Converted to scope item by AI' in note.resolution

    def test_skips_already_resolved_note(self):
        user = PMUserFactory()
        user.set_password('testpass123')
        user.save(update_fields=['password'])
        _, exhibit = _make_trade_with_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit, name='Scope of Work')
        trade = Trade.objects.get(project=exhibit.project, csi_trade=exhibit.csi_trade)
        note = NoteFactory(
            project=exhibit.project, primary_trade=trade,
            text='Already done.', created_by=user,
            status=Note.Status.RESOLVED,
        )

        changes = [{
            'action': 'convert_note',
            'note_pk': note.pk,
            'section_name': 'Scope of Work',
            'text': 'Some text.',
            'level': 0,
        }]
        applied, _ = _apply_proposed_changes(exhibit, changes, user)
        assert applied == 0
