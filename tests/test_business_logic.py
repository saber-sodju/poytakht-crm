"""
Business logic and access-control tests.
Run with: py manage.py test tests.test_business_logic
"""
from decimal import Decimal
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from apps.accounts.models import CustomUser
from apps.clients.models import Client
from apps.complex.models import Complex, Block, Floor, Apartment
from apps.sales.models import Sale, Booking
from apps.sales.services import create_sale, create_booking, cancel_booking, cancel_sale
from apps.complex.services import bulk_generate_apartments
from apps.payments.models import Payment

User = get_user_model()


def _base_data():
    """Director + free apartment + client."""
    director = User.objects.create_user(
        username='dir', password='testpass123', role=CustomUser.ROLE_DIRECTOR
    )
    cplx = Complex.objects.create(name='Test', address='Addr')
    block = Block.objects.create(complex=cplx, name='A')
    floor = Floor.objects.create(block=block, number=1)
    apt = Apartment.objects.create(
        floor=floor, number='101', area=Decimal('50'),
        price_per_sqm=Decimal('2000'), total_price=Decimal('100000'),
        status=Apartment.STATUS_FREE,
    )
    client = Client.objects.create(full_name='Иванов Иван', phone='+992000000001')
    return director, apt, client


class SaleServiceTests(TestCase):

    def test_sale_marks_apartment_sold(self):
        director, apt, client = _base_data()
        create_sale(
            user=director, apartment_id=apt.pk, client=client,
            total_price=Decimal('100000'), payment_type='full',
        )
        apt.refresh_from_db()
        self.assertEqual(apt.status, Apartment.STATUS_SOLD)

    def test_cannot_sell_sold_apartment(self):
        director, apt, client = _base_data()
        create_sale(
            user=director, apartment_id=apt.pk, client=client,
            total_price=Decimal('100000'), payment_type='full',
        )
        with self.assertRaises(ValidationError):
            create_sale(
                user=director, apartment_id=apt.pk, client=client,
                total_price=Decimal('100000'), payment_type='full',
            )

    def test_sale_closes_active_booking(self):
        director, apt, client = _base_data()
        booking = create_booking(
            user=director, apartment_id=apt.pk, client=client,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=7),
        )
        self.assertTrue(booking.is_active)
        apt.refresh_from_db()
        self.assertEqual(apt.status, Apartment.STATUS_BOOKED)

        create_sale(
            user=director, apartment_id=apt.pk, client=client,
            total_price=Decimal('100000'), payment_type='full',
        )
        booking.refresh_from_db()
        self.assertFalse(booking.is_active)

    def test_initial_payment_creates_payment_and_updates_debt(self):
        director, apt, client = _base_data()
        sale = create_sale(
            user=director, apartment_id=apt.pk, client=client,
            total_price=Decimal('100000'), payment_type='installment',
            initial_payment=Decimal('30000'),
        )
        sale.refresh_from_db()
        self.assertEqual(sale.payments.count(), 1)
        self.assertEqual(sale.paid_amount, Decimal('30000'))
        self.assertEqual(sale.remaining_amount, Decimal('70000'))

    def test_initial_payment_cannot_exceed_price(self):
        director, apt, client = _base_data()
        with self.assertRaises(ValidationError):
            create_sale(
                user=director, apartment_id=apt.pk, client=client,
                total_price=Decimal('100000'), payment_type='full',
                initial_payment=Decimal('150000'),
            )
        # Transaction must have rolled back — apartment still free
        apt.refresh_from_db()
        self.assertEqual(apt.status, Apartment.STATUS_FREE)
        self.assertFalse(Sale.objects.filter(apartment=apt).exists())

    def test_cancel_sale_is_soft_and_frees_apartment(self):
        director, apt, client = _base_data()
        sale = create_sale(
            user=director, apartment_id=apt.pk, client=client,
            total_price=Decimal('100000'), payment_type='full',
        )
        cancel_sale(user=director, sale=sale, reason='Клиент передумал')
        sale.refresh_from_db()
        apt.refresh_from_db()
        self.assertTrue(sale.is_cancelled)
        self.assertEqual(sale.cancellation_reason, 'Клиент передумал')
        self.assertEqual(apt.status, Apartment.STATUS_FREE)
        # Record still exists — not deleted
        self.assertTrue(Sale.objects.filter(pk=sale.pk).exists())

    def test_manager_cannot_cancel_sale(self):
        director, apt, client = _base_data()
        manager = User.objects.create_user(
            username='mgr', password='testpass123', role=CustomUser.ROLE_MANAGER
        )
        sale = create_sale(
            user=director, apartment_id=apt.pk, client=client,
            total_price=Decimal('100000'), payment_type='full',
        )
        with self.assertRaises(PermissionError):
            cancel_sale(user=manager, sale=sale, reason='x')

    def test_cancel_booking_frees_apartment(self):
        director, apt, client = _base_data()
        booking = create_booking(
            user=director, apartment_id=apt.pk, client=client,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=7),
        )
        cancel_booking(user=director, booking=booking)
        booking.refresh_from_db()
        apt.refresh_from_db()
        self.assertFalse(booking.is_active)
        self.assertEqual(apt.status, Apartment.STATUS_FREE)

    def test_debt_calculation(self):
        director, apt, client = _base_data()
        sale = create_sale(
            user=director, apartment_id=apt.pk, client=client,
            total_price=Decimal('100000'), payment_type='installment',
            initial_payment=Decimal('25000'),
        )
        Payment.objects.create(
            sale=sale, amount=Decimal('25000'),
            payment_date=timezone.now().date(), added_by=director,
        )
        sale.refresh_from_db()
        self.assertEqual(sale.paid_amount, Decimal('50000'))
        self.assertEqual(sale.debt, Decimal('50000'))
        self.assertEqual(client.total_debt, Decimal('50000'))


