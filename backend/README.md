# GhostCart Backend

FastAPI backend implementing AP2 Protocol with AWS Bedrock Agent Strands orchestration.

## Architecture Overview

The backend is organized into layers following clean architecture principles:

```
backend/src/
├── agents/          # AI agent orchestration (Strands SDK)
├── api/             # REST API endpoints
├── services/        # Business logic layer
├── db/              # Database models and ORM
├── models/          # Pydantic models for validation
└── mocks/           # Mock external services
```

## Agent Architecture

### Multi-Agent System (AWS Strands SDK)

The system uses a **Supervisor-Specialist** pattern with four agents:

#### 1. Supervisor Agent (`supervisor_strands.py`)
- **Role**: Entry point for all user interactions
- **Responsibility**: Intelligent routing using LLM reasoning
- **Pattern**: Uses specialist agents as `@tool`-decorated functions
- **Routing Logic**:
  - Immediate purchases → HP Shopping Agent
  - Conditional/future purchases → HNP Delegate Agent
  - Ambiguous requests → Asks clarifying questions

#### 2. HP Shopping Agent (`hp_shopping_strands.py`)
- **Role**: Handles human-present immediate purchases
- **Tools**:
  - `search_products()` - Search product catalog
  - `create_shopping_cart()` - Create Cart Mandate
  - `request_user_cart_signature()` - Trigger signature modal
  - `get_signed_cart_mandate()` - Retrieve signed mandate
  - `invoke_payment_processing()` - Call Payment Agent

#### 3. HNP Delegate Agent (`hnp_delegate_strands.py`)
- **Role**: Handles human-not-present autonomous monitoring
- **Tools**:
  - `extract_monitoring_constraints()` - Parse price/delivery limits
  - `search_products()` - Find matching products
  - `create_hnp_intent()` - Create Intent Mandate
  - `request_user_intent_signature()` - Trigger signature modal
  - `get_signed_intent_mandate()` - Retrieve signed mandate
  - `activate_monitoring_job()` - Start background monitoring

#### 4. Payment Agent (`payment_agent/agent.py`)
- **Role**: Domain-independent payment processing
- **Tools** (Sequential Execution):
  - `validate_hp_chain()` / `validate_hnp_chain()` - Validate mandate chain
  - `retrieve_payment_credentials()` - Get tokenized payment methods
  - `process_payment_authorization()` - Process payment
- **Key Feature**: Zero knowledge of products/merchants (AP2 compliant)

## API Endpoints

### Chat & Streaming
- `POST /api/chat/stream` - SSE streaming chat endpoint
  - Accepts user messages
  - Streams agent responses in real-time
  - Returns mandate IDs and transaction results

### Products
- `GET /api/products/search` - Search product catalog
  - Query params: `q` (search term), `max_price` (optional)
  - Returns: Product list with images, prices, delivery

### Mandates
- `POST /api/mandates/sign` - Sign a mandate
  - Body: `{ "mandate_id": "...", "user_id": "..." }`
  - Adds HMAC-SHA256 signature
  - Returns: Updated mandate with signature

- `GET /api/mandates/{mandate_id}` - Get mandate details
  - Returns: Complete mandate JSON with signature status

### Payments
- `GET /api/payment-methods` - Get tokenized payment methods
  - Query params: `user_id`
  - Returns: List of tokenized credentials (tok_*)

### Transactions
- `GET /api/transactions` - List user transactions
  - Query params: `user_id`
  - Returns: Transaction history with mandate chain links

- `GET /api/transactions/{transaction_id}` - Get transaction details
  - Returns: Complete transaction with authorization/decline info

### Monitoring
- `GET /api/monitoring/status` - Get active monitoring jobs
  - Query params: `user_id`
  - Returns: Active jobs with last check time, status

- `POST /api/monitoring/cancel` - Cancel monitoring job
  - Body: `{ "job_id": "..." }`
  - Stops background monitoring

### Health
- `GET /api/health` - Health check endpoint
  - Returns: Server status, version, environment info

## Services Layer

### Bedrock Service (`bedrock_service.py`)
- Manages AWS Bedrock client
- Invokes Claude Sonnet 4 model
- Supports streaming and non-streaming responses
- Handles retries and error handling

