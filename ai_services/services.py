import json
import re
import time

import anthropic
from django.conf import settings
from django.utils.html import escape as html_escape

from .models import AIRequestLog
from .prompts import (
    CHAT_SYSTEM_PROMPT,
    COMPLETENESS_SYSTEM_PROMPT,
    EXPAND_ITEM_SYSTEM_PROMPT,
    NOTE_TO_SCOPE_SYSTEM_PROMPT,
    REWRITE_ITEM_SYSTEM_PROMPT,
    REWRITE_SECTION_SYSTEM_PROMPT,
    SCOPE_FROM_DESCRIPTION_SYSTEM_PROMPT,
    SCOPE_ITEM_SYSTEM_PROMPT,
    SECTION_AI_SYSTEM_PROMPT,
)

# Exhibits with this many items or more switch to gap-fill mode
# instead of full scope generation.
GAP_FILL_THRESHOLD = 5


# ---------------------------------------------------------------------------
# Chat tool definitions (Claude Tool Use API)
# ---------------------------------------------------------------------------

CHAT_TOOLS = [
    {
        "name": "add_scope_item",
        "description": "Add a new scope item to a section of the exhibit.",
        "input_schema": {
            "type": "object",
            "properties": {
                "section_name": {"type": "string", "description": "Exact name of the target section."},
                "text": {"type": "string", "description": "The scope item text."},
                "level": {"type": "integer", "enum": [0, 1], "description": "0 = top-level, 1 = sub-item."},
                "parent_item_pk": {
                    "type": "integer",
                    "description": "pk of the parent item to nest under. Required when level=1. Omit for top-level items.",
                },
            },
            "required": ["section_name", "text", "level"],
        },
    },
    {
        "name": "edit_scope_item",
        "description": "Edit an existing scope item identified by its pk.",
        "input_schema": {
            "type": "object",
            "properties": {
                "target_item_pk": {"type": "integer", "description": "The pk of the item to edit."},
                "text": {"type": "string", "description": "The new text for the item."},
                "level": {"type": "integer", "enum": [0, 1], "description": "0 = top-level, 1 = sub-item."},
            },
            "required": ["target_item_pk", "text", "level"],
        },
    },
    {
        "name": "delete_scope_item",
        "description": "Delete an existing scope item identified by its pk.",
        "input_schema": {
            "type": "object",
            "properties": {
                "target_item_pk": {"type": "integer", "description": "The pk of the item to delete."},
            },
            "required": ["target_item_pk"],
        },
    },
    {
        "name": "convert_note_to_scope",
        "description": "Convert an open note into a scope item. Creates a pending scope item and resolves the note.",
        "input_schema": {
            "type": "object",
            "properties": {
                "note_pk": {"type": "integer", "description": "The pk of the note to convert."},
                "section_name": {"type": "string", "description": "Exact name of the target section for the new item."},
                "text": {"type": "string", "description": "The scope item text derived from the note."},
                "level": {"type": "integer", "enum": [0, 1], "description": "0 = top-level, 1 = sub-item."},
            },
            "required": ["note_pk", "section_name", "text", "level"],
        },
    },
]


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class AIDisabledError(Exception):
    """Raised when AI_ENABLED=False in settings."""
    pass


class AIServiceError(Exception):
    """Raised when the Claude API call fails after retries."""
    pass


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_client():
    return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)


