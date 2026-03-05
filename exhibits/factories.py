import factory
from factory.django import DjangoModelFactory
from core.factories import CompanyFactory, PMUserFactory, CSITradeFactory
from projects.factories import ProjectFactory
from .models import ScopeExhibit, ExhibitSection, ScopeItem


class ScopeExhibitFactory(DjangoModelFactory):
    class Meta:
        model = ScopeExhibit

    company = factory.SubFactory(CompanyFactory)
    csi_trade = factory.SubFactory(CSITradeFactory)
    project = factory.SubFactory(ProjectFactory)
    is_template = False
    status = ScopeExhibit.Status.DRAFT
    last_edited_by = factory.SubFactory(PMUserFactory)
    created_by = factory.SubFactory(PMUserFactory)


class TemplateExhibitFactory(ScopeExhibitFactory):
    is_template = True
    project = None


class ExhibitSectionFactory(DjangoModelFactory):
    class Meta:
        model = ExhibitSection

    scope_exhibit = factory.SubFactory(ScopeExhibitFactory)
    name = factory.Sequence(lambda n: f'Section {n}')
    order = factory.Sequence(lambda n: n)


class ScopeItemFactory(DjangoModelFactory):
    class Meta:
        model = ScopeItem

    section = factory.SubFactory(ExhibitSectionFactory)
    parent = None
    level = 0
    text = factory.Faker('sentence')
    is_ai_generated = False
    order = factory.Sequence(lambda n: n)
    created_by = factory.SubFactory(PMUserFactory)
