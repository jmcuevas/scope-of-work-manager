import json
from unittest.mock import MagicMock, patch, call

import anthropic
import pytest
from django.urls import reverse

from core.factories import CSITradeFactory, CompanyFactory, PMUserFactory
from exhibits.factories import ExhibitSectionFactory, ScopeExhibitFactory, ScopeItemFactory
from exhibits.models import ScopeItem
from notes.factories import NoteFactory
from notes.models import Note
from projects.factories import ProjectFactory, TradeFactory

from .models import AIRequestLog
from .services import (
    AIDisabledError,
    AIServiceError,
    CHAT_TOOLS,
    _build_structured_chat_context,
    _call_claude,
    _call_claude_with_tools,
    _linkify_item_refs,
    _parse_json_response,
    _tool_calls_to_changes,
    chat_with_exhibit,
    check_exhibit_completeness,
    expand_scope_item,
    generate_scope_from_description,
    generate_scope_item,
    rewrite_scope_item,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BACKEND = 'django.contrib.auth.backends.ModelBackend'


def _login(client, user):
    user.set_password('testpass123')
    user.save(update_fields=['password'])
    client.force_login(user, backend=_BACKEND)


def _make_exhibit(user):
    project = ProjectFactory(company=user.company)
    csi = CSITradeFactory()
    return ScopeExhibitFactory(
        company=user.company,
        project=project,
        csi_trade=csi,
        created_by=user,
        last_edited_by=user,
        scope_description='Install all HVAC equipment per plans.',
    )


def _mock_response(text):
    """Build a minimal fake anthropic response."""
    content = MagicMock()
    content.text = text
    response = MagicMock()
    response.content = [content]
    response.usage.input_tokens = 100
    response.usage.output_tokens = 200
    return response


def _mock_tool_response(text='', tool_calls=None):
    """Build a mock Anthropic response with TextBlock and ToolUseBlock content."""
    content = []
    if text:
        content.append(MagicMock(type='text', text=text))
    for tc in (tool_calls or []):
        block = MagicMock(type='tool_use')
        # MagicMock treats 'name' as a special constructor arg, so set it after init
        block.name = tc['name']
        block.input = tc['input']
        content.append(block)
    resp = MagicMock()
    resp.content = content
    resp.usage.input_tokens = 100
    resp.usage.output_tokens = 50
    return resp


# ---------------------------------------------------------------------------
# _parse_json_response
# ---------------------------------------------------------------------------

class TestParseJsonResponse:
    def test_valid_json(self):
        result = _parse_json_response('{"key": "value"}')
        assert result == {'key': 'value'}

    def test_strips_markdown_fences(self):
        text = '```json\n{"key": "value"}\n```'
        assert _parse_json_response(text) == {'key': 'value'}

    def test_returns_none_on_bad_json(self):
        assert _parse_json_response('not json at all') is None

    def test_returns_none_on_empty_string(self):
        assert _parse_json_response('') is None


# ---------------------------------------------------------------------------
# _call_claude — success path
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestCallClaudeSuccess:
    def test_returns_response_text(self):
        exhibit = _make_exhibit(PMUserFactory())
        fake = _mock_response('hello')
        with patch('ai_services.services._get_client') as mock_client:
            mock_client.return_value.messages.create.return_value = fake
            result = _call_claude('sys', 'user', exhibit=exhibit, request_type=AIRequestLog.RequestType.SCOPE_ITEM)
        assert result == 'hello'

    def test_logs_success(self):
        exhibit = _make_exhibit(PMUserFactory())
        fake = _mock_response('hello')
        with patch('ai_services.services._get_client') as mock_client:
            mock_client.return_value.messages.create.return_value = fake
            _call_claude('sys', 'user', exhibit=exhibit, request_type=AIRequestLog.RequestType.SCOPE_ITEM)
        log = AIRequestLog.objects.get()
        assert log.success is True
        assert log.tokens_used == 300
        assert log.exhibit == exhibit


# ---------------------------------------------------------------------------
# _call_claude — retry on 5xx
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestCallClaudeRetry:
    def test_retries_once_on_5xx_then_succeeds(self):
        exhibit = _make_exhibit(PMUserFactory())
        fake = _mock_response('ok')
        server_error = anthropic.APIStatusError(
            message='Server Error',
            response=MagicMock(status_code=500),
            body={},
        )
        with patch('ai_services.services._get_client') as mock_client:
            mock_client.return_value.messages.create.side_effect = [server_error, fake]
            result = _call_claude('sys', 'user', exhibit=exhibit, request_type=AIRequestLog.RequestType.SCOPE_ITEM)
        assert result == 'ok'

    def test_logs_failure_after_all_retries_exhausted(self):
        exhibit = _make_exhibit(PMUserFactory())
        server_error = anthropic.APIStatusError(
            message='Server Error',
            response=MagicMock(status_code=500),
            body={},
        )
        with patch('ai_services.services._get_client') as mock_client:
            mock_client.return_value.messages.create.side_effect = [server_error, server_error]
            with pytest.raises(AIServiceError):
                _call_claude('sys', 'user', exhibit=exhibit, request_type=AIRequestLog.RequestType.SCOPE_ITEM)
        log = AIRequestLog.objects.get()
        assert log.success is False
        assert log.error_message != ''

    def test_does_not_retry_on_4xx(self):
        exhibit = _make_exhibit(PMUserFactory())
        auth_error = anthropic.APIStatusError(
            message='Unauthorized',
            response=MagicMock(status_code=401),
            body={},
        )
        with patch('ai_services.services._get_client') as mock_client:
            mock_client.return_value.messages.create.side_effect = [auth_error]
            with pytest.raises(AIServiceError):
                _call_claude('sys', 'user', exhibit=exhibit, request_type=AIRequestLog.RequestType.SCOPE_ITEM)
        # Only one call — no retry
        assert mock_client.return_value.messages.create.call_count == 1

    def test_does_not_retry_on_timeout(self):
        exhibit = _make_exhibit(PMUserFactory())
        with patch('ai_services.services._get_client') as mock_client:
            mock_client.return_value.messages.create.side_effect = anthropic.APITimeoutError(request=MagicMock())
            with pytest.raises(AIServiceError):
                _call_claude('sys', 'user', exhibit=exhibit, request_type=AIRequestLog.RequestType.SCOPE_ITEM)
        assert mock_client.return_value.messages.create.call_count == 1


# ---------------------------------------------------------------------------
# generate_scope_from_description
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestGenerateScopeFromDescription:
    def _valid_response(self):
        return json.dumps({
            'scope_items': [
                {
                    'section_name': 'Scope of Work',
                    'items': [
                        {'text': 'Provide and install all ductwork.', 'level': 0},
                        {'text': 'Include all supports and hangers.', 'level': 1},
                    ],
                }
            ]
        })

    def test_returns_parsed_dict_on_success(self):
        user = PMUserFactory()
        exhibit = _make_exhibit(user)
        with patch('ai_services.services._get_client') as mock_client:
            mock_client.return_value.messages.create.return_value = _mock_response(self._valid_response())
            result = generate_scope_from_description(exhibit)
        assert result is not None
        assert 'scope_items' in result
        assert result['scope_items'][0]['section_name'] == 'Scope of Work'

    def test_returns_none_on_malformed_json(self):
        user = PMUserFactory()
        exhibit = _make_exhibit(user)
        with patch('ai_services.services._get_client') as mock_client:
            mock_client.return_value.messages.create.return_value = _mock_response('not valid json')
            result = generate_scope_from_description(exhibit)
        assert result is None

    def test_raises_ai_disabled_error(self):
        user = PMUserFactory()
        exhibit = _make_exhibit(user)
        with patch('ai_services.services.settings') as mock_settings:
            mock_settings.AI_ENABLED = False
            with pytest.raises(AIDisabledError):
                generate_scope_from_description(exhibit)

    def test_raises_ai_service_error_on_api_failure(self):
        user = PMUserFactory()
        exhibit = _make_exhibit(user)
        with patch('ai_services.services._get_client') as mock_client:
            mock_client.return_value.messages.create.side_effect = Exception('boom')
            with pytest.raises(AIServiceError):
                generate_scope_from_description(exhibit)

    def test_sparse_exhibit_uses_generate_prompt(self):
        """Exhibits with fewer than GAP_FILL_THRESHOLD items use full-generate mode."""
        user = PMUserFactory()
        exhibit = _make_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit, name='Scope of Work')
        # Only 2 items — below threshold
        ScopeItemFactory(section=section, text='Item one')
        ScopeItemFactory(section=section, text='Item two')

        with patch('ai_services.services._get_client') as mock_client:
            mock_client.return_value.messages.create.return_value = _mock_response(self._valid_response())
            generate_scope_from_description(exhibit)

        prompt_sent = mock_client.return_value.messages.create.call_args[1]['messages'][0]['content']
        assert 'Generate scope items' in prompt_sent
        assert 'MISSING' not in prompt_sent

    def test_populated_exhibit_uses_gap_fill_prompt(self):
        """Exhibits with >= GAP_FILL_THRESHOLD items switch to gap-fill mode."""
        user = PMUserFactory()
        exhibit = _make_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit, name='Scope of Work')
        # Create 6 items — above threshold
        for i in range(6):
            ScopeItemFactory(section=section, text=f'Item {i}')

        gap_response = json.dumps({
            'scope_items': [{
                'section_name': 'Scope of Work',
                'items': [{'text': 'Provide seismic bracing for all ductwork.', 'level': 0}],
            }]
        })
        with patch('ai_services.services._get_client') as mock_client:
            mock_client.return_value.messages.create.return_value = _mock_response(gap_response)
            result = generate_scope_from_description(exhibit)

        prompt_sent = mock_client.return_value.messages.create.call_args[1]['messages'][0]['content']
        assert 'MISSING' in prompt_sent
        assert 'Generate scope items' not in prompt_sent
        # Same return format as full-generate mode
        assert result is not None
        assert 'scope_items' in result

    def test_populated_exhibit_with_no_gaps_returns_empty_scope_items(self):
        """Gap-fill mode returns valid dict even when Claude finds no gaps."""
        user = PMUserFactory()
        exhibit = _make_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit, name='Scope of Work')
        for i in range(6):
            ScopeItemFactory(section=section, text=f'Item {i}')

        empty_response = json.dumps({'scope_items': []})
        with patch('ai_services.services._get_client') as mock_client:
            mock_client.return_value.messages.create.return_value = _mock_response(empty_response)
            result = generate_scope_from_description(exhibit)

        assert result is not None
        assert result['scope_items'] == []