def _call_claude(system_prompt, user_prompt=None, messages=None, exhibit=None, request_type=None):
    """
    Send a request to Claude and return the response text.

    - Pass user_prompt for single-turn requests (builds messages list internally).
    - Pass messages directly for multi-turn chat (list of {role, content} dicts).
    - Retries once on server errors (5xx).
    - Logs every attempt to AIRequestLog (success or failure).
    - Raises AIServiceError if all attempts fail.
    """
    if messages is None:
        messages = [{'role': 'user', 'content': user_prompt}]

    client = _get_client()
    last_error = None

    for attempt in range(2):  # try twice
        start = time.monotonic()
        try:
            response = client.messages.create(
                model='claude-sonnet-4-6',
                max_tokens=4096,
                system=system_prompt,
                messages=messages,
            )
            latency_ms = int((time.monotonic() - start) * 1000)
            tokens = response.usage.input_tokens + response.usage.output_tokens

            AIRequestLog.objects.create(
                request_type=request_type,
                exhibit=exhibit,
                success=True,
                tokens_used=tokens,
                latency_ms=latency_ms,
            )
            return response.content[0].text

        except anthropic.APITimeoutError as e:
            last_error = 'Request timed out. Please try again.'
            break  # No point retrying a timeout

        except anthropic.APIStatusError as e:
            last_error = str(e)
            # Only retry on server errors (5xx); fail immediately on 4xx
            if e.status_code < 500:
                break

        except Exception as e:
            last_error = str(e)
            break

    latency_ms = int((time.monotonic() - start) * 1000)
    AIRequestLog.objects.create(
        request_type=request_type,
        exhibit=exhibit,
        success=False,
        error_message=last_error or 'Unknown error',
        latency_ms=latency_ms,
    )
    raise AIServiceError(last_error or 'AI request failed')


def _parse_json_response(text):
    """
    Parse JSON from Claude's response text.
    Returns the parsed dict, or None if parsing fails.
    """
    try:
        # Strip markdown code fences if Claude added them despite instructions
        text = text.strip()
        if text.startswith('```'):
            text = text.split('\n', 1)[1]
            text = text.rsplit('```', 1)[0]
        return json.loads(text)
    except (json.JSONDecodeError, IndexError):
        return None


def _call_claude_with_tools(system_prompt, messages, tools, exhibit=None, request_type=None):
    """
    Send a request to Claude with tool definitions and return parsed response.

    Returns dict: {"text": "...", "tool_calls": [{"name": "...", "input": {...}}]}
    Raises AIServiceError on failure.
    """
    client = _get_client()
    last_error = None

    for attempt in range(2):
        start = time.monotonic()
        try:
            response = client.messages.create(
                model='claude-sonnet-4-6',
                max_tokens=4096,
                system=system_prompt,
                messages=messages,
                tools=tools,
            )
            latency_ms = int((time.monotonic() - start) * 1000)
            tokens = response.usage.input_tokens + response.usage.output_tokens

            AIRequestLog.objects.create(
                request_type=request_type,
                exhibit=exhibit,
                success=True,
                tokens_used=tokens,
                latency_ms=latency_ms,
            )

            # Extract text blocks and tool_use blocks
            text_parts = []
            tool_calls = []
            for block in response.content:
                if block.type == 'text':
                    text_parts.append(block.text)
                elif block.type == 'tool_use':
                    tool_calls.append({'name': block.name, 'input': block.input})

            return {'text': '\n\n'.join(text_parts), 'tool_calls': tool_calls}

        except anthropic.APITimeoutError:
            last_error = 'Request timed out. Please try again.'
            break

        except anthropic.APIStatusError as e:
            last_error = str(e)
            if e.status_code < 500:
                break

        except Exception as e:
            last_error = str(e)
            break

    latency_ms = int((time.monotonic() - start) * 1000)
    AIRequestLog.objects.create(
        request_type=request_type,
        exhibit=exhibit,
        success=False,
        error_message=last_error or 'Unknown error',
        latency_ms=latency_ms,
    )
    raise AIServiceError(last_error or 'AI request failed')