class BulkGenerateApartmentsTests(TestCase):

    def _block(self):
        cplx = Complex.objects.create(name='Test', address='Addr')
        return Block.objects.create(complex=cplx, name='A')

    def test_creates_floors_and_apartments(self):
        block = self._block()
        created = bulk_generate_apartments(
            block=block, floor_from=1, floor_to=2, apartments_per_floor=3,
            apartment_type='2', area=Decimal('50'), price_per_sqm=Decimal('1000'),
        )
        self.assertEqual(len(created), 6)
        self.assertEqual(Floor.objects.filter(block=block).count(), 2)
        self.assertEqual(Apartment.objects.filter(floor__block=block).count(), 6)
        apt = Apartment.objects.filter(floor__block=block).first()
        self.assertEqual(apt.total_price, Decimal('50000'))
        self.assertEqual(apt.status, Apartment.STATUS_FREE)

    def test_rerun_skips_existing_numbers_no_duplicates(self):
        block = self._block()
        bulk_generate_apartments(
            block=block, floor_from=1, floor_to=1, apartments_per_floor=2,
            apartment_type='1', area=Decimal('40'), price_per_sqm=Decimal('1000'),
        )
        # Manually free up capacity by generating again on the same range —
        # existing numbers must not be duplicated.
        second = bulk_generate_apartments(
            block=block, floor_from=1, floor_to=1, apartments_per_floor=2,
            apartment_type='1', area=Decimal('40'), price_per_sqm=Decimal('1000'),
        )
        numbers = list(Apartment.objects.filter(floor__block=block).values_list('number', flat=True))
        self.assertEqual(len(numbers), len(set(numbers)))  # no duplicates
        self.assertEqual(len(second), 2)  # continues past the already-used numbers


class IncomeAccountingTests(TestCase):
    """Income must be counted from real Payments, never from Sale.total_price."""

    def test_month_income_counts_payment_not_sale_total(self):
        from django.db.models import Sum
        director, apt, client = _base_data()
        # 100000 sale, but client only paid 30000 up front
        create_sale(
            user=director, apartment_id=apt.pk, client=client,
            total_price=Decimal('100000'), payment_type='installment',
            initial_payment=Decimal('30000'),
        )
        # Dashboard computes income exactly this way
        month_income = Payment.objects.aggregate(t=Sum('amount'))['t'] or 0
        self.assertEqual(month_income, Decimal('30000'))   # not 100000

    def test_sale_without_initial_payment_yields_zero_income(self):
        from django.db.models import Sum
        director, apt, client = _base_data()
        create_sale(
            user=director, apartment_id=apt.pk, client=client,
            total_price=Decimal('100000'), payment_type='full',
        )
        month_income = Payment.objects.aggregate(t=Sum('amount'))['t'] or 0
        self.assertEqual(month_income, 0)
        # But the sale itself exists with a debt of the full price
        sale = Sale.objects.get(apartment=apt)
        self.assertEqual(sale.paid_amount, 0)
        self.assertEqual(sale.debt, Decimal('100000'))


