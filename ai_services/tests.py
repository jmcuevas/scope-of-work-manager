import json
from unittest.mock import MagicMock, patch, call

import anthropic
import pytest
from django.urls import reverse

from core.factories import CSITradeFactory, CompanyFactory, PMUserFactory
from exhibits.factories import ExhibitSectionFactory, ScopeExhibitFactory, ScopeItemFactory
from exhibits.models import ScopeItem
from projects.factories import ProjectFactory

from .models import AIRequestLog
from .services import (
    AIDisabledError,
    AIServiceError,
    _call_claude,
    _parse_json_response,
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

        payload = json.dumps({
            'message': 'Looks good! The scope covers the main items.',
            'proposed_changes': [],
        })
        history = [{'role': 'user', 'content': 'Does the scope look complete?'}]
        with patch('ai_services.services._get_client') as mock_client:
            mock_client.return_value.messages.create.return_value = _mock_response(payload)
            result = chat_with_exhibit(exhibit, history)

        assert result['message'] == 'Looks good! The scope covers the main items.'
        assert result['proposed_changes'] == []

    def test_returns_proposed_changes(self):
        user = PMUserFactory()
        exhibit = _make_exhibit(user)

        payload = json.dumps({
            'message': "I've suggested one addition.",
            'proposed_changes': [
                {'action': 'add', 'section_name': 'Scope of Work',
                 'text': 'Coordinate with Electrical Contractor.', 'level': 0},
            ],
        })
        history = [{'role': 'user', 'content': 'Add a coordination item.'}]
        with patch('ai_services.services._get_client') as mock_client:
            mock_client.return_value.messages.create.return_value = _mock_response(payload)
            result = chat_with_exhibit(exhibit, history)

        assert len(result['proposed_changes']) == 1
        assert result['proposed_changes'][0]['action'] == 'add'

    def test_passes_full_conversation_history_to_api(self):
        user = PMUserFactory()
        exhibit = _make_exhibit(user)

        payload = json.dumps({'message': 'Sure.', 'proposed_changes': []})
        history = [
            {'role': 'user', 'content': 'First message'},
            {'role': 'assistant', 'content': 'First reply'},
            {'role': 'user', 'content': 'Second message'},
        ]
        with patch('ai_services.services._get_client') as mock_client:
            mock_client.return_value.messages.create.return_value = _mock_response(payload)
            chat_with_exhibit(exhibit, history)

        call_args = mock_client.return_value.messages.create.call_args
        assert call_args.kwargs['messages'] == history

    def test_returns_none_on_malformed_json(self):
        user = PMUserFactory()
        exhibit = _make_exhibit(user)

        history = [{'role': 'user', 'content': 'Hello'}]
        with patch('ai_services.services._get_client') as mock_client:
            mock_client.return_value.messages.create.return_value = _mock_response('bad json')
            result = chat_with_exhibit(exhibit, history)

        assert result is None

    def test_raises_ai_disabled_error(self, settings):
        settings.AI_ENABLED = False
        user = PMUserFactory()
        exhibit = _make_exhibit(user)
        with pytest.raises(AIDisabledError):
            chat_with_exhibit(exhibit, [{'role': 'user', 'content': 'Hello'}])

    def test_logs_request_type(self):
        user = PMUserFactory()
        exhibit = _make_exhibit(user)

        payload = json.dumps({'message': 'Done.', 'proposed_changes': []})
        history = [{'role': 'user', 'content': 'Hello'}]
        with patch('ai_services.services._get_client') as mock_client:
            mock_client.return_value.messages.create.return_value = _mock_response(payload)
            chat_with_exhibit(exhibit, history)

        log = AIRequestLog.objects.latest('created_at')
        assert log.request_type == AIRequestLog.RequestType.CHAT
        assert log.success is True


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
