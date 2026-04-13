# payment_processing_service
# 🏦 Async Payment Processing Service

Микросервис для асинхронной обработки платежей на FastAPI + RabbitMQ + PostgreSQL

## 📐 Архитектура

```
Client
  │
  ▼
[FastAPI API]
  │  POST /api/v1/payments
  │  ┌─────────────────────────────────────┐
  │  │  1. Создаём Payment (status=pending) │ ◄─ транзакция
  │  │  2. Создаём OutboxEvent             │
  │  └─────────────────────────────────────┘
  │
  ▼
[Outbox Publisher] (polling каждые 2 сек)
  │  SELECT unpublished events FOR UPDATE SKIP LOCKED
  │  PUBLISH → RabbitMQ exchange "payments"
  │  UPDATE outbox_events SET published=true
  │
  ▼
[RabbitMQ]  exchange: payments
            queue:    payments.new  (x-delivery-limit: 3)
            DLX:      payments.dlx
            DLQ:      payments.dlq
  │
  ▼
[Consumer]
  │  1. Получает сообщение
  │  2. Эмулирует шлюз (2-5 сек, 90% успех)
  │  3. Обновляет Payment.status в БД
  │  4. Отправляет webhook (3 попытки, экспоненц. задержка)
  └─► При ошибке → сообщение идёт в DLQ после 3 попыток
```

## 🚀 Быстрый старт

```bash
# Клонировать репозиторий
git clone https://github.com/poxiQ/payment_processing_service.git
cd payments-service

# Запустить все сервисы
make build & make up

# Создать и применить миграцию
make migrate-create & make migrate-up

# Запуск тестов
make build & make test
```

## 📡 API Примеры

### Создать платёж
```bash
curl -X POST http://localhost:8000/api/v1/payments \
  -H "Content-Type: application/json" \
  -H "X-API-Key: super-secret-api-key-change-in-prod" \
  -H "Idempotency-Key: unique-key-$(uuidgen)" \
  -d '{
    "amount": "1500.00",
    "currency": "RUB",
    "description": "Оплата заказа #12345",
    "metadata": {"order_id": "12345", "user_id": "42"},
    "webhook_url": "https://yourapp.com/webhooks/payment"
  }'
```

**Ответ 202 Accepted:**
```json
{
  "payment_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "created_at": "2024-01-15T10:30:00Z"
}
```

### Получить статус платежа
```bash
curl http://localhost:8000/api/v1/payments/550e8400-e29b-41d4-a716-446655440000 \
  -H "X-API-Key: super-secret-api-key-change-in-prod"
```

### Webhook payload (от сервиса → ваш URL)
```json
{
  "payment_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "succeeded",
  "processed_at": "2024-01-15T10:30:04Z",
  "amount": "1500.00",
  "currency": "RUB"
}
```

## 🔧 Переменные окружения

| Переменная      | Описание                    | По умолчанию                             |
|-----------------|-----------------------------|------------------------------------------|
| POSTGRES_PORT    | PostgreSQL port             | 5432    |
| POSTGRES_PASSWORD    | PostgreSQL user password    | change_me    |
| POSTGRES_USER    | PostgreSQL user             | postgres    |
| POSTGRES_DB    | PostgreSQL database name    | backend    |
| POSTGRES_HOST    | PostgreSQL host             | postgres    |
| POSTGRES_DATA_PATH    | PostgreSQL path/to/data     | /var/lib/postgresql/data   |
| POSTGRES_LOGS_PATH    | PostgreSQL path/to/logs     | /var/lib/postgresql/logs   |
| RABBITMQ_DEFAULT_USER    | RabbitMQ user               | rabbit_user               |
| RABBITMQ_DEFAULT_PASS    | RabbitMQ user password      | rabbit_secret              |
| RABBITMQ_DATA_PATH    | RabbitMQ path/to/data       | /var/lib/rabbitmq              |
| RABBITMQ_LOGS_PATH    | RabbitMQ path/to/logs       | /var/log/rabbitmq              |
| RABBITMQ_HOST    | RabbitMQ host               | localhost               |
| RABBITMQ_PORT    | RabbitMQ port               | 5672               |
| RABBITMQ_WEB_PORT    | RabbitMQ port web interface | 15672               |
| API_KEY         | Static key for API          | super-secret-api-key       |

## 📊 Мониторинг

- **RabbitMQ Management UI**: http://localhost:15672 (rabbit_user / rabbit_secret)
- **API Swagger**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
