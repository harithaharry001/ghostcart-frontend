# Implementation Plan: GhostCart - AP2 Protocol Demonstration

**Branch**: `002-read-the-specification` | **Date**: 2025-10-17 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-read-the-specification/spec.md`

## Summary

Build GhostCart to demonstrate Agent Payments Protocol (AP2) v0.1 interoperability with AWS Strands SDK. The system provides two purchase flows: human-present (immediate) and human-not-present (autonomous monitoring), using four Strands agents (Supervisor, HP Shopping, HNP Delegate, Payment) with complete mandate chain visualization and real-time transparency via Server-Sent Events. Key innovation: Payment Agent is 100% reusable with zero GhostCart domain coupling, proving AP2 protocol universality.

**Technical Approach**: FastAPI backend + React frontend, SQLite persistence, APScheduler for monitoring jobs, AWS Bedrock for Claude Sonnet 4.5, HMAC-SHA256 signatures (mocking production ECDSA), all services mocked locally per AP2 role architecture.

## Technical Context

**Language/Version**: Python 3.11+ (backend), JavaScript ES2022+ (frontend)
**Primary Dependencies**: FastAPI 0.100+, React 18+, Pydantic v2, AWS Strands SDK, boto3 (Bedrock), APScheduler 3.10+, SQLAlchemy 2.0+
**Storage**: SQLite (mandates, monitoring_jobs, transactions, sessions tables)
**Testing**: pytest (backend), Vitest (frontend), contract tests for AP2 schema compliance
**Target Platform**: Linux/macOS server (development), laptop browser (primary UI target)
**Project Type**: Web application (FastAPI backend + React/Vite frontend)
**Performance Goals**: <500ms agent response streaming, <2s monitoring checks, 10 concurrent jobs, <1s mandate chain viz load
**Constraints**: <90s HP flow completion, <60s HNP setup, <3min complete demo, 100% AP2 schema compliance, 100% job persistence across restarts
**Scale/Scope**: Hackathon demo (not production), 15 mock products, ~90% mock payment approval rate, 7-day monitoring duration

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

### ✅ Principle I: Protocol Compliance (ABSOLUTELY NON-NEGOTIABLE)

**Status**: PASS

- All mandate structures (Intent, Cart, Payment) implemented as Pydantic v2 models matching AP2 JSON schemas (see data-model.md)
- Mandate chain validation enforced: HP flow (Cart requires user sig), HNP flow (Intent requires user sig, Cart references Intent ID)
- Role separation maintained: shopping agents never access raw payment data, only tokenized credentials from mock Credentials Provider
- AP2 standard error codes used exclusively: `ap2:mandate:chain_invalid`, `ap2:mandate:signature_invalid`, `ap2:mandate:expired`, `ap2:mandate:constraints_violated`, `ap2:credentials:unavailable`, `ap2:payment:declined`

**Evidence**: See `contracts/openapi.yaml` for schema definitions, `data-model.md` for validation logic

### ✅ Principle II: Payment Agent Reusability (CORE INNOVATION)

**Status**: PASS

- Payment Agent folder (`backend/src/agents/payment_agent/`) completely self-contained
- Zero imports from parent directories: no `../agents`, no `../mocks`, no `../models`
- Only imports: Python stdlib, Pydantic, AWS Strands SDK
- Accepts only AP2 mandate primitives as input, returns only payment results
- No knowledge of products, categories, pricing, merchants, or GhostCart UI
- Validation: Import linter checks in CI, documented isolation strategy in research.md

**Evidence**: See research.md "Payment Agent Isolation Strategy" section

### ✅ Principle III: Agent Architecture (STRANDS PATTERNS)

**Status**: PASS

- Four Strands agents: Supervisor (orchestrator), HP Shopping (immediate purchase), HNP Delegate (monitoring setup), Payment Agent (mandate processing)
- Supervisor uses Claude Sonnet 4.5 via Bedrock for linguistic routing (no hardcoded keyword if-statements)
- Each specialist agent has singular focus per constitution
- Payment Agent invoked as tool by specialists (not separate microservice)
- All agents run in-process via FastAPI for hackathon simplicity

**Evidence**: See research.md "AWS Strands Agents SDK Integration" section

### ✅ Principle IV: Transparency (USER SEES EVERYTHING)

**Status**: PASS

- Complete mandate chain visualization (Intent → Cart → Payment → Transaction) with signature validation status
- Real-time agent message streaming via Server-Sent Events (agent thoughts, product results, mandate creation, payment processing)
- User explicitly approves via biometric-style signature modal with clear consent text
- Mandate chain JSON exportable ("Copy JSON", "Download Chain" buttons)
- All agent actions visible in real-time SSE stream

**Evidence**: See spec.md acceptance scenarios, openapi.yaml `/api/stream` endpoint, data-model.md "Mandate Chain Flow"

### ✅ Principle V: Mock Everything (NO EXTERNAL DEPENDENCIES)

**Status**: PASS

- Mock Merchant API: 15 products across 4 categories, search filtering, in-stock/out-of-stock mix
- Mock Credentials Provider: 2-3 tokenized payment methods per user, never raw PCI data
- Mock Payment Processor: ~90% approval rate, realistic decline reasons (insufficient funds, card expired, fraud suspected)
- Zero external HTTP calls except AWS Bedrock (LLM only)
- Failure scenarios included: payment declines, out of stock, expired mandates

**Evidence**: See research.md "Mock Services Implementation" section, data-model.md "Mock Service Data Structures"

### ✅ Principle VI: Technical Foundation

**Status**: PASS

- Backend: Python 3.11+ with FastAPI, async/await patterns
- Frontend: React 18+ with Vite, Tailwind CSS styling
- Storage: SQLite (mandates, monitoring_jobs, transactions, sessions tables)
- Scheduling: APScheduler with SQLAlchemyJobStore (persists across restarts)
- Real-time: Server-Sent Events (not WebSockets)
- LLM: Claude Sonnet 4.5 via AWS Bedrock (configurable region, model: us.anthropic.claude-sonnet-4-20250514-v1:0)
- Cryptography: HMAC-SHA256 (clearly labeled as mocking production ECDSA)
- Currency: USD only

**Evidence**: See research.md "Technology Stack Summary"

### ✅ Principle VII: Code Quality Standards

**Status**: PASS (design phase, enforced during implementation)

- All errors return AP2 standard error codes (see openapi.yaml ErrorResponse schema)
- Pydantic models ensure runtime validation for all mandate structures
- Type hints required for all Python functions (enforced by mypy in CI)
- Docstrings required explaining AP2 compliance rationale
- Structured logging with JSON format (no print statements)
- FastAPI exception handlers map to AP2 error codes

**Evidence**: See data-model.md validation logic, research.md "Exception Hierarchy"

## Project Structure

### Documentation (this feature)

```
specs/002-read-the-specification/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 output (technical decisions)
├── data-model.md        # Phase 1 output (entities, schemas, validation)
├── quickstart.md        # Phase 1 output (local development setup)
├── contracts/           # Phase 1 output (API contracts)
│   └── openapi.yaml     # REST API specification
└── tasks.md             # Phase 2 output (will be created by /speckit.tasks)
```

### Source Code (repository root)

**Selected Structure**: Option 2 (Web application)

```
backend/
├── src/
│   ├── agents/              # Strands agents with Bedrock integration
│   │   ├── supervisor.py    # Orchestrator, routes based on LLM analysis
│   │   ├── hp_shopping.py   # Human-present immediate purchases
│   │   ├── hnp_delegate.py  # Human-not-present monitoring setup
│   │   └── payment_agent/   # ← REUSABLE: Zero GhostCart coupling
│   │       ├── agent.py         # Payment agent definition
│   │       ├── tools.py         # Validation, credentials, processing
│   │       ├── models.py        # AP2 mandate Pydantic models
│   │       └── crypto.py        # HMAC signature functions
│   ├── mocks/               # AP2 role architecture mocks
│   │   ├── merchant_api.py      # Product catalog (15 products)
│   │   ├── credentials_provider.py  # Tokenized payment methods
│   │   └── payment_processor.py     # Authorization/decline simulation
│   ├── models/              # Shared Pydantic models
│   │   ├── mandates.py          # IntentMandate, CartMandate, PaymentMandate
│   │   ├── transactions.py
│   │   └── sessions.py
│   ├── services/            # Business logic
│   │   ├── mandate_service.py
│   │   ├── monitoring_service.py
│   │   ├── signature_service.py
│   │   └── scheduler.py         # APScheduler configuration
│   ├── api/                 # FastAPI routes
│   │   ├── chat.py              # POST /api/chat
│   │   ├── stream.py            # GET /api/stream (SSE)
│   │   ├── mandates.py          # POST /api/mandates/sign
│   │   ├── transactions.py      # GET /api/transactions/{id}/chain
│   │   ├── monitoring.py        # /api/monitoring/jobs endpoints
│   │   ├── products.py          # GET /api/products/search
│   │   └── payments.py          # GET /api/payment-methods
│   ├── db/                  # Database setup
│   │   ├── init_db.py           # Creates tables, indexes
│   │   └── models.py            # SQLAlchemy ORM models
│   ├── exceptions.py        # AP2 error code hierarchy
│   ├── config.py            # Environment configuration
│   └── main.py              # FastAPI app entry point
├── tests/
│   ├── contract/            # AP2 schema compliance tests
│   ├── integration/         # Agent orchestration flow tests
│   └── unit/                # Mandate validation, signature tests
├── requirements.txt
├── .env.example
└── ghostcart.db            # SQLite database (auto-created)

