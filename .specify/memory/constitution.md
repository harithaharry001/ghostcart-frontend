<!--
SYNC IMPACT REPORT
==================
Version Change: 0.0.0 → 1.0.0
Created: 2025-10-17

Initial constitution creation for GhostCart AP2 demonstration project.

Modified Principles: N/A (initial creation)
Added Sections:
  - Core Principles (7 principles)
  - Technical Foundation
  - Development Standards
  - Governance

Templates Status:
  ✅ plan-template.md - Constitution Check section reviewed, aligns with principles
  ✅ spec-template.md - User scenarios and requirements align with transparency principle
  ✅ tasks-template.md - Task categorization supports principle-driven development
  ⚠ commands/*.md - No command files found yet

Follow-up TODOs: None
-->

# GhostCart AP2 Constitution

## Core Principles

### I. Protocol Compliance (ABSOLUTELY NON-NEGOTIABLE)

**Mandate**: Follow AP2 specification exactly from https://ap2-protocol.org/specification/ and reference implementation at https://github.com/google-agentic-commerce/AP2. Every mandate MUST match official JSON schemas. Intent Mandate, Cart Mandate, Payment Mandate structures cannot deviate. Mandate chain validation is mandatory for all transactions. In human-not-present flow, Cart MUST reference Intent ID. Role separation per AP2 is sacred—shopping agents never touch raw payment data, only tokenized credentials from Credentials Provider. Payment network never sees product details, only payment mandates.

**Rationale**: AP2 protocol compliance is the primary demonstration objective for hackathon judges. Any deviation invalidates the demo and fails to prove interoperability. Protocol compliance enables multi-vendor ecosystems and establishes trust boundaries between payment and commerce domains.

### II. Payment Agent Reusability (CORE INNOVATION)

**Mandate**: Payment Agent MUST be 100% use-case agnostic with zero coupling to GhostCart domain. Payment Agent has no knowledge of products, categories, pricing, merchants, or UI. It works purely with AP2 mandate primitives as input and output. Any developer anywhere should extract the `payment_agent` folder, drop it into a travel booking app, subscription service, or B2B procurement system, pass valid AP2 mandates, and it just works—no modifications needed.

**Rationale**: This reusability proves AP2 protocol works beyond a single use case. This is the key innovation we are demonstrating to hackathon judges—that the payment abstraction layer is truly universal.

**Validation**: If Payment Agent imports anything from shopping agents or UI modules, it fails this principle. If domain-specific logic appears in Payment Agent code, it fails this principle.

### III. Agent Architecture (STRANDS PATTERNS)

**Mandate**: Use AWS Strands Agents-as-Tools pattern exclusively. Supervisor Agent orchestrates and never executes domain logic. Each specialist agent has singular focus: HP Shopping Agent only handles immediate purchases, HNP Delegate Agent only handles monitoring setup, Payment Agent only processes mandates. LLM (Claude Sonnet 4.5 via Bedrock) makes all routing decisions by analyzing user intent linguistically—no hardcoded if-statements checking for keywords. Let the LLM reason about what the user wants. Payment Agent is a Strands agent invoked as a tool by specialists, not a separate microservice.

**Rationale**: Strands architecture demonstrates modern agentic patterns. Linguistic routing via LLM showcases AI capabilities over brittle rule-based systems. Tool-based composition enables modular, testable agent design.

**Validation**: If routing logic contains keyword matching if-statements, it fails this principle. If agents execute tasks outside their singular domain, it fails this principle.

### IV. Transparency (USER SEES EVERYTHING)

**Mandate**: Complete cryptographic audit trail for every transaction visible to user. Intent → Cart → Payment → Transaction flow MUST be visualizable. Signature validation status shown with visual indicators. Real-time streaming of agent thoughts and actions via Server-Sent Events. User explicitly approves autonomous actions through mandate signing with clear consent flow. Never hide what agents are doing. No black boxes. No "trust me it worked". Show the receipts.

**Rationale**: Transparency builds user trust in autonomous agents. Cryptographic audit trails enable dispute resolution and debugging. Explicit consent for autonomous actions addresses ethical AI concerns.

**Validation**: If user cannot trace mandate chain from intent to payment, it fails this principle. If agent actions occur without streamed visibility, it fails this principle.

### V. Mock Everything (NO EXTERNAL DEPENDENCIES)

**Mandate**: All external services mocked following AP2 role architecture. Merchant API mocked locally returning product data. Credentials Provider mocked returning tokenized payment methods. Payment Processor mocked returning authorizations and declines. Zero actual payment processing. Zero external API calls. Zero network dependencies. Mocks MUST feel realistic enough to convince judges but be clearly marked as demo. Include failure scenarios, not just happy path: payment declines, out of stock products, expired mandates, network timeouts.

**Rationale**: Mocked dependencies ensure demo reliability without external service failures. Demonstrates AP2 role separation clearly when all roles are locally implemented. Reduces demo complexity and setup requirements.

**Validation**: If code makes external HTTP calls (except to local Bedrock), it fails this principle. If mocks lack failure scenarios, it fails completeness requirements.

### VI. Technical Foundation

**Mandate**: All monetary values in USD for consistency. Backend Python 3.11+ with FastAPI. Frontend React with Vite and Tailwind. SQLite for persistence—no PostgreSQL complexity for hackathon. APScheduler with SQLite job store for monitoring that survives restarts. Server-Sent Events for real-time streaming, not websockets. Cryptographic signatures for demo using HMAC-SHA256, clearly labeled as mocking production ECDSA with hardware-backed device keys per AP2 specification.

**Rationale**: Technology choices balance modern tooling with hackathon time constraints. SQLite reduces operational complexity. SSE provides simpler real-time streaming than websockets for demo purposes.

### VII. Code Quality Standards

**Mandate**: All errors MUST return AP2 standard error codes: `ap2:mandate:chain_invalid`, `ap2:mandate:signature_invalid`, `ap2:mandate:expired`, `ap2:mandate:constraints_violated`, `ap2:credentials:unavailable`, `ap2:payment:declined`. Every Python function has type hints. Every function has docstring explaining AP2 compliance rationale for design decisions. Use Pydantic models for all mandate structures ensuring runtime validation. No commented-out code. No print statements. Use proper logging with structured format.

**Rationale**: Standardized error codes enable interoperability debugging. Type hints and docstrings improve code maintainability and review efficiency. Pydantic ensures mandate validation happens at runtime, not just in tests.

**Validation**: If errors return non-AP2 codes, they fail interoperability. If functions lack type hints or docstrings, they fail review. If print statements exist in committed code, they fail quality gate.

## Technical Foundation

**Language**: Python 3.11+ for backend, JavaScript (React) for frontend
**Backend Framework**: FastAPI with async/await patterns
**Frontend Framework**: React with Vite build tooling, Tailwind CSS for styling
**Storage**: SQLite with migrations (no PostgreSQL)
**Scheduling**: APScheduler with SQLite job store
**Real-time Communication**: Server-Sent Events (SSE), not WebSockets
**LLM Integration**: Claude Sonnet 4.5 via AWS Bedrock
**Agent Framework**: AWS Strands Agents-as-Tools pattern
**Cryptography**: HMAC-SHA256 for demo (mocking production ECDSA)
**Data Validation**: Pydantic models for all AP2 mandate structures
**Logging**: Structured logging with JSON format, no print statements

## Development Standards

### Error Handling
All errors MUST use AP2 standard error codes:
- `ap2:mandate:chain_invalid` - Mandate chain validation failed
- `ap2:mandate:signature_invalid` - Signature verification failed
- `ap2:mandate:expired` - Mandate past expiration time
- `ap2:mandate:constraints_violated` - Constraint validation failed
- `ap2:credentials:unavailable` - Payment credentials not accessible
- `ap2:payment:declined` - Payment processor declined transaction

### Code Documentation
- Every function MUST have type hints
- Every function MUST have docstring explaining AP2 compliance rationale
- Every agent interaction MUST be logged with structured format
- Every mandate transformation MUST document which AP2 role performs it

### Testing Requirements
- Unit tests for mandate validation logic
- Integration tests for agent orchestration flows
- Mock failure scenarios: declines, timeouts, invalid signatures
- Contract tests ensuring mandate schemas match AP2 specification

### Repository Structure
```
backend/
├── src/
│   ├── agents/              # Strands agents
│   │   ├── supervisor.py    # Orchestrator only
│   │   ├── hp_shopping.py   # Human-present shopping
│   │   ├── hnp_delegate.py  # Human-not-present delegate
│   │   └── payment_agent/   # REUSABLE - no domain coupling
│   ├── mocks/               # AP2 role mocks
│   │   ├── merchant_api.py
│   │   ├── credentials_provider.py
│   │   └── payment_processor.py
│   ├── models/              # Pydantic mandate models
│   ├── services/
│   └── api/
└── tests/

frontend/
├── src/
│   ├── components/
│   ├── pages/
│   └── services/
└── tests/
```

## Governance

These principles override all implementation details and convenience shortcuts.

**Immutable Requirements**:
1. **Payment Agent Reusability**: If it imports anything from shopping agents or UI, it fails.
2. **AP2 Compliance**: If mandates do not match specification, it fails.
3. **Strands Architecture**: If we hardcode routing logic instead of LLM-based reasoning, it fails.

**Amendment Process**:
Any deviation from these principles requires updating this constitution first with:
1. Explicit justification for why deviation is necessary
2. Documentation of how core principles are still maintained
3. Approval recorded in constitution version history

**Complexity Justification**:
If implementation violates simplicity (e.g., adding unnecessary abstractions), it MUST be documented in plan.md Complexity Tracking table with:
- What violation occurred
- Why simpler approach was insufficient
- Which principle required the complexity

**Compliance Review**:
All pull requests and specifications MUST verify compliance with:
- Protocol Compliance: Mandates match AP2 schemas
- Reusability: Payment Agent has zero domain coupling
- Architecture: Strands patterns correctly implemented
- Transparency: User can trace all mandate chains
- Quality: Error codes, type hints, docstrings present

**Version**: 1.0.0 | **Ratified**: 2025-10-17 | **Last Amended**: 2025-10-17