def _tool_calls_to_changes(tool_calls):
    """Convert tool_use calls into the proposed_changes list format."""
    changes = []
    for tc in tool_calls:
        inp = tc['input']
        if tc['name'] == 'add_scope_item':
            change = {
                'action': 'add',
                'section_name': inp['section_name'],
                'text': inp['text'],
                'level': inp['level'],
            }
            if 'parent_item_pk' in inp:
                change['parent_item_pk'] = inp['parent_item_pk']
            changes.append(change)
        elif tc['name'] == 'edit_scope_item':
            changes.append({
                'action': 'edit',
                'target_item_pk': inp['target_item_pk'],
                'text': inp['text'],
                'level': inp['level'],
            })
        elif tc['name'] == 'delete_scope_item':
            changes.append({
                'action': 'delete',
                'target_item_pk': inp['target_item_pk'],
            })
        elif tc['name'] == 'convert_note_to_scope':
            changes.append({
                'action': 'convert_note',
                'note_pk': inp['note_pk'],
                'section_name': inp['section_name'],
                'text': inp['text'],
                'level': inp['level'],
            })
    return changes


def _build_existing_scope_context(exhibit):
    """Build a plain-text summary of the exhibit's current sections and items."""
    from exhibits.services import flatten_section_items
    lines = []
    for section in exhibit.sections.order_by('order'):
        lines.append(f'\nSection: {section.name}')
        for item in flatten_section_items(section):
            indent = '  ' * item.level
            lines.append(f'{indent}- {item.text}')
    return '\n'.join(lines) if lines else 'No items yet.'


def _build_structured_chat_context(exhibit):
    """
    Build a structured dict of the exhibit's current state for chat context.

    Returns a dict with trade, project, sections, items (flat with PKs),
    and open notes for the exhibit's trade.
    """
    from exhibits.services import compute_exhibit_numbering, flatten_section_items
    from notes.models import Note
    from projects.models import Trade

    # Trade info
    trade_info = {
        'csi_code': exhibit.csi_trade.csi_code,
        'name': exhibit.csi_trade.name,
    }

    # Project info
    project = exhibit.project
    if project:
        project_info = {
            'name': project.name,
            'type': str(project.project_type) if project.project_type else None,
        }
    else:
        project_info = None

    # Compute exhibit-level numbering (A.1, A.1.1, B.2, etc.)
    numbers, section_letters = compute_exhibit_numbering(exhibit)

    # Sections with items nested inside
    sections = []
    for section in exhibit.sections.order_by('order'):
        section_dict = {'id': section.pk, 'name': section.name}
        letter = section_letters.get(section.pk)
        if letter:
            section_dict['letter'] = letter
        section_items = []
        for item in flatten_section_items(section):
            item_dict = {
                'ref': numbers.get(item.pk, ''),
                'pk': item.pk,
                'text': item.text,
                'level': item.level,
            }
            if item.parent_id:
                item_dict['parent_pk'] = item.parent_id
            if item.is_pending_review:
                item_dict['is_pending_review'] = True
            if item.is_ai_generated:
                item_dict['is_ai_generated'] = True
            if item.is_pending_review and item.pending_original_text:
                item_dict['original_text'] = item.pending_original_text
            section_items.append(item_dict)
        section_dict['items'] = section_items
        sections.append(section_dict)

    # Notes: open notes for the exhibit's trade (primary or related)
    notes = []
    if project:
        try:
            trade = Trade.objects.get(project=project, csi_trade=exhibit.csi_trade)
        except Trade.DoesNotExist:
            trade = None
        if trade:
            from django.db.models import Q
            open_notes = (
                Note.objects
                .filter(
                    Q(primary_trade=trade) | Q(related_trades=trade),
                    status=Note.Status.OPEN,
                )
                .distinct()
            )
            for note in open_notes:
                notes.append({
                    'pk': note.pk,
                    'text': note.text[:500],
                    'note_type': note.note_type,
                    'status': note.status,
                })

    return {
        'trade': trade_info,
        'project': project_info,
        'sections': sections,
        'notes': notes,
    }


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------

