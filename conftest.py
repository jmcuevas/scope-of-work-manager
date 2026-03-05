import pytest
from core.models import Company, User, ProjectType, CSITrade


@pytest.fixture
def company():
    return Company.objects.create(name='Test GC')


@pytest.fixture
def company_b():
    return Company.objects.create(name='Other GC')


@pytest.fixture
def project_type():
    return ProjectType.objects.create(name='Office TI')


@pytest.fixture
def csi_trade():
    return CSITrade.objects.create(csi_code='230000', name='HVAC')


@pytest.fixture
def csi_trade_b():
    return CSITrade.objects.create(csi_code='260000', name='Electrical')


@pytest.fixture
def pm_user(company):
    return User.objects.create_user(
        email='pm@testgc.com',
        password='testpass123',
        company=company,
        role=User.Role.PM,
    )


@pytest.fixture
def pe_user(company):
    return User.objects.create_user(
        email='pe@testgc.com',
        password='testpass123',
        company=company,
        role=User.Role.PE,
    )