# ---------------------------------------------------------------------------
# generate_scope_item
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestGenerateScopeItem:
    def test_returns_cleaned_string_on_success(self):
        user = PMUserFactory()
        exhibit = _make_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit, name='Scope of Work')
        payload = json.dumps({'exhibit_text': '  Provide and install all hangers.  '})
        with patch('ai_services.services._get_client') as mock_client:
            mock_client.return_value.messages.create.return_value = _mock_response(payload)
            result = generate_scope_item('include hangers', exhibit, section)
        assert result == 'Provide and install all hangers.'

    def test_returns_none_on_malformed_json(self):
        user = PMUserFactory()
        exhibit = _make_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit)
        with patch('ai_services.services._get_client') as mock_client:
            mock_client.return_value.messages.create.return_value = _mock_response('oops')
            result = generate_scope_item('include hangers', exhibit, section)
        assert result is None

    def test_returns_none_when_exhibit_text_missing(self):
        user = PMUserFactory()
        exhibit = _make_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit)
        with patch('ai_services.services._get_client') as mock_client:
            mock_client.return_value.messages.create.return_value = _mock_response('{"other": "key"}')
            result = generate_scope_item('include hangers', exhibit, section)
        assert result is None

    def test_raises_ai_disabled_error(self):
        user = PMUserFactory()
        exhibit = _make_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit)
        with patch('ai_services.services.settings') as mock_settings:
            mock_settings.AI_ENABLED = False
            with pytest.raises(AIDisabledError):
                generate_scope_item('include hangers', exhibit, section)