def generate_scope_from_description(exhibit):
    """
    Generate scope items for an exhibit based on its scope description,
    trade, and project context.

    Behaviour adapts based on existing content:
    - Sparse exhibit (< GAP_FILL_THRESHOLD items): generates a full scope draft.
    - Populated exhibit (>= GAP_FILL_THRESHOLD items): identifies gaps and
      suggests only the missing items.

    Returns a dict:
        {"scope_items": [{"section_name": "...", "items": [{"text": "...", "level": 0}]}]}
    or None if the response could not be parsed.

    Raises:
        AIDisabledError — if AI_ENABLED=False
        AIServiceError  — if the API call fails after retries
    """
    if not settings.AI_ENABLED:
        raise AIDisabledError('AI is disabled.')

    project = exhibit.project
    section_names = list(exhibit.sections.order_by('order').values_list('name', flat=True))
    existing_scope = _build_existing_scope_context(exhibit)

    # Count existing items to decide mode
    from exhibits.models import ScopeItem
    item_count = ScopeItem.objects.filter(section__scope_exhibit=exhibit).count()

    if item_count >= GAP_FILL_THRESHOLD:
        instruction = (
            "Review the existing scope below and identify important items "
            "that are MISSING. Only suggest items that fill genuine gaps — "
            "do NOT duplicate or rephrase existing items."
        )
        existing_label = "EXISTING SCOPE (do not duplicate — only suggest what is missing)"
    else:
        instruction = "Generate scope items for the following exhibit."
        existing_label = "EXISTING SCOPE (do not duplicate these items)"

    user_prompt = f"""
{instruction}

TRADE: {exhibit.csi_trade.csi_code} — {exhibit.csi_trade.name}
PROJECT TYPE: {project.project_type if project and project.project_type else 'Not specified'}
PROJECT DESCRIPTION: {project.description if project and project.description else 'Not provided'}
SCOPE DESCRIPTION: {exhibit.scope_description or 'Not provided'}

AVAILABLE SECTIONS (use only these names):
{chr(10).join(f'- {name}' for name in section_names)}

{existing_label}:
{existing_scope}
""".strip()

    text = _call_claude(
        system_prompt=SCOPE_FROM_DESCRIPTION_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        exhibit=exhibit,
        request_type=AIRequestLog.RequestType.SCOPE_FROM_DESCRIPTION,
    )
    return _parse_json_response(text)


def generate_scope_item(input_text, exhibit, section):
    """
    Convert a PM's plain-language note into a single polished scope item.

    Returns the exhibit_text string, or None if the response could not be parsed.

    Raises:
        AIDisabledError — if AI_ENABLED=False
        AIServiceError  — if the API call fails after retries
    """
    if not settings.AI_ENABLED:
        raise AIDisabledError('AI is disabled.')

    existing_scope = _build_existing_scope_context(exhibit)

    user_prompt = f"""
Rewrite the following note as a single scope item.

TRADE: {exhibit.csi_trade.csi_code} — {exhibit.csi_trade.name}
SECTION: {section.name}
PM'S NOTE: {input_text}

EXISTING SCOPE CONTEXT (for reference — do not duplicate):
{existing_scope}
""".strip()

    text = _call_claude(
        system_prompt=SCOPE_ITEM_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        exhibit=exhibit,
        request_type=AIRequestLog.RequestType.SCOPE_ITEM,
    )
    parsed = _parse_json_response(text)
    if parsed is None:
        return None
    return parsed.get('exhibit_text', '').strip() or None


def rewrite_scope_item(item, exhibit, instruction=''):
    """
    Propose a rewrite of an existing scope item.

    Returns the proposed new text string, or None if the response could not be parsed.

    Raises:
        AIDisabledError — if AI_ENABLED=False
        AIServiceError  — if the API call fails after retries
    """
    if not settings.AI_ENABLED:
        raise AIDisabledError('AI is disabled.')

    user_prompt_parts = [
        f'TRADE: {exhibit.csi_trade.csi_code} — {exhibit.csi_trade.name}',
        f'SECTION: {item.section.name}',
        f'EXISTING ITEM: {item.text}',
    ]
    if instruction:
        user_prompt_parts.append(f'INSTRUCTION: {instruction}')

    user_prompt = '\n'.join(user_prompt_parts)

    text = _call_claude(
        system_prompt=REWRITE_ITEM_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        exhibit=exhibit,
        request_type=AIRequestLog.RequestType.REWRITE_ITEM,
    )
    parsed = _parse_json_response(text)
    if parsed is None:
        return None
    return parsed.get('exhibit_text', '').strip() or None