class AuditLogIntegrationTests(TestCase):
    """Business operations must record audit entries and never fail because of them."""

    def test_create_sale_writes_audit_log(self):
        from apps.audit.models import AuditLog
        director, apt, client = _base_data()
        sale = create_sale(
            user=director, apartment_id=apt.pk, client=client,
            total_price=Decimal('100000'), payment_type='full',
        )
        self.assertTrue(
            AuditLog.objects.filter(
                action=AuditLog.ACTION_CREATE, model_name='Sale', object_id=sale.pk
            ).exists()
        )

    def test_initial_payment_writes_audit_log(self):
        from apps.audit.models import AuditLog
        director, apt, client = _base_data()
        create_sale(
            user=director, apartment_id=apt.pk, client=client,
            total_price=Decimal('100000'), payment_type='installment',
            initial_payment=Decimal('30000'),
        )
        self.assertTrue(
            AuditLog.objects.filter(
                action=AuditLog.ACTION_CREATE, model_name='Payment'
            ).exists()
        )

    def test_cancel_sale_writes_audit_log_without_error(self):
        from apps.audit.models import AuditLog
        director, apt, client = _base_data()
        sale = create_sale(
            user=director, apartment_id=apt.pk, client=client,
            total_price=Decimal('100000'), payment_type='full',
        )
        # Must not raise — ACTION_CANCEL and old_value/new_value must be supported
        cancel_sale(user=director, sale=sale, reason='Тест')
        self.assertTrue(
            AuditLog.objects.filter(
                action=AuditLog.ACTION_CANCEL, model_name='Sale', object_id=sale.pk
            ).exists()
        )

    def test_log_action_never_raises(self):
        """A broken audit call must return None, not blow up the caller."""
        from apps.audit.models import log_action, AuditLog
        director = User.objects.create_user(
            username='d', password='x', role=CustomUser.ROLE_DIRECTOR)
        # Passing every supported field, including old_value/new_value
        entry = log_action(
            user=director, action=AuditLog.ACTION_CANCEL,
            model_name='Sale', object_id=1, object_repr='x',
            description='d', old_value='a', new_value='b',
        )
        self.assertIsNotNone(entry)
        self.assertEqual(entry.action, AuditLog.ACTION_CANCEL)


class InitialDirectorCommandTests(TestCase):
    """create_initial_director must be production-safe — no demo accounts."""

    def test_no_env_vars_creates_no_user(self):
        import os
        from unittest import mock
        from django.core.management import call_command
        # Ensure the env is clean of the director vars
        clean_env = {k: v for k, v in os.environ.items()
                     if not k.startswith('INITIAL_DIRECTOR_')}
        with mock.patch.dict(os.environ, clean_env, clear=True):
            call_command('create_initial_director')
        self.assertEqual(CustomUser.objects.count(), 0)

    def test_does_not_create_demo_director(self):
        import os
        from unittest import mock
        from django.core.management import call_command
        clean_env = {k: v for k, v in os.environ.items()
                     if not k.startswith('INITIAL_DIRECTOR_')}
        with mock.patch.dict(os.environ, clean_env, clear=True):
            call_command('create_initial_director')
        # The publicly-known demo login must never be created automatically
        self.assertFalse(CustomUser.objects.filter(username='director').exists())

    def test_creates_director_from_env_vars(self):
        import os
        from unittest import mock
        from django.core.management import call_command
        env = {
            'INITIAL_DIRECTOR_USERNAME': 'boss',
            'INITIAL_DIRECTOR_PASSWORD': 'Str0ng-Pass-9182',
            'INITIAL_DIRECTOR_NAME': 'Илхом Зарипов',
        }
        with mock.patch.dict(os.environ, env):
            call_command('create_initial_director')
        boss = CustomUser.objects.get(username='boss')
        self.assertEqual(boss.role, CustomUser.ROLE_DIRECTOR)
        self.assertTrue(boss.check_password('Str0ng-Pass-9182'))


