# Tasks: GhostCart - AP2 Protocol Demonstration

**Input**: Design documents from `/specs/002-read-the-specification/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/openapi.yaml

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, Setup, Foundation)
- Include exact file paths in descriptions

/## Path Conventions
- **Backend**: `backend/src/`
- **Frontend**: `frontend/src/`
- **Database**: `backend/ghostcart.db` (SQLite)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure per plan.md

- [ ] T001 [P] [Setup] Create backend directory structure: `backend/src/{agents,mocks,models,services,api,db,}`, `backend/tests/{contract,integration,unit}`, create `backend/requirements.txt`, `backend/.env.example`
- [ ] T002 [P] [Setup] Create frontend directory structure: `frontend/src/{components,pages,services,context}`, `frontend/public/`, create `frontend/package.json`, `frontend/vite.config.js`, `frontend/tailwind.config.js`
- [ ] T003 [Setup] Initialize backend Python dependencies in `backend/requirements.txt`: fastapi>=0.100.0, uvicorn[standard]>=0.23.0, pydantic>=2.0.0, sqlalchemy>=2.0.0, apscheduler>=3.10.0, boto3>=1.28.0, python-multipart, aiosqlite
- [ ] T004 [Setup] Initialize frontend Node dependencies in `frontend/package.json`: react@18+, react-dom@18+, vite@4+, tailwindcss@3+, autoprefixer, postcss
- [ ] T005 [P] [Setup] Create backend configuration module `backend/src/config.py`: load environment variables (AWS_REGION, AWS_BEDROCK_MODEL_ID, DEMO_MODE, LOG_LEVEL, secrets, database path, server host/port)
- [ ] T006 [P] [Setup] Create frontend environment config `frontend/.env`: VITE_API_BASE_URL=http://localhost:8000/api
- [ ] T007 [P] [Setup] Configure Tailwind CSS in `frontend/tailwind.config.js`: custom color scheme (blue primary, green success, orange warning, red error, gray neutrals), animation utilities
- [ ] T008 [P] [Setup] Create frontend API client service `frontend/src/services/api.js`: fetch wrapper with base URL, error handling, JSON parsing

**Checkpoint**: Project structure and dependencies installed

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T009 [Foundation] Create database initialization script `backend/src/db/init_db.py`: create tables (mandates, monitoring_jobs, transactions, sessions) with indexes per data-model.md schema
- [ ] T010 [Foundation] Create SQLAlchemy ORM models in `backend/src/db/models.py`: MandateModel, MonitoringJobModel, TransactionModel, SessionModel matching database schema
- [ ] T011 [P] [Foundation] Create Pydantic SignatureObject model in `backend/src/models/signatures.py`: algorithm, signer_identity, timestamp, signature_value with validation rules
- [ ] T012 [P] [Foundation] Create Pydantic IntentMandate model in `backend/src/models/mandates.py`: mandate_id, mandate_type, user_id, scenario, product_query, constraints, expiration, signature with AP2 validation rules
- [ ] T013 [P] [Foundation] Create Pydantic CartMandate model in `backend/src/models/mandates.py`: mandate_id, items, total, merchant_info, delivery_estimate_days, references, signature with nested types (LineItem, TotalObject, MerchantInfo)
- [ ] T014 [P] [Foundation] Create Pydantic PaymentMandate model in `backend/src/models/mandates.py`: mandate_id, references, amount_cents, payment_credentials, human_not_present, timestamp, signature
- [ ] T015 [P] [Foundation] Create Pydantic Transaction model in `backend/src/models/transactions.py`: transaction_id, mandate IDs, user_id, status, authorization_code, decline_reason, amount_cents
- [ ] T016 [P] [Foundation] Create AP2 exception hierarchy in `backend/src/exceptions.py`: AP2Error base class, specific exceptions (ChainInvalidError, SignatureInvalidError, ExpiredError, ConstraintsViolatedError, CredentialsUnavailableError, PaymentDeclinedError) with error codes
- [ ] T017 [Foundation] Create signature service in `backend/src/services/signature_service.py`: HMAC-SHA256 signing function, verification function with constant-time comparison, three secret keys (user, agent, payment agent)
- [ ] T018 [P] [Foundation] Create mock Merchant API in `backend/src/mocks/merchant_api.py`: 15-product catalog across 4 categories (Electronics, Kitchen, Fashion, Home), search function by query and max_price, include Philips HD7462 Coffee Maker (~$70) and Apple AirPods Pro (~$250)
- [ ] T019 [P] [Foundation] Create mock Credentials Provider in `backend/src/mocks/credentials_provider.py`: return 2-3 tokenized payment methods per user (tok_visa_4242, tok_mc_5555, tok_amex_3782), never raw card data
- [ ] T020 [P] [Foundation] Create mock Payment Processor in `backend/src/mocks/payment_processor.py`: authorization function with ~90% approval rate, realistic decline reasons (insufficient funds, card expired, declined by issuer, fraud suspected), return transaction_id and authorization_code on success
- [ ] T021 [Foundation] Create FastAPI app initialization in `backend/src/main.py`: create FastAPI app, add CORS middleware (allow localhost:5173), include routers (will be added per story), mount frontend build directory, add exception handlers for AP2 errors
- [ ] T022 [Foundation] Configure AWS Bedrock client in `backend/src/services/bedrock_client.py`: initialize boto3 Bedrock client with configurable region (defaults from config), model ID us.anthropic.claude-sonnet-4-20250514-v1:0, connection test function
- [ ] T023 [P] [Foundation] Create SSE event manager in `backend/src/services/sse_manager.py`: session-based event queue, broadcast function by session_id, event formatting (event type + JSON data payload)
- [ ] T024 [Foundation] Create SSE streaming endpoint in `backend/src/api/stream.py`: GET /api/stream with session_id query param, StreamingResponse with text/event-stream media type, generator yielding events from event manager

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Human-Present Immediate Purchase (Priority: P1) 🎯 MVP

**Goal**: Complete immediate purchase flow from search through transaction with mandate chain visualization

**Independent Test**: User searches for product, selects item, approves cart with signature, payment processes, mandate chain displays with Intent (context-only), Cart (user signed), Payment (agent signed), Transaction

### Backend Implementation for User Story 1

- [X] T025 [P] [US1] Create Payment Agent isolation structure: `backend/src/agents/payment_agent/` folder with `__init__.py`, ensure ZERO imports from parent directories
- [X] T026 [P] [US1] Create Payment Agent Pydantic models in `backend/src/agents/payment_agent/models.py`: re-define IntentMandate, CartMandate, PaymentMandate with only Python stdlib + Pydantic imports (no `from src.models`)
- [X] T027 [P] [US1] Create Payment Agent crypto module in `backend/src/agents/payment_agent/crypto.py`: signature verification using HMAC-SHA256 with secret from environment
- [X] T028 [US1] Create Payment Agent validation tools in `backend/src/agents/payment_agent/tools.py`: validate_hp_chain (verify Cart user signature, amounts match), validate_hnp_chain (verify Intent user signature, Cart agent signature, constraints not violated, Intent not expired), retrieve_credentials (call mock provider), process_payment (call mock processor) - **Updated with @tool decorators for Strands SDK**
- [X] T029 [US1] Create Payment Agent definition in `backend/src/agents/payment_agent/agent.py`: Strands Agent with tools from tools.py, system prompt emphasizing AP2 compliance and domain independence, tool calling for HP flow mandate processing - **Implemented with Strands SDK (BedrockModel + Agent)**
- [X] T030 [P] [US1] Create HP Shopping Agent in `backend/src/agents/hp_shopping_strands.py`: Strands Agent with system prompt for immediate purchase, tools for product search, cart creation, payment agent invocation, mandate signature requests - **Implemented with Strands SDK** (old hp_shopping.py removed)
- [X] T031 [US1] Create mandate service in `backend/src/services/mandate_service.py`: create_intent_mandate (HP scenario with optional signature), create_cart_mandate (requires user signature for HP), create_payment_mandate (payment agent signature), store in database, update with transaction_id
- [X] T032 [US1] Create transaction service in `backend/src/services/transaction_service.py`: create_transaction (links mandates, stores authorization or decline result), get_transaction_chain (retrieves Intent, Cart, Payment, Transaction by transaction_id)
- [X] T033 [US1] Create products search endpoint in `backend/src/api/products.py`: GET /api/products/search with query and max_price params, calls mock merchant API
- [X] T034 [US1] Create payment methods endpoint in `backend/src/api/payments.py`: GET /api/payment-methods with user_id param, calls mock credentials provider
- [X] T035 [US1] Create mandate signing endpoint in `backend/src/api/mandates.py`: POST /api/mandates/sign with mandate_id, mandate_type, user_id, creates signature using signature service, updates mandate in database, returns signed mandate + signature
- [X] T036 [US1] Create transactions endpoint in `backend/src/api/transactions.py`: GET /api/transactions/{transaction_id}/chain, calls transaction service to retrieve complete mandate chain
- [X] T037 [US1] Create HP chat handler in `backend/src/api/chat.py`: POST /api/chat with message and session_id, invokes HP Shopping Agent, streams events via SSE manager, returns response with flow_type="hp" - **Updated to use Strands SDK agents**

### Frontend Implementation for User Story 1

- [X] T038 [P] [US1] Create SSE connection service in `frontend/src/services/sse.js`: EventSource wrapper with reconnection logic, event handler registration, session_id management
- [X] T039 [P] [US1] Create SessionContext in `frontend/src/context/SessionContext.jsx`: session_id state, user_id state, current_flow_type state, context provider
- [X] T040 [P] [US1] Create SSEContext in `frontend/src/context/SSEContext.jsx`: EventSource connection management, event listeners, SSE state (connected, disconnected, error)
- [X] T041 [US1] Create ChatInterface component in `frontend/src/components/ChatInterface.jsx`: message history display, input field, send button, integrates with SessionContext, displays streaming SSE events (agent thoughts, product results, payment status)
- [X] T042 [P] [US1] Create ProductCard component in `frontend/src/components/ProductCard.jsx`: product image, name, price, delivery estimate, stock status, select button, Tailwind styling
- [X] T043 [P] [US1] Create CartDisplay component in `frontend/src/components/CartDisplay.jsx`: line items list, subtotal/tax/shipping/total breakdown, "Approve Purchase" button (blue primary)
- [X] T044 [US1] Create SignatureModal component in `frontend/src/components/SignatureModal.jsx`: biometric-style modal with fingerprint icon, mandate summary text, confirm button, animation states (idle, scanning 1s pulse, verified green checkmark, error red X), calls POST /api/mandates/sign endpoint
- [X] T045 [US1] Create MandateChainViz component in `frontend/src/components/MandateChainViz.jsx`: timeline visualization with connected boxes (Intent gray "Context Only", Cart green "User Signed", Payment agent signed, Transaction status badge), expandable boxes showing JSON, tooltips explaining AP2 flow, "Copy JSON" and "Download Chain" buttons
- [X] T046 [US1] Create Home page in `frontend/src/pages/Home.jsx`: integrates ChatInterface, ProductCard grid, CartDisplay, SignatureModal, MandateChainViz, orchestrates HP flow based on SSE events
- [X] T047 [US1] Create App component in `frontend/src/App.jsx`: SessionContext provider, SSEContext provider, renders Home page, Tailwind CSS import

**Checkpoint**: User Story 1 (HP flow) is fully functional - search, cart, signature, payment, mandate chain visualization work end-to-end

---

## Phase 4: User Story 2 - Human-Not-Present Autonomous Monitoring (Priority: P2)

**Goal**: Setup autonomous monitoring with constraints, background job checks conditions, autonomous purchase when met, user notification

**Independent Test**: User sets monitoring request with price/delivery constraints, signs Intent pre-authorization, monitoring job runs in background, conditions met triggers autonomous purchase without user interaction, notification displays with mandate chain showing Intent (user signed), Cart (agent signed with Intent reference), Payment (HNP flag set)

### Backend Implementation for User Story 2

- [X] T048 [P] [US2] Create HNP Delegate Agent in `backend/src/agents/hnp_delegate_strands.py`: Strands Agent with system prompt for monitoring setup, tools for constraint extraction, Intent creation, monitoring job scheduling, expiration handling (old hnp_delegate.py removed)
- [X] T049 [US2] Create APScheduler configuration in `backend/src/services/scheduler.py`: BackgroundScheduler with SQLAlchemyJobStore backed by SQLite, job function for monitoring checks, start/stop lifecycle management
- [X] T050 [US2] Create monitoring service in `backend/src/services/monitoring_service.py`: create_monitoring_job (creates Intent mandate, schedules APScheduler job with interval trigger, stores in monitoring_jobs table), check_conditions (queries mock merchant API, evaluates price and delivery constraints), trigger_autonomous_purchase (creates Cart with agent signature, references Intent ID, validates constraints not exceeded, invokes Payment Agent with HNP flag), cancel_job (deactivates and removes from scheduler)
- [X] T051 [US2] Update mandate service in `backend/src/services/mandate_service.py`: add create_intent_mandate for HNP scenario (requires user signature, constraints, expiration), add create_cart_mandate for HNP scenario (agent signature, references Intent ID), update create_payment_mandate to set human_not_present flag when HNP
- [X] T052 [US2] Update Payment Agent tools in `backend/src/agents/payment_agent/tools.py`: enhance validate_hnp_chain to verify Intent user signature, Cart agent signature, Cart references Intent ID, constraints not violated (price, delivery), Intent not expired, human_not_present flag set
- [X] T053 [US2] Create monitoring endpoints in `backend/src/api/monitoring.py`: GET /api/monitoring/jobs with user_id query param (lists all jobs with status), DELETE /api/monitoring/jobs/{job_id} (cancels active job)
- [X] T054 [US2] Update chat endpoint in `backend/src/api/chat.py`: add HNP routing logic, invoke HNP Delegate Agent when monitoring intent detected, return flow_type="hnp"
- [X] T055 [US2] Integrate scheduler startup in `backend/src/main.py`: start APScheduler on app startup, shutdown on app shutdown, ensure existing jobs resume from database

### Frontend Implementation for User Story 2

- [X] T056 [P] [US2] Create MonitoringStatusCard component in `frontend/src/components/MonitoringStatusCard.jsx`: displays "Monitoring Active" status, product name, check frequency, constraints (price/delivery), expiration countdown, last check timestamp, current price, status reason ("conditions not met - price too high"), "Cancel Monitoring" button (calls DELETE endpoint)
- [X] T057 [P] [US2] Create NotificationBanner component in `frontend/src/components/NotificationBanner.jsx`: large notification for autonomous purchase complete, displays product name, price paid, original authorization date and constraints, transaction ID, "View Details" and "View Chain" buttons, dismissible
- [X] T058 [US2] Update SignatureModal component in `frontend/src/components/SignatureModal.jsx`: add HNP warning mode with orange alert text "You are authorizing autonomous purchase. The agent will buy automatically when conditions are met without asking you again.", different header text for Intent vs Cart signing
- [X] T059 [US2] Update MandateChainViz component in `frontend/src/components/MandateChainViz.jsx`: add HNP flow visualization, Intent box with green "User Signed - Pre-Authorization" header, Cart box with blue "Agent Signed - Autonomous Action" header and robot icon, display "References Intent ID" in Cart box, Payment box shows "Human Not Present Flag Set" badge
- [X] T060 [US2] Update Home page in `frontend/src/pages/Home.jsx`: integrate MonitoringStatusCard (displayed when monitoring active), integrate NotificationBanner (displayed when autonomous purchase completes), handle HNP flow orchestration based on SSE events (monitoring setup, background checks, autonomous purchase)

**Checkpoint**: User Story 2 (HNP flow) is fully functional - monitoring setup with Intent signature, background jobs run and persist across restarts, autonomous purchase when conditions met, notifications work

---

## Phase 5: User Story 3 - Intelligent Agent Routing (Priority: P3)

**Goal**: Supervisor agent uses LLM reasoning to route user messages to appropriate specialist agent (HP Shopping or HNP Delegate) based on linguistic analysis, asks clarifying questions for ambiguous requests

**Independent Test**: Send various phrasings of immediate purchase intents (present tense, no conditionals) and verify routing to HP Shopping Agent, send monitoring intents (future action, conditional logic) and verify routing to HNP Delegate Agent, send ambiguous requests and verify clarifying questions before routing

### Backend Implementation for User Story 3

- [X] T061 [US3] Create Supervisor Agent in `backend/src/agents/supervisor_strands.py`: Strands Agent with Claude Sonnet 4.5 via Bedrock, system prompt emphasizing linguistic analysis for intent detection (immediate vs monitoring vs ambiguous), tools for routing to HP Shopping Agent and HNP Delegate Agent, clarifying question generation for ambiguous requests - **COMPLETED: Implemented with Strands SDK agents-as-tools pattern, HP and HNP agents wrapped as @tool decorated functions**
- [X] T062 [US3] Update chat endpoint in `backend/src/api/chat.py`: replace direct agent invocation with Supervisor Agent orchestration, Supervisor analyzes message and routes to specialist (HP Shopping for immediate, HNP Delegate for monitoring), if ambiguous return flow_type="clarification" with clarifying question - **COMPLETED: Supervisor properly invokes specialist agents, flow_type detection from tool calls, SSE events for transparency**
- [X] T063 [US3] Add session management in `backend/src/services/session_service.py`: create_session (generate session_id, store in sessions table), update_session (update last_activity_at, store context_data JSON), get_session (retrieve session for continuity), save conversation history for multi-turn clarifications

### Frontend Implementation for User Story 3

- [ ] T064 [US3] Update ChatInterface component in `frontend/src/components/ChatInterface.jsx`: handle clarification responses from Supervisor (display options or follow-up questions), display agent routing messages ("Routing to shopping assistant" vs "Routing to monitoring assistant"), maintain conversation history across clarifications

**Checkpoint**: User Story 3 (agent routing) is fully functional - Supervisor correctly routes based on linguistic analysis, clarifying questions work for ambiguous requests, no hardcoded keyword matching

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories and demo preparation

- [ ] T065 [P] [Polish] Add structured logging across all services in `backend/src/`: JSON format logs with correlation IDs (session_id, transaction_id), separate loggers (mandate_ops, signature_ops, payment_ops, scheduler_ops, errors), log levels per config
- [ ] T066 [P] [Polish] Add error handling polish in `backend/src/main.py`: FastAPI exception handlers map AP2 errors to ErrorResponse schema, log all errors with stack traces, return user-friendly error messages
- [ ] T067 [P] [Polish] Create Payment Agent README in `backend/src/agents/payment_agent/README.md`: document isolation strategy, import restrictions, extraction instructions, reusability demonstration for judges
- [ ] T068 [Polish] Add demo mode accelerated monitoring in `backend/src/services/scheduler.py`: when DEMO_MODE=true use 30-second intervals instead of 5 minutes, document in quickstart.md
- [ ] T069 [P] [Polish] Frontend error handling in `frontend/src/components/`: display user-friendly error messages from API, retry buttons for transient errors, handle SSE connection drops with automatic reconnection
- [ ] T070 [P] [Polish] Frontend performance optimization: lazy load MandateChainViz component, optimize SSE event handling to prevent unnecessary re-renders, add loading states during API calls
- [ ] T071 [Polish] Create demo data seed script in `backend/src/db/seed_demo_data.py`: pre-populate products including spec examples (Coffee Maker $69, AirPods $250), demo user with payment methods, test both success and decline payment scenarios
- [ ] T072 [Polish] Validation against quickstart.md in `specs/002-read-the-specification/quickstart.md`: verify setup instructions work, test HP flow completion <90s (SC-001), test HNP setup <60s (SC-002), verify agent messages stream <500ms (SC-003), verify monitoring checks <2s (SC-004), verify 10 concurrent jobs work (SC-005), verify complete demo <3min (SC-006)
- [ ] T073 [P] [Polish] Payment Agent reusability validation: copy `backend/src/agents/payment_agent/` to test project, verify zero GhostCart imports, confirm it works with different commerce scenario (SC-007)
- [ ] T074 [P] [Polish] AP2 schema compliance validation: contract tests validating IntentMandate, CartMandate, PaymentMandate match official AP2 JSON schemas with 100% field compliance (SC-008)
- [ ] T075 [Polish] Server restart persistence test: start monitoring job, restart backend server, verify job resumes and completes purchase (SC-009)
- [ ] T076 [P] [Polish] Frontend polish: add 1-second fingerprint scanning animation (SC-014), verify mandate chain loads <1s (SC-010), test error messages with 3 non-dev users (SC-011)
- [ ] T077 [Polish] Demo preparation: practice HP flow (target <90s), practice HNP flow setup (target <60s), prepare failure scenarios (payment decline, out of stock, expired mandate), verify Payment Agent extraction demo, rehearse complete demo (both flows + mandate chain viz, target <3min)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational phase completion
- **User Story 2 (Phase 4)**: Depends on Foundational phase completion (can run in parallel with US1 with separate team)
- **User Story 3 (Phase 5)**: Depends on Foundational phase completion + User Story 1 and 2 agents (Supervisor needs specialists to route to)
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories - MVP!
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Independent of US1 but integrates Payment Agent from US1
- **User Story 3 (P3)**: Requires US1 and US2 specialist agents to exist for routing

### Within Each User Story

- Backend tasks generally before frontend (models/services before UI)
- Payment Agent isolation (T025-T029) before HP Shopping Agent (T030)
- Services before endpoints
- Frontend Context providers before components that use them
- Core components before page integration

### Parallel Opportunities

**Phase 1 Setup**: T001, T002 (different directories), T005-T008 (different files)

**Phase 2 Foundational**: T011-T015 (Pydantic models), T018-T020 (mock services), T023-T024 (SSE) can all run in parallel

**User Story 1 Backend**: T025-T027 (Payment Agent), T030 (HP Shopping Agent), T031-T032 (services), T033-T036 (endpoints) have some parallelization opportunities for different files

**User Story 1 Frontend**: T038-T040 (contexts), T042-T043 (components) can run in parallel

**User Story 2**: T048-T049 can run in parallel with T056-T057 (backend vs frontend)

**Polish**: Many tasks (T065-T067, T069-T070, T073-T074, T076) are independent and can run in parallel

---

## Parallel Example: Foundational Phase

```bash
# Launch all Pydantic models together:
Task T011: "Create Pydantic SignatureObject model"
Task T012: "Create Pydantic IntentMandate model"
Task T013: "Create Pydantic CartMandate model"
Task T014: "Create Pydantic PaymentMandate model"
Task T015: "Create Pydantic Transaction model"