def expand_scope_item(item, exhibit):
    """
    Expand a scope item into a list of child sub-items.

    Returns a list of {"text": "...", "level": N} dicts, or None on failure.

    Raises:
        AIDisabledError — if AI_ENABLED=False
        AIServiceError  — if the API call fails after retries
    """
    if not settings.AI_ENABLED:
        raise AIDisabledError('AI is disabled.')

    child_level = item.level + 1

    user_prompt = f"""
TRADE: {exhibit.csi_trade.csi_code} — {exhibit.csi_trade.name}
SECTION: {item.section.name}
PARENT ITEM (level {item.level}): {item.text}
CHILD LEVEL: {child_level}

Generate 2–5 sub-items that clarify or detail the parent item above.
All items must use level = {child_level}.
""".strip()

    text = _call_claude(
        system_prompt=EXPAND_ITEM_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        exhibit=exhibit,
        request_type=AIRequestLog.RequestType.EXPAND_ITEM,
    )
    parsed = _parse_json_response(text)
    if parsed is None:
        return None
    items = parsed.get('items', [])
    # Validate and normalise each item
    result = []
    for entry in items:
        text_val = entry.get('text', '').strip()
        if text_val:
            result.append({'text': text_val, 'level': child_level})
    return result or None


def check_exhibit_completeness(exhibit):
    """
    Identify scope items that may be missing from the exhibit.

    Returns a list of gap dicts:
        [{"section_name": "...", "text": "...", "reason": "..."}]
    or None if the response could not be parsed.

    Raises:
        AIDisabledError — if AI_ENABLED=False
        AIServiceError  — if the API call fails after retries
    """
    if not settings.AI_ENABLED:
        raise AIDisabledError('AI is disabled.')

    section_names = list(exhibit.sections.order_by('order').values_list('name', flat=True))
    existing_scope = _build_existing_scope_context(exhibit)

    project = exhibit.project
    user_prompt = f"""
Review this exhibit for missing scope items.

TRADE: {exhibit.csi_trade.csi_code} — {exhibit.csi_trade.name}
PROJECT TYPE: {project.project_type if project and project.project_type else 'Not specified'}
SCOPE DESCRIPTION: {exhibit.scope_description or 'Not provided'}

AVAILABLE SECTIONS (section_name must match one of these exactly):
{chr(10).join(f'- {name}' for name in section_names)}

CURRENT EXHIBIT CONTENT:
{existing_scope}

What important scope items are missing from this exhibit?
""".strip()

    text = _call_claude(
        system_prompt=COMPLETENESS_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        exhibit=exhibit,
        request_type=AIRequestLog.RequestType.COMPLETENESS_CHECK,
    )
    parsed = _parse_json_response(text)
    if parsed is None or 'gaps' not in parsed:
        return None
    return [
        g for g in parsed['gaps']
        if g.get('text', '').strip() and g.get('section_name', '').strip()
    ] or []


