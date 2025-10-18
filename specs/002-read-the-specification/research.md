# Research: GhostCart AP2 Protocol Demonstration

**Feature**: GhostCart - AP2 Protocol Demonstration
**Date**: 2025-10-17
**Phase**: 0 - Outline & Research

## Purpose

This document consolidates technical research findings and architectural decisions for implementing GhostCart, an e-commerce demonstration proving Agent Payments Protocol (AP2) v0.1 works with AWS Strands SDK.

## Key Technical Decisions

### 1. Strands Agents SDK Integration

**Decision**: Use Strands SDK (https://github.com/strands-agents/sdk-python) with Agents-as-Tools pattern and Claude Sonnet 4.5 via AWS Bedrock

**Package Installation**:
```bash
pip install strands-agents strands-agents-tools
```
**Note**: Package is `strands-agents`, NOT "aws-strands-sdk" (common confusion point)

**Rationale**:
- Strands SDK provides model-agnostic agent orchestration with tool composition
- Native AWS Bedrock support with Claude Sonnet 4.5 (model: `us.anthropic.claude-sonnet-4-20250514-v1:0`)
- Simple decorator-based tool definition (`@tool`) for custom functions
- Built-in Model Context Protocol (MCP) support for extensibility
- All agents read model/region from centralized config (backend/src/config.py)
- Configuration set via environment variables (AWS_REGION, AWS_BEDROCK_MODEL_ID)
- In-process agent execution simplifies hackathon deployment vs microservices

**Alternatives Considered**:
- LangChain: More complex setup, heavier dependency footprint
- Custom agent framework: Would require significant boilerplate for hackathon timeline
- Google Agent Development Kit: Would not demonstrate AP2 interoperability beyond reference implementation

**Implementation Approach**:
```python
from strands import Agent, tool
from strands.models import BedrockModel

# Configure Bedrock model
bedrock_model = BedrockModel(
    model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
    temperature=0.7,
    streaming=True
)

# Define custom tools
@tool
def search_products(query: str, max_price: float = None) -> list:
    """Search product catalog by query and optional max price."""
    # Implementation here
    pass

# Create agent
agent = Agent(
    model=bedrock_model,
    tools=[search_products],
    system_prompt="You are a shopping assistant..."
)

# Use agent
response = agent("Find me a coffee maker under $70")
```

**Multi-Agent Pattern**:
- Define four separate Agent instances (Supervisor, HP Shopping, HNP Delegate, Payment)
- Each agent receives tailored system prompt defining role and available tools
- Supervisor agent invokes specialist agents by calling them as Python functions (agents-as-tools pattern)
- Tool results flow back to Supervisor for orchestration

### 2. AP2 Mandate Schema Compliance

**Decision**: Use Pydantic v2 models with strict validation matching official AP2 JSON schemas

**Rationale**:
- Pydantic provides runtime validation ensuring mandate structures never deviate from AP2 specification
- Type hints enable IDE support and catch errors during development
- Strict mode prevents extra fields that would violate protocol compliance
- JSON schema export capability allows validation against official AP2 schemas

**Alternatives Considered**:
- Manual dict validation: Error-prone, no type safety
- Dataclasses: Lack runtime validation
- marshmallow: Less modern, no async support

**Implementation Approach**:
- Define three core models: `IntentMandate`, `CartMandate`, `PaymentMandate`
- Include nested models for complex fields (constraints, references, signature objects)
- Configure `ConfigDict` with `strict=True` and `extra='forbid'`
- Add custom validators for AP2-specific rules (expiration times, constraint relationships)

### 3. Cryptographic Signature Simulation

**Decision**: HMAC-SHA256 using Python standard library (`hmac`, `hashlib`), labeled as mocking production ECDSA

**Rationale**:
- HMAC-SHA256 provides cryptographic integrity verification for demo purposes
- Python standard library implementation requires zero external dependencies
- Constant-time comparison via `hmac.compare_digest()` prevents timing attacks
- Clear labeling as demo mock satisfies transparency requirements

**Alternatives Considered**:
- Real ECDSA with python-ecdsa: Unnecessary complexity for demo, no hardware backing available
- JWT signatures: Heavier library dependency, overkill for mandate signing
- Plain SHA256 hashing: Not cryptographically secure for authentication

**Implementation Approach**:
- Maintain three separate HMAC secrets (user, agent, payment agent) in environment config
- Signing: Create canonical JSON representation, combine with metadata (timestamp, signer ID), compute HMAC
- Verification: Recompute HMAC and use constant-time comparison
- Store signature with metadata object (algorithm, timestamp, signer identity)

### 4. Background Job Persistence

**Decision**: APScheduler with SQLAlchemyJobStore backed by SQLite

**Rationale**:
- APScheduler provides interval-based scheduling matching 5-minute monitoring requirement (FR-016)
- SQLAlchemyJobStore ensures jobs survive server restarts (SC-009: 100% job persistence)
- SQLite keeps deployment simple for hackathon vs PostgreSQL
- Supports programmatic job creation when Intent Mandate signed

**Alternatives Considered**:
- Celery + Redis: Overkill for demo, adds deployment complexity
- In-memory scheduler: Would lose jobs on restart, violating SC-009
- Cron jobs: Cannot create dynamically from user actions

**Implementation Approach**:
- Configure APScheduler with SQLAlchemyJobStore pointing to SQLite database
- Create interval trigger when HNP Delegate Agent creates Intent Mandate
- Job function: Query mock merchant API, evaluate constraints, trigger autonomous purchase if met
- Support environment variable for accelerated demo mode (faster than 5-minute intervals)

### 5. Real-Time Communication Pattern

**Decision**: Server-Sent Events (SSE) over WebSockets

**Rationale**:
- SSE provides unidirectional server→client streaming matching transparency requirement (FR-041)
- Simpler protocol than WebSockets (no handshake complexity, works over HTTP)
- Native browser EventSource API with automatic reconnection
- FastAPI supports SSE via StreamingResponse with `text/event-stream` media type

**Alternatives Considered**:
- WebSockets: Bidirectional capability not needed, more complex implementation
- Long polling: Poor user experience, higher server load
- GraphQL subscriptions: Unnecessary dependency overhead

**Implementation Approach**:
- FastAPI endpoint returning StreamingResponse with media type `text/event-stream`
- Generator function yields formatted SSE messages (event type, data payload)
- Frontend uses EventSource API to connect, parses events, updates React state
- Event types: `agent_thought`, `product_results`, `mandate_created`, `signature_request`, `payment_processing`, `result`, `error`

### 6. Payment Agent Isolation Strategy

**Decision**: Completely self-contained `payment_agent/` folder with zero imports from parent directories

**Rationale**:
- Proves AP2 protocol truly enables reusable payment abstraction (Constitution Principle II)
- Demonstrates Payment Agent can be extracted and used in any commerce scenario (FR-037: travel, subscriptions, B2B)
- Validates architectural principle that payment layer knows nothing about commerce domain (FR-034)
- Enables judges to literally copy folder to another project and have it work

**Alternatives Considered**:
- Shared utilities folder: Would create coupling, violate reusability principle
- Microservice deployment: Overcomplicates demo, defeats "extractable folder" demonstration
- Plugin architecture: Adds unnecessary abstraction layers

**Implementation Approach**:
- Organize `payment_agent/` with agent definition, tool implementations, Pydantic schemas, crypto functions
- Restrict imports to: Python standard library, Pydantic, AWS Strands SDK only
- No imports from `../agents/`, `../mocks/`, `../models/`, or any GhostCart-specific code
- Accept only AP2 mandate primitives as input, return only payment results as output
- Document this isolation in README within payment_agent folder

### 7. Database Schema Design

**Decision**: SQLite with four normalized tables (mandates, monitoring_jobs, transactions, sessions)

**Rationale**:
- SQLite provides ACID transactions without deployment complexity (Constitution Principle VI)
- Normalized design separates concerns (mandates, jobs, transactions, sessions)
- Supports efficient queries for mandate chain reconstruction (FR-007, FR-061)
- Enables APScheduler job store integration for persistence

**Alternatives Considered**:
- PostgreSQL: Overkill for demo scale (10 concurrent jobs), requires separate process
- MongoDB: Lacks transaction guarantees, unnecessary flexibility
- JSON files: No transactional integrity, poor query performance

**Schema Design**:

**mandates table**:
- `id` (TEXT PRIMARY KEY): Mandate ID (e.g., `intent_hp_abc123`, `cart_xyz789`, `payment_def456`)
- `mandate_type` (TEXT): One of `intent`, `cart`, `payment`
- `user_id` (TEXT): User identifier
- `transaction_id` (TEXT): Groups related mandates (nullable for incomplete chains)
- `mandate_data` (TEXT): JSON blob of complete mandate per AP2 schema
- `signer_identity` (TEXT): Who signed (user ID, agent ID, payment agent ID)
- `signature` (TEXT): HMAC signature value
- `signature_metadata` (TEXT): JSON with algorithm, timestamp, signer details
- `validation_status` (TEXT): `valid`, `invalid`, `unsigned`
- `created_at` (TIMESTAMP)
- `updated_at` (TIMESTAMP)

Indexes: `user_id`, `transaction_id`, `mandate_type`

**monitoring_jobs table**:
- `job_id` (TEXT PRIMARY KEY): APScheduler job identifier
- `intent_mandate_id` (TEXT FOREIGN KEY): Links to Intent Mandate for HNP flow
- `user_id` (TEXT): User who created monitoring
- `product_query` (TEXT): Product search terms
- `constraints` (TEXT): JSON with price_max, delivery_max, expiration
- `schedule_interval_minutes` (INTEGER): Default 5, configurable for demo mode
- `active` (BOOLEAN): Whether job is still running
- `last_check_at` (TIMESTAMP): Last monitoring iteration
- `created_at` (TIMESTAMP)
- `expires_at` (TIMESTAMP): From Intent Mandate expiration

Indexes: `user_id`, `active`, `expires_at`

**transactions table**:
- `transaction_id` (TEXT PRIMARY KEY)
- `intent_mandate_id` (TEXT FOREIGN KEY): Links to Intent (nullable for HP flow context-only)
- `cart_mandate_id` (TEXT FOREIGN KEY): Links to Cart
- `payment_mandate_id` (TEXT FOREIGN KEY): Links to Payment
- `user_id` (TEXT)
- `status` (TEXT): `authorized`, `declined`, `expired`, `failed`
- `authorization_code` (TEXT): On success (nullable)
- `decline_reason` (TEXT): On failure (nullable)
- `amount_cents` (INTEGER): Total in cents
- `currency` (TEXT): Always `USD` per constitution
- `created_at` (TIMESTAMP)

Indexes: `user_id`, `status`, `created_at`

**sessions table**:
- `session_id` (TEXT PRIMARY KEY)
- `user_id` (TEXT)
- `current_flow_type` (TEXT): `hp`, `hnp`, or `none`
- `context_data` (TEXT): JSON for session continuity
- `last_activity_at` (TIMESTAMP)
- `created_at` (TIMESTAMP)

Indexes: `user_id`, `last_activity_at`

### 8. Mock Services Implementation

**Decision**: Three Python modules implementing AP2 role architecture (Merchant, Credentials Provider, Payment Processor)

**Mock Merchant API** (`mocks/merchant_api.py`):
- Product catalog with 15 products across 4 categories (Electronics, Kitchen, Fashion, Home)
- Includes spec examples: Philips HD7462 Coffee Maker (~$70), Apple AirPods Pro (~$250)
- Price range $30-$700 for constraint testing
- Mix of in-stock and out-of-stock for monitoring scenarios
- Search function filters by query terms and price constraints
- Returns product objects with ID, name, description, category, price, stock status, delivery estimate, image URL

**Mock Credentials Provider** (`mocks/credentials_provider.py`):
- Returns 2-3 tokenized payment methods per user
- Example tokens: `tok_visa_4242`, `tok_mc_5555`, `tok_amex_3782`
- Never returns raw card numbers (PCI compliance simulation)
- Each method includes: token, brand, last 4 digits, expiration (mock), billing address (mock)
- Role separation: Only Payment Agent calls this service, shopping agents never access

**Mock Payment Processor** (`mocks/payment_processor.py`):
- Authorization function with ~90% approval rate (FR-057)
- Success: Returns transaction ID (`txn_abc123`) and authorization code (`AUTH_xy45z8`)
- Decline scenarios with realistic distribution:
  - Insufficient funds (40% of declines)
  - Card expired (20% of declines)
  - Transaction declined by issuer (30% of declines)
  - Fraud suspected for high-value transactions >$500 (10% of declines)
- Returns AP2 standard error code `ap2:payment:declined` with specific reason

### 9. REST API Endpoint Design

**Decision**: FastAPI REST API with SSE streaming endpoint plus standard CRUD operations

**Endpoints**:

`POST /api/chat` - Submit user message to Supervisor Agent
- Request: `{message: string, session_id: string}`
- Response: `{response: string, session_id: string, flow_type: "hp"|"hnp"|"clarification"}`

`GET /api/stream` - Server-Sent Events for real-time updates
- Query param: `session_id`
- Returns: `text/event-stream` with event types and JSON data payloads

`POST /api/mandates/sign` - User signs mandate (HP Cart or HNP Intent)
- Request: `{mandate_id: string, mandate_type: string, user_id: string}`
- Response: `{signed_mandate: object, signature: string}`

`GET /api/transactions/{transaction_id}/chain` - Retrieve mandate chain visualization
- Response: `{intent: object|null, cart: object, payment: object, transaction: object}`

`GET /api/monitoring/jobs` - List active monitoring jobs for user
- Query param: `user_id`
- Response: `{jobs: [job objects with status]}`

`DELETE /api/monitoring/jobs/{job_id}` - Cancel monitoring job
- Response: `{success: boolean}`

`GET /api/products/search` - Search products (calls mock merchant)
- Query params: `query`, `max_price`
- Response: `{products: [product objects]}`

`GET /api/payment-methods` - Get tokenized payment methods (calls mock credentials provider)
- Query param: `user_id`
- Response: `{payment_methods: [tokenized method objects]}`

### 10. Frontend Architecture Decisions

**React Component Structure**:
- `ChatInterface`: Main conversation UI with message history and input
- `SignatureModal`: Biometric-style confirmation with fingerprint icon, animation states (idle, scanning, verified, error)
- `MandateChainViz`: Timeline visualization with expandable mandate boxes, tooltips, JSON view
- `MonitoringStatusCard`: Real-time job status with last check time, current price, conditions, expiration countdown
- `ProductCard`: Product display with image, name, price, delivery, stock status, select button
- `CartDisplay`: Cart summary with line items, total, "Approve Purchase" button
- `NotificationBanner`: Large notifications for autonomous purchases or errors

**State Management**:
- Component-local state with `useState` for UI concerns (modal visibility, expanded sections, form inputs)
- Global session context with Context API for session ID, user ID, current flow type
- SSE connection context managing EventSource with reconnection logic
- Monitoring jobs context for real-time job status updates

**Styling Approach**:
- Tailwind CSS utility classes for rapid styling
- Custom color scheme: blue primary, green success, orange warning, red error, gray neutrals
- Animations: 1-second pulse for fingerprint scanning (SC-014), smooth transitions for expandable sections
- Responsive considerations: Primary target laptop (1024px+), mobile as stretch goal

## AP2 Specification Compliance Strategy

### Mandate Chain Validation Rules

**Human-Present Flow Validation** (FR-005, FR-007):
1. Verify Cart Mandate structure matches AP2 schema
2. Verify Cart Mandate has user signature
3. Validate signature cryptographically
4. Optionally validate Intent Mandate for audit context (but no user signature required)
5. Create Payment Mandate referencing Cart Mandate
6. Store complete chain with transaction ID grouping

**Human-Not-Present Flow Validation** (FR-015, FR-019, FR-020, FR-022):
1. Verify Intent Mandate structure matches AP2 schema
2. Verify Intent Mandate has user signature (pre-authorization)
3. Validate Intent not expired (check timestamp against expiration field)
4. When conditions met, create Cart Mandate with agent signature (NOT user)
5. Verify Cart Mandate includes Intent Mandate ID in references field
6. Validate Cart constraints do not exceed Intent constraints:
   - Cart total ≤ Intent max_price
   - Cart delivery time ≤ Intent max_delivery_days
7. Set human-not-present flag in Payment Mandate
8. Store complete chain proving autonomous action within pre-authorized boundaries

### Error Code Mapping

**AP2 Standard Error Codes** (FR-040, Constitution Principle VII):
- `ap2:mandate:chain_invalid`: Cart does not reference Intent in HNP flow, or mandate missing in chain
- `ap2:mandate:signature_invalid`: HMAC verification failed, signer identity mismatch
- `ap2:mandate:expired`: Current timestamp > Intent expiration timestamp
- `ap2:mandate:constraints_violated`: Cart total exceeds Intent max_price, or delivery exceeds max_delivery_days
- `ap2:credentials:unavailable`: Credentials Provider returned no payment methods for user
- `ap2:payment:declined`: Payment Processor rejected authorization with specific decline reason

## Best Practices Applied

### FastAPI Async Patterns
- Use `async def` for all endpoints calling external services (even mocked ones)
- Use `await` for database operations with async SQLAlchemy session
- Generator functions for SSE streaming use `async for` to yield events

### Pydantic Model Organization
- Nest related models (e.g., `Signature` model within mandate models)
- Use Pydantic `Field` for documentation and validation rules
- Define custom validators with `@field_validator` decorator for cross-field validation

### Agent System Prompt Engineering
- Supervisor: Emphasize linguistic analysis, pattern recognition for intent vs monitoring
- HP Shopping: Focus on immediate action, product search, cart creation workflow
- HNP Delegate: Focus on constraint extraction, monitoring setup, expiration handling
- Payment Agent: Emphasize AP2 compliance, domain independence, error code usage

### Logging Strategy
- Structured logging with JSON format for machine parsing
- Separate loggers: `mandate_ops`, `signature_ops`, `payment_ops`, `scheduler_ops`, `errors`
- Log levels: DEBUG for agent reasoning, INFO for mandate operations, WARNING for validation failures, ERROR for exceptions
- Include correlation IDs (session_id, transaction_id) in all log entries

## Technology Stack Summary

**Backend**:
- Python 3.10+ (required by Strands SDK, type hints, asyncio, match statements)
- FastAPI 0.100+ (async endpoints, dependency injection, OpenAPI)
- Pydantic v2 (strict validation, JSON schema)
- SQLAlchemy 2.0+ (async session, ORM)
- APScheduler 3.10+ (SQLAlchemyJobStore)
- boto3 (AWS Bedrock client)
- strands-agents + strands-agents-tools (agent orchestration with Bedrock)

**Frontend**:
- React 18+ (hooks, concurrent rendering)
- Vite 4+ (fast dev server, optimized builds)
- Tailwind CSS 3+ (utility-first styling)
- EventSource API (native SSE support)

**Development Tools**:
- uvicorn (ASGI server)
- pytest (testing framework)
- black (code formatting)
- mypy (static type checking)
- ruff (fast linting)

**Deployment**:
- Single process via uvicorn
- Environment variables for config (AWS credentials, demo mode, log level, database path)
- FastAPI serves both API and static React build (mounted at root)

## Risk Mitigation

### AP2 Schema Compliance
- **Risk**: Mandate structures drift from official AP2 schemas
- **Mitigation**: Pydantic strict mode with schema validation tests, documented schema source URLs

### Payment Agent Coupling
- **Risk**: Accidental imports from GhostCart-specific modules
- **Mitigation**: Import linter checks in CI, clear folder boundaries, documented import restrictions

### Demo Reliability
- **Risk**: External Bedrock API failures during demo
- **Mitigation**: Fallback prompts, error handling, mock mode for agent responses if needed

### Performance Under Monitoring Load
- **Risk**: 10 concurrent jobs overwhelm scheduler
- **Mitigation**: Job execution timeout limits, monitoring job dashboard, load testing before demo

## Open Questions Resolved

All technical unknowns identified during specification phase have been resolved through this research:

1. ✅ LLM provider for agent routing: AWS Bedrock with Claude Sonnet 4.5
2. ✅ Agent orchestration pattern: AWS Strands Agents-as-Tools
3. ✅ Real-time communication: Server-Sent Events
4. ✅ Background job persistence: APScheduler + SQLAlchemyJobStore + SQLite
5. ✅ Signature cryptography: HMAC-SHA256 with constant-time comparison
6. ✅ Payment Agent isolation: Self-contained folder with import restrictions
7. ✅ Mandate validation approach: Pydantic models with custom validators
8. ✅ Error code standardization: AP2 error code hierarchy with FastAPI handlers

## Next Steps

Proceed to **Phase 1: Design & Contracts**:
1. Generate `data-model.md` with complete entity schemas
2. Generate API contracts in `contracts/` folder (OpenAPI schema)
3. Generate `quickstart.md` for local development setup
4. Update agent context with technology stack decisions
5. Re-evaluate Constitution Check with concrete design decisions
