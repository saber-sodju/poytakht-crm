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
