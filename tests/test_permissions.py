"""
Role and permission tests.
Run with: py manage.py test tests.test_permissions
"""
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from apps.accounts.models import CustomUser
from apps.accounts.decorators import (
    director_required, finance_required, staff_required,
    construction_required, warehouse_required,
)
from apps.accounts.permissions import (
    can_view_client, can_view_sale, can_add_payment,
    can_cancel_sale, can_create_sale, can_manage_user,
    can_access_workers, can_access_materials,
)

User = get_user_model()


def _make_user(role, username=None):
    return User.objects.create_user(
        username=username or f'user_{role}',
        password='testpass123',
        role=role,
    )


class RolePropertyTests(TestCase):
    """CustomUser role properties return correct booleans."""

    def test_director_properties(self):
        u = _make_user(CustomUser.ROLE_DIRECTOR)
        self.assertTrue(u.is_director)
        self.assertFalse(u.is_admin)
        self.assertTrue(u.can_see_finance)
        self.assertTrue(u.can_manage_users)
        self.assertTrue(u.can_manage_sales)
        self.assertTrue(u.can_manage_clients)
        self.assertTrue(u.can_manage_workers)
        self.assertTrue(u.can_manage_materials)
        self.assertTrue(u.is_staff_member)

    def test_manager_cannot_see_finance(self):
        u = _make_user(CustomUser.ROLE_MANAGER)
        self.assertFalse(u.can_see_finance)
        self.assertFalse(u.can_manage_users)
        self.assertTrue(u.can_manage_sales)
        self.assertTrue(u.is_staff_member)

    def test_accountant_properties(self):
        u = _make_user(CustomUser.ROLE_ACCOUNTANT)
        self.assertTrue(u.can_see_finance)
        self.assertFalse(u.can_manage_users)
        self.assertFalse(u.can_manage_sales)
        self.assertFalse(u.can_manage_workers)

    def test_construction_manager_properties(self):
        u = _make_user(CustomUser.ROLE_CONSTRUCTION)
        self.assertFalse(u.can_see_finance)
        self.assertTrue(u.can_manage_workers)
        self.assertTrue(u.can_manage_materials)
        self.assertFalse(u.can_manage_sales)
        self.assertTrue(u.is_staff_member)

    def test_warehouse_properties(self):
        u = _make_user(CustomUser.ROLE_WAREHOUSE)
        self.assertFalse(u.can_manage_workers)
        self.assertTrue(u.can_manage_materials)
        self.assertFalse(u.can_see_finance)
        self.assertTrue(u.is_staff_member)

    def test_client_is_not_staff(self):
        u = _make_user(CustomUser.ROLE_CLIENT)
        self.assertFalse(u.is_staff_member)
        self.assertFalse(u.can_see_finance)
        self.assertFalse(u.can_manage_sales)


class PermissionFunctionTests(TestCase):
    """Object-level permission helper functions."""

    def setUp(self):
        self.director = _make_user(CustomUser.ROLE_DIRECTOR, 'director1')
        self.manager  = _make_user(CustomUser.ROLE_MANAGER,  'manager1')
        self.accountant = _make_user(CustomUser.ROLE_ACCOUNTANT, 'accountant1')
        self.construction = _make_user(CustomUser.ROLE_CONSTRUCTION, 'foreman1')
        self.warehouse = _make_user(CustomUser.ROLE_WAREHOUSE, 'warehouse1')
        self.client_user = _make_user(CustomUser.ROLE_CLIENT, 'client1')

    def test_can_add_payment(self):
        self.assertTrue(can_add_payment(self.director))
        self.assertTrue(can_add_payment(self.accountant))
        self.assertFalse(can_add_payment(self.manager))
        self.assertFalse(can_add_payment(self.construction))
        self.assertFalse(can_add_payment(self.client_user))

    def test_can_cancel_sale(self):
        self.assertTrue(can_cancel_sale(self.director))
        self.assertFalse(can_cancel_sale(self.manager))
        self.assertFalse(can_cancel_sale(self.accountant))
        self.assertFalse(can_cancel_sale(self.client_user))

    def test_can_create_sale(self):
        self.assertTrue(can_create_sale(self.director))
        self.assertTrue(can_create_sale(self.manager))
        self.assertFalse(can_create_sale(self.accountant))
        self.assertFalse(can_create_sale(self.warehouse))

    def test_can_access_workers(self):
        self.assertTrue(can_access_workers(self.director))
        self.assertTrue(can_access_workers(self.construction))
        self.assertFalse(can_access_workers(self.manager))
        self.assertFalse(can_access_workers(self.warehouse))
        self.assertFalse(can_access_workers(self.accountant))

    def test_can_access_materials(self):
        self.assertTrue(can_access_materials(self.director))
        self.assertTrue(can_access_materials(self.construction))
        self.assertTrue(can_access_materials(self.warehouse))
        self.assertFalse(can_access_materials(self.manager))
        self.assertFalse(can_access_materials(self.accountant))

    def test_can_manage_user(self):
        other_director = _make_user(CustomUser.ROLE_DIRECTOR, 'dir2')
        # Director can manage non-director users
        self.assertTrue(can_manage_user(self.director, self.manager))
        # Director can edit themselves
        self.assertTrue(can_manage_user(self.director, self.director))
        # Non-director cannot manage users
        self.assertFalse(can_manage_user(self.manager, self.accountant))


