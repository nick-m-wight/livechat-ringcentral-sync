# LiveChat-RingCentral Sync

A production-ready bidirectional synchronization system that integrates LiveChat and RingCentral platforms, enabling seamless communication tracking and agent presence management across both systems.

## 🎯 Overview

This application automatically synchronizes conversations and agent states between LiveChat (customer chat support) and RingCentral (business phone system), ensuring agents' availability is consistent across platforms and all customer interactions are properly tracked.

## ✨ Features

- **Bidirectional Webhook Processing** - Real-time event handling from both LiveChat and RingCentral
- **Agent State Synchronization** - Automatically updates agent presence across platforms
- **Conversation Tracking** - Maintains unified records of all customer interactions
- **Contact Matching** - Intelligent customer identification across platforms
- **Idempotency Guarantees** - Prevents duplicate webhook processing
- **Async Task Processing** - Background job handling with Celery
- **Comprehensive Logging** - Structured logging with operation audit trails
- **Error Handling** - Graceful failure management with retry mechanisms
- **Database Persistence** - PostgreSQL storage for all entities and events

## 🏗️ Architecture

```
┌─────────────┐         ┌──────────────┐
│  LiveChat   │◄────────┤   FastAPI    │
│   Webhooks  │         │  Application │
└─────────────┘         └──────┬───────┘
                               │
┌─────────────┐                │         ┌─────────────┐
│ RingCentral │◄───────────────┴────────►│    Redis    │
│  Webhooks   │                          │   (Cache)   │
└─────────────┘                          └─────────────┘
                                                │
                               ┌────────────────┴────────────┐
                               │                             │
                        ┌──────▼────────┐         ┌────────▼────────┐
                        │    Celery     │         │   PostgreSQL    │
                        │    Workers    │         │    Database     │
                        └───────────────┘         └─────────────────┘
```

## 📋 Prerequisites

- **Docker** & **Docker Compose** (recommended)
- **Python 3.11+** (for local development)
- **Poetry** (Python dependency management)
- **PostgreSQL 16+**
- **Redis 7+**
- **LiveChat API Credentials**
- **RingCentral API Credentials**

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/nick-m-wight/livechat-ringcentral-sync.git
cd livechat-ringcentral-sync
```

### 2. Configure Environment

```bash
cp .env.template .env
```

Edit `.env` and add your API credentials:

```env
# LiveChat API Configuration
LIVECHAT_CLIENT_ID=your_livechat_client_id
LIVECHAT_CLIENT_SECRET=your_livechat_client_secret
LIVECHAT_ACCESS_TOKEN=your_livechat_access_token
LIVECHAT_WEBHOOK_SECRET=your_livechat_webhook_secret

# RingCentral API Configuration
RINGCENTRAL_CLIENT_ID=your_ringcentral_client_id
RINGCENTRAL_CLIENT_SECRET=your_ringcentral_client_secret
RINGCENTRAL_JWT_TOKEN=your_ringcentral_jwt_token
RINGCENTRAL_WEBHOOK_SECRET=your_ringcentral_webhook_secret

# Application Configuration
WEBHOOK_BASE_URL=https://your-domain.com
```

### 3. Start the Application

**Using Docker (Recommended):**

```bash
# Build and start all services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f app
```

**Local Development:**

```bash
# Install dependencies
poetry install

# Run database migrations
poetry run alembic upgrade head

# Start the application
poetry run uvicorn app.main:app --reload

# In separate terminals, start workers:
poetry run celery -A app.core.celery_app worker --loglevel=info
poetry run celery -A app.core.celery_app beat --loglevel=info
```

### 4. Initialize Database

```bash
# Run migrations
docker-compose exec app alembic upgrade head

# Seed test data (optional)
docker-compose exec app python scripts/seed_data.py
```

### 5. Verify Installation

```bash
# Check health endpoint
curl http://localhost:8000/health

# Response should be:
# {"status": "healthy", "database": "connected"}
```

## 🔧 Configuration

### Agent Mappings

Create agent mappings to link LiveChat agents with RingCentral extensions:

```sql
INSERT INTO agents (livechat_agent_id, ringcentral_extension_id, email, name)
VALUES ('lc_agent_123', '101', 'agent@company.com', 'John Smith');
```

Or use the seed script:

```bash
docker-compose exec app python scripts/seed_data.py
```

### Webhook Setup

**LiveChat Webhooks:**

1. Go to LiveChat Developer Console
2. Create webhook subscriptions:
   - `incoming_chat` → `https://your-domain.com/webhooks/livechat/incoming_chat`
   - `chat_deactivated` → `https://your-domain.com/webhooks/livechat/chat_deactivated`
3. Set webhook secret in `.env`

**RingCentral Webhooks:**

1. Go to RingCentral Developer Console
2. Create webhook subscription:
   - Event: `/restapi/v1.0/account/~/extension/~/telephony/sessions`
   - URL: `https://your-domain.com/webhooks/ringcentral/telephony-session`
3. Set webhook secret in `.env`

## 📡 API Endpoints

### Health Check

```bash
GET /health
```

Returns application health status and database connectivity.

### Webhooks

```bash
POST /webhooks/livechat/incoming_chat
POST /webhooks/livechat/chat_deactivated
POST /webhooks/ringcentral/telephony-session
POST /webhooks/ringcentral/call-log
```

## 🧪 Testing

### Run Test Suite

```bash
# Using Docker
docker-compose exec app pytest tests/ -v

# Local
poetry run pytest tests/ -v
```

### Manual Webhook Testing