# Launch all mock services together:
Task T018: "Create mock Merchant API"
Task T019: "Create mock Credentials Provider"
Task T020: "Create mock Payment Processor"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T008)
2. Complete Phase 2: Foundational (T009-T024) - CRITICAL
3. Complete Phase 3: User Story 1 (T025-T047)
4. **STOP and VALIDATE**: Test HP flow end-to-end (search → cart → signature → payment → mandate chain)
5. Demo ready with core purchase flow

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready (T001-T024)
2. Add User Story 1 → Test independently → Deploy/Demo MVP! (T025-T047)
3. Add User Story 2 → Test independently → Deploy/Demo with autonomous monitoring (T048-T060)
4. Add User Story 3 → Test independently → Deploy/Demo with intelligent routing (T061-T064)
5. Polish → Final demo preparation (T065-T077)

### Parallel Team Strategy

With multiple developers after Foundational phase completes:

**Team allocation**:
- Developer A: User Story 1 Backend (T025-T037)
- Developer B: User Story 1 Frontend (T038-T047)
- Developer C: User Story 2 (T048-T060) - starts after T025-T029 complete (needs Payment Agent)
- Developer D: Polish tasks (can start anytime)

---

## Task Summary

**Total Tasks**: 77 tasks
- Phase 1 Setup: 8 tasks
- Phase 2 Foundational: 16 tasks (BLOCKING)
- Phase 3 User Story 1 (P1): 23 tasks (MVP)
- Phase 4 User Story 2 (P2): 13 tasks
- Phase 5 User Story 3 (P3): 4 tasks
- Phase 6 Polish: 13 tasks

**Parallel Opportunities**: ~30 tasks marked [P] can run concurrently with other tasks

**MVP Scope** (Minimum for hackathon demo):
- Phases 1-3 (T001-T047): Setup + Foundational + User Story 1
- Result: Working HP purchase flow with mandate chain visualization
- Time estimate: 3-4 days for backend + 2 days for frontend = 5-6 days

**Full Feature Scope**:
- All phases (T001-T077): Complete GhostCart with HP, HNP, routing, polish
- Time estimate: 6-9 days per plan.md

---

## Notes

- [P] tasks = different files, no dependencies within same phase
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Payment Agent isolation (T025-T029) is CRITICAL for Constitution Principle II
- Tests are not explicitly included per spec - validation happens via quickstart.md scenarios
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Focus: MVP first (User Story 1), then incremental delivery of User Stories 2 and 3
