# GhostCart AP2 Architecture Documentation

## Overview

**GhostCart** is a full-stack e-commerce demonstration application showcasing the **Agent Payments Protocol (AP2) v0.1** implementation using AWS Bedrock Agent Strands SDK. It demonstrates both human-present (HP) and human-not-present (HNP) purchase flows with intelligent agent orchestration.

**Classification**:
- Multi-tier web application (Frontend + Backend)
- Microservices-ready architecture with containerized deployment
- AI-powered agent orchestration system
- Real-time streaming chat interface

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              USER BROWSER                                        │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │  React Frontend (Vite)                                                    │  │
│  │  ├─ ChatInterface (SSE Streaming)                                         │  │
│  │  ├─ SignatureModal (Biometric-style signing)                              │  │
│  │  ├─ MandateChainViz (Intent → Cart → Payment → Transaction)              │  │
│  │  └─ MonitoringStatusCard (Real-time updates)                              │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
└────────────────────────┬───────────────────────────────────────────────────────┘
                         │ HTTP/HTTPS + SSE
                         │ (REST API + Server-Sent Events)
┌────────────────────────▼───────────────────────────────────────────────────────┐
│                     AWS INFRASTRUCTURE                                          │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │  Application Load Balancer (ALB)                                          │  │
│  │  ├─ Route 53 DNS                                                          │  │
│  │  ├─ HTTPS/HTTP Routing                                                    │  │
│  │  └─ Health Checks                                                          │  │
│  └────────────────────┬─────────────────────────────────────────────────────┘  │
│                       │                                                          │
│  ┌────────────────────▼─────────────────────────────────────────────────────┐  │
│  │  ECS Fargate Service                                                      │  │
│  │  ┌──────────────────────────────────────────────────────────────────────┐│  │
│  │  │  Docker Container                                                     ││  │
│  │  │  ├─ Frontend Static Files (from Vite build)                          ││  │
│  │  │  └─ Backend Application (FastAPI on :8000)                           ││  │
│  │  └──────────────────────────────────────────────────────────────────────┘│  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │  CloudWatch                                                               │  │
│  │  ├─ Log Group: /ecs/ghostcart-backend                                    │  │
│  │  └─ Container Monitoring                                                  │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                       FASTAPI APPLICATION (Backend)                              │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │  API Layer (/api)                                                         │  │
│  │  ├─ /chat/stream (SSE) ──────────────┐                                   │  │
│  │  ├─ /mandates/sign                   │                                   │  │
│  │  ├─ /products/search                 │                                   │  │
│  │  ├─ /payment-methods                 │                                   │  │
│  │  ├─ /transactions                    │                                   │  │
│  │  └─ /monitoring/status               │                                   │  │
│  └─────────────────┬────────────────────┼───────────────────────────────────┘  │
│                    │                    │                                       │
│  ┌─────────────────▼────────────────────▼───────────────────────────────────┐  │
│  │  Session & Context Management                                            │  │
│  │  └─ SessionManager (conversation history + state)                        │  │
│  └─────────────────┬──────────────────────────────────────────────────────┘  │
│                    │                                                            │
│  ┌─────────────────▼─────────────────────────────────────────────────────────┐│
│  │  AWS BEDROCK AGENT STRANDS ORCHESTRATION                                  ││
│  │  ┌──────────────────────────────────────────────────────────────────────┐││
│  │  │  Supervisor Agent (Entry Point)                                      │││
│  │  │  ├─ LLM-based intelligent routing                                    │││
│  │  │  ├─ Claude Sonnet 4.5 (AWS Bedrock)                                  │││
│  │  │  └─ Uses agents as @tool-decorated functions                         │││
│  │  └──────────┬──────────────────────────┬────────────────────────────────┘││
│  │             │                          │                                  ││
│  │   ┌─────────▼──────────┐    ┌─────────▼──────────────────┐              ││
│  │   │ HP Shopping Agent  │    │ HNP Delegate Agent         │              ││
│  │   │ (Immediate Buy)    │    │ (Autonomous Monitoring)     │              ││
│  │   │                    │    │                             │              ││
│  │   │ Tools:             │    │ Tools:                      │              ││
│  │   │ ┌────────────────┐ │    │ ┌─────────────────────────┐│              ││
│  │   │ │search_products │ │    │ │extract_constraints      ││              ││
│  │   │ │create_cart     │ │    │ │search_products          ││              ││
│  │   │ │request_sig     │ │    │ │create_hnp_intent        ││              ││
│  │   │ │get_signed_cart │ │    │ │request_intent_sig       ││              ││
│  │   │ │invoke_payment  │─┼────┼─│activate_monitoring_job  ││              ││
│  │   │ └────────────────┘ │    │ └─────────────────────────┘│              ││
│  │   └────────────────────┘    └────────┬───────────────────┘              ││
│  │                                       │                                   ││
│  │   ┌───────────────────────────────────▼───────────────────────────────┐ ││
│  │   │ Payment Agent (Domain-Independent)                                 │ ││
│  │   │                                                                     │ ││
│  │   │ Tools (Sequential Executor):                                       │ ││
│  │   │ ┌────────────────────────────────────────────────────────────────┐│ ││
│  │   │ │ 1. validate_hp_chain / validate_hnp_chain                      ││ ││
│  │   │ │ 2. retrieve_payment_credentials                                ││ ││
│  │   │ │ 3. process_payment_authorization                               ││ ││
│  │   │ └────────────────────────────────────────────────────────────────┘│ ││
│  │   │                                                                     │ ││
│  │   │ AP2 Compliance: Zero knowledge of products/merchants               │ ││
│  │   └─────────────────────────────────────────────────────────────────────┘ ││
│  └──────────────────────────────────────────────────────────────────────────┘│
│                                                                                │
│  ┌──────────────────────────────────────────────────────────────────────────┐│
│  │  Service Layer                                                            ││
│  │  ├─ mandate_service (Intent/Cart/Payment mandate creation)               ││
│  │  ├─ signature_service (HMAC-SHA256 signing per AP2 spec)                 ││
│  │  ├─ monitoring_service (APScheduler background jobs)                     ││
│  │  ├─ transaction_service (Purchase record linkage)                        ││
│  │  ├─ sse_service (Server-Sent Events for real-time updates)               ││
│  │  └─ bedrock_service (AWS Bedrock Claude invocation)                      ││
│  └──────────────────────────────────────────────────────────────────────────┘│
│                                                                                │
│  ┌──────────────────────────────────────────────────────────────────────────┐│
│  │  Background Processing (APScheduler)                                      ││
│  │  ┌──────────────────────────────────────────────────────────────────────┐││
│  │  │ Monitoring Loop (every 10s demo / 5min prod)                         │││
│  │  │ ├─ Check product price & availability                                │││
│  │  │ ├─ Emit SSE monitoring events                                        │││
│  │  │ ├─ When conditions met:                                              │││
│  │  │ │  ├─ Create Cart Mandate (agent-signed)                             │││
│  │  │ │  ├─ Invoke Payment Agent                                           │││
│  │  │ │  └─ Create Transaction                                             │││
│  │  │ └─ Handle expiration (7 days)                                        │││
│  │  └──────────────────────────────────────────────────────────────────────┘││
│  └──────────────────────────────────────────────────────────────────────────┘│
│                                                                                │
│  ┌──────────────────────────────────────────────────────────────────────────┐│
│  │  Mock Integrations (Demo)                                                 ││
│  │  ├─ credentials_provider (tokenized payment methods)                     ││
│  │  ├─ payment_processor (~90% approval rate simulator)                     ││
│  │  └─ merchant_api (product catalog ~15 items)                             ││
│  └──────────────────────────────────────────────────────────────────────────┘│
└────────────────────────┬───────────────────────────────────────────────────────┘
                         │