def section_ai_action(section, exhibit, instruction):
    """
    Handle a free-form AI instruction scoped to a single section.

    Uses tool-based API to let Claude decide whether to add, edit, or delete
    items based on the instruction. Returns a list of changes in the same
    format as _tool_calls_to_changes, or None on failure.

    Raises:
        AIDisabledError — if AI_ENABLED=False
        AIServiceError  — if the API call fails after retries
    """
    if not settings.AI_ENABLED:
        raise AIDisabledError('AI is disabled.')

    from exhibits.services import compute_exhibit_numbering, flatten_section_items

    # Build section items context
    numbers, _ = compute_exhibit_numbering(exhibit)
    items = list(flatten_section_items(section))
    items_json = []
    for item in items:
        d = {
            'pk': item.pk,
            'ref': numbers.get(item.pk, ''),
            'text': item.text,
            'level': item.level,
        }
        if item.parent_id:
            d['parent_pk'] = item.parent_id
        if item.is_pending_review:
            d['is_pending_review'] = True
        items_json.append(d)

    user_prompt = json.dumps({
        'trade': f'{exhibit.csi_trade.csi_code} — {exhibit.csi_trade.name}',
        'section_name': section.name,
        'instruction': instruction,
        'items': items_json,
    })

    # Use only add/edit/delete tools (no convert_note_to_scope)
    section_tools = CHAT_TOOLS[:3]

    result = _call_claude_with_tools(
        system_prompt=SECTION_AI_SYSTEM_PROMPT,
        messages=[{'role': 'user', 'content': user_prompt}],
        tools=section_tools,
        exhibit=exhibit,
        request_type=AIRequestLog.RequestType.REWRITE_SECTION,
    )

    if not result or not result.get('tool_calls'):
        return None

    return _tool_calls_to_changes(result['tool_calls'])


def rewrite_section_items(section, exhibit, instruction):
    """
    Rewrite all non-pending items in a section with a single API call.

    Returns a list of {"pk": int, "exhibit_text": str} dicts, or None on failure.
    Returns [] for empty sections (no API call).

    Raises:
        AIDisabledError — if AI_ENABLED=False
        AIServiceError  — if the API call fails after retries
    """
    if not settings.AI_ENABLED:
        raise AIDisabledError('AI is disabled.')

    from exhibits.services import flatten_section_items

    items = [i for i in flatten_section_items(section) if not i.is_pending_review]
    if not items:
        return []

    items_text = '\n'.join(
        f'pk: {item.pk} | level: {item.level} | text: {item.text}'
        for item in items
    )

    user_prompt = f"""
TRADE: {exhibit.csi_trade.csi_code} — {exhibit.csi_trade.name}
SECTION: {section.name}
INSTRUCTION: {instruction}

ITEMS TO REWRITE:
{items_text}
""".strip()

    text = _call_claude(
        system_prompt=REWRITE_SECTION_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        exhibit=exhibit,
        request_type=AIRequestLog.RequestType.REWRITE_SECTION,
    )
    parsed = _parse_json_response(text)
    if parsed is None:
        return None

    result = []
    valid_pks = {item.pk for item in items}
    for entry in parsed.get('items', []):
        pk = entry.get('pk')
        exhibit_text = entry.get('exhibit_text', '').strip()
        if pk in valid_pks and exhibit_text:
            result.append({'pk': pk, 'exhibit_text': exhibit_text})
    return result


def convert_note_to_scope(note, exhibit, instruction=''):
    """
    Convert a note to a scope item, checking for overlap first.

    Returns a dict:
        {"status": "overlap", "overlap_item_pk": int, "explanation": str}
        or
        {"status": "created", "section_name": str, "exhibit_text": str}
    or None if the response could not be parsed.

    Raises:
        AIDisabledError — if AI_ENABLED=False
        AIServiceError  — if the API call fails after retries
    """
    if not settings.AI_ENABLED:
        raise AIDisabledError('AI is disabled.')

    context = _build_structured_chat_context(exhibit)
    context_json = json.dumps(context)
    section_names = [s['name'] for s in context.get('sections', [])]

    note_parts = [f'NOTE TEXT: {note.text}']
    if note.resolution:
        note_parts.append(f'RESOLUTION: {note.resolution}')
    note_parts.append(f'NOTE TYPE: {note.get_note_type_display()}')
    if instruction:
        note_parts.append(f'USER INSTRUCTION: {instruction}')

    user_prompt = f"""
TRADE: {exhibit.csi_trade.csi_code} — {exhibit.csi_trade.name}

{chr(10).join(note_parts)}

AVAILABLE SECTIONS (section_name must match one of these exactly):
{chr(10).join(f'- {name}' for name in section_names)}

EXISTING EXHIBIT (JSON with item PKs — use the pk field for overlap_item_pk):
{context_json}
""".strip()

    text = _call_claude(
        system_prompt=NOTE_TO_SCOPE_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        exhibit=exhibit,
        request_type=AIRequestLog.RequestType.NOTE_TO_SCOPE,
    )
    parsed = _parse_json_response(text)
    if parsed is None:
        return None

    status = parsed.get('status')
    if status == 'overlap':
        return {
            'status': 'overlap',
            'overlap_item_pk': parsed.get('overlap_item_pk'),
            'explanation': parsed.get('explanation', ''),
        }
    elif status == 'created':
        exhibit_text = parsed.get('exhibit_text', '').strip()
        section_name = parsed.get('section_name', '').strip()
        if exhibit_text and section_name:
            return {
                'status': 'created',
                'section_name': section_name,
                'exhibit_text': exhibit_text,
            }
    return None