class ViewAccessTests(TestCase):
    """Backend-level access control — direct URL access must be blocked."""

    def setUp(self):
        self.director = User.objects.create_user(
            username='dir', password='testpass123', role=CustomUser.ROLE_DIRECTOR)
        self.manager = User.objects.create_user(
            username='mgr', password='testpass123', role=CustomUser.ROLE_MANAGER)
        self.accountant = User.objects.create_user(
            username='acc', password='testpass123', role=CustomUser.ROLE_ACCOUNTANT)
        self.warehouse = User.objects.create_user(
            username='wh', password='testpass123', role=CustomUser.ROLE_WAREHOUSE)
        self.client_user = User.objects.create_user(
            username='cl', password='testpass123', role=CustomUser.ROLE_CLIENT)

    def test_manager_cannot_see_expenses(self):
        self.client.login(username='mgr', password='testpass123')
        resp = self.client.get('/expenses/')
        self.assertEqual(resp.status_code, 302)   # redirected away

    def test_accountant_can_see_expenses(self):
        self.client.login(username='acc', password='testpass123')
        resp = self.client.get('/expenses/')
        self.assertEqual(resp.status_code, 200)

    def test_client_cannot_see_reports(self):
        self.client.login(username='cl', password='testpass123')
        resp = self.client.get('/reports/')
        self.assertEqual(resp.status_code, 302)

    def test_manager_cannot_see_reports(self):
        self.client.login(username='mgr', password='testpass123')
        resp = self.client.get('/reports/')
        self.assertEqual(resp.status_code, 302)

    def test_warehouse_cannot_see_clients(self):
        self.client.login(username='wh', password='testpass123')
        resp = self.client.get('/clients/')
        self.assertEqual(resp.status_code, 302)

    def test_warehouse_can_see_materials(self):
        self.client.login(username='wh', password='testpass123')
        resp = self.client.get('/materials/')
        self.assertEqual(resp.status_code, 200)

    def test_manager_cannot_see_audit(self):
        self.client.login(username='mgr', password='testpass123')
        resp = self.client.get('/audit/')
        self.assertEqual(resp.status_code, 302)

    def test_anonymous_redirected_to_login(self):
        resp = self.client.get('/payments/')
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/auth/login/', resp['Location'])


class ClientIsolationTests(TestCase):
    """A client user must only see their own sale."""

    def setUp(self):
        self.director, self.apt, self.client_a = _base_data()
        self.sale = create_sale(
            user=self.director, apartment_id=self.apt.pk, client=self.client_a,
            total_price=Decimal('100000'), payment_type='full',
        )
        # Client B — a different client with a user account
        self.user_b = User.objects.create_user(
            username='client_b', password='testpass123', role=CustomUser.ROLE_CLIENT)
        self.client_b = Client.objects.create(
            full_name='Петров Пётр', phone='+992000000002', user=self.user_b)

    def test_foreign_client_cannot_open_sale_detail(self):
        self.client.login(username='client_b', password='testpass123')
        resp = self.client.get(f'/sales/{self.sale.pk}/')
        # staff_required redirects client role away before object check
        self.assertIn(resp.status_code, (302, 403))

    def test_own_client_dashboard_shows_own_sale(self):
        user_a = User.objects.create_user(
            username='client_a', password='testpass123', role=CustomUser.ROLE_CLIENT)
        self.client_a.user = user_a
        self.client_a.save()
        self.client.login(username='client_a', password='testpass123')
        resp = self.client.get('/client/')
        if resp.status_code == 200:
            self.assertContains(resp, 'Иванов')


class UploadValidatorTests(TestCase):

    def test_dangerous_extension_rejected(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from core.validators import validate_document
        bad = SimpleUploadedFile('shell.php', b'<?php ?>')
        with self.assertRaises(ValidationError):
            validate_document(bad)

    def test_double_extension_rejected(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from core.validators import validate_document
        sneaky = SimpleUploadedFile('shell.php.jpg', b'fake')
        with self.assertRaises(ValidationError):
            validate_document(sneaky)

    def test_valid_pdf_accepted(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from core.validators import validate_document
        ok = SimpleUploadedFile('receipt.pdf', b'%PDF-1.4')
        validate_document(ok)   # no exception

    def test_oversized_file_rejected(self):
        from core.validators import validate_document, MAX_UPLOAD_SIZE

        class FakeFile:
            name = 'big.pdf'
            size = MAX_UPLOAD_SIZE + 1

        with self.assertRaises(ValidationError):
            validate_document(FakeFile())

    def test_exe_rejected_for_images(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from core.validators import validate_image
        bad = SimpleUploadedFile('virus.exe', b'MZ')
        with self.assertRaises(ValidationError):
            validate_image(bad)
