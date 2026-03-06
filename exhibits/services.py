from django.db import transaction
from .models import ScopeExhibit, ExhibitSection, ScopeItem


def compute_section_numbering(section):
    """
    Returns {item_pk: "1.2.3"} for all items in the section.
    Numbers are assigned by tree position: top-level items get 1, 2, 3…;
    their children get 1.1, 1.2…; grandchildren get 1.1.1, etc.
    """
    all_items = list(section.items.order_by('order'))

    # Group by parent_id (None = top-level)
    children_by_parent = {}
    for item in all_items:
        children_by_parent.setdefault(item.parent_id, []).append(item)

    numbers = {}

    def assign(parent_id, prefix):
        for i, item in enumerate(children_by_parent.get(parent_id, []), start=1):
            number = f'{prefix}{i}'
            numbers[item.pk] = number
            assign(item.pk, f'{number}.')

    assign(None, '')
    return numbers

DEFAULT_SECTIONS = [
    'General Conditions',
    'Scope of Work',
    'Specific Inclusions',
    'Specific Exclusions',
    'Clarifications & Assumptions',
]


def flatten_section_items(section):
    """Return all items in DFS (tree) order for a section."""
    all_items = list(section.items.order_by('order'))
    children_by_parent = {}
    for item in all_items:
        children_by_parent.setdefault(item.parent_id, []).append(item)

    result = []

    def walk(parent_id):
        for item in children_by_parent.get(parent_id, []):
            result.append(item)
            walk(item.pk)

    walk(None)
    return result


def _collect_descendants(item):
    """Return all descendants of item (not including item itself)."""
    result = []
    for child in item.children.all():
        result.append(child)
        result.extend(_collect_descendants(child))
    return result


@transaction.atomic
def indent_item(item):
    """Make item the last child of its previous sibling."""
    siblings = list(
        ScopeItem.objects.filter(section=item.section, parent=item.parent).order_by('order')
    )
    idx = next(i for i, s in enumerate(siblings) if s.pk == item.pk)
    if idx == 0:
        return  # No previous sibling — cannot indent

    new_parent = siblings[idx - 1]

    # Append to end of new parent's children
    last = new_parent.children.order_by('-order').values_list('order', flat=True).first()
    new_order = (last + 1) if last is not None else 0

    level_delta = (new_parent.level + 1) - item.level

    item.parent = new_parent
    item.level = new_parent.level + 1
    item.order = new_order
    item.save(update_fields=['parent', 'level', 'order', 'updated_at'])

    # Remove item from old sibling list and repack orders
    remaining = [s for s in siblings if s.pk != item.pk]
    for i, s in enumerate(remaining):
        s.order = i
    if remaining:
        ScopeItem.objects.bulk_update(remaining, ['order'])

    # Cascade level change to descendants
    if level_delta != 0:
        descendants = _collect_descendants(item)
        for d in descendants:
            d.level += level_delta
        if descendants:
            ScopeItem.objects.bulk_update(descendants, ['level'])


@transaction.atomic
def outdent_item(item):
    """Move item out from under its parent, inserting after the parent."""
    if item.parent is None:
        return  # Already top-level

    old_parent = item.parent
    grandparent = old_parent.parent  # may be None

    new_level = 0 if grandparent is None else grandparent.level + 1
    level_delta = new_level - item.level

    # Remove item from current sibling group and repack
    old_siblings = list(
        ScopeItem.objects.filter(section=item.section, parent=old_parent).order_by('order')
    )
    remaining = [s for s in old_siblings if s.pk != item.pk]
    for i, s in enumerate(remaining):
        s.order = i
    if remaining:
        ScopeItem.objects.bulk_update(remaining, ['order'])

    # Insert item after old_parent in grandparent's children, then repack
    new_siblings = list(
        ScopeItem.objects.filter(section=item.section, parent=grandparent).order_by('order')
    )
    parent_idx = next(i for i, s in enumerate(new_siblings) if s.pk == old_parent.pk)
    new_siblings.insert(parent_idx + 1, item)

    item.parent = grandparent
    item.level = new_level
    item.save(update_fields=['parent', 'level', 'updated_at'])

    for i, s in enumerate(new_siblings):
        s.order = i
    ScopeItem.objects.bulk_update(new_siblings, ['order'])

    # Cascade level change to descendants
    descendants = _collect_descendants(item)
    for d in descendants:
        d.level += level_delta
    if descendants:
        ScopeItem.objects.bulk_update(descendants, ['level'])