# ---------------------------------------------------------------------------
# View: exhibit_generate_scope — company isolation + item creation
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestExhibitGenerateScopeView:
    def test_creates_items_in_matching_sections(self, client):
        user = PMUserFactory()
        _login(client, user)
        exhibit = _make_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit, name='Scope of Work')

        payload = json.dumps({
            'scope_items': [
                {
                    'section_name': 'Scope of Work',
                    'items': [{'text': 'Provide and install ductwork.', 'level': 0}],
                }
            ]
        })
        with patch('ai_services.services._get_client') as mock_client:
            mock_client.return_value.messages.create.return_value = _mock_response(payload)
            url = reverse('exhibits:generate_scope', kwargs={'pk': exhibit.pk})
            response = client.post(url)

        assert response.status_code == 200
        assert response['HX-Trigger'] == 'pendingChanged'
        item = ScopeItem.objects.get(section=section)
        assert item.text == 'Provide and install ductwork.'
        assert item.is_ai_generated is True
        assert item.is_pending_review is True

    def test_skips_unmatched_section_names(self, client):
        user = PMUserFactory()
        _login(client, user)
        exhibit = _make_exhibit(user)
        ExhibitSectionFactory(scope_exhibit=exhibit, name='Scope of Work')

        payload = json.dumps({
            'scope_items': [
                {
                    'section_name': 'Nonexistent Section',
                    'items': [{'text': 'This should not be created.', 'level': 0}],
                }
            ]
        })
        with patch('ai_services.services._get_client') as mock_client:
            mock_client.return_value.messages.create.return_value = _mock_response(payload)
            url = reverse('exhibits:generate_scope', kwargs={'pk': exhibit.pk})
            client.post(url)

        assert ScopeItem.objects.count() == 0

    def test_rejects_other_company_exhibit(self, client):
        user = PMUserFactory()
        _login(client, user)
        other_exhibit = ScopeExhibitFactory()  # different company
        url = reverse('exhibits:generate_scope', kwargs={'pk': other_exhibit.pk})
        response = client.post(url)
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# View: item_generate — company isolation + fallback
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestItemGenerateView:
    def test_creates_ai_generated_item(self, client):
        user = PMUserFactory()
        _login(client, user)
        exhibit = _make_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit)

        payload = json.dumps({'exhibit_text': 'Provide and install all hangers.'})
        with patch('ai_services.services._get_client') as mock_client:
            mock_client.return_value.messages.create.return_value = _mock_response(payload)
            url = reverse('exhibits:item_generate', kwargs={'pk': exhibit.pk, 'section_pk': section.pk})
            response = client.post(url, {'text': 'include hangers'})

        assert response.status_code == 200
        assert response['HX-Trigger'] == 'pendingChanged'
        item = ScopeItem.objects.get(section=section)
        assert item.text == 'Provide and install all hangers.'
        assert item.is_ai_generated is True
        assert item.is_pending_review is True

    def test_falls_back_to_raw_input_on_ai_failure(self, client):
        user = PMUserFactory()
        _login(client, user)
        exhibit = _make_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit)

        with patch('ai_services.services._get_client') as mock_client:
            mock_client.return_value.messages.create.side_effect = Exception('API down')
            url = reverse('exhibits:item_generate', kwargs={'pk': exhibit.pk, 'section_pk': section.pk})
            response = client.post(url, {'text': 'include hangers'})

        assert response.status_code == 200
        assert 'HX-Trigger' not in response
        item = ScopeItem.objects.get(section=section)
        assert item.text == 'include hangers'
        assert item.is_ai_generated is False
        assert item.is_pending_review is False

    def test_empty_input_returns_item_list_unchanged(self, client):
        user = PMUserFactory()
        _login(client, user)
        exhibit = _make_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit)

        url = reverse('exhibits:item_generate', kwargs={'pk': exhibit.pk, 'section_pk': section.pk})
        response = client.post(url, {'text': ''})

        assert response.status_code == 200
        assert ScopeItem.objects.count() == 0

    def test_rejects_other_company_exhibit(self, client):
        user = PMUserFactory()
        _login(client, user)
        other_exhibit = ScopeExhibitFactory()
        section = ExhibitSectionFactory(scope_exhibit=other_exhibit)
        url = reverse('exhibits:item_generate', kwargs={'pk': other_exhibit.pk, 'section_pk': section.pk})
        response = client.post(url, {'text': 'some text'})
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# rewrite_scope_item
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestRewriteScopeItem:

    def test_returns_proposed_text_on_success(self):
        user = PMUserFactory()
        exhibit = _make_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit)
        item = ScopeItemFactory(section=section, text='install ducts', created_by=user)

        payload = json.dumps({'exhibit_text': 'Provide and install all ductwork per Contract Documents.'})
        with patch('ai_services.services._get_client') as mock_client:
            mock_client.return_value.messages.create.return_value = _mock_response(payload)
            result = rewrite_scope_item(item, exhibit)

        assert result == 'Provide and install all ductwork per Contract Documents.'

    def test_includes_instruction_in_call(self):
        user = PMUserFactory()
        exhibit = _make_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit)
        item = ScopeItemFactory(section=section, text='install ducts', created_by=user)

        payload = json.dumps({'exhibit_text': 'Provide and install all ductwork including seismic bracing.'})
        with patch('ai_services.services._get_client') as mock_client:
            mock_client.return_value.messages.create.return_value = _mock_response(payload)
            result = rewrite_scope_item(item, exhibit, instruction='add seismic bracing reference')

        # Verify the instruction was sent in the user message
        call_args = mock_client.return_value.messages.create.call_args
        messages = call_args.kwargs['messages']
        assert 'add seismic bracing reference' in messages[0]['content']
        assert result == 'Provide and install all ductwork including seismic bracing.'

    def test_returns_none_on_malformed_json(self):
        user = PMUserFactory()
        exhibit = _make_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit)
        item = ScopeItemFactory(section=section, text='install ducts', created_by=user)

        with patch('ai_services.services._get_client') as mock_client:
            mock_client.return_value.messages.create.return_value = _mock_response('not json')
            result = rewrite_scope_item(item, exhibit)

        assert result is None

    def test_raises_ai_disabled_error(self, settings):
        settings.AI_ENABLED = False
        user = PMUserFactory()
        exhibit = _make_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit)
        item = ScopeItemFactory(section=section, created_by=user)
        with pytest.raises(AIDisabledError):
            rewrite_scope_item(item, exhibit)

    def test_logs_request_type(self):
        user = PMUserFactory()
        exhibit = _make_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit)
        item = ScopeItemFactory(section=section, text='install ducts', created_by=user)

        payload = json.dumps({'exhibit_text': 'Provide and install ductwork.'})
        with patch('ai_services.services._get_client') as mock_client:
            mock_client.return_value.messages.create.return_value = _mock_response(payload)
            rewrite_scope_item(item, exhibit)

        log = AIRequestLog.objects.latest('created_at')
        assert log.request_type == AIRequestLog.RequestType.REWRITE_ITEM
        assert log.success is True


# ---------------------------------------------------------------------------
# expand_scope_item
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestExpandScopeItem:

    def test_returns_child_items_on_success(self):
        user = PMUserFactory()
        exhibit = _make_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit)
        item = ScopeItemFactory(section=section, level=0, text='Provide ductwork.', created_by=user)

        payload = json.dumps({'items': [
            {'text': 'Include all hangers and supports.', 'level': 1},
            {'text': 'Include all flexible connections.', 'level': 1},
        ]})
        with patch('ai_services.services._get_client') as mock_client:
            mock_client.return_value.messages.create.return_value = _mock_response(payload)
            result = expand_scope_item(item, exhibit)

        assert len(result) == 2
        assert result[0] == {'text': 'Include all hangers and supports.', 'level': 1}
        assert result[1] == {'text': 'Include all flexible connections.', 'level': 1}

    def test_child_level_is_parent_level_plus_one(self):
        user = PMUserFactory()
        exhibit = _make_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit)
        # Parent at level 1 — children should be level 2
        item = ScopeItemFactory(section=section, level=1, text='Include hangers.', created_by=user)

        payload = json.dumps({'items': [
            {'text': 'Rod hangers at 8ft spacing.', 'level': 2},
        ]})
        with patch('ai_services.services._get_client') as mock_client:
            mock_client.return_value.messages.create.return_value = _mock_response(payload)
            result = expand_scope_item(item, exhibit)

        assert result[0]['level'] == 2

    def test_returns_none_on_malformed_json(self):
        user = PMUserFactory()
        exhibit = _make_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit)
        item = ScopeItemFactory(section=section, created_by=user)

        with patch('ai_services.services._get_client') as mock_client:
            mock_client.return_value.messages.create.return_value = _mock_response('bad json')
            result = expand_scope_item(item, exhibit)

        assert result is None

    def test_raises_ai_disabled_error(self, settings):
        settings.AI_ENABLED = False
        user = PMUserFactory()
        exhibit = _make_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit)
        item = ScopeItemFactory(section=section, created_by=user)
        with pytest.raises(AIDisabledError):
            expand_scope_item(item, exhibit)

    def test_logs_request_type(self):
        user = PMUserFactory()
        exhibit = _make_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit)
        item = ScopeItemFactory(section=section, level=0, text='Provide ductwork.', created_by=user)

        payload = json.dumps({'items': [{'text': 'Include hangers.', 'level': 1}]})
        with patch('ai_services.services._get_client') as mock_client:
            mock_client.return_value.messages.create.return_value = _mock_response(payload)
            expand_scope_item(item, exhibit)

        log = AIRequestLog.objects.latest('created_at')
        assert log.request_type == AIRequestLog.RequestType.EXPAND_ITEM
        assert log.success is True


