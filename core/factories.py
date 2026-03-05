import factory
from factory.django import DjangoModelFactory
from .models import Company, User, ProjectType, CSITrade


class CompanyFactory(DjangoModelFactory):
    class Meta:
        model = Company

    name = factory.Sequence(lambda n: f'General Contractor {n}')


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    email = factory.Sequence(lambda n: f'user{n}@testgc.com')
    password = factory.PostGenerationMethodCall('set_password', 'testpass123')
    company = factory.SubFactory(CompanyFactory)
    role = User.Role.PE
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')


class PMUserFactory(UserFactory):
    role = User.Role.PM


class ProjectTypeFactory(DjangoModelFactory):
    class Meta:
        model = ProjectType

    name = factory.Sequence(lambda n: f'Project Type {n}')


class CSITradeFactory(DjangoModelFactory):
    class Meta:
        model = CSITrade

    csi_code = factory.Sequence(lambda n: f'{230000 + n}')
    name = factory.Sequence(lambda n: f'Trade {n}')
