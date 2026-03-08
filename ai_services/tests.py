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
    generate_scope_from_description,
    generate_scope_item,
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
        item = ScopeItem.objects.get(section=section)
        assert item.text == 'Provide and install ductwork.'
        assert item.is_ai_generated is True

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
        item = ScopeItem.objects.get(section=section)
        assert item.text == 'Provide and install all hangers.'
        assert item.is_ai_generated is True

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
        item = ScopeItem.objects.get(section=section)
        assert item.text == 'include hangers'
        assert item.is_ai_generated is False

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