@transaction.atomic
def save_as_template(source_exhibit, user):
    """Clone a ScopeExhibit as a reusable template (is_template=True, project=None)."""
    new_exhibit = ScopeExhibit.objects.create(
        company=user.company,
        csi_trade=source_exhibit.csi_trade,
        project=None,
        is_template=True,
        status=ScopeExhibit.Status.DRAFT,
        based_on=source_exhibit,
        created_by=user,
        last_edited_by=user,
    )

    item_map = {}

    for old_section in source_exhibit.sections.order_by('order'):
        new_section = ExhibitSection.objects.create(
            scope_exhibit=new_exhibit,
            name=old_section.name,
            order=old_section.order,
        )
        for old_item in old_section.items.order_by('order'):
            new_item = ScopeItem.objects.create(
                section=new_section,
                parent=None,
                level=old_item.level,
                text=old_item.text,
                original_input=old_item.original_input,
                is_ai_generated=old_item.is_ai_generated,
                order=old_item.order,
                created_by=user,
            )
            item_map[old_item.pk] = new_item

    items_to_update = []
    for old_section in source_exhibit.sections.all():
        for old_item in old_section.items.exclude(parent=None):
            new_item = item_map[old_item.pk]
            new_item.parent = item_map[old_item.parent_id]
            items_to_update.append(new_item)

    if items_to_update:
        ScopeItem.objects.bulk_update(items_to_update, ['parent'])

    return new_exhibit


@transaction.atomic
def create_blank_exhibit(trade, user):
    exhibit = ScopeExhibit.objects.create(
        company=user.company,
        csi_trade=trade.csi_trade,
        project=trade.project,
        is_template=False,
        status=ScopeExhibit.Status.DRAFT,
        created_by=user,
        last_edited_by=user,
    )
    ExhibitSection.objects.bulk_create([
        ExhibitSection(scope_exhibit=exhibit, name=name, order=i)
        for i, name in enumerate(DEFAULT_SECTIONS)
    ])
    return exhibit


@transaction.atomic
def clone_exhibit(source_exhibit, trade, user):
    new_exhibit = ScopeExhibit.objects.create(
        company=user.company,
        csi_trade=trade.csi_trade,
        project=trade.project,
        is_template=False,
        status=ScopeExhibit.Status.DRAFT,
        based_on=source_exhibit,
        created_by=user,
        last_edited_by=user,
    )

    # Maps old PKs → new model instances
    section_map = {}  # old_section_pk → new_section
    item_map = {}     # old_item_pk → new_item

    for old_section in source_exhibit.sections.all():
        new_section = ExhibitSection.objects.create(
            scope_exhibit=new_exhibit,
            name=old_section.name,
            order=old_section.order,
        )
        section_map[old_section.pk] = new_section

        # Pass 1: create all items without parent
        for old_item in old_section.items.all():
            new_item = ScopeItem.objects.create(
                section=new_section,
                parent=None,
                level=old_item.level,
                text=old_item.text,
                original_input=old_item.original_input,
                is_ai_generated=old_item.is_ai_generated,
                order=old_item.order,
                created_by=user,
            )
            item_map[old_item.pk] = new_item

    # Pass 2: restore parent relationships
    items_to_update = []
    for old_section in source_exhibit.sections.all():
        for old_item in old_section.items.exclude(parent=None):
            new_item = item_map[old_item.pk]
            new_item.parent = item_map[old_item.parent_id]
            items_to_update.append(new_item)

    if items_to_update:
        ScopeItem.objects.bulk_update(items_to_update, ['parent'])

    return new_exhibit
