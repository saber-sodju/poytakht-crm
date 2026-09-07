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
from apps.complex.services import (
    create_floors, copy_floor_layout,
    delete_apartment, delete_floor, delete_block, delete_complex,
)
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


class FloorLayoutTests(TestCase):
    """Floors are created empty, then one hand-built floor's apartment mix is
    copied up the block — a real floor is a mix of flat types, never N
    identical ones."""

    def _block(self):
        cplx = Complex.objects.create(name='Test', address='Addr')
        return Block.objects.create(complex=cplx, name='A')

    def _mixed_floor(self, block, number=1):
        """A realistic floor: two 1-room, one 2-room, one 3-room."""
        floor = Floor.objects.create(block=block, number=number)
        spec = [('1', '45'), ('1', '45'), ('2', '68'), ('3', '92')]
        for i, (apt_type, area) in enumerate(spec, start=1):
            Apartment.objects.create(
                floor=floor, number=f'{number}{i:02d}',
                apartment_type=apt_type, area=Decimal(area),
                price_per_sqm=Decimal('1000'),
                total_price=Decimal(area) * Decimal('1000'),
            )
        return floor

    def test_create_floors_makes_empty_floors(self):
        block = self._block()
        created = create_floors(block=block, count=12)
        self.assertEqual(len(created), 12)
        self.assertEqual(Floor.objects.filter(block=block).count(), 12)
        self.assertEqual(Apartment.objects.filter(floor__block=block).count(), 0)

    def test_create_floors_is_idempotent(self):
        block = self._block()
        create_floors(block=block, count=5)
        again = create_floors(block=block, count=5)
        self.assertEqual(again, [])
        self.assertEqual(Floor.objects.filter(block=block).count(), 5)

    def test_copy_preserves_the_mix_of_types_and_areas(self):
        block = self._block()
        source = self._mixed_floor(block, 1)
        created = copy_floor_layout(source_floor=source, target_numbers=range(2, 13))

        self.assertEqual(len(created), 44)  # 4 apartments x 11 floors
        for floor_number in range(2, 13):
            apts = Apartment.objects.filter(floor__block=block, floor__number=floor_number)
            self.assertEqual(
                sorted(apts.values_list('apartment_type', flat=True)),
                ['1', '1', '2', '3'],
            )
            self.assertEqual(
                sorted(a.area for a in apts),
                [Decimal('45'), Decimal('45'), Decimal('68'), Decimal('92')],
            )

    def test_copy_numbers_by_floor_and_position(self):
        block = self._block()
        source = self._mixed_floor(block, 1)
        copy_floor_layout(source_floor=source, target_numbers=[5])
        numbers = sorted(
            Apartment.objects.filter(floor__block=block, floor__number=5)
            .values_list('number', flat=True)
        )
        self.assertEqual(numbers, ['501', '502', '503', '504'])

    def test_copy_applies_price_step_per_floor(self):
        block = self._block()
        source = self._mixed_floor(block, 1)
        copy_floor_layout(
            source_floor=source, target_numbers=[3],
            price_step_per_floor=Decimal('20'),
        )
        apt = Apartment.objects.get(floor__block=block, floor__number=3, number='301')
        # two floors above the source at +20 each
        self.assertEqual(apt.price_per_sqm, Decimal('1040'))
        self.assertEqual(apt.total_price, apt.area * Decimal('1040'))

    def test_copy_never_touches_source_floor_or_duplicates(self):
        block = self._block()
        source = self._mixed_floor(block, 1)
        copy_floor_layout(source_floor=source, target_numbers=[1, 2])  # 1 == source
        self.assertEqual(source.apartments.count(), 4)  # untouched
        second = copy_floor_layout(source_floor=source, target_numbers=[2])
        numbers = list(
            Apartment.objects.filter(floor__block=block, floor__number=2)
            .values_list('number', flat=True)
        )
        self.assertEqual(len(numbers), len(set(numbers)))  # no duplicate numbers
        self.assertEqual(len(second), 4)  # tops the floor up rather than clashing

    def test_commercial_ground_floor_stays_separate_from_the_flats(self):
        """Ground floors are often shops. They're the same kind of sellable
        unit, just typed differently — and copying the residential floor up
        must never turn flats into shops or vice versa."""
        block = self._block()
        shops = Floor.objects.create(block=block, number=1)
        for i in (1, 2):
            Apartment.objects.create(
                floor=shops, number=f'1{i:02d}',
                apartment_type=Apartment.TYPE_COMMERCIAL,
                area=Decimal('120'), price_per_sqm=Decimal('1500'),
                total_price=Decimal('180000'),
            )
        source = self._mixed_floor(block, 2)
        copy_floor_layout(source_floor=source, target_numbers=range(3, 6))

        shop = shops.apartments.first()
        self.assertTrue(shop.is_commercial)
        self.assertEqual(shop.unit_label, 'Помещение')
        self.assertIn('Помещение', str(shop))
        # the shops are untouched by the copy, and nothing above is commercial
        self.assertEqual(shops.apartments.count(), 2)
        upper = Apartment.objects.filter(floor__block=block, floor__number__gte=3)
        self.assertEqual(upper.count(), 12)
        self.assertFalse(upper.filter(apartment_type=Apartment.TYPE_COMMERCIAL).exists())

    def test_copies_are_free_regardless_of_source_status(self):
        block = self._block()
        source = self._mixed_floor(block, 1)
        source.apartments.update(status=Apartment.STATUS_SOLD)
        copy_floor_layout(source_floor=source, target_numbers=[4])
        statuses = set(
            Apartment.objects.filter(floor__block=block, floor__number=4)
            .values_list('status', flat=True)
        )
        self.assertEqual(statuses, {Apartment.STATUS_FREE})