```bash
# Test all webhooks
docker-compose exec app python scripts/test_webhooks.py --platform all --event all

# Test specific platform
docker-compose exec app python scripts/test_webhooks.py --platform livechat --event chat_started
docker-compose exec app python scripts/test_webhooks.py --platform ringcentral --event call_started
```

### Test with curl

```bash
# LiveChat webhook
curl -X POST http://localhost:8000/webhooks/livechat/incoming_chat \
  -H "Content-Type: application/json" \
  -d '{
    "webhook_id": "test_001",
    "action": "incoming_chat",
    "payload": {
      "chat": {
        "id": "chat_123",
        "users": [
          {"id": "agent_1", "type": "agent", "email": "agent@example.com"}
        ]
      }
    }
  }'

# RingCentral webhook
curl -X POST http://localhost:8000/webhooks/ringcentral/telephony-session \
  -H "Content-Type: application/json" \
  -d '{
    "uuid": "test_001",
    "event": "/restapi/v1.0/account/~/extension/101/telephony/sessions",
    "body": {
      "sessionId": "session_123",
      "parties": [
        {"extensionId": "101", "status": {"code": "Answered"}}
      ]
    }
  }'
```

## 📁 Project Structure

```
livechat-ringcentral-sync/
├── app/
│   ├── api/                    # FastAPI routes
│   │   ├── health.py          # Health check endpoint
│   │   └── webhooks/          # Webhook endpoints
│   ├── core/                   # Business logic
│   │   ├── agent_state.py     # Agent state management
│   │   ├── contact_matching.py
│   │   ├── conversation_sync.py
│   │   ├── idempotency.py     # Webhook deduplication
│   │   ├── tasks.py           # Celery background tasks
│   │   └── celery_app.py      # Celery configuration
│   ├── db/                     # Database layer
│   │   ├── models.py          # SQLAlchemy models
│   │   └── session.py         # Database session
│   ├── integrations/           # External API clients
│   │   ├── livechat/          # LiveChat API client
│   │   └── ringcentral/       # RingCentral API client
│   ├── middleware/             # FastAPI middleware
│   ├── schemas/                # Pydantic models
│   ├── utils/                  # Utilities
│   ├── config.py              # Application configuration
│   └── main.py                # Application entry point
├── alembic/                    # Database migrations
├── docker/                     # Docker configuration
├── scripts/                    # Utility scripts
│   ├── seed_data.py           # Database seeding
│   └── test_webhooks.py       # Webhook testing
├── tests/                      # Test suite
├── docker-compose.yml
├── pyproject.toml             # Poetry dependencies
└── README.md
```

## 🗄️ Database Schema

- **agents** - Agent mappings between platforms
- **customers** - Customer contact information
- **conversations** - Chat and call sessions
- **messages** - Message history
- **call_records** - Call metadata
- **agent_states** - Agent availability tracking
- **sync_logs** - Operation audit trail
- **webhook_events** - Webhook idempotency tracking

## 🔄 Background Tasks

Celery tasks handle async processing:

- `process_livechat_chat_started` - New chat initiated
- `process_livechat_chat_ended` - Chat completed
- `process_ringcentral_call_started` - Call connected
- `process_ringcentral_call_ended` - Call terminated

## 🛠️ Development

### Code Formatting

```bash
# Format code
poetry run black app/ tests/

# Lint
poetry run ruff check app/ tests/

# Type checking
poetry run mypy app/
```

### Database Migrations

```bash
# Create new migration
docker-compose exec app alembic revision --autogenerate -m "Description"

# Apply migrations
docker-compose exec app alembic upgrade head

# Rollback
docker-compose exec app alembic downgrade -1
```

### Monitoring

```bash
# View application logs
docker-compose logs -f app

# View Celery worker logs
docker-compose logs -f celery_worker

# Check task queue
docker-compose exec redis redis-cli
> LLEN celery

# View database
docker-compose exec postgres psql -U livechat_user -d livechat_sync
```

## 🐛 Troubleshooting

### Common Issues

**Service won't start:**
```bash
docker-compose down -v
docker-compose up -d --build
```

**Database connection errors:**
- Check PostgreSQL is running: `docker-compose ps postgres`
- Verify DATABASE_URL in `.env`
- Check logs: `docker-compose logs postgres`

**Celery tasks not processing:**
- Check Redis is running: `docker-compose ps redis`
- Verify Celery worker: `docker-compose logs celery_worker`
- Ensure CELERY_BROKER_URL is correct in `.env`

**Webhook 401 errors:**
- Verify API credentials in `.env`
- Check token expiration
- Confirm webhook secrets match

## 📊 Performance

- **Webhook Response Time**: < 200ms
- **Task Processing**: Async, non-blocking
- **Database**: Connection pooling enabled
- **Caching**: Redis-backed for frequently accessed data

## 🔒 Security

- Webhook signature verification
- API credential encryption recommended
- CORS configuration for production
- SQL injection prevention via SQLAlchemy ORM
- Input validation with Pydantic

## 📝 License

MIT License - see LICENSE file for details

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📞 Support

For issues or questions:
- GitHub Issues: https://github.com/nick-m-wight/livechat-ringcentral-sync/issues
- Email: support@example.com

## 🙏 Acknowledgments

Built with:
- [FastAPI](https://fastapi.tiangolo.com/)
- [Celery](https://docs.celeryq.dev/)
- [SQLAlchemy](https://www.sqlalchemy.org/)
- [Pydantic](https://docs.pydantic.dev/)

---

**Made with ❤️ for seamless customer communication**