# ---------------------------------------------------------------------------
# chat_with_exhibit
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestChatWithExhibit:

    def test_returns_message_and_empty_changes(self):
        user = PMUserFactory()
        exhibit = _make_exhibit(user)

        history = [{'role': 'user', 'content': 'Does the scope look complete?'}]
        with patch('ai_services.services._get_client') as mock_client:
            mock_client.return_value.messages.create.return_value = _mock_tool_response(
                text='Looks good! The scope covers the main items.',
            )
            result = chat_with_exhibit(exhibit, history)

        assert result['message'] == 'Looks good! The scope covers the main items.'
        assert result['proposed_changes'] == []

    def test_returns_proposed_changes_from_tool_calls(self):
        user = PMUserFactory()
        exhibit = _make_exhibit(user)

        history = [{'role': 'user', 'content': 'Add a coordination item.'}]
        with patch('ai_services.services._get_client') as mock_client:
            mock_client.return_value.messages.create.return_value = _mock_tool_response(
                text="I've suggested one addition.",
                tool_calls=[{
                    'name': 'add_scope_item',
                    'input': {
                        'section_name': 'Scope of Work',
                        'text': 'Coordinate with Electrical Contractor.',
                        'level': 0,
                    },
                }],
            )
            result = chat_with_exhibit(exhibit, history)

        assert len(result['proposed_changes']) == 1
        assert result['proposed_changes'][0]['action'] == 'add'
        assert result['proposed_changes'][0]['section_name'] == 'Scope of Work'

    def test_passes_full_conversation_history_to_api(self):
        user = PMUserFactory()
        exhibit = _make_exhibit(user)

        history = [
            {'role': 'user', 'content': 'First message'},
            {'role': 'assistant', 'content': 'First reply'},
            {'role': 'user', 'content': 'Second message'},
        ]
        with patch('ai_services.services._get_client') as mock_client:
            mock_client.return_value.messages.create.return_value = _mock_tool_response(
                text='Sure.',
            )
            chat_with_exhibit(exhibit, history)

        call_args = mock_client.return_value.messages.create.call_args
        sent_messages = call_args.kwargs['messages']
        # User messages passed through unchanged
        assert sent_messages[0] == {'role': 'user', 'content': 'First message'}
        assert sent_messages[2] == {'role': 'user', 'content': 'Second message'}
        # Assistant messages are plain text now (no JSON wrapping)
        assert sent_messages[1] == {'role': 'assistant', 'content': 'First reply'}

    def test_raises_ai_disabled_error(self, settings):
        settings.AI_ENABLED = False
        user = PMUserFactory()
        exhibit = _make_exhibit(user)
        with pytest.raises(AIDisabledError):
            chat_with_exhibit(exhibit, [{'role': 'user', 'content': 'Hello'}])

    def test_logs_request_type(self):
        user = PMUserFactory()
        exhibit = _make_exhibit(user)

        history = [{'role': 'user', 'content': 'Hello'}]
        with patch('ai_services.services._get_client') as mock_client:
            mock_client.return_value.messages.create.return_value = _mock_tool_response(
                text='Done.',
            )
            chat_with_exhibit(exhibit, history)

        log = AIRequestLog.objects.latest('created_at')
        assert log.request_type == AIRequestLog.RequestType.CHAT
        assert log.success is True

    def test_text_only_response_returns_empty_changes(self):
        user = PMUserFactory()
        exhibit = _make_exhibit(user)

        history = [{'role': 'user', 'content': 'What is this exhibit about?'}]
        with patch('ai_services.services._get_client') as mock_client:
            mock_client.return_value.messages.create.return_value = _mock_tool_response(
                text='This exhibit covers HVAC scope.',
            )
            result = chat_with_exhibit(exhibit, history)

        assert result['message'] == 'This exhibit covers HVAC scope.'
        assert result['proposed_changes'] == []

    def test_passes_tools_to_api(self):
        user = PMUserFactory()
        exhibit = _make_exhibit(user)

        history = [{'role': 'user', 'content': 'Hello'}]
        with patch('ai_services.services._get_client') as mock_client:
            mock_client.return_value.messages.create.return_value = _mock_tool_response(
                text='Hi.',
            )
            chat_with_exhibit(exhibit, history)

        call_args = mock_client.return_value.messages.create.call_args
        assert call_args.kwargs['tools'] == CHAT_TOOLS

    def test_tool_only_no_text_returns_empty_message(self):
        """When Claude returns only tool calls with no text block, message should be empty."""
        user = PMUserFactory()
        exhibit = _make_exhibit(user)
        ExhibitSectionFactory(scope_exhibit=exhibit, name='Scope of Work')

        history = [{'role': 'user', 'content': 'Add a coordination item.'}]
        with patch('ai_services.services._get_client') as mock_client:
            mock_client.return_value.messages.create.return_value = _mock_tool_response(
                text='',
                tool_calls=[{
                    'name': 'add_scope_item',
                    'input': {
                        'section_name': 'Scope of Work',
                        'text': 'Coordinate with other trades.',
                        'level': 0,
                    },
                }],
            )
            result = chat_with_exhibit(exhibit, history)

        assert result['message'] == ''
        assert len(result['proposed_changes']) == 1


# ---------------------------------------------------------------------------
# check_exhibit_completeness
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestCheckExhibitCompleteness:

    def test_returns_gap_list_on_success(self):
        user = PMUserFactory()
        exhibit = _make_exhibit(user)
        ExhibitSectionFactory(scope_exhibit=exhibit, name='Scope of Work')
        payload = json.dumps({
            'gaps': [
                {'section_name': 'Scope of Work', 'text': 'Provide fire stopping.', 'reason': 'Missing.'},
            ]
        })
        with patch('ai_services.services._get_client') as mock_client:
            mock_client.return_value.messages.create.return_value = _mock_response(payload)
            result = check_exhibit_completeness(exhibit)
        assert result is not None
        assert len(result) == 1
        assert result[0]['text'] == 'Provide fire stopping.'

    def test_returns_empty_list_when_no_gaps(self):
        user = PMUserFactory()
        exhibit = _make_exhibit(user)
        payload = json.dumps({'gaps': []})
        with patch('ai_services.services._get_client') as mock_client:
            mock_client.return_value.messages.create.return_value = _mock_response(payload)
            result = check_exhibit_completeness(exhibit)
        assert result == []

    def test_returns_none_on_malformed_json(self):
        user = PMUserFactory()
        exhibit = _make_exhibit(user)
        with patch('ai_services.services._get_client') as mock_client:
            mock_client.return_value.messages.create.return_value = _mock_response('not json')
            result = check_exhibit_completeness(exhibit)
        assert result is None

    def test_raises_ai_disabled_when_flag_off(self, settings):
        settings.AI_ENABLED = False
        user = PMUserFactory()
        exhibit = _make_exhibit(user)
        with pytest.raises(AIDisabledError):
            check_exhibit_completeness(exhibit)

    def test_logs_completeness_check_request_type(self):
        user = PMUserFactory()
        exhibit = _make_exhibit(user)
        payload = json.dumps({'gaps': []})
        with patch('ai_services.services._get_client') as mock_client:
            mock_client.return_value.messages.create.return_value = _mock_response(payload)
            check_exhibit_completeness(exhibit)
        log = AIRequestLog.objects.latest('created_at')
        assert log.request_type == AIRequestLog.RequestType.COMPLETENESS_CHECK
        assert log.success is True


# ---------------------------------------------------------------------------
# ChatSession / ChatMessage models
# ---------------------------------------------------------------------------

from .models import ChatMessage, ChatSession


@pytest.mark.django_db
class TestChatSessionModel:
    def test_create_with_exhibit_and_user(self):
        user = PMUserFactory()
        exhibit = _make_exhibit(user)
        session = ChatSession.objects.create(exhibit=exhibit, user=user)
        assert session.pk is not None
        assert session.exhibit == exhibit
        assert session.user == user
        assert session.context_type == 'exhibit'

    def test_ordering_by_updated_at_desc(self):
        user = PMUserFactory()
        exhibit = _make_exhibit(user)
        s1 = ChatSession.objects.create(exhibit=exhibit, user=user)
        s2 = ChatSession.objects.create(exhibit=exhibit, user=user)
        # s2 created last so updated_at is later
        sessions = list(ChatSession.objects.all())
        assert sessions[0] == s2
        assert sessions[1] == s1

    def test_str(self):
        user = PMUserFactory()
        exhibit = _make_exhibit(user)
        session = ChatSession.objects.create(exhibit=exhibit, user=user)
        assert str(session.pk) in str(session)


