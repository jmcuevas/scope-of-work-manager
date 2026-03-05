import factory
from factory.django import DjangoModelFactory
from core.factories import PMUserFactory
from projects.factories import ProjectFactory, TradeFactory
from .models import Note


class NoteFactory(DjangoModelFactory):
    class Meta:
        model = Note

    project = factory.SubFactory(ProjectFactory)
    primary_trade = factory.SubFactory(TradeFactory)
    text = factory.Faker('sentence')
    note_type = Note.NoteType.SCOPE_CLARIFICATION
    status = Note.Status.OPEN
    created_by = factory.SubFactory(PMUserFactory)
