import pytest
from django.db import IntegrityError
from .factories import CompanyFactory, UserFactory, CSITradeFactory, ProjectTypeFactory
from .models import CSITrade


@pytest.mark.django_db
class TestUser:
    def test_email_is_unique(self):
        UserFactory(email='unique@testgc.com')
        with pytest.raises(IntegrityError):
            UserFactory(email='unique@testgc.com')

    def test_str(self):
        user = UserFactory(email='pm@testgc.com')
        assert str(user) == 'pm@testgc.com'

    def test_is_pm_property(self, pm_user):
        assert pm_user.is_pm is True
        assert pm_user.is_pe is False

    def test_is_pe_property(self, pe_user):
        assert pe_user.is_pe is True
        assert pe_user.is_pm is False


@pytest.mark.django_db
class TestCSITrade:
    def test_csi_code_is_unique(self):
        CSITradeFactory(csi_code='230000')
        with pytest.raises(IntegrityError):
            CSITradeFactory(csi_code='230000')

    def test_str(self):
        trade = CSITradeFactory(csi_code='230000', name='HVAC')
        assert str(trade) == '230000 - HVAC'

    def test_ordered_by_csi_code(self):
        CSITradeFactory(csi_code='260000', name='Electrical')
        CSITradeFactory(csi_code='220000', name='Plumbing')
        codes = list(CSITrade.objects.values_list('csi_code', flat=True))
        assert codes == sorted(codes)


@pytest.mark.django_db
class TestProjectType:
    def test_name_is_unique(self):
        ProjectTypeFactory(name='Office TI')
        with pytest.raises(IntegrityError):
            ProjectTypeFactory(name='Office TI')