@pytest.mark.django_db
class TestChatMessageModel:
    def test_create_user_message(self):
        user = PMUserFactory()
        exhibit = _make_exhibit(user)
        session = ChatSession.objects.create(exhibit=exhibit, user=user)
        msg = ChatMessage.objects.create(
            session=session, role=ChatMessage.Role.USER,
            content='Hello', user=user,
        )
        assert msg.pk is not None
        assert msg.role == 'user'
        assert msg.content == 'Hello'

    def test_create_assistant_message(self):
        user = PMUserFactory()
        exhibit = _make_exhibit(user)
        session = ChatSession.objects.create(exhibit=exhibit, user=user)
        msg = ChatMessage.objects.create(
            session=session, role=ChatMessage.Role.ASSISTANT,
            content='Hi there!', tokens_used=150,
        )
        assert msg.role == 'assistant'
        assert msg.user is None
        assert msg.tokens_used == 150

    def test_ordering_by_created_at_asc(self):
        user = PMUserFactory()
        exhibit = _make_exhibit(user)
        session = ChatSession.objects.create(exhibit=exhibit, user=user)
        m1 = ChatMessage.objects.create(session=session, role='user', content='First')
        m2 = ChatMessage.objects.create(session=session, role='assistant', content='Second')
        msgs = list(session.messages.all())
        assert msgs[0] == m1
        assert msgs[1] == m2

    def test_role_choices(self):
        assert ChatMessage.Role.USER == 'user'
        assert ChatMessage.Role.ASSISTANT == 'assistant'

    def test_str(self):
        user = PMUserFactory()
        exhibit = _make_exhibit(user)
        session = ChatSession.objects.create(exhibit=exhibit, user=user)
        msg = ChatMessage.objects.create(session=session, role='user', content='Test message')
        assert 'user' in str(msg)
        assert 'Test message' in str(msg)


# ---------------------------------------------------------------------------
# _build_structured_chat_context
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestBuildStructuredChatContext:

    def _make_exhibit_with_trade(self, user):
        """Create an exhibit with a matching Trade record (needed for notes)."""
        exhibit = _make_exhibit(user)
        trade = TradeFactory(
            project=exhibit.project,
            csi_trade=exhibit.csi_trade,
        )
        return exhibit, trade

    def test_includes_trade_info(self):
        user = PMUserFactory()
        exhibit = _make_exhibit(user)
        result = _build_structured_chat_context(exhibit)
        assert result['trade']['csi_code'] == exhibit.csi_trade.csi_code
        assert result['trade']['name'] == exhibit.csi_trade.name

    def test_includes_project_info(self):
        user = PMUserFactory()
        exhibit = _make_exhibit(user)
        result = _build_structured_chat_context(exhibit)
        assert result['project']['name'] == exhibit.project.name
        assert result['project']['type'] == str(exhibit.project.project_type)

    def test_template_exhibit_has_null_project(self):
        user = PMUserFactory()
        csi = CSITradeFactory()
        exhibit = ScopeExhibitFactory(
            company=user.company,
            project=None,
            csi_trade=csi,
            is_template=True,
            created_by=user,
            last_edited_by=user,
        )
        result = _build_structured_chat_context(exhibit)
        assert result['project'] is None
        assert result['notes'] == []

    def test_sections_in_order(self):
        user = PMUserFactory()
        exhibit = _make_exhibit(user)
        s1 = ExhibitSectionFactory(scope_exhibit=exhibit, name='General Conditions', order=0)
        s2 = ExhibitSectionFactory(scope_exhibit=exhibit, name='Scope of Work', order=1)
        s3 = ExhibitSectionFactory(scope_exhibit=exhibit, name='Exclusions', order=2)
        result = _build_structured_chat_context(exhibit)
        assert [s['name'] for s in result['sections']] == [
            'General Conditions', 'Scope of Work', 'Exclusions',
        ]

    def test_sections_have_letters(self):
        user = PMUserFactory()
        exhibit = _make_exhibit(user)
        ExhibitSectionFactory(scope_exhibit=exhibit, name='General Conditions', order=0)
        ExhibitSectionFactory(scope_exhibit=exhibit, name='Scope of Work', order=1)
        result = _build_structured_chat_context(exhibit)
        assert result['sections'][0]['letter'] == 'A'
        assert result['sections'][1]['letter'] == 'B'

    def test_items_nested_under_sections(self):
        user = PMUserFactory()
        exhibit = _make_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit, name='Scope of Work')
        item = ScopeItemFactory(section=section, text='Provide ductwork.', created_by=user)
        result = _build_structured_chat_context(exhibit)
        section_data = result['sections'][0]
        assert len(section_data['items']) == 1
        assert section_data['items'][0]['pk'] == item.pk
        assert section_data['items'][0]['text'] == 'Provide ductwork.'

    def test_items_have_ref(self):
        user = PMUserFactory()
        exhibit = _make_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit, name='Scope of Work', order=0)
        item = ScopeItemFactory(section=section, text='Provide ductwork.', order=0, created_by=user)
        result = _build_structured_chat_context(exhibit)
        assert result['sections'][0]['items'][0]['ref'] == 'A.1'

    def test_items_preserve_hierarchy(self):
        user = PMUserFactory()
        exhibit = _make_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit, name='Scope of Work')
        parent = ScopeItemFactory(section=section, text='Provide ductwork.', level=0, created_by=user)
        child = ScopeItemFactory(
            section=section, text='Include hangers.', level=1,
            parent=parent, created_by=user,
        )
        result = _build_structured_chat_context(exhibit)
        items = result['sections'][0]['items']
        assert len(items) == 2
        child_item = next(i for i in items if i['pk'] == child.pk)
        assert child_item['parent_pk'] == parent.pk
        assert child_item['level'] == 1

    def test_pending_item_includes_original_text(self):
        user = PMUserFactory()
        exhibit = _make_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit, name='Scope of Work')
        ScopeItemFactory(
            section=section, text='New text.', level=0, created_by=user,
            is_pending_review=True, is_ai_generated=True,
            pending_original_text='Old text.',
        )
        result = _build_structured_chat_context(exhibit)
        item = result['sections'][0]['items'][0]
        assert item['is_pending_review'] is True
        assert item['original_text'] == 'Old text.'

    def test_pending_item_without_original_omits_field(self):
        user = PMUserFactory()
        exhibit = _make_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit, name='Scope of Work')
        ScopeItemFactory(
            section=section, text='Brand new item.', level=0, created_by=user,
            is_pending_review=True, is_ai_generated=True,
            pending_original_text='',
        )
        result = _build_structured_chat_context(exhibit)
        item = result['sections'][0]['items'][0]
        assert item['is_pending_review'] is True
        assert 'original_text' not in item

    def test_open_notes_included(self):
        user = PMUserFactory()
        exhibit, trade = self._make_exhibit_with_trade(user)
        NoteFactory(
            project=exhibit.project, primary_trade=trade,
            text='Confirm insulation spec.', note_type=Note.NoteType.OPEN_QUESTION,
            status=Note.Status.OPEN, created_by=user,
        )
        result = _build_structured_chat_context(exhibit)
        assert len(result['notes']) == 1
        assert result['notes'][0]['text'] == 'Confirm insulation spec.'
        assert result['notes'][0]['note_type'] == 'OPEN_QUESTION'

    def test_resolved_notes_excluded(self):
        user = PMUserFactory()
        exhibit, trade = self._make_exhibit_with_trade(user)
        NoteFactory(
            project=exhibit.project, primary_trade=trade,
            text='Already resolved.', note_type=Note.NoteType.OPEN_QUESTION,
            status=Note.Status.RESOLVED, created_by=user,
        )
        result = _build_structured_chat_context(exhibit)
        assert result['notes'] == []

    def test_notes_text_truncated(self):
        user = PMUserFactory()
        exhibit, trade = self._make_exhibit_with_trade(user)
        long_text = 'A' * 600
        NoteFactory(
            project=exhibit.project, primary_trade=trade,
            text=long_text, note_type=Note.NoteType.SCOPE_CLARIFICATION,
            status=Note.Status.OPEN, created_by=user,
        )
        result = _build_structured_chat_context(exhibit)
        assert len(result['notes'][0]['text']) == 500

    def test_empty_exhibit(self):
        user = PMUserFactory()
        exhibit = _make_exhibit(user)
        result = _build_structured_chat_context(exhibit)
        assert result['sections'] == []