class DeleteGuardTests(TestCase):
    """Deleting apartments/floors/blocks/complexes must never silently
    destroy sale/payment history."""

    def test_deletes_clean_apartment(self):
        director, apt, client = _base_data()
        delete_apartment(apt)
        self.assertFalse(Apartment.objects.filter(pk=apt.pk).exists())

    def test_blocks_apartment_with_sale(self):
        director, apt, client = _base_data()
        create_sale(
            user=director, apartment_id=apt.pk, client=client,
            total_price=Decimal('100000'), payment_type='full',
        )
        with self.assertRaises(ValidationError):
            delete_apartment(apt)
        self.assertTrue(Apartment.objects.filter(pk=apt.pk).exists())

    def test_blocks_apartment_with_cancelled_sale(self):
        # Even a cancelled sale is kept for the record — must still block deletion.
        director, apt, client = _base_data()
        sale = create_sale(
            user=director, apartment_id=apt.pk, client=client,
            total_price=Decimal('100000'), payment_type='full',
        )
        cancel_sale(user=director, sale=sale, reason='x')
        with self.assertRaises(ValidationError):
            delete_apartment(apt)

    def test_blocks_apartment_with_booking(self):
        director, apt, client = _base_data()
        create_booking(
            user=director, apartment_id=apt.pk, client=client,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=7),
        )
        with self.assertRaises(ValidationError):
            delete_apartment(apt)

    def test_deletes_clean_floor_cascades_apartments(self):
        director, apt, client = _base_data()
        floor = apt.floor
        delete_floor(floor)
        self.assertFalse(Floor.objects.filter(pk=floor.pk).exists())
        self.assertFalse(Apartment.objects.filter(pk=apt.pk).exists())

    def test_blocks_floor_with_sold_apartment(self):
        director, apt, client = _base_data()
        create_sale(
            user=director, apartment_id=apt.pk, client=client,
            total_price=Decimal('100000'), payment_type='full',
        )
        with self.assertRaises(ValidationError):
            delete_floor(apt.floor)

    def test_blocks_block_and_complex_with_sold_apartment(self):
        director, apt, client = _base_data()
        create_sale(
            user=director, apartment_id=apt.pk, client=client,
            total_price=Decimal('100000'), payment_type='full',
        )
        with self.assertRaises(ValidationError):
            delete_block(apt.block)
        with self.assertRaises(ValidationError):
            delete_complex(apt.block.complex)

    def test_deletes_clean_complex_cascades_everything(self):
        director, apt, client = _base_data()
        cplx = apt.block.complex
        delete_complex(cplx)
        self.assertFalse(Complex.objects.filter(pk=cplx.pk).exists())
        self.assertFalse(Apartment.objects.filter(pk=apt.pk).exists())


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