┌────────────────────────▼───────────────────────────────────────────────────────┐
│                       DATABASE LAYER (SQLite + SQLAlchemy)                      │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │  mandates                                                                 │  │
│  │  ├─ AP2 Protocol audit trail                                             │  │
│  │  ├─ Types: intent, cart, payment                                         │  │
│  │  └─ Stores: mandate_data, signatures, validation_status                  │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │  monitoring_jobs                                                          │  │
│  │  ├─ Active background monitoring state                                   │  │
│  │  └─ Links to intent_mandate_id, constraints, expiration                  │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │  transactions                                                             │  │
│  │  ├─ Purchase outcomes                                                     │  │
│  │  └─ Links: intent + cart + payment mandates                              │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │  sessions                                                                 │  │
│  │  └─ Conversation continuity + flow context                               │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                         AWS BEDROCK (External Service)                           │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │  Claude Sonnet 4.5                                                        │  │
│  │  └─ Model: global.anthropic.claude-sonnet-4-5-20250929-v1:0              │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## Main Components

### Frontend (React + Vite)
- **Location**: `/frontend`
- **Tech Stack**: React 18, Vite, Tailwind CSS, React Markdown
- **Purpose**: Real-time chat interface for user interaction with agents
- **Key Components**:
  - `ChatInterface.jsx`: Streaming chat with real-time message updates
  - `SignatureModal.jsx`: Biometric-style mandate signing interface
  - `MandateChainViz.jsx`: Visual timeline of Intent → Cart → Payment → Transaction
  - `MonitoringStatusCard.jsx`: Real-time monitoring status display
  - `ProductCard.jsx`: Product display with pricing
  - SSE (Server-Sent Events) integration for streaming updates

