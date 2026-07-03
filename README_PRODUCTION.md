# Poytakht CRM — Production Guide

Руководство по развёртыванию и обслуживанию системы в production.

---

## 1. Переменные окружения

Обязательные (без них сервер не запустится или будет уязвим):

| Переменная | Пример | Описание |
|---|---|---|
| `SECRET_KEY` | `xk3$...50 случайных символов` | **Обязательно.** Генерация: `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` |
| `DEBUG` | `False` | **Никогда** не ставьте `True` в production |
| `DATABASE_URL` | `postgresql://user:pass@host:5432/db` | Railway ставит автоматически |
| `ALLOWED_HOSTS` | `crm.example.com` | Домены через запятую |
| `CSRF_TRUSTED_ORIGINS` | `https://crm.example.com` | Origins через запятую (с `https://`) |

Первый директор (создаётся автоматически при старте, если директоров нет):

| Переменная | Описание |
|---|---|
| `INITIAL_DIRECTOR_USERNAME` | Логин первого директора |
| `INITIAL_DIRECTOR_PASSWORD` | Пароль (мин. 8 символов, проверяется валидаторами Django) |
| `INITIAL_DIRECTOR_NAME` | Опционально: «Имя Фамилия» |

Опциональные:

| Переменная | По умолчанию | Описание |
|---|---|---|
| `RUN_SEED_DATA` | `0` | `1` = создать demo-данные. **Только dev/staging!** |
| `LARGE_EXPENSE_THRESHOLD` | `5000` | Расход от этой суммы ($) уведомляет директоров |
| `WEB_CONCURRENCY` | `2` | Число воркеров Gunicorn |

---

## 2. Деплой на Railway

1. Подключите GitHub-репозиторий к Railway.
2. Добавьте PostgreSQL plugin — `DATABASE_URL` появится автоматически.
3. В Variables задайте: `SECRET_KEY`, `DEBUG=False`, `INITIAL_DIRECTOR_USERNAME`, `INITIAL_DIRECTOR_PASSWORD`.
4. Деплой запускает `start.sh`: collectstatic → migrate → create_initial_director → gunicorn.

**Важно:** `SECURE_SSL_REDIRECT` в Django не включён намеренно — Railway сам
редиректит HTTP→HTTPS на балансировщике. Включение в Django создаёт петлю редиректов.

---

## 3. Backup PostgreSQL

### Ручной бэкап (Railway)

```bash
# Установите Railway CLI и залогиньтесь
railway login
railway link   # выберите проект

# Дамп всей базы
railway run pg_dump '$DATABASE_URL' --format=custom --file=backup_$(date +%Y%m%d).dump
```

Или напрямую, взяв `DATABASE_URL` из Railway Variables:

```bash
pg_dump "postgresql://user:pass@host:port/dbname" \
  --format=custom \
  --file=poytakht_backup_$(date +%Y%m%d_%H%M).dump
```

### Восстановление

```bash
pg_restore --clean --no-owner --no-privileges \
  --dbname="postgresql://user:pass@host:port/dbname" \
  poytakht_backup_20260101_1200.dump
```

### Автоматический бэкап (рекомендуется)

Вариант А — Railway сам делает снапшоты Postgres (проверьте тариф).

Вариант Б — cron на любом сервере / GitHub Actions по расписанию:

```yaml
# .github/workflows/backup.yml
name: DB Backup
on:
  schedule:
    - cron: '0 2 * * *'   # каждый день в 02:00 UTC
jobs:
  backup:
    runs-on: ubuntu-latest
    steps:
      - run: |
          pg_dump "${{ secrets.DATABASE_URL }}" --format=custom --file=backup.dump
      - uses: actions/upload-artifact@v4
        with:
          name: db-backup-${{ github.run_id }}
          path: backup.dump
          retention-days: 30
```

**Правило 3-2-1:** 3 копии, 2 разных носителя, 1 вне площадки.

---

## 4. Медиа-файлы (квитанции, фото)

Файлы в `/media/` раздаются через Django с проверкой прав:
- Сотрудники видят все файлы.
- Клиенты — только квитанции своих платежей.

⚠️ На Railway файловая система **эфемерная** — загруженные файлы пропадают
при редеплое. Для реального production подключите S3-совместимое хранилище
(django-storages + AWS S3 / Cloudflare R2 / Backblaze B2).

---

## 5. Безопасность — чеклист перед запуском

- [ ] `DEBUG=False`
- [ ] `SECRET_KEY` — уникальный, 50+ символов, не из репозитория
- [ ] `.env` не закоммичен (проверьте `.gitignore`)
- [ ] Пароль директора сменён с демо на реальный
- [ ] `RUN_SEED_DATA` не установлен (или `0`)
- [ ] HTTPS работает (Railway даёт из коробки)
- [ ] Бэкап настроен и восстановление проверено
- [ ] `python manage.py check --deploy` — без критических предупреждений

---

## 6. Обслуживание

```bash
# Проверка настроек безопасности
python manage.py check --deploy

# Тесты (42 шт.)
python manage.py test tests

# Создание нового пользователя — только через UI директором
# (Сотрудники → Новый пользователь)
```

## 7. Роли и доступ

| Роль | Доступ |
|---|---|
| Директор | Всё |
| Гл. администратор | Всё кроме управления пользователями |
| Менеджер | Квартиры, клиенты, продажи, брони, платежи (без расходов/прибыли/отчётов) |
| Бухгалтер | Платежи, расходы, отчёты, зарплаты |
| Прораб | Рабочие, посещаемость, материалы |
| Складовщик | Материалы, поставщики, движение |
| Клиент | Только свой кабинет: квартира, платежи, долг |
