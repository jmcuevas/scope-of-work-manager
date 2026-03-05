import pytest
from django.db import IntegrityError
from .factories import ProjectFactory, TradeFactory
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
