Create governing principles for GhostCart demonstrating Agent Payments Protocol version 0.1 working with AWS Strands SDK.

PROTOCOL COMPLIANCE - ABSOLUTELY NON-NEGOTIABLE:
Follow AP2 specification exactly from https://ap2-protocol.org/specification/ and reference implementation at https://github.com/google-agentic-commerce/AP2. Every mandate must match official JSON schemas. Intent Mandate, Cart Mandate, Payment Mandate structures cannot deviate. Mandate chain validation mandatory for all transactions. In human-not-present flow Cart MUST reference Intent ID. Role separation per AP2 is sacred - shopping agents never touch raw payment data, only tokenized credentials from Credentials Provider. Payment network never sees product details, only payment mandates.

PAYMENT AGENT REUSABILITY - CORE INNOVATION:
Payment Agent must be 100 percent use-case agnostic. Zero coupling to GhostCart domain. No knowledge of products, categories, pricing, merchants, or UI. Works purely with AP2 mandate primitives as input and output. Any developer anywhere should extract payment_agent folder, drop into travel booking app or subscription service or B2B procurement system, pass valid AP2 mandates, and it just works. No modifications needed. This reusability proves AP2 protocol works beyond single use case. This is what we are demonstrating to hackathon judges.

AGENT ARCHITECTURE - STRANDS PATTERNS:
AWS Strands Agents-as-Tools pattern exclusively. Supervisor Agent orchestrates, never executes. Each specialist agent has singular focus. HP Shopping Agent only does immediate purchases. HNP Delegate Agent only does monitoring setup. Payment Agent only processes mandates. LLM makes all routing decisions by analyzing user intent linguistically. No hardcoded if statements checking for keywords. Let Claude Sonnet 4.5 via Bedrock reason about what user wants. Payment Agent is Strands agent invoked as tool by specialists, not separate microservice.

TRANSPARENCY - USER SEES EVERYTHING:
Complete cryptographic audit trail for every transaction visible to user. Intent to Cart to Payment to Transaction flow must be visualizable. Signature validation status shown with visual indicators. Real-time streaming of agent thoughts and actions via Server-Sent Events. User explicitly approves autonomous actions through mandate signing with clear consent flow. Never hide what agents are doing. No black boxes. No "trust me it worked". Show the receipts.

MOCK EVERYTHING - NO EXTERNAL DEPENDENCIES:
All external services mocked following AP2 role architecture. Merchant API mocked locally returning product data. Credentials Provider mocked returning tokenized payment methods. Payment Processor mocked returning authorizations and declines. Zero actual payment processing. Zero external API calls. Zero network dependencies. Mocks must feel realistic enough to convince judges but clearly marked as demo. Include failure scenarios not just happy path. Payment declines. Out of stock products. Expired mandates. Network timeouts.

TECHNICAL FOUNDATION:
All monetary values in USD for consistency. Backend Python 3.11+ with FastAPI. Frontend React with Vite and Tailwind. SQLite for persistence, no PostgreSQL complexity for hackathon. APScheduler with SQLite job store for monitoring that survives restarts. Server-Sent Events for real-time streaming not websockets. Cryptographic signatures for demo using HMAC-SHA256 clearly labeled as mocking production ECDSA with hardware-backed device keys per AP2 specification.

CODE QUALITY STANDARDS:
All errors must return AP2 standard error codes. ap2:mandate:chain_invalid, ap2:mandate:signature_invalid, ap2:mandate:expired, ap2:mandate:constraints_violated, ap2:credentials:unavailable, ap2:payment:declined. Every Python function has type hints. Every function has docstring explaining AP2 compliance rationale for design decisions. Use Pydantic models for all mandate structures ensuring runtime validation. No commented-out code. No print statements. Use proper logging.

GOVERNANCE:
These principles override all implementation details and convenience shortcuts. Payment Agent reusability is immutable - if it imports anything from shopping agents or UI, it fails. AP2 compliance is immutable - if mandates do not match specification, it fails. Strands architecture is immutable - if we hardcode routing logic, it fails. Any deviation from these principles requires updating this constitution first with explicit justification for why deviation necessary and how core principles still maintained.