# ---------------------------------------------------------------------------
# TestChatWithExhibit — structured context integration tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestChatWithExhibitStructuredContext:

    def test_system_prompt_contains_item_pks(self):
        user = PMUserFactory()
        exhibit = _make_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit, name='Scope of Work')
        item = ScopeItemFactory(section=section, text='Provide ductwork.', created_by=user)

        history = [{'role': 'user', 'content': 'Hello'}]
        with patch('ai_services.services._get_client') as mock_client:
            mock_client.return_value.messages.create.return_value = _mock_tool_response(text='OK.')
            chat_with_exhibit(exhibit, history)

        call_args = mock_client.return_value.messages.create.call_args
        system = call_args.kwargs['system']
        assert f'"pk": {item.pk}' in system

    def test_system_prompt_contains_section_ids(self):
        user = PMUserFactory()
        exhibit = _make_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit, name='Scope of Work')

        history = [{'role': 'user', 'content': 'Hello'}]
        with patch('ai_services.services._get_client') as mock_client:
            mock_client.return_value.messages.create.return_value = _mock_tool_response(text='OK.')
            chat_with_exhibit(exhibit, history)

        call_args = mock_client.return_value.messages.create.call_args
        system = call_args.kwargs['system']
        assert f'"id": {section.pk}' in system

    def test_system_prompt_contains_open_notes(self):
        user = PMUserFactory()
        exhibit = _make_exhibit(user)
        trade = TradeFactory(project=exhibit.project, csi_trade=exhibit.csi_trade)
        NoteFactory(
            project=exhibit.project, primary_trade=trade,
            text='Confirm spec.', note_type=Note.NoteType.OPEN_QUESTION,
            status=Note.Status.OPEN, created_by=user,
        )

        history = [{'role': 'user', 'content': 'Hello'}]
        with patch('ai_services.services._get_client') as mock_client:
            mock_client.return_value.messages.create.return_value = _mock_tool_response(text='OK.')
            chat_with_exhibit(exhibit, history)

        call_args = mock_client.return_value.messages.create.call_args
        system = call_args.kwargs['system']
        assert 'Confirm spec.' in system

    def test_system_prompt_excludes_resolved_notes(self):
        user = PMUserFactory()
        exhibit = _make_exhibit(user)
        trade = TradeFactory(project=exhibit.project, csi_trade=exhibit.csi_trade)
        NoteFactory(
            project=exhibit.project, primary_trade=trade,
            text='Already resolved note.', note_type=Note.NoteType.OPEN_QUESTION,
            status=Note.Status.RESOLVED, created_by=user,
        )

        history = [{'role': 'user', 'content': 'Hello'}]
        with patch('ai_services.services._get_client') as mock_client:
            mock_client.return_value.messages.create.return_value = _mock_tool_response(text='OK.')
            chat_with_exhibit(exhibit, history)

        call_args = mock_client.return_value.messages.create.call_args
        system = call_args.kwargs['system']
        assert 'Already resolved note.' not in system


# ---------------------------------------------------------------------------
# _linkify_item_refs
# ---------------------------------------------------------------------------

class TestLinkifyItemRefs:

    def test_replaces_ref_with_link(self):
        ref_to_pk = {'A.1': 42}
        result = _linkify_item_refs('See item A.1 for details.', ref_to_pk)
        assert 'scrollToItem(42)' in result
        assert 'A.1</a>' in result
        assert 'href="#item-42"' in result

    def test_no_refs_returns_escaped(self):
        result = _linkify_item_refs('No refs here.', {})
        assert result == 'No refs here.'

    def test_html_escaped(self):
        result = _linkify_item_refs('Use <b>bold</b>.', {})
        assert '&lt;b&gt;' in result

    def test_longer_ref_matched_first(self):
        ref_to_pk = {'A.1': 10, 'A.1.1': 20}
        result = _linkify_item_refs('Check A.1.1 and A.1.', ref_to_pk)
        assert 'scrollToItem(20)' in result
        assert 'scrollToItem(10)' in result

    def test_does_not_partial_match_dot_digit(self):
        """A.1 should not match inside A.1.1"""
        ref_to_pk = {'A.1': 10}
        result = _linkify_item_refs('See A.1.1 which is different.', ref_to_pk)
        # A.1 should NOT be linked when followed by .1
        assert 'scrollToItem(10)' not in result

    def test_does_not_partial_match_trailing_digit(self):
        """B.1 should not match inside B.19"""
        ref_to_pk = {'B.1': 10}
        result = _linkify_item_refs('See B.19 which is a different item.', ref_to_pk)
        assert 'scrollToItem(10)' not in result

    def test_b19_matched_correctly(self):
        """B.19 should be linked, B.1 should not match inside B.19"""
        ref_to_pk = {'B.1': 10, 'B.19': 99}
        result = _linkify_item_refs('Check B.19 and also B.1.', ref_to_pk)
        assert 'scrollToItem(99)' in result  # B.19 linked
        assert 'scrollToItem(10)' in result  # B.1 linked separately
        assert result.count('scrollToItem(99)') == 1
        assert result.count('scrollToItem(10)') == 1

    def test_multiple_occurrences(self):
        ref_to_pk = {'B.2': 50}
        result = _linkify_item_refs('Compare B.2 and also B.2 again.', ref_to_pk)
        assert result.count('scrollToItem(50)') == 2


# ---------------------------------------------------------------------------
# _tool_calls_to_changes
# ---------------------------------------------------------------------------

