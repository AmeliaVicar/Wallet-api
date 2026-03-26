# Wallet API

Асинхронный REST API для работы с кошельками пользователей на FastAPI и PostgreSQL.

## Стек

- Python 3.11+
- FastAPI
- SQLAlchemy 2.x Async
- PostgreSQL
- Alembic
- pytest
- Docker / Docker Compose

## Возможности

- `GET /api/v1/wallets/{wallet_uuid}`: получить текущий баланс кошелька
- `POST /api/v1/wallets/{wallet_uuid}/operation`: выполнить `DEPOSIT` или `WITHDRAW`
- транзакционная обработка изменения баланса
- защита от race condition через `SELECT ... FOR UPDATE`
- миграции Alembic
- интеграционные и конкурентные тесты

## Структура проекта

```text
app/
  api/
  core/
  db/
  repositories/
  schemas/
  services/
alembic/
tests/
docker/
```

## Переменные окружения

Скопируйте `.env.example` в `.env` и при необходимости измените значения:

- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_HOST`
- `POSTGRES_PORT`
- `DATABASE_URL`
- `TEST_DATABASE_URL`

## Запуск через Docker Compose

```bash
docker-compose up --build
```

После старта:

- API: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`

Миграции применяются автоматически при старте контейнера приложения.

## Локальный запуск без Docker

1. Установить зависимости:

```bash
pip install -e .[dev]
```

2. Поднять PostgreSQL и настроить `.env`

3. Применить миграции:

```bash
alembic upgrade head
```

4. Запустить приложение:

```bash
uvicorn app.main:app --reload
```

## Запуск тестов

Тесты используют PostgreSQL. Укажите отдельную БД в `TEST_DATABASE_URL`.

```bash
pytest
```

Если тестовая PostgreSQL недоступна, `pytest` теперь падает с ошибкой, а не маскирует проблему через `skip`.

## Запуск тестов через Docker

Для контейнерного запуска тестов добавлены отдельные файлы `Dockerfile.test` и `docker-compose.test.yml`.

```bash
docker compose -f docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from test test
```

Что делает эта команда:

- поднимает отдельный контейнер `test-db` с PostgreSQL для тестов;
- собирает отдельный test-образ с dev-зависимостями;
- запускает `pytest -q` внутри контейнера `test`;
- возвращает код завершения именно от тестов.

После завершения можно убрать контейнеры и сеть так:

```bash
docker compose -f docker-compose.test.yml down -v
```

## API примеры

### Получение баланса

```bash
curl http://localhost:8000/api/v1/wallets/4fcb5f4b-0d5b-4f66-8a76-1b7d3669f2d1
```

Пример ответа:

```json
{
  "wallet_id": "4fcb5f4b-0d5b-4f66-8a76-1b7d3669f2d1",
  "balance": 1000
}
```

### Пополнение

```bash
curl -X POST http://localhost:8000/api/v1/wallets/4fcb5f4b-0d5b-4f66-8a76-1b7d3669f2d1/operation \
  -H "Content-Type: application/json" \
  -d '{"operation_type":"DEPOSIT","amount":500}'
```

### Списание

```bash
curl -X POST http://localhost:8000/api/v1/wallets/4fcb5f4b-0d5b-4f66-8a76-1b7d3669f2d1/operation \
  -H "Content-Type: application/json" \
  -d '{"operation_type":"WITHDRAW","amount":300}'
```

## Ключевые решения

- Сумма хранится как `integer` в минимальных неделимых единицах.
- Кошелек должен существовать в БД до вызова API.
- Баланс не может стать отрицательным.
- Для конкурентной безопасности используется транзакция и блокировка строки `SELECT ... FOR UPDATE`.
- На уровне БД добавлен `CHECK (balance >= 0)`.

## Ограничения и допущения

- Создание кошелька не входит в публичный API.
- Валютная модель не вводится.
- История операций не сохраняется отдельной сущностью.

 -u origin main