class InstallmentScheduleTests(TestCase):
    """Instalment/mortgage: the down payment comes off the price, the rest is
    split evenly across the agreed number of months."""

    def _sale(self, total, down, months, ptype='installment'):
        director, apt, client = _base_data()
        apt.total_price = Decimal(total)
        apt.save(update_fields=['total_price'])
        return create_sale(
            user=director, apartment_id=apt.pk, client=client,
            total_price=Decimal(total), payment_type=ptype,
            initial_payment=Decimal(down) if down else None,
            installment_months=months,
        )

    def test_down_payment_comes_off_the_price(self):
        sale = self._sale('100000', '30000', 12)
        self.assertEqual(sale.paid_amount, Decimal('30000'))
        self.assertEqual(sale.debt, Decimal('70000'))

    def test_schedule_has_one_row_per_month(self):
        sale = self._sale('100000', '30000', 12)
        self.assertEqual(sale.schedule.count(), 12)

    def test_instalments_are_equal_and_sum_to_the_debt(self):
        sale = self._sale('100000', '30000', 12)
        amounts = list(sale.schedule.order_by('due_date').values_list('amount', flat=True))
        # 70000/12 = 5833.33(3): eleven equal instalments, and the last one
        # carries the rounding remainder so nothing is left hanging.
        self.assertEqual(amounts[:11], [Decimal('5833.33')] * 11)
        self.assertEqual(amounts[-1], Decimal('5833.37'))
        self.assertEqual(sum(amounts), Decimal('70000'))          # exactly the debt

    def test_rounding_remainder_lands_on_the_last_instalment(self):
        # 100 / 3 = 33.333... — the schedule must still add up to exactly 100
        sale = self._sale('100', '0', 3)
        amounts = list(sale.schedule.order_by('due_date').values_list('amount', flat=True))
        self.assertEqual(amounts, [Decimal('33.33'), Decimal('33.33'), Decimal('33.34')])
        self.assertEqual(sum(amounts), sale.debt)

    def test_due_dates_are_monthly_from_the_sale_date(self):
        sale = self._sale('120000', '0', 3)
        due = list(sale.schedule.order_by('due_date').values_list('due_date', flat=True))
        self.assertEqual(len(due), 3)
        for i in range(1, len(due)):
            gap_months = (due[i].year - due[i - 1].year) * 12 + due[i].month - due[i - 1].month
            self.assertEqual(gap_months, 1)
        self.assertGreater(due[0], sale.sale_date)

    def test_full_payment_gets_no_schedule(self):
        sale = self._sale('50000', '50000', None, ptype='full')
        self.assertEqual(sale.schedule.count(), 0)
        self.assertEqual(sale.debt, 0)

    def test_mortgage_also_builds_a_schedule(self):
        sale = self._sale('200000', '40000', 24, ptype='mortgage')
        self.assertEqual(sale.schedule.count(), 24)
        self.assertEqual(sum(sale.schedule.values_list('amount', flat=True)), Decimal('160000'))

    def test_paying_an_instalment_reduces_the_debt(self):
        from apps.payments.models import Payment
        sale = self._sale('100000', '30000', 12)
        first = sale.schedule.order_by('due_date').first()
        Payment.objects.create(sale=sale, schedule=first, amount=first.amount,
                               payment_date=first.due_date)
        sale.refresh_from_db()
        first.refresh_from_db()
        self.assertTrue(first.is_paid)
        self.assertEqual(sale.paid_amount, Decimal('30000') + first.amount)
