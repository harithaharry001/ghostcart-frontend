Implement GhostCart using the following technical stack and architectural decisions.

TECHNOLOGY STACK:
Backend: Python 3.11+ with FastAPI web framework
Frontend: React 18+ with Vite build tool and Tailwind CSS for styling
AI Agents: AWS Strands Agents SDK with Claude Sonnet 4.5 via AWS Bedrock (model: us.anthropic.claude-sonnet-4-20250514-v1:0, region: configurable via environment)
Database: SQLite for local persistence
Background Jobs: APScheduler with SQLAlchemyJobStore for persistence across restarts
Real-time Communication: Server-Sent Events not WebSockets
Cryptographic Signatures: HMAC-SHA256 using Python hmac and hashlib modules for demo purposes, clearly labeled as mocking production ECDSA with hardware-backed keys
Data Validation: Pydantic v2 models for all mandate structures with strict validation
Deployment: Single monolithic process via Uvicorn server for hackathon simplicity

ARCHITECTURE PATTERN:
AWS Strands Agents-as-Tools pattern where Supervisor Agent orchestrates specialist agents. Each agent is separate Strands Agent instance with focused system prompt and tools. Payment Agent implemented as reusable Strands agent invokable as tool by other agents. All agents run in-process not as separate microservices.

AGENT ARCHITECTURE:
Four agents with clear separation of concerns:
- Supervisor Agent: Routes user messages to appropriate specialist based on linguistic analysis, has tools for HP agent, HNP agent, and clarification
- HP Shopping Agent: Handles immediate purchases with tools for product search, cart creation, and payment processing
- HNP Delegate Agent: Handles monitoring setup with tools for intent creation, job scheduling, constraint evaluation, and payment processing
- Payment Agent: Validates mandates per AP2, processes payments with tools for validation, credentials retrieval, payment mandate creation, processor submission, transaction recording

Each agent has system prompt establishing role and available tools. Supervisor uses LLM reasoning for routing not hardcoded keyword matching. Payment Agent system prompt emphasizes AP2 compliance and zero knowledge of GhostCart domain.

FOLDER STRUCTURE:
Root contains FastAPI app. agents/ folder for supervisor, HP shopping, HNP delegate implementations. payment_agent/ folder completely isolated with zero imports from parent directories proving reusability. mocks/ folder for merchant, credentials provider, payment processor implementations. frontend/ folder with React app and dist/ build output.

DATABASE DESIGN:
SQLite with four tables:
- mandates: Stores all Intent, Cart, Payment mandates with metadata including mandate type, JSON blob, user ID, transaction ID for grouping, signer identity, signature, validation status, timestamps
- monitoring_jobs: Stores background monitoring jobs with job ID, associated Intent mandate, user ID, product query, constraints as JSON, schedule information, active status, timestamps
- transactions: Stores transaction results with transaction ID, associated mandate IDs, status, authorization code or decline reason, amount, currency, timestamp
- sessions: Stores user sessions with session ID, user ID, current flow type, activity timestamps

Use appropriate indexes on frequently queried columns like user_id, transaction_id, active status.

APSCHEDULER CONFIGURATION:
Configure with SQLAlchemyJobStore backed by SQLite ensuring jobs survive server restarts. When Intent Mandate signed create scheduled job with interval trigger. Job function queries merchant for product, evaluates constraints, triggers autonomous purchase if conditions met, deactivates after completion or expiration. Support demo mode with accelerated check interval via environment variable.

CRYPTOGRAPHIC SIGNATURE APPROACH:
Use HMAC-SHA256 with shared secrets for demo labeled as production mock. Separate secrets for user, agent, payment agent signers. Signing process creates canonical JSON representation, combines with metadata into payload, computes HMAC. Verification recomputes HMAC and uses constant-time comparison. Store signature with metadata including signer identity, timestamp, algorithm identifier.

PYDANTIC MODELS:
Define three Pydantic models matching AP2 schemas:
- IntentMandate: Fields for mandate ID, user ID, product query, constraints object, scenario, expiration, maximum price, signature object
- CartMandate: Fields for mandate ID, items list, total object, merchant info, references object, signature object
- PaymentMandate: Fields for mandate ID, references object, payment details, payment credentials with tokenized data, human-not-present flag, timestamp, signature object

Configure models with strict validation ensuring all required fields present per AP2 specification.

