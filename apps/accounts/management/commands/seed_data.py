"""
Management command: python manage.py seed_data [--reset]

Creates demo data for all roles and modules. Idempotent by default (skips
anything that already exists) — pass --reset to wipe ALL existing data
first (including every user account) and rebuild from scratch.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal
import random


class Command(BaseCommand):
    help = 'Seed demo data for CRM'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset', action='store_true',
            help='Delete ALL existing data first (users, sales, apartments, everything), then reseed.',
        )
        parser.add_argument(
            '--users-only', action='store_true',
            help='Only create the 3 staff accounts — skip all demo complex/clients/sales/expenses/workers/materials data.',
        )
        parser.add_argument(
            '--keep-users', action='store_true',
            help='With --reset: wipe business data but leave existing accounts alone '
                 '(keeps their current passwords and login history).',
        )

    def handle(self, *args, **kwargs):
        if kwargs.get('reset'):
            self._wipe_all(keep_users=kwargs.get('keep_users', False))

        self.stdout.write('Creating seed data...')

        self._create_users()

        if not kwargs.get('users_only'):
            self._create_complex()
            self._create_clients()
            self._create_leads()
            self._create_sales()
            self._create_expenses()
            self._create_workers()
            self._create_materials()

        self.stdout.write(self.style.SUCCESS('[OK] Dannye sozdany!'))
        self.stdout.write('')
        self.stdout.write('Loginy dlya vkhoda:')
        self.stdout.write('  umed     / 7777  - Direktor (Umed)')
        self.stdout.write('  firuz    / 8888  - Administrator (Firuz)')
        self.stdout.write('  manager  / 6666  - Menedzher')

    # ── Wipe ──────────────────────────────────────────────────────────────────

    def _wipe_all(self, keep_users=False):
        from apps.audit.models import AuditLog
        from apps.payments.models import Payment, PaymentSchedule
        from apps.sales.models import Sale, Booking
        from apps.clients.models import Client, Lead
        from apps.complex.models import Complex, Block, Floor, Apartment, ConstructionStage, PhotoReport
        from apps.expenses.models import Expense
        from apps.workers.models import Worker, Team, Position, Attendance, SalaryPayment
        from apps.materials.models import Material, Supplier, MaterialMovement
        from apps.accounts.models import CustomUser, Notification

        AuditLog.objects.all().delete()
        Payment.objects.all().delete()
        PaymentSchedule.objects.all().delete()
        Sale.objects.all().delete()
        Booking.objects.all().delete()
        Lead.objects.all().delete()
        Client.objects.all().delete()
        PhotoReport.objects.all().delete()
        ConstructionStage.objects.all().delete()
        Apartment.objects.all().delete()
        Floor.objects.all().delete()
        Block.objects.all().delete()
        Complex.objects.all().delete()
        Expense.objects.all().delete()
        SalaryPayment.objects.all().delete()
        Attendance.objects.all().delete()
        Worker.objects.all().delete()
        Team.objects.all().delete()
        Position.objects.all().delete()
        MaterialMovement.objects.all().delete()
        Material.objects.all().delete()
        Supplier.objects.all().delete()
        Notification.objects.all().delete()
        if keep_users:
            # Clearing out test data before handover: the real staff accounts
            # stay exactly as they are — same passwords, same login history.
            self.stdout.write(self.style.WARNING(
                f'  Wiped all business data. Kept {CustomUser.objects.count()} account(s).'
            ))
        else:
            CustomUser.objects.all().delete()
            self.stdout.write(self.style.WARNING('  Wiped ALL existing data, including accounts.'))

    # ── Users ─────────────────────────────────────────────────────────────────

    def _create_users(self):
        from apps.accounts.models import CustomUser
        # NOTE: these passwords (7777/8888/6666) deliberately violate the
        # project's own AUTH_PASSWORD_VALIDATORS (min length 8, not fully
        # numeric) — set explicitly per the client's request. create_user()
        # only hashes the password, it doesn't run the validators (those are
        # only invoked by form clean()), so this works, but it's a real
        # brute-force risk: a 4-digit PIN is 10,000 combinations, well within
        # the 5-attempts/15-min lockout being annoying rather than protective
        # if someone specifically targets these accounts.
        users_data = [
            {'username': 'umed', 'first_name': 'Умед', 'role': 'director', 'password': '7777', 'phone': '+992900000001'},
            {'username': 'firuz', 'first_name': 'Фируз', 'role': 'admin', 'password': '8888', 'phone': '+992900000002'},
            {'username': 'manager', 'first_name': 'Менеджер', 'role': 'manager', 'password': '6666', 'phone': '+992900000003'},
        ]
        for data in users_data:
            if not CustomUser.objects.filter(username=data['username']).exists():
                user = CustomUser.objects.create_user(
                    username=data['username'],
                    password=data['password'],
                    first_name=data['first_name'],
                    role=data['role'],
                    phone=data['phone'],
                    email=f"{data['username']}@poytakhtinshoot.com",
                )
                self.stdout.write(f'  User created: {user.username} ({data["role"]})')

    # ── Complex / Blocks / Floors / Apartments ──────────────────────────────────

    def _create_complex(self):
        from apps.complex.models import Complex, Block, Floor, Apartment, ConstructionStage

        if Complex.objects.exists():
            self.stdout.write('  Complex already exists, skipping.')
            return

        cx = Complex.objects.create(
            name='ЖК Пойтахт Плаза',
            address='г. Душанбе, пр. Рудаки, д. 45',
            description='Современный жилой комплекс в центре Душанбе',
        )

        blocks_data = [
            {'name': 'Блок А', 'budget': 800000},
            {'name': 'Блок Б', 'budget': 750000},
            {'name': 'Блок В', 'budget': 600000},
        ]

        apt_types = ['1', '2', '3', '2', '1', '3', '2']
        # ~40% sold, ~10% booked, ~50% free — a complex mid-way through sales,
        # not a ghost building and not sold out either.
        statuses = ['sold'] * 4 + ['booked'] + ['free'] * 5

        for bdata in blocks_data:
            block = Block.objects.create(
                complex=cx,
                name=bdata['name'],
                budget_planned=bdata['budget'],
            )
            for stage_key, _ in ConstructionStage.STAGE_CHOICES:
                ConstructionStage.objects.create(
                    block=block, stage=stage_key,
                    status='completed' if stage_key in ['foundation', 'frame', 'walls'] else 'in_progress',
                    progress=100 if stage_key in ['foundation', 'frame', 'walls'] else random.randint(20, 80),
                    responsible='Прораб Мирзоев А.',
                )

            apt_number = 1
            for floor_num in range(1, 10):
                floor = Floor.objects.create(block=block, number=floor_num)
                for pos in range(4):
                    apt_type = apt_types[(apt_number - 1) % len(apt_types)]
                    area = {'1': Decimal('45.5'), '2': Decimal('72.0'), '3': Decimal('95.0')}[apt_type]
                    price_per_sqm = Decimal('800') + Decimal(str(floor_num * 20))
                    total = area * price_per_sqm
                    status_idx = (apt_number - 1) % len(statuses)
                    status = statuses[status_idx]

                    Apartment.objects.create(
                        floor=floor,
                        number=str(apt_number + (100 if bdata['name'] == 'Блок А' else 200 if bdata['name'] == 'Блок Б' else 300)),
                        apartment_type=apt_type,
                        area=area,
                        price_per_sqm=price_per_sqm,
                        total_price=total,
                        status=status,
                    )
                    apt_number += 1

        self.stdout.write(f'  Complex created: {cx.name} ({Apartment.objects.count()} apartments)')

    # ── Clients ───────────────────────────────────────────────────────────────

    FIRST_NAMES_M = ['Бахром', 'Темур', 'Санжар', 'Шухрат', 'Рустам', 'Фаридун', 'Комил',
                      'Далер', 'Джамшед', 'Хасан', 'Азиз', 'Нурулло', 'Умарали', 'Сухроб',
                      'Парвиз', 'Искандар', 'Толиб', 'Фирдавс', 'Бехруз', 'Манучехр']
    FIRST_NAMES_F = ['Мадина', 'Зарина', 'Лола', 'Дилноза', 'Гулнора', 'Саноат', 'Мунира',
                      'Нигина', 'Фарзона', 'Шахноза', 'Наргис', 'Замира', 'Малика', 'Севара']
    LAST_STEMS = ['Акрамов', 'Холматов', 'Назаров', 'Рашидов', 'Юсупов', 'Мирзоев', 'Каримов',
                  'Тошматов', 'Исмоилов', 'Баротов', 'Алиев', 'Хасанов', 'Тоиров', 'Раджабов',
                  'Собиров', 'Файзуллоев', 'Гуломов', 'Шарипов', 'Одинаев', 'Пулатов']
    PATRONYMIC_M = ['Саидович', 'Рустамович', 'Алишерович', 'Хасанович', 'Бекович', 'Умарович',
                    'Шамсович', 'Бахтиёрович', 'Джураевич', 'Комилович']
    PATRONYMIC_F = ['Саидовна', 'Рустамовна', 'Фаридовна', 'Бахтиёровна', 'Улмасовна', 'Хасановна']

    def _generate_client_names(self, n):
        random.seed(42)  # reproducible across runs
        names = []
        used = set()
        while len(names) < n:
            is_male = random.random() < 0.6
            first = random.choice(self.FIRST_NAMES_M if is_male else self.FIRST_NAMES_F)
            stem = random.choice(self.LAST_STEMS)
            last = stem if is_male else stem[:-2] + 'а'  # crude masc->fem surname ending
            patronymic = random.choice(self.PATRONYMIC_M if is_male else self.PATRONYMIC_F)
            full = f'{last} {first} {patronymic}'
            if full in used:
                continue
            used.add(full)
            names.append(full)
        return names

    def _create_clients(self):
        from apps.clients.models import Client
        from apps.accounts.models import CustomUser

        if Client.objects.exists():
            return

        manager = CustomUser.objects.filter(role='manager').first()
        names = self._generate_client_names(45)
        series_pool = ['АА', 'АБ', 'АВ', 'АГ', 'АД', 'АЕ', 'АЖ', 'АЗ', 'АИ', 'АК']
        clients = []
        for i, full_name in enumerate(names):
            c = Client.objects.create(
                full_name=full_name,
                phone=f'+9929{i:07d}',
                passport_series=series_pool[i % len(series_pool)],
                passport_number=f'{1000000 + i * 137}',
                added_by=manager,
            )
            clients.append(c)
        self.stdout.write(f'  Created {len(clients)} clients')

    # ── Leads ─────────────────────────────────────────────────────────────────

    def _create_leads(self):
        from apps.clients.models import Lead
        from apps.accounts.models import CustomUser

        if Lead.objects.exists():
            return

        manager = CustomUser.objects.filter(role='manager').first()
        today = date.today()
        leads_data = [
            ('Исмоилов Рустам', '+992910111111', 'new', '2-комнатная', 60000, 'instagram'),
            ('Баротова Саноат', '+992910222222', 'thinking', '3-комнатная', 85000, 'call'),
            ('Алиев Нурулло', '+992910333333', 'callback', '1-комнатная', 40000, 'office'),
            ('Хасанов Азиз', '+992910444444', 'negotiation', '2-комнатная', 65000, 'referral'),
            ('Тоирова Мунира', '+992910555555', 'refused', '3-комнатная', 90000, 'advertising'),
            ('Раджабов Фаридун', '+992910666666', 'new', '2-комнатная', 62000, 'instagram'),
            ('Собирова Нигина', '+992910777777', 'negotiation', '1-комнатная', 42000, 'referral'),
            ('Пулатов Джамшед', '+992910888888', 'callback', '3-комнатная', 88000, 'call'),
        ]
        for name, phone, status, interest, budget, source in leads_data:
            Lead.objects.create(
                name=name, phone=phone, status=status,
                interested_in=interest, budget=budget, source=source,
                assigned_to=manager,
                next_contact_date=today + timedelta(days=random.randint(1, 7)) if status in ['callback', 'negotiation'] else None,
            )
        self.stdout.write(f'  Created {len(leads_data)} leads')

    # ── Sales / Payments (the detailed "who owes what" part) ────────────────────

    def _create_sales(self):
        from apps.complex.models import Apartment
        from apps.clients.models import Client
        from apps.sales.models import Sale, Booking
        from apps.payments.models import Payment, PaymentSchedule
        from apps.accounts.models import CustomUser

        if Sale.objects.exists():
            return

        manager = CustomUser.objects.filter(role='manager').first()
        # No accountant role in this dataset — fall back to admin for "who recorded the payment".
        money_user = CustomUser.objects.filter(role='accountant').first() \
            or CustomUser.objects.filter(role='admin').first() or manager
        clients = list(Client.objects.all())
        today = date.today()
        client_i = 0

        def next_client():
            nonlocal client_i
            c = clients[client_i % len(clients)]
            client_i += 1
            return c

        # Bookings — a few 'booked' apartments get an active reservation with a deposit.
        booked_apts = list(Apartment.objects.filter(status='booked'))
        for apt in booked_apts:
            Booking.objects.create(
                apartment=apt, client=next_client(),
                end_date=today + timedelta(days=random.randint(3, 14)),
                deposit=(apt.total_price * Decimal('0.05')).quantize(Decimal('1')),
                created_by=manager,
            )

        # Sales — EVERY 'sold' apartment gets a real Sale record with a realistic
        # payment history, not just the first few. Payment type + how far along
        # the installment/mortgage plan is are both randomized so debt figures
        # vary realistically across the portfolio.
        sold_apts = list(Apartment.objects.filter(status='sold'))
        payment_types = ['full', 'installment', 'installment', 'mortgage']
        random.seed(7)

        for i, apt in enumerate(sold_apts):
            client = next_client()
            ptype = payment_types[i % len(payment_types)]
            months_ago = random.randint(1, 20)
            sale_date = today - timedelta(days=months_ago * 30 + random.randint(0, 25))

            sale = Sale.objects.create(
                apartment=apt, client=client,
                total_price=apt.total_price,
                payment_type=ptype,
                contract_number=f'ДКП-2025-{1000 + i}',
                contract_date=sale_date,
                sale_date=sale_date,
                created_by=manager,
            )

            if ptype == 'full':
                Payment.objects.create(
                    sale=sale, amount=apt.total_price,
                    payment_date=sale_date, added_by=money_user,
                    note='Оплата полной суммы при оформлении',
                )
            else:
                # installment or mortgage: an upfront deposit, then a monthly
                # schedule over 12 (installment) or 24 (mortgage) months.
                deposit_pct = Decimal('0.30') if ptype == 'installment' else Decimal('0.20')
                plan_months = 12 if ptype == 'installment' else 24
                deposit = (apt.total_price * deposit_pct).quantize(Decimal('0.01'))

                Payment.objects.create(
                    sale=sale, amount=deposit,
                    payment_date=sale_date, added_by=money_user,
                    note='Первоначальный взнос',
                )

                monthly = ((apt.total_price - deposit) / plan_months).quantize(Decimal('0.01'))
                # how many of the plan's monthly payments are already due by now
                months_elapsed = min(plan_months, months_ago)
                for m in range(1, plan_months + 1):
                    due = sale_date + timedelta(days=m * 30)
                    schedule = PaymentSchedule.objects.create(
                        sale=sale, due_date=due, amount=monthly,
                    )
                    if m <= months_elapsed:
                        # ~85% of due installments were actually paid on time —
                        # the rest are left unpaid/overdue, on purpose, so the
                        # CRM's overdue-debt tracking has something real to show.
                        if random.random() < 0.85:
                            Payment.objects.create(
                                sale=sale, schedule=schedule, amount=monthly,
                                payment_date=due, added_by=money_user,
                                note=f'Плановый платёж {m}/{plan_months}',
                            )

            sale.update_paid_amount()

        self.stdout.write(f'  Created {len(sold_apts)} sales (with realistic payment history) and {len(booked_apts)} bookings')

    # ── Expenses ──────────────────────────────────────────────────────────────

    def _create_expenses(self):
        from apps.expenses.models import Expense
        from apps.complex.models import Block, Complex
        from apps.accounts.models import CustomUser

        if Expense.objects.exists():
            return

        money_user = CustomUser.objects.filter(role='accountant').first() \
            or CustomUser.objects.filter(role='admin').first()
        blocks = list(Block.objects.all())
        cx = Complex.objects.first()
        today = date.today()

        expenses_data = [
            ('materials', 45000, 'Кирпич и цемент для кладки'),
            ('salary', 28000, 'Зарплата рабочих за месяц'),
            ('equipment', 12000, 'Аренда крана'),
            ('transport', 3500, 'Доставка материалов'),
            ('documents', 800, 'Проектная документация'),
            ('taxes', 5200, 'НДС за квартал'),
            ('materials', 32000, 'Металлоконструкции'),
            ('utilities', 1200, 'Электричество на стройплощадке'),
        ]

        for i, (cat, amount, desc) in enumerate(expenses_data):
            block = blocks[i % len(blocks)] if blocks else None
            Expense.objects.create(
                complex=cx, block=block,
                category=cat, amount=amount,
                date=today - timedelta(days=random.randint(1, 60)),
                description=desc, added_by=money_user,
            )
        self.stdout.write('  Created 8 expenses')

    # ── Workers ───────────────────────────────────────────────────────────────

    def _create_workers(self):
        from apps.workers.models import Position, Team, Worker, Attendance
        from apps.complex.models import Complex
        from apps.accounts.models import CustomUser

        if Worker.objects.exists():
            return

        cx = Complex.objects.first()
        admin = CustomUser.objects.filter(role='admin').first() or CustomUser.objects.first()
        today = date.today()

        positions_data = ['Прораб', 'Каменщик', 'Бетонщик', 'Сварщик',
                          'Электрик', 'Плиточник', 'Разнорабочий']
        positions = {p: Position.objects.get_or_create(name=p)[0] for p in positions_data}

        team_a = Team.objects.create(name='Бригада А', complex=cx)
        team_b = Team.objects.create(name='Бригада Б', complex=cx)

        workers_data = [
            ('Мирзоев Акбар Холович', '+992911001001', 'Прораб', team_a, 'monthly', 800),
            ('Рахимов Баходур Акбарович', '+992911001002', 'Каменщик', team_a, 'daily', 30),
            ('Назаров Шохрух Бекович', '+992911001003', 'Каменщик', team_a, 'daily', 28),
            ('Алиев Комил Рустамович', '+992911001004', 'Бетонщик', team_a, 'daily', 32),
            ('Юсупов Фирдавс Умарович', '+992911001005', 'Сварщик', team_b, 'daily', 35),
            ('Хасанов Пулод Шамсович', '+992911001006', 'Электрик', team_b, 'monthly', 600),
            ('Каримов Зафар Бахтиёрович', '+992911001007', 'Плиточник', team_b, 'daily', 30),
            ('Турсунов Даврон Сайдалиевич', '+992911001008', 'Разнорабочий', team_b, 'daily', 20),
        ]

        workers = []
        for fname, phone, pos_name, team, s_type, rate in workers_data:
            w = Worker.objects.create(
                full_name=fname, phone=phone,
                position=positions[pos_name], team=team,
                salary_type=s_type, salary_rate=Decimal(str(rate)),
                hired_date=today - timedelta(days=random.randint(60, 365)),
                added_by=admin,
            )
            workers.append(w)

        statuses = ['present', 'present', 'present', 'present', 'half', 'absent', 'present']
        for w in workers:
            for i, days_back in enumerate(range(6, -1, -1)):
                d = today - timedelta(days=days_back)
                Attendance.objects.create(
                    worker=w, date=d,
                    status=statuses[i % len(statuses)],
                    recorded_by=admin,
                )

        self.stdout.write(f'  Created {len(workers)} workers with attendance')

    # ── Materials ─────────────────────────────────────────────────────────────

    def _create_materials(self):
        from apps.materials.models import Supplier, Material, MaterialMovement
        from apps.complex.models import Block
        from apps.accounts.models import CustomUser

        if Material.objects.exists():
            return

        admin = CustomUser.objects.filter(role='admin').first() or CustomUser.objects.first()
        block = Block.objects.first()
        today = date.today()

        sup1 = Supplier.objects.create(
            name='ТаджикСтройМат', phone='+992372001111',
            contact_person='Назаров Комил', address='г. Душанбе, ул. Ленина 10'
        )
        sup2 = Supplier.objects.create(
            name='Стройбаза Восток', phone='+992372002222',
            contact_person='Рахимов Шухрат', address='г. Душанбе, ул. Айни 25'
        )

        materials_data = [
            ('Цемент М400', 'bag', sup1, 50, 500, 8.50),
            ('Арматура 12мм', 'ton', sup1, 2, 20, 850),
            ('Кирпич красный', 'piece', sup2, 500, 5000, 0.25),
            ('Песок строительный', 'm3', sup2, 5, 50, 25),
            ('Щебень 20-40мм', 'm3', sup1, 5, 30, 35),
            ('Фанера 18мм', 'piece', sup2, 10, 50, 18),
            ('Проволока вязальная', 'kg', sup1, 50, 200, 1.20),
            ('Гвозди 80мм', 'kg', sup1, 20, 100, 1.50),
        ]

        for name, unit, supplier, min_qty, qty, price in materials_data:
            m = Material.objects.create(
                name=name, unit=unit, supplier=supplier,
                min_quantity=Decimal(str(min_qty)),
                price_per_unit=Decimal(str(price)),
            )
            mv = MaterialMovement(
                material=m, direction='in',
                quantity=Decimal(str(qty)),
                price_per_unit=Decimal(str(price)),
                supplier=supplier, block=block,
                date=today - timedelta(days=random.randint(5, 30)),
                note='Начальный остаток', added_by=admin,
            )
            mv.save()

        cement = Material.objects.filter(name='Цемент М400').first()
        if cement:
            mv = MaterialMovement(
                material=cement, direction='out',
                quantity=Decimal('150'), price_per_unit=cement.price_per_unit,
                block=block, date=today - timedelta(days=3),
                note='Использовано для кладки', added_by=admin,
            )
            mv.save()

        self.stdout.write('  Created materials and suppliers')
