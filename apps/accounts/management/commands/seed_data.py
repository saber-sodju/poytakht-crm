"""
Management command: python manage.py seed_data
Creates demo data for all roles and modules.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal
import random


class Command(BaseCommand):
    help = 'Seed demo data for CRM'

    def handle(self, *args, **kwargs):
        self.stdout.write('Creating seed data...')

        self._create_users()
        self._create_complex()
        self._create_clients()
        self._create_leads()
        self._create_sales()
        self._create_expenses()
        self._create_workers()
        self._create_materials()

        self.stdout.write(self.style.SUCCESS('[OK] Testovye dannye sozdany!'))
        self.stdout.write('')
        self.stdout.write('Loginy dlya vkhoda:')
        self.stdout.write('  director     / demo123456  - Direktor')
        self.stdout.write('  admin_crm    / demo123456  - Administrator')
        self.stdout.write('  manager1     / demo123456  - Menedzher')
        self.stdout.write('  accountant1  / demo123456  - Bukhgalter')

    def _create_users(self):
        from apps.accounts.models import CustomUser
        users_data = [
            {'username': 'director', 'first_name': 'Фируз', 'last_name': 'Рахимов', 'role': 'director', 'phone': '+992900000001'},
            {'username': 'admin_crm', 'first_name': 'Шамс', 'last_name': 'Назаров', 'role': 'admin', 'phone': '+992900000002'},
            {'username': 'manager1', 'first_name': 'Нилуфар', 'last_name': 'Алиева', 'role': 'manager', 'phone': '+992900000003'},
            {'username': 'accountant1', 'first_name': 'Зафар', 'last_name': 'Холов', 'role': 'accountant', 'phone': '+992900000004'},
        ]
        for data in users_data:
            if not CustomUser.objects.filter(username=data['username']).exists():
                user = CustomUser.objects.create_user(
                    username=data['username'],
                    password='demo123456',
                    first_name=data['first_name'],
                    last_name=data['last_name'],
                    role=data['role'],
                    phone=data['phone'],
                    email=f"{data['username']}@poytakht.tj",
                )
                self.stdout.write(f'  User created: {user.username}')

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
        statuses = ['free'] * 6 + ['booked'] + ['sold'] * 4

        for bdata in blocks_data:
            block = Block.objects.create(
                complex=cx,
                name=bdata['name'],
                budget_planned=bdata['budget'],
            )
            # Create stages
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

        self.stdout.write(f'  Complex created: {cx.name}')

    def _create_clients(self):
        from apps.clients.models import Client
        from apps.accounts.models import CustomUser

        if Client.objects.exists():
            return

        manager = CustomUser.objects.filter(role='manager').first()
        clients_data = [
            ('Акрамов Бахром Саидович', '+992901234567', 'АА', '1234567'),
            ('Холматова Мадина Рустамовна', '+992902345678', 'АБ', '2345678'),
            ('Назаров Темур Алишерович', '+992903456789', 'АВ', '3456789'),
            ('Рашидова Зарина Фаридовна', '+992904567890', 'АГ', '4567890'),
            ('Юсупов Санжар Хасанович', '+992905678901', 'АД', '5678901'),
            ('Мирзоева Лола Бахтиёровна', '+992906789012', 'АЕ', '6789012'),
            ('Каримов Шухрат Бекович', '+992907890123', 'АЖ', '7890123'),
            ('Тошматова Дилноза Улмасовна', '+992908901234', 'АЗ', '8901234'),
        ]
        clients = []
        for full_name, phone, pser, pnum in clients_data:
            c = Client.objects.create(
                full_name=full_name, phone=phone,
                passport_series=pser, passport_number=pnum,
                added_by=manager,
            )
            clients.append(c)
        self.stdout.write(f'  Created {len(clients)} clients')

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
        ]
        for name, phone, status, interest, budget, source in leads_data:
            Lead.objects.create(
                name=name, phone=phone, status=status,
                interested_in=interest, budget=budget, source=source,
                assigned_to=manager,
                next_contact_date=today + timedelta(days=random.randint(1, 7)) if status in ['callback', 'negotiation'] else None,
            )
        self.stdout.write('  Created 5 leads')

    def _create_sales(self):
        from apps.complex.models import Apartment
        from apps.clients.models import Client
        from apps.sales.models import Sale, Booking
        from apps.payments.models import Payment, PaymentSchedule
        from apps.accounts.models import CustomUser

        if Sale.objects.exists():
            return

        manager = CustomUser.objects.filter(role='manager').first()
        accountant = CustomUser.objects.filter(role='accountant').first()
        clients = list(Client.objects.all())
        today = date.today()

        sold_apts = list(Apartment.objects.filter(status='sold')[:4])
        booked_apts = list(Apartment.objects.filter(status='booked')[:1])

        # Bookings
        for i, apt in enumerate(booked_apts):
            if i < len(clients):
                Booking.objects.create(
                    apartment=apt, client=clients[i],
                    end_date=today + timedelta(days=7),
                    deposit=Decimal('1000'),
                    created_by=manager,
                )

        # Sales
        payment_types = ['installment', 'full', 'installment', 'mortgage']
        for i, apt in enumerate(sold_apts):
            client = clients[i + 1] if i + 1 < len(clients) else clients[0]
            ptype = payment_types[i % len(payment_types)]
            sale = Sale.objects.create(
                apartment=apt, client=client,
                total_price=apt.total_price,
                payment_type=ptype,
                contract_number=f'ДКП-2024-{1000 + i}',
                contract_date=today - timedelta(days=random.randint(30, 180)),
                sale_date=today - timedelta(days=random.randint(30, 180)),
                created_by=manager,
            )

            # Add payments
            if ptype == 'full':
                Payment.objects.create(
                    sale=sale, amount=apt.total_price,
                    payment_date=sale.sale_date, added_by=accountant,
                )
            elif ptype == 'installment':
                # First payment 30%, rest as schedule
                first_pay = apt.total_price * Decimal('0.3')
                Payment.objects.create(
                    sale=sale, amount=first_pay,
                    payment_date=sale.sale_date, added_by=accountant,
                )
                months = 12
                monthly = (apt.total_price - first_pay) / months
                for m in range(1, months + 1):
                    due = today + timedelta(days=m * 30)
                    PaymentSchedule.objects.create(
                        sale=sale, due_date=due, amount=monthly.quantize(Decimal('0.01')),
                    )
            elif ptype == 'mortgage':
                first_pay = apt.total_price * Decimal('0.2')
                Payment.objects.create(
                    sale=sale, amount=first_pay,
                    payment_date=sale.sale_date, added_by=accountant,
                )

            sale.update_paid_amount()

        self.stdout.write(f'  Created {len(sold_apts)} sales')

    def _create_expenses(self):
        from apps.expenses.models import Expense
        from apps.complex.models import Block, Complex
        from apps.accounts.models import CustomUser

        if Expense.objects.exists():
            return

        accountant = CustomUser.objects.filter(role='accountant').first()
        blocks = list(Block.objects.all())
        cx = Complex.objects.first()
        today = date.today()

        expenses_data = [
            ('materials', 45000, 'Кирпич и цемент для кладки'),
            ('salary', 28000, 'Зарплата рабочих за ноябрь'),
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
                description=desc, added_by=accountant,
            )
        self.stdout.write('  Created 8 expenses')

    def _create_workers(self):
        from apps.workers.models import Position, Team, Worker, Attendance, SalaryPayment
        from apps.complex.models import Complex
        from apps.accounts.models import CustomUser

        if Worker.objects.exists():
            return

        cx = Complex.objects.first()
        admin = CustomUser.objects.filter(role='admin').first() or CustomUser.objects.first()
        today = date.today()

        # Positions
        positions_data = ['Прораб', 'Каменщик', 'Бетонщик', 'Сварщик',
                          'Электрик', 'Плиточник', 'Разнорабочий']
        positions = {p: Position.objects.get_or_create(name=p)[0] for p in positions_data}

        # Teams
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

        # Attendance for last 7 days
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

    def _create_materials(self):
        from apps.materials.models import Supplier, Material, MaterialMovement
        from apps.complex.models import Block
        from apps.accounts.models import CustomUser

        if Material.objects.exists():
            return

        admin = CustomUser.objects.filter(role='admin').first() or CustomUser.objects.first()
        block = Block.objects.first()
        today = date.today()

        # Suppliers
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
            # Add incoming movement
            mv = MaterialMovement(
                material=m, direction='in',
                quantity=Decimal(str(qty)),
                price_per_unit=Decimal(str(price)),
                supplier=supplier, block=block,
                date=today - timedelta(days=random.randint(5, 30)),
                note='Начальный остаток', added_by=admin,
            )
            mv.save()

        # Some outgoing movements
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
