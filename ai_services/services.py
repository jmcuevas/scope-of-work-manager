import json
import time

import anthropic
from django.conf import settings

from .models import AIRequestLog
from .prompts import (
    CHAT_SYSTEM_PROMPT,
    COMPLETENESS_SYSTEM_PROMPT,
    EXPAND_ITEM_SYSTEM_PROMPT,
    REWRITE_ITEM_SYSTEM_PROMPT,
    SCOPE_FROM_DESCRIPTION_SYSTEM_PROMPT,
    SCOPE_ITEM_SYSTEM_PROMPT,
)


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


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------

def generate_scope_from_description(exhibit):
    """
    Generate a full set of scope items for an exhibit based on its
    scope description, trade, and project context.

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

    user_prompt = f"""
Generate scope items for the following exhibit.

TRADE: {exhibit.csi_trade.csi_code} — {exhibit.csi_trade.name}
PROJECT TYPE: {project.project_type if project and project.project_type else 'Not specified'}
PROJECT DESCRIPTION: {project.description if project and project.description else 'Not provided'}
SCOPE DESCRIPTION: {exhibit.scope_description or 'Not provided'}

AVAILABLE SECTIONS (use only these names):
{chr(10).join(f'- {name}' for name in section_names)}

EXISTING SCOPE (do not duplicate these items):
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


def chat_with_exhibit(exhibit, conversation_history):
    """
    Multi-turn conversational AI for exhibit-level assistance.

    conversation_history: list of {"role": "user"|"assistant", "content": "..."} dicts.

    Returns a dict:
        {
            "message": "...",           # assistant reply to display
            "proposed_changes": [...]   # list of change dicts (may be empty)
        }
    or None if the response could not be parsed.

    Raises:
        AIDisabledError — if AI_ENABLED=False
        AIServiceError  — if the API call fails after retries
    """
    if not settings.AI_ENABLED:
        raise AIDisabledError('AI is disabled.')

    existing_scope = _build_existing_scope_context(exhibit)
    section_names = list(exhibit.sections.order_by('order').values_list('name', flat=True))

    # Build the system prompt with live exhibit context injected
    system_prompt = CHAT_SYSTEM_PROMPT + f"""

CURRENT EXHIBIT CONTEXT:
Trade: {exhibit.csi_trade.csi_code} — {exhibit.csi_trade.name}
Project: {exhibit.project.name if exhibit.project else 'Template'}
Available sections: {', '.join(section_names)}

Current scope:
{existing_scope}
"""

    text = _call_claude(
        system_prompt=system_prompt,
        messages=conversation_history,
        exhibit=exhibit,
        request_type=AIRequestLog.RequestType.CHAT,
    )
    parsed = _parse_json_response(text)
    if parsed is None:
        return None
    return {
        'message': parsed.get('message', '').strip(),
        'proposed_changes': parsed.get('proposed_changes', []),
    }
