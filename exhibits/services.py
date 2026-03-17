import re

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


def accept_ai_item(item):
    """Accept an AI-proposed item: clear pending state, keep text as-is."""
    item.is_pending_review = False
    item.pending_original_text = ''
    item.save(update_fields=['is_pending_review', 'pending_original_text', 'updated_at'])


def reject_ai_item(item):
    """
    Reject an AI-proposed item.
    - Edit proposal (pending_original_text non-empty): restore original text.
    - New item proposal (pending_original_text empty): delete the item and all descendants.
    """
    if item.pending_original_text:
        item.text = item.pending_original_text
        item.is_pending_review = False
        item.pending_original_text = ''
        item.save(update_fields=['text', 'is_pending_review', 'pending_original_text', 'updated_at'])
    else:
        descendants = _collect_descendants(item)
        pks_to_delete = [d.pk for d in descendants] + [item.pk]
        ScopeItem.objects.filter(pk__in=pks_to_delete).delete()


@transaction.atomic
def accept_all_pending(exhibit):
    """Accept all pending AI items across the exhibit."""
    ScopeItem.objects.filter(
        section__scope_exhibit=exhibit,
        is_pending_review=True,
    ).update(is_pending_review=False, pending_original_text='')


@transaction.atomic
def reject_all_pending(exhibit):
    """
    Reject all pending AI items across the exhibit.
    Items with pending_original_text are restored; new items (empty original) are deleted.
    """
    pending = list(
        ScopeItem.objects.filter(section__scope_exhibit=exhibit, is_pending_review=True)
    )

    to_restore = [i for i in pending if i.pending_original_text]
    to_delete = [i for i in pending if not i.pending_original_text]

    if to_restore:
        for item in to_restore:
            item.text = item.pending_original_text
            item.is_pending_review = False
            item.pending_original_text = ''
        ScopeItem.objects.bulk_update(to_restore, ['text', 'is_pending_review', 'pending_original_text'])

    if to_delete:
        # Collect all descendants of new items to ensure clean deletion
        descendant_pks = []
        for item in to_delete:
            descendant_pks.extend(d.pk for d in _collect_descendants(item))
        delete_pks = descendant_pks + [i.pk for i in to_delete]
        ScopeItem.objects.filter(pk__in=delete_pks).delete()


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


# ---------------------------------------------------------------------------
# Multi-line paste support
# ---------------------------------------------------------------------------

# Dotted numeric: "1.", "1.1", "1.1.1", "2.3.1." etc.
_RE_DOTTED = re.compile(r'^(\d+(?:\.\d+)*)\.\s+(.*)')
# Dotted numeric without trailing dot: "1.1 text" (level from dot count)
_RE_DOTTED_NO_TRAIL = re.compile(r'^(\d+(?:\.\d+)+)\s+(.*)')
# Single number with dot: "1. text"
_RE_SINGLE_NUM = re.compile(r'^\d+\.\s+(.*)')
# Lettered: "A.", "a)", "(a)", "A)" etc.
_RE_LETTER = re.compile(r'^(?:\(?[A-Za-z]\)|[A-Za-z][\.\)])\s+(.*)')
# Bullet: starts with -, *, or bullet char after optional whitespace
_RE_BULLET = re.compile(r'^[\-\*\u2022]\s+(.*)')


def parse_pasted_items(raw_text):
    """Parse pasted text into a list of {'text': ..., 'level': ...} dicts.

    Detects hierarchy from numbering prefixes or indentation.
    Pure function — no database access.
    """
    text = raw_text.replace('\r\n', '\n').replace('\r', '\n')
    lines = [line for line in text.split('\n') if line.strip()]

    if not lines:
        return []

    if len(lines) == 1:
        return [{'text': lines[0].strip(), 'level': 0}]

    parsed = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # 1) Dotted numeric with trailing dot: "1.1. text" → level = dot-count - 1
        m = _RE_DOTTED.match(stripped)
        if m:
            level = m.group(1).count('.')
            parsed.append({'text': m.group(2).strip(), 'level': level})
            continue

        # 2) Dotted numeric without trailing dot: "1.1 text"
        m = _RE_DOTTED_NO_TRAIL.match(stripped)
        if m:
            level = m.group(1).count('.')
            parsed.append({'text': m.group(2).strip(), 'level': level})
            continue

        # 3) Single number: "1. text" → level 0
        m = _RE_SINGLE_NUM.match(stripped)
        if m:
            parsed.append({'text': m.group(1).strip(), 'level': 0})
            continue

        # 4) Lettered: "A.", "a)", "(a)" → level 0
        m = _RE_LETTER.match(stripped)
        if m:
            parsed.append({'text': m.group(1).strip(), 'level': 0})
            continue

        # 5) Bullet with indentation
        leading = len(line) - len(line.lstrip())
        # Expand tabs to 4 spaces for indent calculation
        leading_expanded = len(line.expandtabs(4)) - len(line.expandtabs(4).lstrip())
        m = _RE_BULLET.match(stripped)
        if m:
            indent_level = leading_expanded // 2 if leading_expanded else 0
            parsed.append({'text': m.group(1).strip(), 'level': indent_level})
            continue

        # 6) Plain indentation
        if leading_expanded > 0:
            indent_level = leading_expanded // 2
            parsed.append({'text': stripped, 'level': indent_level})
            continue

        # 7) No prefix, no indent → level 0
        parsed.append({'text': stripped, 'level': 0})

    # Clamp level jumps: max +1 from previous, cap at 3
    prev_level = 0
    for item in parsed:
        item['level'] = min(item['level'], prev_level + 1, 3)
        prev_level = item['level']

    return parsed


@transaction.atomic
def bulk_add_items(section, parsed_items, user):
    """Create ScopeItems from parsed paste data with correct parent/level/order.

    Items are appended after existing items in the section.
    All items are created with is_pending_review=True.
    """
    last = section.items.order_by('-order').values_list('order', flat=True).first()
    next_order = (last + 1) if last is not None else 0

    parent_at_level = {}
    created = []
    for i, item_data in enumerate(parsed_items):
        text = item_data['text']
        level = item_data['level']
        parent = parent_at_level.get(level - 1) if level > 0 else None

        item = ScopeItem.objects.create(
            section=section,
            text=text,
            level=level,
            parent=parent,
            order=next_order + i,
            is_pending_review=True,
            created_by=user,
        )
        parent_at_level[level] = item
        created.append(item)

    return created