class LoginRateLimitTests(TestCase):
    """Login view rate limiting."""

    def setUp(self):
        User.objects.create_user(username='testuser', password='correct_pass', role=CustomUser.ROLE_MANAGER)
        from django.core.cache import cache
        cache.clear()

    def test_successful_login_clears_attempts(self):
        from django.core.cache import cache
        # Simulate 2 failed attempts
        cache.set('login_attempts:127.0.0.1', 2, 900)
        response = self.client.post('/auth/login/', {
            'username': 'testuser', 'password': 'correct_pass'
        })
        self.assertEqual(response.status_code, 302)
        self.assertIsNone(cache.get('login_attempts:127.0.0.1'))

    def test_failed_login_increments_counter(self):
        from django.core.cache import cache
        self.client.post('/auth/login/', {
            'username': 'testuser', 'password': 'wrong_pass'
        })
        attempts = cache.get('login_attempts:127.0.0.1', 0)
        self.assertGreater(attempts, 0)

    def test_too_many_attempts_blocks_login(self):
        from django.core.cache import cache
        cache.set('login_attempts:127.0.0.1', 5, 900)
        response = self.client.post('/auth/login/', {
            'username': 'testuser', 'password': 'correct_pass'
        })
        # Should render login page with locked=True, not redirect to dashboard
        self.assertEqual(response.status_code, 200)
        self.assertIn('locked', response.context)
        self.assertTrue(response.context['locked'])


class SaleModelTests(TestCase):
    """Sale model property tests."""

    def _make_sale_data(self):
        from decimal import Decimal
        from apps.clients.models import Client
        from apps.complex.models import Complex, Block, Floor, Apartment

        director = _make_user(CustomUser.ROLE_DIRECTOR, 'dir_sale')
        cplx = Complex.objects.create(name='Test Complex', address='Test')
        block = Block.objects.create(complex=cplx, name='A')
        floor = Floor.objects.create(block=block, number=1)
        apt = Apartment.objects.create(
            floor=floor, number='101', area=50,
            price_per_sqm=Decimal('2000'), total_price=Decimal('100000'),
        )
        client = Client.objects.create(full_name='Test Client', phone='+1234567890')
        return director, apt, client

    def test_payment_progress(self):
        from decimal import Decimal
        from apps.sales.models import Sale
        director, apt, client = self._make_sale_data()
        sale = Sale.objects.create(
            apartment=apt, client=client, total_price=Decimal('100000'),
            payment_type='full', created_by=director,
        )
        self.assertEqual(sale.payment_progress, 0)
        sale.paid_amount = Decimal('50000')
        sale.save()
        self.assertEqual(sale.payment_progress, 50)

    def test_remaining_amount(self):
        from decimal import Decimal
        from apps.sales.models import Sale
        director, apt, client = self._make_sale_data()
        sale = Sale.objects.create(
            apartment=apt, client=client, total_price=Decimal('100000'),
            payment_type='full', paid_amount=Decimal('30000'), created_by=director,
        )
        self.assertEqual(sale.remaining_amount, Decimal('70000'))

    def test_is_not_cancelled_by_default(self):
        from decimal import Decimal
        from apps.sales.models import Sale
        director, apt, client = self._make_sale_data()
        sale = Sale.objects.create(
            apartment=apt, client=client, total_price=Decimal('100000'),
            payment_type='full', created_by=director,
        )
        self.assertFalse(sale.is_cancelled)
        self.assertIsNone(sale.cancelled_at)