### Backend (Python FastAPI)
- **Location**: `/backend`
- **Tech Stack**: Python 3.11, FastAPI, SQLAlchemy, SQLite, AWS Bedrock

#### Core Layers:

**1. API Layer** (`/backend/src/api`)
- `chat.py`: Chat endpoint with SSE streaming for agent conversations
- `payments.py`: Tokenized payment methods retrieval
- `mandates.py`: Mandate signing and verification endpoints
- `products.py`: Product search and catalog
- `transactions.py`: Transaction history and status
- `monitoring.py`: Monitoring job status

**2. Agent Layer** (`/backend/src/agents`)

- **Supervisor Agent** (`supervisor_strands.py`):
  - Entry point for all user interactions
  - LLM-based intelligent routing (not keyword-based)
  - Routes to HP Shopping or HNP Delegate agents
  - Uses agents-as-tools pattern with Strands SDK

- **HP Shopping Agent** (`hp_shopping_strands.py`):
  - Handles immediate purchase flows
  - Tools: search_products, create_shopping_cart, request_user_cart_signature, get_signed_cart_mandate, invoke_payment_processing
  - Stateless agent receiving context from Supervisor

- **HNP Delegate Agent** (`hnp_delegate_strands.py`):
  - Handles autonomous monitoring setup
  - Tools: extract_monitoring_constraints, search_products, create_hnp_intent, request_user_intent_signature, get_signed_intent_mandate, activate_monitoring_job
  - Guides users through pre-authorization workflow

- **Payment Agent** (`payment_agent/agent.py`):
  - Isolated, reusable AP2 payment processor
  - Tools: validate_hp_chain, validate_hnp_chain, retrieve_payment_credentials, process_payment_authorization
  - Zero knowledge of products/merchants (Constitution Principle II compliance)
  - Can be extracted to separate projects without modification

**3. Database Layer** (`/backend/src/db`)
- SQLite with async SQLAlchemy ORM
- **Models**:
  - `MandateModel`: Stores Intent, Cart, Payment mandates with signatures
  - `TransactionModel`: Links mandates to transaction outcomes
  - `MonitoringJobModel`: Stores active monitoring jobs with expiration
  - `SessionModel`: User session state for conversation continuity