class TestToolCallsToChanges:

    def test_add_tool_call(self):
        tool_calls = [{'name': 'add_scope_item', 'input': {
            'section_name': 'Scope of Work',
            'text': 'Provide ductwork.',
            'level': 0,
        }}]
        changes = _tool_calls_to_changes(tool_calls)
        assert changes == [{
            'action': 'add',
            'section_name': 'Scope of Work',
            'text': 'Provide ductwork.',
            'level': 0,
        }]

    def test_edit_tool_call(self):
        tool_calls = [{'name': 'edit_scope_item', 'input': {
            'target_item_pk': 42,
            'text': 'Updated text.',
            'level': 1,
        }}]
        changes = _tool_calls_to_changes(tool_calls)
        assert changes == [{
            'action': 'edit',
            'target_item_pk': 42,
            'text': 'Updated text.',
            'level': 1,
        }]

    def test_delete_tool_call(self):
        tool_calls = [{'name': 'delete_scope_item', 'input': {
            'target_item_pk': 17,
        }}]
        changes = _tool_calls_to_changes(tool_calls)
        assert changes == [{'action': 'delete', 'target_item_pk': 17}]

    def test_mixed_tool_calls(self):
        tool_calls = [
            {'name': 'add_scope_item', 'input': {
                'section_name': 'Inclusions', 'text': 'New item.', 'level': 0}},
            {'name': 'edit_scope_item', 'input': {
                'target_item_pk': 10, 'text': 'Edited.', 'level': 0}},
            {'name': 'delete_scope_item', 'input': {'target_item_pk': 5}},
        ]
        changes = _tool_calls_to_changes(tool_calls)
        assert len(changes) == 3
        assert changes[0]['action'] == 'add'
        assert changes[1]['action'] == 'edit'
        assert changes[2]['action'] == 'delete'

    def test_empty_tool_calls(self):
        assert _tool_calls_to_changes([]) == []

    def test_add_with_parent_item_pk(self):
        tool_calls = [{'name': 'add_scope_item', 'input': {
            'section_name': 'Scope of Work',
            'text': 'Include hangers.',
            'level': 1,
            'parent_item_pk': 101,
        }}]
        changes = _tool_calls_to_changes(tool_calls)
        assert changes == [{
            'action': 'add',
            'section_name': 'Scope of Work',
            'text': 'Include hangers.',
            'level': 1,
            'parent_item_pk': 101,
        }]

    def test_add_without_parent_item_pk(self):
        """Backward compat: no parent_item_pk key when omitted from input."""
        tool_calls = [{'name': 'add_scope_item', 'input': {
            'section_name': 'Scope of Work',
            'text': 'Provide ductwork.',
            'level': 0,
        }}]
        changes = _tool_calls_to_changes(tool_calls)
        assert 'parent_item_pk' not in changes[0]


# ---------------------------------------------------------------------------
# _call_claude_with_tools
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestCallClaudeWithTools:

    def test_returns_text_and_tool_calls(self):
        exhibit = _make_exhibit(PMUserFactory())
        with patch('ai_services.services._get_client') as mock_client:
            mock_client.return_value.messages.create.return_value = _mock_tool_response(
                text='Here is an addition.',
                tool_calls=[{'name': 'add_scope_item', 'input': {
                    'section_name': 'Scope of Work', 'text': 'New item.', 'level': 0,
                }}],
            )
            result = _call_claude_with_tools(
                'sys', [{'role': 'user', 'content': 'add item'}],
                tools=CHAT_TOOLS, exhibit=exhibit,
                request_type=AIRequestLog.RequestType.CHAT,
            )
        assert result['text'] == 'Here is an addition.'
        assert len(result['tool_calls']) == 1
        assert result['tool_calls'][0]['name'] == 'add_scope_item'

    def test_passes_tools_to_api(self):
        exhibit = _make_exhibit(PMUserFactory())
        with patch('ai_services.services._get_client') as mock_client:
            mock_client.return_value.messages.create.return_value = _mock_tool_response(text='OK.')
            _call_claude_with_tools(
                'sys', [{'role': 'user', 'content': 'hi'}],
                tools=CHAT_TOOLS, exhibit=exhibit,
                request_type=AIRequestLog.RequestType.CHAT,
            )
        call_args = mock_client.return_value.messages.create.call_args
        assert call_args.kwargs['tools'] == CHAT_TOOLS

    def test_logs_success(self):
        exhibit = _make_exhibit(PMUserFactory())
        with patch('ai_services.services._get_client') as mock_client:
            mock_client.return_value.messages.create.return_value = _mock_tool_response(text='OK.')
            _call_claude_with_tools(
                'sys', [{'role': 'user', 'content': 'hi'}],
                tools=CHAT_TOOLS, exhibit=exhibit,
                request_type=AIRequestLog.RequestType.CHAT,
            )
        log = AIRequestLog.objects.get()
        assert log.success is True
        assert log.tokens_used == 150
        assert log.request_type == AIRequestLog.RequestType.CHAT

    def test_retries_on_5xx(self):
        exhibit = _make_exhibit(PMUserFactory())
        server_error = anthropic.APIStatusError(
            message='Server Error',
            response=MagicMock(status_code=500),
            body={},
        )
        with patch('ai_services.services._get_client') as mock_client:
            mock_client.return_value.messages.create.side_effect = [
                server_error,
                _mock_tool_response(text='Recovered.'),
            ]
            result = _call_claude_with_tools(
                'sys', [{'role': 'user', 'content': 'hi'}],
                tools=CHAT_TOOLS, exhibit=exhibit,
                request_type=AIRequestLog.RequestType.CHAT,
            )
        assert result['text'] == 'Recovered.'

    def test_raises_on_failure(self):
        exhibit = _make_exhibit(PMUserFactory())
        with patch('ai_services.services._get_client') as mock_client:
            mock_client.return_value.messages.create.side_effect = Exception('boom')
            with pytest.raises(AIServiceError):
                _call_claude_with_tools(
                    'sys', [{'role': 'user', 'content': 'hi'}],
                    tools=CHAT_TOOLS, exhibit=exhibit,
                    request_type=AIRequestLog.RequestType.CHAT,
                )

    def test_text_only_response(self):
        exhibit = _make_exhibit(PMUserFactory())
        with patch('ai_services.services._get_client') as mock_client:
            mock_client.return_value.messages.create.return_value = _mock_tool_response(
                text='Just text, no tools.',
            )
            result = _call_claude_with_tools(
                'sys', [{'role': 'user', 'content': 'hi'}],
                tools=CHAT_TOOLS, exhibit=exhibit,
                request_type=AIRequestLog.RequestType.CHAT,
            )
        assert result['text'] == 'Just text, no tools.'
        assert result['tool_calls'] == []


# ---------------------------------------------------------------------------
# rewrite_section_items
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestRewriteSectionItems:
    def test_rewrites_all_items(self):
        from ai_services.services import rewrite_section_items
        user = PMUserFactory()
        exhibit = _make_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit, name='Scope of Work', order=0)
        item1 = ScopeItemFactory(section=section, text='Install ductwork.', order=0, created_by=user)
        item2 = ScopeItemFactory(section=section, text='Provide hangers.', order=1, created_by=user)

        response_json = json.dumps({
            'items': [
                {'pk': item1.pk, 'exhibit_text': 'Subcontractor shall install all ductwork.'},
                {'pk': item2.pk, 'exhibit_text': 'Subcontractor shall provide all hangers.'},
            ]
        })
        with patch('ai_services.services._get_client') as mock_client:
            mock_client.return_value.messages.create.return_value = _mock_response(response_json)
            result = rewrite_section_items(section, exhibit, 'convert to subcontract language')

        assert len(result) == 2
        assert result[0]['pk'] == item1.pk
        assert 'Subcontractor' in result[0]['exhibit_text']

    def test_empty_section_returns_empty_list(self):
        from ai_services.services import rewrite_section_items
        user = PMUserFactory()
        exhibit = _make_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit, name='Empty', order=0)

        result = rewrite_section_items(section, exhibit, 'anything')
        assert result == []

    def test_skips_pending_items(self):
        from ai_services.services import rewrite_section_items
        user = PMUserFactory()
        exhibit = _make_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit, name='Scope', order=0)
        ScopeItemFactory(section=section, text='Pending item.', order=0, is_pending_review=True, created_by=user)
        live_item = ScopeItemFactory(section=section, text='Live item.', order=1, created_by=user)

        response_json = json.dumps({
            'items': [{'pk': live_item.pk, 'exhibit_text': 'Rewritten live item.'}]
        })
        with patch('ai_services.services._get_client') as mock_client:
            mock_client.return_value.messages.create.return_value = _mock_response(response_json)
            result = rewrite_section_items(section, exhibit, 'improve')

        assert len(result) == 1
        assert result[0]['pk'] == live_item.pk

    def test_skips_unknown_pks(self):
        from ai_services.services import rewrite_section_items
        user = PMUserFactory()
        exhibit = _make_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit, name='Scope', order=0)
        item = ScopeItemFactory(section=section, text='Item.', order=0, created_by=user)

        response_json = json.dumps({
            'items': [
                {'pk': item.pk, 'exhibit_text': 'Good.'},
                {'pk': 99999, 'exhibit_text': 'Unknown.'},
            ]
        })
        with patch('ai_services.services._get_client') as mock_client:
            mock_client.return_value.messages.create.return_value = _mock_response(response_json)
            result = rewrite_section_items(section, exhibit, 'improve')

        assert len(result) == 1

    @pytest.mark.parametrize('enabled', [False])
    def test_ai_disabled(self, settings, enabled):
        from ai_services.services import rewrite_section_items
        settings.AI_ENABLED = enabled
        user = PMUserFactory()
        exhibit = _make_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit, order=0)
        with pytest.raises(AIDisabledError):
            rewrite_section_items(section, exhibit, 'anything')