### Mandate Service (`mandate_service.py`)
- Creates Intent, Cart, and Payment mandates
- Validates mandate structures against AP2 schema
- Stores mandates in database
- Links mandates in chain (Intent → Cart → Payment)

### Signature Service (`signature_service.py`)
- Generates HMAC-SHA256 signatures (demo)
- Validates signatures
- Stores signature metadata (timestamp, algorithm, signer)
- Production would use ECDSA with hardware-backed keys

### Monitoring Service (`monitoring_service.py`)
- Creates monitoring jobs in database
- Registers jobs with APScheduler
- Executes periodic checks (every 5 minutes)
- Triggers autonomous purchases when conditions met
- Handles job expiration (7 days)

### Transaction Service (`transaction_service.py`)
- Creates transaction records
- Links transactions to mandate chain
- Stores authorization codes or decline reasons
- Provides transaction history

### Session Service (`session_service.py`)
- Manages user sessions
- Stores conversation context
- Tracks current flow type (HP/HNP)
- Enables conversation continuity

### SSE Service (`sse_service.py`)
- Manages Server-Sent Events connections
- Emits real-time updates to frontend
- Event types:
  - `agent_message` - Agent responses
  - `product_results` - Search results
  - `cart_created` - Cart mandate created
  - `signature_requested` - Signature modal trigger
  - `monitoring_activated` - Monitoring started
  - `monitoring_check_complete` - Check result
  - `autonomous_purchase_complete` - HNP purchase done

### Scheduler (`scheduler.py`)
- Wraps APScheduler
- Manages background monitoring jobs
- Survives server restarts (jobs persisted in DB)
- Handles job cleanup on expiration

## Database Models

### Mandates Table
```python
class MandateModel:
    id: str  # mandate_id (intent_*, cart_*, payment_*)
    mandate_type: str  # intent, cart, payment
    user_id: str
    transaction_id: str (nullable)
    mandate_data: JSON  # Complete AP2 mandate structure
    signer_identity: str  # user_* or ap2_agent_*
    signature: JSON  # { signature, timestamp, algorithm }
    validation_status: str  # valid, invalid, unsigned
    created_at: datetime
    updated_at: datetime
```

### Monitoring Jobs Table
```python
class MonitoringJobModel:
    job_id: str  # APScheduler job ID
    intent_mandate_id: str  # FK to mandates
    user_id: str
    product_query: str
    constraints: JSON  # { max_price_cents, max_delivery_days }
    schedule_interval_minutes: int
    active: bool
    last_check_at: datetime (nullable)
    created_at: datetime
    expires_at: datetime
```

### Transactions Table
```python
class TransactionModel:
    transaction_id: str
    intent_mandate_id: str (nullable, HNP only)
    cart_mandate_id: str
    payment_mandate_id: str
    user_id: str
    status: str  # authorized, declined, expired, failed
    authorization_code: str (nullable)
    decline_reason: str (nullable)
    amount_cents: int
    currency: str
    created_at: datetime
```

### Sessions Table
```python
class SessionModel:
    session_id: str
    user_id: str
    current_flow_type: str  # hp, hnp, none
    context_data: JSON
    last_activity_at: datetime
    created_at: datetime
```

## Mock Services

### Credentials Provider (`mocks/credentials_provider.py`)
- Returns 2-3 tokenized payment methods per user
- Format: `tok_visa_1234`, `tok_mastercard_5678`
- Never returns raw PCI data (AP2 role separation)

### Payment Processor (`mocks/payment_processor.py`)
- Simulates payment authorization
- ~90% approval rate
- Returns authorization codes on success
- Returns specific decline reasons on failure:
  - Insufficient funds
  - Card expired
  - Transaction declined by issuer
  - Fraud suspected (high value transactions)

### Merchant API (`mocks/merchant_api.py`)
- Product catalog with ~15 items
- Categories: Electronics, Kitchen, Fashion, Home
- Includes products from demo scenarios:
  - Coffee makers around $70
  - AirPods around $250
- Mix of in-stock and out-of-stock items
- Price range: $30 - $700

## Configuration

### Environment Variables
```bash
# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret

# Bedrock Model
AWS_BEDROCK_MODEL_ID=global.anthropic.claude-sonnet-4-5-20250929-v1:0

# Secrets (Demo - change for production)
USER_SIGNATURE_SECRET=demo_user_secret_key_change_in_production
AGENT_SIGNATURE_SECRET=demo_agent_secret_key_change_in_production
PAYMENT_AGENT_SECRET=demo_payment_secret_key_change_in_production

# Application
DEMO_MODE=true
LOG_LEVEL=INFO
```