def _linkify_item_refs(message, ref_to_pk):
    """
    Replace item references (e.g. "A.1.1") in a chat message with clickable
    HTML links that scroll to the item in the editor.

    The message text is HTML-escaped first, then refs are replaced with <a> tags.
    """
    if not ref_to_pk:
        return html_escape(message)

    escaped = html_escape(message)

    # Sort refs longest-first to avoid partial matches (A.1.1 before A.1)
    sorted_refs = sorted(ref_to_pk.keys(), key=len, reverse=True)

    for ref in sorted_refs:
        pk = ref_to_pk[ref]
        # Match the ref as a standalone token:
        # - not followed by a digit (prevents B.1 matching inside B.19)
        # - not followed by dot+digit (prevents B.1 matching inside B.1.1)
        pattern = re.escape(ref) + r'(?!\d)(?!\.\d)'
        link = (
            f'<a href="#item-{pk}" onclick="scrollToItem({pk}); return false;" '
            f'class="text-primary-600 font-medium hover:underline cursor-pointer">{ref}</a>'
        )
        escaped = re.sub(pattern, link, escaped)

    return escaped


def chat_with_exhibit(exhibit, conversation_history):
    """
    Multi-turn conversational AI for exhibit-level assistance.

    conversation_history: list of {"role": "user"|"assistant", "content": "..."} dicts.

    Returns a dict:
        {
            "message": "...",           # assistant reply to display
            "proposed_changes": [...]   # list of change dicts (may be empty)
        }

    Raises:
        AIDisabledError — if AI_ENABLED=False
        AIServiceError  — if the API call fails after retries
    """
    if not settings.AI_ENABLED:
        raise AIDisabledError('AI is disabled.')

    context = _build_structured_chat_context(exhibit)
    context_json = json.dumps(context)

    # Build the system prompt with live exhibit context injected
    system_prompt = CHAT_SYSTEM_PROMPT + f"\n\nCURRENT EXHIBIT CONTEXT (JSON):\n{context_json}\n"

    # Build API messages — assistant messages are plain text now (no JSON wrapping)
    api_messages = []
    for msg in conversation_history:
        api_messages.append({'role': msg['role'], 'content': msg['content']})

    result = _call_claude_with_tools(
        system_prompt=system_prompt,
        messages=api_messages,
        tools=CHAT_TOOLS,
        exhibit=exhibit,
        request_type=AIRequestLog.RequestType.CHAT,
    )

    raw_message = result['text'].strip()
    proposed_changes = _tool_calls_to_changes(result['tool_calls'])

    # Build ref→pk mapping from context and linkify item references
    ref_to_pk = {}
    for section in context.get('sections', []):
        for item in section.get('items', []):
            if item.get('ref'):
                ref_to_pk[item['ref']] = item['pk']
    linkified_message = _linkify_item_refs(raw_message, ref_to_pk)

    return {
        'message': linkified_message,
        'proposed_changes': proposed_changes,
    }