MANDATE VALIDATION APPROACH:
Implement AP2 validation rules as reusable functions:
- Human-present flow: Verify Cart mandate structure, verify user signature on Cart, optionally validate Intent for context
- Human-not-present flow: Verify Intent structure and user signature, verify Intent not expired, verify Cart structure and agent signature, verify Cart references Intent, verify Cart complies with Intent constraints on price and delivery

Raise AP2 standard exceptions with error codes for validation failures. Use constant-time comparison for signature verification preventing timing attacks.

MOCK SERVICES DESIGN:
Implement three mock services as Python modules:
- Merchant Client: Product catalog with approximately 15 products across categories matching spec examples, search function filtering by query and price, function to retrieve product details
- Credentials Provider: Wallet simulation with 2-3 payment methods per user, function returning payment methods list, function returning tokenized credentials never raw card data
- Payment Processor: Authorization function with realistic approval rate around 90%, various decline reasons with appropriate distribution, returns transaction ID and authorization code on success or specific decline reason on failure

SERVER-SENT EVENTS DESIGN:
FastAPI endpoint returning streaming response with event-stream media type. Generator function yields formatted SSE messages. Event types for agent thoughts, product results, mandate creation, signature requests, payment processing, results, errors. Frontend connects with EventSource, parses events, updates UI state.

PAYMENT AGENT ISOLATION STRATEGY:
Organize payment_agent as completely self-contained folder with agent definition, tool implementations, Pydantic schemas, cryptographic functions. Critical constraint: Zero imports from other project folders, only Python standard library, Pydantic, and Strands SDK. This proves true reusability enabling extraction to any other commerce project.

EXCEPTION HIERARCHY:
Define base exception class for AP2 errors with error code and details. Define subclasses for each AP2 error type: chain invalid, signature invalid, mandate expired, constraints violated, credentials unavailable, payment declined. Register FastAPI exception handlers returning JSON responses with error codes and user-friendly messages.

REST API DESIGN:
Endpoints for chat interaction, SSE streaming, mandate signing, transaction chain retrieval, monitoring job management, product search, payment method retrieval. Use appropriate HTTP methods and status codes. Return JSON responses with consistent structure.

STRANDS AGENT CONFIGURATION:
Configure all agents with Claude Sonnet 4.5 model via Bedrock. Initialize Bedrock client with appropriate region and credentials from environment. Each agent has tailored system prompt defining role, available tools, and behavioral guidelines. Supervisor prompt emphasizes linguistic routing. Specialist agent prompts focus on specific workflows. Payment agent prompt emphasizes AP2 compliance and domain independence.

DEPLOYMENT STRATEGY:
Single FastAPI process serving both API and static React build. Mount static files at root enabling client-side routing. Configure Uvicorn server. Use environment variables for configuration including demo mode for accelerated monitoring, AWS credentials, log level, database path.

LOGGING STRATEGY:
Configure Python logging with multiple loggers for different concerns: mandate operations, signature operations, payment operations, scheduler operations, errors. Use appropriate log levels. Output to console for development and rotating files for production. Log key events with structured metadata for debugging and audit.

FRONTEND STATE MANAGEMENT:
Use React hooks for state. Component-local state with useState for UI concerns like modal visibility, form inputs, selections. Global state with Context API for session data, SSE connection status, monitoring jobs. Custom context providers managing EventSource connection with reconnection logic. Side effects with useEffect for API calls, subscriptions, cleanup.

REACT COMPONENT STRUCTURE:
Key components: SignatureModal for biometric-style confirmation with animation states, MandateChainViz for timeline visualization with expandable sections, MonitoringStatusCard for job status with real-time updates, ProductCard for product display with selection, CartDisplay for cart with approval, ChatInterface for messages with streaming.

Use Tailwind utility classes for styling. Implement smooth transitions and animations. Handle loading and error states. Ensure responsive layout primarily targeting laptop viewport.

QUALITY CONSIDERATIONS:
Response times under 500ms for agent interactions. Real-time updates with no perceived lag. Monitoring checks complete within 2 seconds. Support at least 10 concurrent monitoring jobs. Clear error messages without technical jargon for users. Proper error boundaries and fallback UI.

Follow this technical plan to generate task breakdown and implementation. The AI agent should determine specific implementation details within these architectural constraints.