frontend/
├── src/
│   ├── components/
│   │   ├── ChatInterface.jsx        # Main conversation UI
│   │   ├── SignatureModal.jsx       # Biometric-style confirmation
│   │   ├── MandateChainViz.jsx      # Timeline visualization
│   │   ├── MonitoringStatusCard.jsx # Real-time job status
│   │   ├── ProductCard.jsx          # Product display
│   │   ├── CartDisplay.jsx          # Cart summary
│   │   └── NotificationBanner.jsx   # Autonomous purchase alerts
│   ├── pages/
│   │   └── Home.jsx                 # Main app page
│   ├── services/
│   │   ├── api.js                   # API client (fetch wrapper)
│   │   └── sse.js                   # EventSource connection manager
│   ├── context/
│   │   ├── SessionContext.jsx       # Session state management
│   │   └── SSEContext.jsx           # SSE connection context
│   ├── App.jsx
│   └── main.jsx
├── public/
├── index.html
├── package.json
├── vite.config.js
└── tailwind.config.js
```

**Structure Decision**: Web application structure selected because project has distinct backend (FastAPI Python) and frontend (React JavaScript) concerns. Backend serves both API endpoints and static React build in production. Payment Agent folder isolation within backend enables reusability demonstration.

## Complexity Tracking

*No constitution violations requiring justification. All design decisions align with principles.*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | N/A | N/A |

## Phase 0: Research (Completed)

**Deliverable**: `research.md` with 10 technical decisions documented

**Key Findings**:
1. AWS Strands Agents-as-Tools pattern with Claude Sonnet 4.5 via Bedrock
2. Pydantic v2 models with strict validation for AP2 compliance
3. HMAC-SHA256 signatures (labeled as mocking production ECDSA)
4. APScheduler + SQLAlchemyJobStore for persistent monitoring jobs
5. Server-Sent Events (simpler than WebSockets for unidirectional streaming)
6. Payment Agent isolation via folder boundaries and import restrictions
7. SQLite schema with 4 tables (mandates, monitoring_jobs, transactions, sessions)
8. Three mock services (Merchant API, Credentials Provider, Payment Processor)
9. REST API with 8 endpoints (chat, stream, mandates, transactions, monitoring, products, payments)
10. React component architecture with Context API for state management

**All technical unknowns resolved. No NEEDS CLARIFICATION items remain.**

## Phase 1: Design & Contracts (Completed)

**Deliverables**:
- ✅ `data-model.md` with complete AP2 mandate entities, database schema, validation logic
- ✅ `contracts/openapi.yaml` with REST API specification (8 endpoints, all request/response schemas)
- ✅ `quickstart.md` with local development setup instructions

**Key Outputs**:

1. **Data Model**:
   - AP2 Mandate Pydantic models: IntentMandate, CartMandate, PaymentMandate, Transaction
   - Database schema: 4 SQLite tables with indexes for performance
   - Mandate chain flow diagrams for HP and HNP flows
   - Validation logic ensuring AP2 compliance (signature requirements, chain links, constraints)

2. **API Contracts**:
   - OpenAPI 3.0.3 specification with 8 endpoints
   - Complete request/response schemas for all mandate types
   - AP2 error code definitions
   - SSE event types and payloads documented

3. **Quickstart Guide**:
   - Prerequisites (Python 3.11+, Node 18+, AWS Bedrock access)
   - Installation steps (backend venv, frontend npm)
   - Environment configuration (AWS credentials, demo mode, secrets)
   - Database initialization
   - Running in development and production modes
   - Testing both HP and HNP flows
   - Troubleshooting common issues
   - Performance validation against success criteria

## Constitution Re-Check (Post-Design)

**Status**: ✅ ALL PRINCIPLES VALIDATED

- Protocol Compliance: Mandate structures match AP2 schemas, validation enforced
- Payment Agent Reusability: Folder isolation verified, zero domain coupling
- Agent Architecture: Strands pattern documented, LLM routing specified
- Transparency: SSE streaming + mandate chain visualization designed
- Mock Everything: All three services specified with realistic behavior
- Technical Foundation: Stack confirmed (Python/FastAPI, React/Vite, SQLite, Bedrock, APScheduler, SSE)
- Code Quality: Error codes, type hints, docstrings, Pydantic validation all specified

**No deviations from constitution. Ready for implementation.**

## Next Steps

1. **Run `/speckit.tasks`** to generate implementation task breakdown
   - Tasks will be organized by user story (P1: HP flow, P2: HNP flow, P3: Agent routing)
   - Each task references specific files from project structure above
   - Parallelizable tasks marked with [P] flag

2. **Implementation Order** (recommended):
   - Phase 1: Setup (project structure, dependencies)
   - Phase 2: Foundational (database, Pydantic models, mock services)
   - Phase 3: User Story 1 - HP Flow (Supervisor, HP Shopping, Payment Agent)
   - Phase 4: User Story 2 - HNP Flow (HNP Delegate, monitoring jobs, autonomous purchase)
   - Phase 5: User Story 3 - Agent Routing (Supervisor refinement)
   - Phase 6: Polish (mandate chain viz, SSE reliability, error messages)

3. **Implementation Duration Estimate**:
   - Backend: 3-4 days (mandate models, agents, mock services, API endpoints)
   - Frontend: 2-3 days (components, SSE integration, mandate chain viz)
   - Testing: 1-2 days (contract tests, integration tests, end-to-end flows)
   - **Total**: 6-9 days for hackathon-ready demo

4. **Demo Preparation**:
   - Practice HP flow (target: <90 seconds)
   - Practice HNP flow setup (target: <60 seconds)
   - Prepare failure scenarios (decline, out of stock, expired mandate)
   - Verify Payment Agent extraction works (copy folder test)
   - Complete demo (both flows + mandate chain viz): <3 minutes

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Bedrock API latency during demo | Medium | High | Cache common responses, fallback prompts |
| APScheduler jobs not persisting | Low | High | Integration tests verifying restart survival |
| SSE connection drops | Medium | Medium | Automatic reconnection logic in EventSource wrapper |
| Payment Agent accidental coupling | Low | Critical | Import linter in CI, code review checklist |
| Mandate schema drift from AP2 | Low | Critical | Contract tests validating against official schemas |
| Demo exceeds 3-minute target | Medium | Medium | Script practice, time each flow, optimize agent prompts |

## Success Metrics Tracking

| Metric | Target | Validation Method |
|--------|--------|-------------------|
| SC-001: HP flow completion time | <90 seconds | Manual testing with timer |
| SC-002: HNP setup time | <60 seconds | Manual testing with timer |
| SC-003: Agent message streaming | <500ms | Network tab monitoring |
| SC-004: Monitoring check duration | <2 seconds | Backend log analysis |
| SC-005: Concurrent monitoring jobs | 10 jobs | Load testing script |
| SC-006: Complete demo duration | <3 minutes | Rehearsal with stopwatch |
| SC-007: Payment Agent reusability | 100% extraction success | Copy folder to test project, verify it works |
| SC-008: AP2 schema compliance | 100% field match | Contract tests with official schemas |
| SC-009: Job persistence | 100% survival rate | Server restart test |
| SC-010: Mandate chain viz load | <1 second | Network tab monitoring |
| SC-011: Error message clarity | 3/3 non-dev testers understand | User testing |
| SC-012: Success + failure demo | Both scenarios shown | Demo script includes decline |
| SC-013: Mandate chain traceability | 100% transactions | Audit trail validation |
| SC-014: Signature flow feedback | 1-second animation | Manual UX testing |

## Artifacts Generated

1. ✅ `research.md` - 10 technical decisions with rationale, alternatives, implementation approach
2. ✅ `data-model.md` - AP2 mandate entities, database schema, validation logic, mandate chain flows
3. ✅ `contracts/openapi.yaml` - REST API specification with 8 endpoints, complete schemas
4. ✅ `quickstart.md` - Local development setup, testing flows, troubleshooting, performance validation
5. ⏳ `tasks.md` - Will be created by `/speckit.tasks` command (next step)

**Planning Phase Complete. Ready for task generation and implementation.**
