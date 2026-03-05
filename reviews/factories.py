import factory
from factory.django import DjangoModelFactory
from core.factories import CompanyFactory, PMUserFactory, CSITradeFactory
from exhibits.factories import ScopeExhibitFactory
from projects.factories import ProjectFactory
from .models import ChecklistItem, FinalReview, FinalReviewItem


class ChecklistItemFactory(DjangoModelFactory):
    class Meta:
        model = ChecklistItem

    company = factory.SubFactory(CompanyFactory)
    csi_trade = factory.SubFactory(CSITradeFactory)
    text = factory.Faker('sentence')
    created_by = factory.SubFactory(PMUserFactory)
    source_project = None


class FinalReviewFactory(DjangoModelFactory):
    class Meta:
        model = FinalReview

    scope_exhibit = factory.SubFactory(ScopeExhibitFactory)
    initiated_by = factory.SubFactory(PMUserFactory)
    status = FinalReview.Status.IN_PROGRESS


class FinalReviewItemFactory(DjangoModelFactory):
    class Meta:
        model = FinalReviewItem

    final_review = factory.SubFactory(FinalReviewFactory)
    check_type = FinalReviewItem.CheckType.OPEN_NOTE
    description = factory.Faker('sentence')
    status = FinalReviewItem.ItemStatus.WARNING