# ---------------------------------------------------------------------------
# section_ai_action
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestSectionAIAction:
    def test_returns_add_changes(self):
        from ai_services.services import section_ai_action
        user = PMUserFactory()
        exhibit = _make_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit, name='Scope of Work', order=0)
        ScopeItemFactory(section=section, text='Existing item.', order=0, created_by=user)

        tool_calls = [
            {'name': 'add_scope_item', 'input': {
                'section_name': 'Scope of Work', 'text': 'New AI item.', 'level': 0,
            }},
        ]
        with patch('ai_services.services._get_client') as mock_client:
            mock_client.return_value.messages.create.return_value = _mock_tool_response(
                tool_calls=tool_calls,
            )
            result = section_ai_action(section, exhibit, 'add an exclusion')

        assert len(result) == 1
        assert result[0]['action'] == 'add'
        assert result[0]['text'] == 'New AI item.'

    def test_returns_edit_changes(self):
        from ai_services.services import section_ai_action
        user = PMUserFactory()
        exhibit = _make_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit, name='Scope', order=0)
        item = ScopeItemFactory(section=section, text='Old text.', order=0, created_by=user)

        tool_calls = [
            {'name': 'edit_scope_item', 'input': {
                'target_item_pk': item.pk, 'text': 'Rewritten text.', 'level': 0,
            }},
        ]
        with patch('ai_services.services._get_client') as mock_client:
            mock_client.return_value.messages.create.return_value = _mock_tool_response(
                tool_calls=tool_calls,
            )
            result = section_ai_action(section, exhibit, 'rewrite in subcontract language')

        assert len(result) == 1
        assert result[0]['action'] == 'edit'
        assert result[0]['target_item_pk'] == item.pk

    def test_no_tool_calls_returns_none(self):
        from ai_services.services import section_ai_action
        user = PMUserFactory()
        exhibit = _make_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit, name='Scope', order=0)

        with patch('ai_services.services._get_client') as mock_client:
            mock_client.return_value.messages.create.return_value = _mock_tool_response(
                text='I don\'t understand.', tool_calls=[],
            )
            result = section_ai_action(section, exhibit, 'unclear instruction')

        assert result is None

    @pytest.mark.parametrize('enabled', [False])
    def test_ai_disabled(self, settings, enabled):
        from ai_services.services import section_ai_action
        settings.AI_ENABLED = enabled
        user = PMUserFactory()
        exhibit = _make_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit, order=0)
        with pytest.raises(AIDisabledError):
            section_ai_action(section, exhibit, 'anything')


# ---------------------------------------------------------------------------
# convert_note_to_scope
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestConvertNoteToScope:
    def _make_note(self, exhibit, user, resolution=''):
        trade = TradeFactory(
            project=exhibit.project, csi_trade=exhibit.csi_trade,
        )
        note = NoteFactory(
            project=exhibit.project, primary_trade=trade,
            text='Caulking should be in glazing scope.',
            created_by=user,
        )
        if resolution:
            note.resolution = resolution
            note.save(update_fields=['resolution'])
        return note

    def test_no_overlap_returns_created(self):
        from ai_services.services import convert_note_to_scope
        user = PMUserFactory()
        exhibit = _make_exhibit(user)
        ExhibitSectionFactory(scope_exhibit=exhibit, name='Scope of Work', order=0)
        note = self._make_note(exhibit, user)

        response_json = json.dumps({
            'status': 'created',
            'section_name': 'Scope of Work',
            'exhibit_text': 'Provide all caulking at curtain wall assemblies.',
        })
        with patch('ai_services.services._get_client') as mock_client:
            mock_client.return_value.messages.create.return_value = _mock_response(response_json)
            result = convert_note_to_scope(note, exhibit)

        assert result['status'] == 'created'
        assert result['section_name'] == 'Scope of Work'
        assert 'caulking' in result['exhibit_text'].lower()

    def test_overlap_returns_overlap(self):
        from ai_services.services import convert_note_to_scope
        user = PMUserFactory()
        exhibit = _make_exhibit(user)
        section = ExhibitSectionFactory(scope_exhibit=exhibit, name='Scope of Work', order=0)
        item = ScopeItemFactory(section=section, text='Provide all caulking.', order=0, created_by=user)
        note = self._make_note(exhibit, user)

        response_json = json.dumps({
            'status': 'overlap',
            'overlap_item_pk': item.pk,
            'explanation': 'Item already covers caulking.',
        })
        with patch('ai_services.services._get_client') as mock_client:
            mock_client.return_value.messages.create.return_value = _mock_response(response_json)
            result = convert_note_to_scope(note, exhibit)

        assert result['status'] == 'overlap'
        assert result['overlap_item_pk'] == item.pk

    def test_includes_resolution_in_prompt(self):
        from ai_services.services import convert_note_to_scope
        user = PMUserFactory()
        exhibit = _make_exhibit(user)
        ExhibitSectionFactory(scope_exhibit=exhibit, name='Scope of Work', order=0)
        note = self._make_note(exhibit, user, resolution='Confirmed: glazing carries caulking.')

        response_json = json.dumps({
            'status': 'created',
            'section_name': 'Scope of Work',
            'exhibit_text': 'Provide all caulking.',
        })
        with patch('ai_services.services._get_client') as mock_client:
            mock_client.return_value.messages.create.return_value = _mock_response(response_json)
            convert_note_to_scope(note, exhibit)

        # Verify resolution was in the user prompt
        call_args = mock_client.return_value.messages.create.call_args
        user_msg = call_args.kwargs['messages'][0]['content']
        assert 'Confirmed: glazing carries caulking.' in user_msg

    @pytest.mark.parametrize('enabled', [False])
    def test_ai_disabled(self, settings, enabled):
        from ai_services.services import convert_note_to_scope
        settings.AI_ENABLED = enabled
        user = PMUserFactory()
        exhibit = _make_exhibit(user)
        note = self._make_note(exhibit, user)
        with pytest.raises(AIDisabledError):
            convert_note_to_scope(note, exhibit)


# ---------------------------------------------------------------------------
# _tool_calls_to_changes: convert_note_to_scope
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestToolCallsConvertNote:
    def test_convert_note_tool_call(self):
        result = _tool_calls_to_changes([{
            'name': 'convert_note_to_scope',
            'input': {
                'note_pk': 42,
                'section_name': 'Scope of Work',
                'text': 'Provide all caulking.',
                'level': 0,
            },
        }])
        assert len(result) == 1
        assert result[0]['action'] == 'convert_note'
        assert result[0]['note_pk'] == 42
        assert result[0]['section_name'] == 'Scope of Work'
