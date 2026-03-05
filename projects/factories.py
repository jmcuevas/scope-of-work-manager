import factory
from factory.django import DjangoModelFactory
from core.factories import CompanyFactory, PMUserFactory, CSITradeFactory, ProjectTypeFactory
from .models import Project, Trade


class ProjectFactory(DjangoModelFactory):
    class Meta:
        model = Project

    company = factory.SubFactory(CompanyFactory)
    name = factory.Sequence(lambda n: f'Project {n}')
    number = factory.Sequence(lambda n: f'2026-{n:04d}')
    project_type = factory.SubFactory(ProjectTypeFactory)
    created_by = factory.SubFactory(PMUserFactory)


class TradeFactory(DjangoModelFactory):
    class Meta:
        model = Trade

    project = factory.SubFactory(ProjectFactory)
    csi_trade = factory.SubFactory(CSITradeFactory)
    status = Trade.Status.NOT_STARTED
    order = factory.Sequence(lambda n: n)
