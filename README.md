# GhostCart - AP2 Protocol Demonstration

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![React 18](https://img.shields.io/badge/react-18.2-blue.svg)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)

**GhostCart** is a full-stack demonstration of the [Agent Payments Protocol (AP2) v0.1](https://ap2-protocol.org/specification/), showcasing mandate-based payments with intelligent AI agent orchestration using AWS Bedrock and Strands SDK.

## 🎯 What is GhostCart?

GhostCart proves that AP2 achieves true interoperability by implementing the protocol with AWS Strands SDK (not just Google's reference implementation). It demonstrates two revolutionary purchase flows with intelligent multi-agent orchestration:

### 🛒 Human-Present (HP) Flow
Traditional e-commerce enhanced with AI: users search for products through natural conversation with the AI shopping assistant, review results in real-time, and approve purchases with biometric-style signatures. Every authorization is cryptographically signed and validated, creating a complete audit trail showing exactly how the purchase was authorized through the mandate chain (Intent → Cart → Payment → Transaction).

### 🤖 Human-Not-Present (HNP) Flow
The future of autonomous shopping: users pre-authorize AI agents to monitor products 24/7 and purchase automatically when conditions are met. Set your price and delivery constraints ("buy AirPods if price drops below $180 with delivery in 2 days"), sign the Intent mandate once, and the system continuously monitors every 10 seconds in demo mode (configurable - 5 minutes in production). When conditions match, the agent autonomously creates a Cart mandate, processes payment through the Payment Agent, and notifies you of completion - all while maintaining the complete AP2 mandate chain for full transparency and auditability.

## ✨ Key Features

- **🧠 Multi-Agent Orchestration**: Supervisor agent intelligently routes requests to specialist agents (HP Shopping, HNP Delegate, Payment Agent) using LLM reasoning and the Strands SDK agents-as-tools pattern
- **🔐 AP2 Protocol Compliance**: Complete mandate chain (Intent → Cart → Payment → Transaction) with HMAC-SHA256 cryptographic signatures and full validation
- **⚡ Real-Time Transparency**: Server-Sent Events (SSE) stream every agent action, decision, and tool invocation in real-time with automatic UI updates on purchase completion
- **🔄 Autonomous Monitoring**: APScheduler background jobs check product conditions every 10 seconds (demo mode) and purchase automatically when constraints are met
- **🔔 Live Updates**: Order history and monitoring jobs automatically refresh via SSE events when purchases complete - no manual refresh needed
- **📊 Mandate Chain Visualization**: Interactive UI showing the complete authorization flow with signature verification
- **♻️ Reusable Payment Agent**: Domain-independent payment processor with its own tools and validation logic, extractable to any commerce project
- **🚀 Production-Ready**: Deployed on AWS ECS Fargate with Application Load Balancer and CloudWatch logging
- **💾 Persistent State**: SQLite database with SQLAlchemy ORM stores all mandates, transactions, and monitoring jobs
- **🎨 Modern UI**: React 18 with Tailwind CSS featuring AWS-inspired professional design and smooth animations

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- AWS Account with Bedrock access (Claude Sonnet 4.5)
- Docker (for deployment)

### Local Development

**1. Backend Setup:**
```bash
cd backend
pip install -r requirements.txt

# Configure AWS credentials
export AWS_REGION=us-east-1
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret

# Run backend
python -m uvicorn src.main:app --reload --port 8000
```

Backend will be available at http://localhost:8000

**2. Frontend Setup:**
```bash
cd frontend
npm install
npm run dev
```

Frontend will be available at http://localhost:5173

**3. Try It Out:**
- Open http://localhost:5173
- Try HP flow: "Find me a coffee maker under $70"
- Try HNP flow: "Buy AirPods if price drops below $180"

### AWS Deployment

**1. Setup Infrastructure:**
```bash
chmod +x infrastructure/ecs-setup.sh
./infrastructure/ecs-setup.sh
```

This creates:
- ECS Fargate cluster
- Application Load Balancer
- Security groups
- Target groups
- IAM roles

**2. Deploy Backend:**
```bash
chmod +x deploy-ecs.sh
./deploy-ecs.sh
```

This:
- Builds backend-only Docker image (using `backend-only.Dockerfile`)
- Pushes to Amazon ECR
- Creates/updates ECS task definition and service
- Provides ALB URL for API endpoints

**3. Optional: Configure HTTPS with CloudFront (Free AWS Certificate):**
```bash
chmod +x infrastructure/configure-cloudfront.sh
./infrastructure/configure-cloudfront.sh
```

This provides:
- Free HTTPS with AWS-managed certificate (no domain required)
- Global CDN for better performance
- DDoS protection
- CloudFront domain: `https://[distribution-id].cloudfront.net`

## 📚 Documentation

- **[ARCHITECTURE.md](./ARCHITECTURE.md)** - Comprehensive technical architecture and data flows
- **[infrastructure/README.md](./infrastructure/README.md)** - AWS deployment and infrastructure guide
- **[SYSTEM_DIAGRAM.md](./SYSTEM_DIAGRAM.md)** - Visual system components diagram

## 🏗️ Project Structure

```
ap2-hack/
├── backend/                 # FastAPI backend with AI agents
│   ├── src/
│   │   ├── agents/         # Strands agents (Supervisor, HP, HNP, Payment)
│   │   ├── api/            # REST API endpoints
│   │   ├── services/       # Business logic layer
│   │   ├── db/             # Database models and initialization
│   │   └── mocks/          # Mock services for demo
│   └── requirements.txt
├── frontend/               # React frontend with Vite
│   ├── src/
│   │   ├── components/    # UI components
│   │   ├── context/       # React context providers
│   │   ├── pages/         # Page components
│   │   └── services/      # API and SSE clients
│   └── package.json
├── infrastructure/         # AWS deployment scripts
│   ├── ecs-setup.sh       # Infrastructure setup
│   └── configure-cloudfront.sh # CloudFront HTTPS setup
├── specs/                  # AP2 specification and requirements
├── docs/                   # Additional documentation
├── backend-only.Dockerfile # Backend Docker build
├── ecs-task-definition.json
└── deploy-ecs.sh          # Deployment script
```

## 🎬 Demo Scenarios

### Scenario 1: Human-Present Purchase
```
User: "Find me [product] under $[budget]"
→ Supervisor Agent analyzes intent and routes to HP Shopping Agent
→ HP Shopping Agent searches products via search_products tool
→ Shows matching results with prices, delivery estimates, stock status
→ User selects desired product
→ HP Agent calls create_hp_cart tool to create Cart mandate
→ User signs Cart mandate through biometric-style modal (HMAC-SHA256)
→ HP Agent invokes Payment Agent with signed Cart
→ Payment Agent validates mandate chain and processes payment
→ Transaction created with authorization code
→ Complete mandate chain viewable in UI: Intent → Cart → Payment → Transaction
```

### Scenario 2: Human-Not-Present Monitoring
```
User: "Buy AirPods if price drops below $180 and delivery is 2 days or less"
→ Supervisor Agent routes to HNP Delegate Agent
→ HNP Agent extracts constraints: max_price=$180, max_delivery=2 days
→ HNP Agent calls create_hnp_intent tool to create unsigned Intent mandate
→ System returns Intent for user signature
→ User reviews constraints and signs Intent Mandate (pre-authorization)
→ HNP Agent calls create_monitoring_job tool with signed Intent
→ APScheduler creates background job checking every 10 seconds (demo mode)
→ Monitoring job persists in database (survives restarts)
→ Job checks product conditions via search_products API
→ When price drops to $179 with 1-day delivery: CONDITIONS MET
→ Job autonomously creates agent-signed Cart mandate (references Intent)
→ Calls Payment Agent with Cart + human_not_present flag
→ Payment Agent validates Intent constraints, processes payment
→ User notified via chat stream with transaction details
→ Complete HNP mandate chain: Intent (user-signed) → Cart (agent-signed) → Payment → Transaction
```

## 🔧 Technology Stack

### Backend
- **Framework**: FastAPI 0.100+ with async/await and Pydantic 2.0 for data validation
- **AI/ML**: AWS Bedrock (Claude Sonnet 4.5 via `us.anthropic.claude-sonnet-4-20250514-v1:0`)
- **Agent Framework**: Strands Agents SDK 0.1.0+ with agents-as-tools pattern
- **Database**: SQLite with SQLAlchemy 2.0 async ORM
- **Scheduling**: APScheduler 3.10+ with SQLAlchemy job store (persistent across restarts)
- **Real-time**: Server-Sent Events (SSE) streaming through FastAPI StreamingResponse
- **Testing**: pytest with pytest-asyncio and httpx for async API testing

### Frontend
- **Framework**: React 18.2 with functional components and hooks
- **Build Tool**: Vite 4.3 (ES modules, HMR, optimized builds)
- **Styling**: Tailwind CSS 3.3 with custom AWS-inspired design system
- **State Management**: React Context API (SessionContext for user/session state)
- **Real-time**: EventSource API for SSE consumption
- **Markdown**: react-markdown 10.1 for rendering agent messages

### Infrastructure
- **Container Orchestration**: AWS ECS Fargate (serverless containers)
- **Load Balancing**: Application Load Balancer (ALB) with health checks
- **CDN**: CloudFront (optional) for HTTPS, global distribution, and DDoS protection
- **Container Registry**: Amazon ECR for Docker images
- **Logging**: CloudWatch Logs with structured logging
- **Networking**: VPC with public/private subnets, Security Groups
- **Deployment**: Backend-only Docker container (API server only)

## 🔐 AP2 Protocol Implementation

GhostCart implements the complete AP2 v0.1 specification with full mandate chain validation:

### Mandate Types (All stored in database)
- **Intent Mandate**: Captures user's original request with constraints
  - HP Flow: Context-only (no signature required)
  - HNP Flow: User-signed pre-authorization with expiration (typically 7 days)
  - Contains: `product_query`, `constraints` (max_price_cents, max_delivery_days), `scenario`, `expiration`

- **Cart Mandate**: Exact items, quantities, and prices
  - HP Flow: User-signed after product selection
  - HNP Flow: Agent-signed when conditions met (references Intent mandate_id)
  - Contains: `items[]` (product_id, name, price, quantity), `total_amount_cents`, `parent_mandate_id`

- **Payment Mandate**: Payment processing authorization
  - Always created by Payment Agent
  - References Cart mandate_id
  - Includes `human_not_present: true/false` flag for autonomous purchases
  - Contains: payment method, amount, merchant details

- **Transaction**: Final outcome record
  - `status`: "approved" or "declined"
  - `authorization_code`: Payment processor reference (or error code if declined)
  - Complete timestamp and audit trail

### Signature & Validation (backend/src/agents/payment_agent/crypto.py)
- **Algorithm**: HMAC-SHA256 with SHA-256 canonical serialization
- **Secrets**: Separate signing keys for user, agent, and payment agent
- **Signature Metadata**: Includes algorithm, signer identity, timestamp, nonce
- **Chain Validation**: Payment Agent validates complete mandate chain before processing:
  1. Verify Cart signature (user in HP, agent in HNP)
  2. If HNP: verify Intent signature and expiration
  3. If HNP: validate constraints not violated (price ≤ max_price, delivery ≤ max_delivery)
  4. Verify payment amount matches Cart total
  5. Check payment credentials available
- **Production Note**: Demo uses HMAC-SHA256 for simplicity; production should use ECDSA with hardware-backed keys

### AP2 Error Codes (backend/src/exceptions.py)
- `ap2:mandate:chain_invalid` - Mandate chain validation failed
- `ap2:mandate:signature_invalid` - Signature verification failed
- `ap2:mandate:expired` - Intent mandate past expiration
- `ap2:mandate:constraints_violated` - HNP purchase violates Intent constraints
- `ap2:credentials:unavailable` - Payment credentials not configured
- `ap2:payment:declined` - Payment processor declined transaction
- `ap2:product:out_of_stock` - Requested product unavailable

## 🏗️ Multi-Agent Architecture

GhostCart implements a sophisticated multi-agent system using the Strands SDK:

### Agent Hierarchy (backend/src/agents/)

**1. Supervisor Agent** (`supervisor_strands.py`)
- **Role**: Main orchestrator and entry point for all user interactions
- **Pattern**: Agents-as-tools (specialist agents registered as @tool functions)
- **Intelligence**: Uses LLM reasoning to analyze user intent and route to appropriate specialist
- **Tools**:
  - `shopping_assistant` - Routes to HP Shopping Agent
  - `monitoring_assistant` - Routes to HNP Delegate Agent
- **Contextual Translation**: Reformulates ambiguous user input ("yes", "the first one") into concrete instructions for specialists
- **Session Management**: Uses Strands SessionManager for conversation persistence

**2. HP Shopping Agent** (`hp_shopping_strands.py`)
- **Role**: Handles immediate purchase flow (Human-Present)
- **Tools**:
  - `search_products` - Searches merchant catalog with filters
  - `create_hp_cart` - Creates Cart mandate for user signature
  - `process_hp_payment` - Invokes Payment Agent with signed Cart
- **Flow**: Product search → User selection → Cart creation → User signature → Payment

**3. HNP Delegate Agent** (`hnp_delegate_strands.py`)
- **Role**: Sets up autonomous monitoring for conditional purchases (Human-Not-Present)
- **Tools**:
  - `create_hnp_intent` - Creates Intent mandate with constraints
  - `create_monitoring_job` - Schedules APScheduler job for price monitoring
- **Flow**: Parse constraints → Create Intent → Request user signature → Activate monitoring

**4. Payment Agent** (`agents/payment_agent/agent.py`)
- **Role**: Processes payments with full AP2 validation (domain-independent, reusable)
- **Tools**:
  - `validate_mandate_chain` - Validates complete mandate chain and signatures
  - `process_payment` - Processes payment through mock payment processor
- **Validation**: Chain integrity, signature verification, constraint checking (HNP only)
- **Isolation**: Has its own crypto module, models, and can be extracted to other projects

### Background Monitoring System

**APScheduler Integration** (`services/scheduler.py`, `services/monitoring_service.py`)
- **Job Storage**: SQLAlchemy-backed job store (persists across restarts)
- **Interval**: 10 seconds in demo mode (configurable - 5 minutes in production via `demo_mode` setting)
- **Job Function**:
  1. Fetches Intent mandate constraints from database
  2. Searches products via merchant API
  3. Checks if price ≤ max_price AND delivery ≤ max_delivery
  4. If conditions met: creates agent-signed Cart → calls Payment Agent → creates Transaction
  5. Notifies user via SSE stream
  6. Deactivates monitoring job
- **Demo Feature**: Mock merchant API simulates price drop 20 seconds after monitoring activation

### Real-Time Communication

**Server-Sent Events (SSE)** (`services/sse_service.py`, `api/chat.py`)
- **Endpoint**: `/api/chat/stream` (FastAPI StreamingResponse)
- **Event Types**:
  - `agent_message` - Agent responses and tool outputs
  - `tool_invocation` - Tool calls with parameters
  - `signature_request` - Mandate signing requests
  - `hp_purchase_complete` - HP (immediate) purchase notifications → triggers automatic order refresh
  - `autonomous_purchase_complete` - HNP (autonomous) purchase notifications → triggers automatic order and monitoring job refresh
  - `monitoring_activated` - Monitoring job started
  - `error` - Error messages
- **Frontend**: EventSource API in `ChatInterface.jsx` processes events and updates UI
- **Auto-Refresh Behavior**:
  - When `hp_purchase_complete` or `autonomous_purchase_complete` events fire, the frontend automatically refreshes the Order History section
  - When `autonomous_purchase_complete` fires, completed monitoring jobs are automatically removed from the UI
  - No manual refresh button clicks needed - everything updates in real-time


### Integration Testing
1. Start backend: `cd backend && python -m uvicorn src.main:app --reload`
2. Start frontend: `cd frontend && npm run dev`
3. Test HP flow with product search ("Find headphones under $100")
4. Test HNP flow with monitoring setup ("Buy AirPods if price drops below $180")
5. Wait ~30 seconds for monitoring to trigger (mock API drops price after 20s, checked every 10s)
6. Verify mandate chain visualization shows complete audit trail in Order History

## 📦 Demo Product Catalog

The mock merchant API (`backend/src/mocks/merchant_api.py`) provides **15 products** across 4 categories:

- **Electronics (4)**: Apple AirPods Pro ($249), Sony WH-1000XM5 Headphones ($399), Samsung Galaxy Tab S9 ($799 - out of stock), Fitbit Charge 6 ($159.99)
- **Kitchen (4)**: Keurig K-Elite Coffee Maker ($169.99), Ninja Air Fryer ($99.99), KitchenAid Stand Mixer ($399.99 - out of stock), Instant Pot Duo ($79.99)
- **Fashion (4)**: Levi's 501 Jeans ($69.99), Nike Air Max Sneakers ($129.99), Ray-Ban Aviator Sunglasses ($159.99), Patagonia Fleece Jacket ($149.99)
- **Home (3)**: Dyson V15 Vacuum ($699.99), Philips Hue Starter Kit ($199.99), iRobot Roomba j7+ ($799.99)

**Price Drop Simulation**: When monitoring is activated via HNP flow, the system automatically registers the target product for a price drop. After 20 seconds, the mock API reduces the product price to exactly meet the user's constraints (accounting for tax and shipping) to demonstrate autonomous purchase triggering.

## 🎨 Frontend Components

Key React components in `frontend/src/components/`:

- **ChatInterface.jsx**: Main chat UI with SSE event handling, message rendering, signature modal integration, and automatic refresh triggers for orders/monitoring
- **MonitoringStatusCard.jsx**: Real-time monitoring job display with countdown timers and constraint visualization (auto-clears after autonomous purchase)
- **SignatureModal.jsx**: Biometric-style signature capture UI for mandate signing
- **MandateChainFlow.jsx**: Interactive timeline visualization of mandate chain (Intent → Cart → Payment)
- **OrdersSection.jsx**: Transaction history with mandate chain viewing (auto-refreshes on purchase completion via SSE events)
- **AP2InfoSection.jsx**: Educational collapsible section explaining AP2 protocol
- **Home.jsx**: Main page orchestrating real-time updates - coordinates automatic refresh of orders and monitoring jobs when purchases complete

## 🤝 Contributing

This is a hackathon demonstration project showcasing AP2 protocol implementation. For production deployment:

**Security Enhancements:**
1. Replace HMAC-SHA256 with ECDSA (P-256/secp256r1) signatures
2. Use hardware-backed key storage (AWS KMS, HSM, or secure enclaves)
3. Implement proper user authentication (OAuth 2.0, JWT tokens)

**Infrastructure Improvements:**
1. Replace SQLite with PostgreSQL/RDS for scalability
2. Add Redis for session caching and job queue
3. Implement distributed tracing (AWS X-Ray, OpenTelemetry)
4. Add comprehensive monitoring and alerting (CloudWatch, Datadog)
5. Configure auto-scaling policies for ECS tasks
6. Enable WAF (Web Application Firewall) on ALB

**Code Quality:**
1. Add comprehensive unit and integration tests (target >80% coverage)
2. Implement CI/CD pipeline with automated testing
3. Add API documentation with OpenAPI/Swagger
4. Implement proper error recovery and retry logic
5. Add input sanitization and validation layers
6. Implement audit logging for all mandate operations

## 📄 License

MIT License - see LICENSE file for details

## 🙏 Acknowledgments

- [Agent Payments Protocol (AP2)](https://ap2-protocol.org/) specification
- [AWS Bedrock](https://aws.amazon.com/bedrock/) for Claude Sonnet 4
- [Strands Agents SDK](https://github.com/strands-agents/sdk-python) for agent orchestration
- FastAPI and React communities

## ⚙️ Configuration

### Environment Variables

**Backend** (`backend/src/config.py`):
```bash
# AWS Configuration
AWS_REGION=us-east-1                                    # AWS region for Bedrock
AWS_ACCESS_KEY_ID=<your-key>                           # AWS credentials
AWS_SECRET_ACCESS_KEY=<your-secret>
AWS_BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-20250514-v1:0

# Monitoring (Note: demo_mode=true overrides this with 10-second interval)
# MONITORING_INTERVAL_MINUTES is not used - interval is controlled by demo_mode setting in config.py

# Signature Secrets (demo only - use KMS in production)
USER_SIGNATURE_SECRET=user_demo_secret_key_2024
AGENT_SIGNATURE_SECRET=agent_demo_secret_key_2024
PAYMENT_AGENT_SECRET=payment_agent_demo_secret_key_2024

# Application
DEMO_MODE=true                                         # Enable demo features
LOG_LEVEL=INFO                                         # Logging level
```

**Frontend** (`frontend/vite.config.js`):
- Development: Proxies API requests to `http://localhost:8000`
- Production: Backend serves frontend static files from `/app/frontend/dist`

### Database Schema

SQLite database (`ghostcart.db`) with 4 main tables:

1. **mandates**: All mandate types (Intent, Cart, Payment) with JSON data and signatures
2. **transactions**: Final purchase outcomes with authorization codes
3. **monitoring_jobs**: APScheduler job metadata and constraints
4. **apscheduler_jobs**: APScheduler internal job storage (enables restart persistence)


**Built for the Global Hackathon 2025** 🚀

Demonstrating the future of AI-powered autonomous payments with AP2 Protocol interoperability.

**Stack**: AWS Bedrock + Strands SDK + FastAPI + React
