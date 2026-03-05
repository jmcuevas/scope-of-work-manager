import pytest
from django.db import IntegrityError
from django.urls import reverse
from .factories import ProjectFactory, TradeFactory
from .models import Trade
from core.factories import CSITradeFactory


@pytest.mark.django_db
class TestTrade:
    def test_unique_trade_per_project(self):
        trade = TradeFactory()
        with pytest.raises(IntegrityError):
            TradeFactory(project=trade.project, csi_trade=trade.csi_trade)

    def test_same_csi_trade_allowed_on_different_projects(self):
        csi_trade = CSITradeFactory()
        project_a = ProjectFactory()
        project_b = ProjectFactory()
        TradeFactory(project=project_a, csi_trade=csi_trade)
        TradeFactory(project=project_b, csi_trade=csi_trade)  # should not raise

    def test_default_status_is_not_started(self):
        trade = TradeFactory()
        assert trade.status == 'NOT_STARTED'

    def test_str(self):
        trade = TradeFactory()
        assert str(trade.project) in str(trade)
        assert str(trade.csi_trade) in str(trade)


@pytest.mark.django_db
class TestProject:
    def test_str_with_number(self):
        project = ProjectFactory(name='456 Montgomery', number='2026-0001')
        assert str(project) == '2026-0001 - 456 Montgomery'

    def test_str_without_number(self):
        project = ProjectFactory(name='456 Montgomery', number='')
        assert str(project) == '456 Montgomery'

    def test_company_isolation(self, company, company_b):
        from projects.models import Project
        ProjectFactory(company=company)
        ProjectFactory(company=company_b)
        assert Project.objects.filter(company=company).count() == 1


@pytest.mark.django_db
class TestProjectViews:
    def test_dashboard_returns_404_for_other_company(self, client, pm_user, company_b):
        other_project = ProjectFactory(company=company_b)
        client.force_login(pm_user)
        url = reverse('projects:dashboard', kwargs={'pk': other_project.pk})
        assert client.get(url).status_code == 404

    def test_dashboard_trade_count_matches_records(self, client, pm_user):
        project = ProjectFactory(company=pm_user.company)
        TradeFactory.create_batch(3, project=project)
        client.force_login(pm_user)
        response = client.get(reverse('projects:dashboard', kwargs={'pk': project.pk}))
        assert response.status_code == 200
        assert response.context['total_trades'] == 3

    def test_trade_status_update_persists(self, client, pm_user):
        project = ProjectFactory(company=pm_user.company)
        trade = TradeFactory(project=project, status=Trade.Status.NOT_STARTED)
        client.force_login(pm_user)
        url = reverse('projects:trade_update_status', kwargs={'pk': project.pk, 'trade_pk': trade.pk})
        client.post(url, {'status': Trade.Status.OUT_TO_BID})
        trade.refresh_from_db()
        assert trade.status == Trade.Status.OUT_TO_BID

    def test_trade_status_update_ignores_invalid_status(self, client, pm_user):
        project = ProjectFactory(company=pm_user.company)
        trade = TradeFactory(project=project, status=Trade.Status.NOT_STARTED)
        client.force_login(pm_user)
        url = reverse('projects:trade_update_status', kwargs={'pk': project.pk, 'trade_pk': trade.pk})
        client.post(url, {'status': 'INVALID_STATUS'})
        trade.refresh_from_db()
        assert trade.status == Trade.Status.NOT_STARTED

    def test_duplicate_csi_trade_rejected_by_form(self, client, pm_user):
        project = ProjectFactory(company=pm_user.company)
        csi = CSITradeFactory()
        TradeFactory(project=project, csi_trade=csi)
        client.force_login(pm_user)
        url = reverse('projects:trade_add', kwargs={'pk': project.pk})
        response = client.post(url, {'csi_trade': csi.pk, 'budget': ''})
        assert response.status_code == 200  # re-renders form with error
        assert project.trades.count() == 1  # no duplicate created