**4. Service Layer** (`/backend/src/services`)
- `bedrock_service.py`: AWS Bedrock Claude model invocation (streaming & non-streaming)
- `mandate_service.py`: Intent/Cart/Payment mandate creation per AP2 schema
- `signature_service.py`: HMAC-SHA256 signing (demo) matching AP2 specification
- `monitoring_service.py`: Background monitoring job scheduler with APScheduler integration
- `session_service.py`: User session management
- `sse_service.py`: Server-Sent Events emission for real-time updates
- `scheduler.py`: APScheduler wrapper for background monitoring jobs
- `transaction_service.py`: Transaction record creation with mandate linkage

**5. Infrastructure & Mocks** (`/backend/src/mocks`)
- `credentials_provider.py`: Returns tokenized payment methods (tok_* format)
- `payment_processor.py`: Simulates payment authorization with ~90% approval rate
- `merchant_api.py`: Product catalog with ~15 items across categories

---

## Technology Stack

### Frontend
- React 18.2.0
- Vite 4.3.0 (build tool)
- Tailwind CSS 3.3.0
- ESLint + Prettier (code quality)
- Node.js

### Backend
- **Framework**: FastAPI 0.100.0+ with Uvicorn
- **AI/ML**:
  - AWS Bedrock API (Claude Sonnet 4.5-20250929)
  - Strands Agents SDK (AWS's agent orchestration framework)
  - strands-agents >= 0.1.0
  - strands-agents-tools >= 0.1.0
- **Database**:
  - SQLAlchemy 2.0+ (ORM)
  - aiosqlite 0.19+ (async SQLite)
  - SQLite (file-based)
- **Async**: Python 3.11+ async/await
- **Validation**: Pydantic 2.0+
- **Scheduling**: APScheduler 3.10.0
- **Cryptography**: HMAC-SHA256 (for demo signatures)
- **Testing**: pytest, pytest-asyncio, httpx
- **Code Quality**: black, mypy, ruff

### AWS Services (Infrastructure)
- **Amazon Bedrock**: Claude model inference
- **EC2 Container Registry (ECR)**: Docker image hosting
- **ECS Fargate**: Containerized backend deployment
- **Application Load Balancer (ALB)**: HTTP/HTTPS routing
- **CloudWatch**: Logging and monitoring
- **VPC**: Network isolation
- **Route 53**: DNS management (HTTPS configuration)

### Deployment
- Docker (multi-stage Dockerfile for frontend + backend)
- ECS Fargate (serverless container orchestration)
- Bash deployment scripts

---

## Component Interactions

```
User Browser (Frontend)
    ↓↑ HTTP/WebSocket (SSE)
    ├─→ REST API Endpoints
    │    ├─ /api/chat/stream (SSE streaming)
    │    ├─ /api/mandates/sign (mandate signing)
    │    ├─ /api/products/search
    │    ├─ /api/payment-methods
    │    └─ /api/transactions
    │
FastAPI Application
    ↓
Session/Context Management
    ├─→ SessionManager (conversation history)
    │
Supervisor Agent (Strands)
    ├─→ LLM routing decision
    │
    ├─→ HP Shopping Agent (Strands)
    │   ├─ search_products() → Merchant API Mock
    │   ├─ create_shopping_cart() → Cart Mandate Service
    │   ├─ request_user_cart_signature() → SSE Event
    │   ├─ get_signed_cart_mandate() → Database
    │   └─ invoke_payment_processing() → Payment Agent
    │
    └─→ HNP Delegate Agent (Strands)
        ├─ extract_monitoring_constraints()
        ├─ search_products() → Merchant API Mock
        ├─ create_hnp_intent() → Intent Mandate Service
        ├─ request_user_intent_signature() → SSE Event
        ├─ get_signed_intent_mandate() → Database
        └─ activate_monitoring_job() → APScheduler

Background Monitoring Loop (APScheduler)
    ├─ Runs every 5-10 seconds (demo) / 5 minutes (production)
    ├─ Checks product availability and prices
    ├─ Emits SSE monitoring events
    ├─ On condition met:
    │   ├─ Creates Cart Mandate (agent-signed)
    │   ├─ Invokes Payment Agent
    │   └─ Creates Transaction record

Payment Agent (Strands)
    ├─ Validates mandate chain (HP or HNP)
    ├─ retrieve_payment_credentials() → Credentials Provider Mock
    ├─ process_payment_authorization() → Payment Processor Mock
    └─ Creates Payment Mandate

Database (SQLite)
    ├─ mandates table (all mandate types + signatures)
    ├─ transactions table (purchase outcomes)
    ├─ monitoring_jobs table (active background jobs)
    └─ sessions table (conversation state)

AWS Bedrock
    └─ Claude Sonnet 4.5 inference (agents reasoning)
```

---

## Data Flow Examples

### HP (Human-Present) Flow

```
User: "Find coffee maker under $70"
    ↓
Supervisor Agent (routes to shopping_assistant tool)
    ↓
HP Shopping Agent
    ├─ Tool: search_products("coffee maker", 70)
    │  └─ Returns: product list via Merchant API Mock
    │  └─ SSE emit: product_results
    ↓
User: "I'll take the first one"
    ↓
HP Shopping Agent
    ├─ Tool: create_shopping_cart(product_id)
    │  ├─ Creates Intent Mandate (context-only, unsigned)
    │  ├─ Creates Cart Mandate (requires user signature)
    │  ├─ Saves to database
    │  └─ SSE emit: cart_created
    ├─ Tool: request_user_cart_signature()
    │  └─ SSE emit: signature_requested (triggers frontend modal)
    ↓
Frontend: Shows biometric signature modal
User: Clicks "Confirm" → POST /api/mandates/sign
    ├─ Signature Service adds HMAC signature
    ├─ Cart Mandate saved with signature
    └─ Frontend continues
    ↓
HP Shopping Agent
    ├─ Tool: get_signed_cart_mandate()
    │  └─ Retrieves signed cart from database
    ├─ Tool: invoke_payment_processing()
    │  ├─ Calls Payment Agent internally
    │  ├─ Payment Agent validates HP chain
    │  ├─ Retrieves tokenized credentials
    │  ├─ Calls Payment Processor Mock
    │  ├─ Creates Payment Mandate
    │  ├─ Creates Transaction record
    │  └─ Returns authorization result
    ↓
Frontend: Shows success with mandate chain visualization
User: Clicks "View Chain" → sees Intent → Cart → Payment → Transaction
```

### HNP (Human-Not-Present) Flow

```
User: "Buy AirPods if price drops below $180 and delivery < 2 days"
    ↓
Supervisor Agent (routes to monitoring_assistant tool)
    ↓
HNP Delegate Agent
    ├─ Tool: extract_monitoring_constraints()
    │  └─ Parses: max_price_cents=18000, max_delivery_days=2
    ├─ Tool: search_products("AirPods", 180)
    │  └─ Returns: matching products
    ├─ Tool: create_hnp_intent()
    │  ├─ Creates Intent Mandate with constraints
    │  ├─ Sets expiration to 7 days
    │  ├─ Saves to database (unsigned)
    │  └─ Returns mandate_id: intent_hnp_abc123
    ├─ Tool: request_user_intent_signature()
    │  └─ SSE emit: signature_requested
    ↓
Frontend: Shows signature modal with ⚠️ "Autonomous Purchase Warning"
User: Clicks "Confirm" → POST /api/mandates/sign
    ├─ Signature Service adds HMAC signature
    ├─ Intent Mandate saved with user signature
    └─ Signals monitoring to activate
    ↓
HNP Delegate Agent
    ├─ Tool: get_signed_intent_mandate()
    │  └─ Retrieves signed Intent from database
    ├─ Tool: activate_monitoring_job()
    │  ├─ Creates MonitoringJobModel in database
    │  ├─ Registers with APScheduler
    │  └─ SSE emit: monitoring_activated
    ↓
Background Monitoring Loop (every 10 sec demo / 5 min prod)
    ├─ Checks price and delivery via Merchant API
    ├─ SSE emit: monitoring_check_started
    ├─ SSE emit: monitoring_check_complete (conditions not met)
    │  ├─ Reason: "price $249 exceeds max $180"
    │  ├─ Repeats until conditions met or expiration
    │
    ├─ WHEN CONDITIONS MET:
    │  ├─ SSE emit: autonomous_purchase_starting
    │  ├─ Agent creates Cart Mandate (agent-signed, references intent_id)
    │  ├─ SSE emit: autonomous_cart_created
    │  ├─ Invokes Payment Agent
    │  │  ├─ Validates HNP chain:
    │  │  │  ├─ Intent has user signature ✓
    │  │  │  ├─ Intent not expired ✓
    │  │  │  ├─ Cart has agent signature ✓
    │  │  │  ├─ Cart references intent_id ✓
    │  │  │  └─ Constraints not violated ✓
    │  │  ├─ Retrieves tokenized credentials
    │  │  ├─ Calls Payment Processor Mock
    │  │  └─ Creates Payment Mandate (human_not_present=true flag)
    │  ├─ Creates Transaction record
    │  └─ SSE emit: autonomous_purchase_complete
    │     ├─ Transaction ID: txn_def789
    │     ├─ Authorization Code: AUTH_xy45z8
    │     └─ User can view mandate chain
    │
    └─ WHEN EXPIRATION REACHED (7 days):
        ├─ SSE emit: monitoring_expired
        ├─ MonitoringJobModel marked inactive
        └─ User notified with current price, option to recreate
```

---

## Infrastructure Setup

### Deployment Architecture

```
ECS Fargate Service
├─ Container (Docker)
│  ├─ Frontend (React/Vite) → Served as static from backend
│  ├─ Backend API (FastAPI on port 8000)
│  └─ SQLite database (ephemeral in container)
│
├─ Task Definition (ecs-task-definition.json)
│  ├─ 1024 CPU units
│  ├─ 2048 MB memory
│  ├─ Health check: GET /api/health
│  └─ Environment variables (AWS_REGION, MODEL_ID, secrets)
│
└─ Application Load Balancer
   ├─ HTTP/HTTPS routing
   ├─ Target group health checks
   └─ Route 53 DNS integration

CloudWatch
├─ Log group: /ecs/ghostcart-backend
└─ Container logs streaming
```

### Dockerization
- **Multi-stage Dockerfile**:
  1. Frontend builder stage (Node 18 + Vite build)
  2. Backend stage (Python 3.11 + dependencies)
  3. Combines frontend dist with backend code
  4. Runs on port 8000

### Database Persistence
- SQLite with WAL mode enabled for concurrent access
- Initialized on container startup via `init_db.py`
- Data is ephemeral (local to container)
- Production version would use RDS

### Monitoring & Logging
- APScheduler for background monitoring jobs
- CloudWatch integration for container logs
- Health check endpoint: `GET /api/health`

---

## Database Schema

### mandates (AP2 protocol audit trail)
```sql
├─ id (mandate_id: intent_hnp_*, cart_hp_*, etc.)
├─ mandate_type (intent, cart, payment)
├─ user_id
├─ transaction_id (foreign key to transactions)
├─ mandate_data (JSON blob)
├─ signer_identity (user_* or ap2_agent_*)
├─ signature (JSON: signature, timestamp, algorithm)
├─ validation_status (valid, invalid, unsigned)
└─ created_at, updated_at
```

### monitoring_jobs (Background monitoring state)
```sql
├─ job_id (APScheduler job ID)
├─ intent_mandate_id (foreign key to mandates)
├─ user_id (index for quick lookups)
├─ product_query
├─ constraints (JSON: max_price_cents, max_delivery_days)
├─ schedule_interval_minutes
├─ active (boolean index)
├─ last_check_at
├─ created_at
└─ expires_at (index for cleanup)
```

### transactions (Purchase outcomes)
```sql
├─ transaction_id
├─ intent_mandate_id (nullable - HNP only)
├─ cart_mandate_id
├─ payment_mandate_id
├─ user_id (index)
├─ status (authorized, declined, expired, failed)
├─ authorization_code
├─ decline_reason
├─ amount_cents
├─ currency
└─ created_at
```

### sessions (Conversation continuity)
```sql
├─ session_id
├─ user_id (index)
├─ current_flow_type (hp, hnp, none)
├─ context_data (JSON)
├─ last_activity_at (index)
└─ created_at
```

---

## Agent/AI Components (AWS Bedrock Agent Strands)

### Strands SDK Architecture
The system uses **AWS Bedrock Agent Strands SDK** for intelligent agent orchestration:

1. **Model**: Claude Sonnet 4.5 (configured in settings)
   - `global.anthropic.claude-sonnet-4-5-20250929-v1:0` (latest)
   - Temperature: 0.7 for shopping, 0.3 for payment validation

2. **Agent Pattern**: Agents-as-Tools
   - Supervisor Agent uses HP Shopping and HNP Delegate agents as @tool-decorated functions
   - Specialist agents are stateless, receiving reformulated context from Supervisor
   - Each agent has custom tools via @tool decorators

3. **Tool Execution**: SequentialToolExecutor for Payment Agent
   - Ensures correct order: validate → retrieve credentials → process payment
   - Default parallel execution for other agents (shopping, monitoring)

### Key Agent Behaviors

**Supervisor Agent**:
- System prompt guides intelligent routing (not keyword matching)
- Understands implicit references ("yes", "the first one")
- Routes to HP Shopping for immediate purchases
- Routes to HNP Delegate for conditional/future purchases
- Handles ambiguity with clarifying questions

**HP Shopping Agent**:
- Stateless - receives full context from Supervisor per call
- Guides: search → select → cart → signature → payment
- No conversation memory (context passed by Supervisor)

**HNP Delegate Agent**:
- Stateless - receives full context from Supervisor
- Guides: constraint extraction → product search → intent creation → signature → monitoring activation
- Critical: Warns users about autonomous purchases before signature

**Payment Agent**:
- Completely domain-independent per AP2 Constitution Principle II
- Validates mandate structures (not knowing product/merchant details)
- Two validation flows:
  - HP Chain: Cart user-signed (authorization)
  - HNP Chain: Intent user-signed + Cart agent-signed + references + expiration + constraints
- Returns structured JSON with success/errors

---

## AP2 Protocol Compliance

### Mandate Types

**Intent Mandate**
```json
{
  "mandate_id": "intent_hnp_*",
  "mandate_type": "intent",
  "user_id": "...",
  "constraints": {
    "max_price_cents": 18000,
    "max_delivery_days": 2,
    "currency": "USD"
  },
  "expiration": "2025-10-28T...",
  "signature": {
    "signer_identity": "user_*",
    "signature": "hmac_sha256_...",
    "timestamp": "..."
  }
}
```

**Cart Mandate**
```json
{
  "mandate_id": "cart_hp_* or cart_hnp_*",
  "mandate_type": "cart",
  "user_id": "...",
  "items": [...],
  "total": { "grand_total_cents": 7300 },
  "references": {
    "intent_mandate_id": "intent_hnp_*" // Only in HNP
  },
  "signature": {
    "signer_identity": "user_* or ap2_agent_*",
    "signature": "...",
    "timestamp": "..."
  }
}
```

**Payment Mandate**
```json
{
  "mandate_id": "payment_*",
  "mandate_type": "payment",
  "cart_mandate_id": "cart_*",
  "amount_cents": 7300,
  "human_not_present": false, // true for HNP
  "signature": { ... }
}
```

### Signature Validation
- Demo uses HMAC-SHA256 (would be ECDSA in production)
- All signatures verified before payment processing
- Audit trail maintained via signature metadata

---

## Key Integration Points

1. **Frontend ↔ Backend**:
   - REST API for synchronous operations (mandates, payments, products)
   - SSE for real-time streaming (chat, monitoring events)
   - Biometric signature modal triggered by SSE events

2. **Backend ↔ AWS Bedrock**:
   - Async invocation of Claude Sonnet 4.5
   - Streaming responses for real-time agent transparency
   - Fallback to demo mode if Bedrock unavailable

3. **Agents ↔ Services**:
   - Agents call tools (decorated functions) that invoke services
   - Services handle database persistence
   - SSE events emitted from within agent tools

4. **Background Jobs ↔ Database**:
   - APScheduler stores job state
   - Database tracks active monitoring jobs
   - Jobs survive server restarts via persistence

5. **Payment Processing**:
   - Isolated Payment Agent can be called from HP or HNP agents
   - Credentials provider → Payment processor → Transaction service
   - No coupling between shopping logic and payment logic

---

## Error Handling & Resilience

- **AP2 Error Codes**:
  - `ap2:mandate:chain_invalid`
  - `ap2:mandate:signature_invalid`
  - `ap2:mandate:expired`
  - `ap2:mandate:constraints_violated`
  - `ap2:credentials:unavailable`
  - `ap2:payment:declined`

- **Fallback**: Demo mode allows operation without AWS Bedrock
- **Validation**: All mandates validated before processing
- **Constraints**: HNP purchases verified against Intent constraints before authorization
- **Monitoring Expiration**: Jobs cleaned up after 7-day expiration

---

## Deployment & Operations

### Development
```bash
# Frontend
cd frontend
npm run dev  # Vite dev server

# Backend
cd backend
python -m uvicorn src.main:app --reload
```

### Production (ECS Fargate)
```bash
./deploy-ecs.sh  # Builds Docker image, pushes to ECR, updates ECS service
```

### Configuration
- `/infrastructure/config.sh`: AWS credentials, VPC, subnet, ALB configuration
- `ecs-task-definition.json`: Container specs, environment variables, health checks
- `.env`: Demo secrets (changed before production)

### Monitoring
- CloudWatch logs at `/ecs/ghostcart-backend`
- Health endpoint: `GET /api/health` (returns status, version, environment)
- APScheduler logs monitoring job execution

---

## Key Architectural Highlights

1. **Multi-Agent Orchestration**: Supervisor uses specialist agents as tools, providing intelligent LLM-based routing

2. **AP2 Protocol Compliance**: Complete mandate chain (Intent → Cart → Payment → Transaction) with proper signatures

3. **Real-time Transparency**: SSE streaming for all agent actions and monitoring updates

4. **Domain Separation**: Payment Agent has zero knowledge of products/merchants (portable across domains)

5. **Autonomous Purchasing**: APScheduler-based background monitoring with constraint validation

6. **Production-Ready**: ECS Fargate deployment with ALB, health checks, CloudWatch logging

7. **Audit Trail**: All mandates persisted with signatures for compliance and debugging

---

## File Structure Reference

```
ap2-hack/
├── backend/
│   ├── src/
│   │   ├── agents/
│   │   │   ├── supervisor_strands.py
│   │   │   ├── hp_shopping_strands.py
│   │   │   ├── hnp_delegate_strands.py
│   │   │   └── payment_agent/
│   │   │       └── agent.py
│   │   ├── api/
│   │   │   ├── chat.py
│   │   │   ├── mandates.py
│   │   │   ├── payments.py
│   │   │   ├── products.py
│   │   │   ├── transactions.py
│   │   │   └── monitoring.py
│   │   ├── db/
│   │   │   └── models.py
│   │   ├── services/
│   │   │   ├── bedrock_service.py
│   │   │   ├── mandate_service.py
│   │   │   ├── signature_service.py
│   │   │   ├── monitoring_service.py
│   │   │   ├── transaction_service.py
│   │   │   ├── session_service.py
│   │   │   ├── sse_service.py
│   │   │   └── scheduler.py
│   │   └── mocks/
│   │       ├── credentials_provider.py
│   │       ├── payment_processor.py
│   │       └── merchant_api.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ChatInterface.jsx
│   │   │   ├── SignatureModal.jsx
│   │   │   ├── MandateChainViz.jsx
│   │   │   └── MonitoringStatusCard.jsx
│   │   └── App.jsx
│   └── package.json
├── infrastructure/
│   ├── deploy-ecs.sh
│   ├── config.sh
│   └── configure-https-route53.sh
├── ecs-task-definition.json
└── Dockerfile
```