### Database
- SQLite with WAL mode enabled
- File: `ghostcart.db` (created automatically)
- Async operations via aiosqlite
- Migrations handled by SQLAlchemy

## Running Locally

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Initialize Database
```bash
python -c "from src.db.init_db import initialize_database; initialize_database()"
```

### Run Development Server
```bash
python -m uvicorn src.main:app --reload --port 8000
```

### Run Tests
```bash
pytest tests/ -v
pytest tests/unit/ -v  # Unit tests only
pytest tests/integration/ -v  # Integration tests only
```

### Code Quality
```bash
black src/  # Format code
mypy src/  # Type checking
ruff src/  # Linting
```

## AP2 Protocol Compliance

### Human-Present Flow
1. Intent Mandate created (context only, unsigned)
2. Cart Mandate created with user signature (authorization)
3. Payment Mandate created referencing Cart
4. Transaction created with result

### Human-Not-Present Flow
1. Intent Mandate created with user signature (pre-authorization)
2. Background monitoring activated
3. When conditions met:
   - Cart Mandate created with agent signature
   - Cart references Intent ID
   - Payment Mandate created with HNP flag
   - Transaction created with result

### Validation Rules
- HP: Cart must have user signature
- HNP: Intent must have user signature, Cart must reference Intent
- All mandates validated before payment processing
- Constraints checked: Cart must not exceed Intent limits
- Expiration checked: Intent must not be expired

## Error Handling

### AP2 Error Codes
- `ap2:mandate:chain_invalid` - Mandate chain validation failed
- `ap2:mandate:signature_invalid` - Signature verification failed
- `ap2:mandate:expired` - Mandate past expiration time
- `ap2:mandate:constraints_violated` - Cart exceeds Intent limits
- `ap2:credentials:unavailable` - Payment credentials not accessible
- `ap2:payment:declined` - Payment processor declined transaction

### Error Response Format
```json
{
  "error_code": "ap2:mandate:signature_invalid",
  "message": "Signature verification failed",
  "details": {
    "mandate_id": "cart_hp_abc123",
    "reason": "Invalid HMAC signature"
  }
}
```

## Performance Considerations

- Async/await throughout for non-blocking I/O
- SQLite with WAL mode for concurrent reads
- Connection pooling for database
- SSE for efficient real-time updates (vs polling)
- APScheduler for efficient background jobs
- Bedrock streaming for faster perceived response time

## Security Notes

**This is a demo implementation. For production:**

1. Replace HMAC-SHA256 with ECDSA signatures
2. Use hardware-backed key storage (HSM, AWS KMS)
3. Implement proper user authentication (OAuth2, JWT)
4. Add rate limiting and DDoS protection
5. Use HTTPS only (no HTTP)
6. Implement CORS properly (not allow all origins)
7. Add input validation and sanitization
8. Use secrets manager (AWS Secrets Manager)
9. Implement audit logging
10. Add monitoring and alerting

## Troubleshooting

### AWS Bedrock Access Denied
- Verify AWS credentials are configured
- Check IAM permissions for Bedrock
- Verify model access in Bedrock console
- Check region supports Claude Sonnet 4

### Database Locked Errors
- Enable WAL mode: `python backend/enable_wal_mode.py`
- Check for long-running transactions
- Verify no other processes accessing DB

### Monitoring Jobs Not Running
- Check APScheduler logs
- Verify jobs in database: `SELECT * FROM monitoring_jobs WHERE active=1`
- Check scheduler is started: Look for "APScheduler started" in logs
- Verify job expiration hasn't passed

### SSE Connection Issues
- Check CORS configuration
- Verify frontend is connecting to correct URL
- Check for proxy/firewall blocking SSE
- Look for "SSE connection established" in browser console

## Additional Resources

- [ARCHITECTURE.md](../ARCHITECTURE.md) - Full system architecture
- [AP2 Specification](https://ap2-protocol.org/specification/)
- [AWS Strands SDK](https://github.com/strands-agents/sdk-python)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

---

For frontend documentation, see [frontend/README.md](../frontend/README.md)
