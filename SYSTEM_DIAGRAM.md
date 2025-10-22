# Strands AP2 Payment Agent System Components Diagram

System diagram of the Strands AP2 Payment Agent implementing the AP2 protocol.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      USER BROWSER                            │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  React Frontend (Vite)                                 │  │
│  │  • ChatInterface - Real-time messaging                 │  │
│  │  • SignatureModal - Biometric-style signing           │  │
│  │  • MandateChainViz - Audit trail visualization        │  │
│  │  • MonitoringStatusCard - HNP job status               │  │
│  └───────────────────────────────────────────────────────┘  │
└──────────────────┬──────────────────────────────────────────┘
                   │ HTTP/HTTPS + SSE
                   │
┌──────────────────▼──────────────────────────────────────────┐
│              AWS INFRASTRUCTURE                              │
│  ┌────────────────────────────────────────────────────┐     │
│  │  Application Load Balancer                          │     │
│  │  • HTTP/HTTPS Routing                               │     │
│  │  • Health Checks (/api/health)                      │     │
│  └──────────────┬─────────────────────────────────────┘     │
│                 │                                            │
│  ┌──────────────▼─────────────────────────────────────┐     │
│  │  ECS Fargate                                 │     │
│  │  ┌──────────────────────────────────────────────┐  │     │
│  │  │  Docker Container                             │  │     │
│  │  │  • Frontend Static Files                      │  │     │
│  │  │  • Backend API (FastAPI:8000)                 │  │     │
│  │  └──────────────────────────────────────────────┘  │     │
│  └────────────────────────────────────────────────────┘     │
└──────────────────┬──────────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────────┐
│              FASTAPI BACKEND                                 │
│  ┌────────────────────────────────────────────────────┐     │
│  │  API Layer                                          │     │
│  │  /api/chat/stream • /api/mandates/sign             │     │
│  │  /api/products • /api/transactions                  │     │
│  └──────────────┬─────────────────────────────────────┘     │
│                 │                                            │
│  ┌──────────────▼─────────────────────────────────────┐     │
│  │  AGENT ORCHESTRATION (AWS Strands)                  │     │
│  │  ┌──────────────────────────────────────────────┐  │     │
│  │  │  Supervisor Agent                             │  │     │
│  │  │  (Claude Sonnet 4.5 via Bedrock)                │  │     │
│  │  └────┬──────────────────┬──────────────────────┘  │     │
│  │       │                  │                          │     │
│  │  ┌────▼────────┐  ┌─────▼──────────────┐          │     │
│  │  │ HP Shopping │  │ HNP Delegate       │          │     │
│  │  │ Agent       │  │ Agent              │          │     │
│  │  └────┬────────┘  └─────┬──────────────┘          │     │
│  │       │                  │                          │     │
│  │  ┌────▼──────────────────▼──────────────────────┐  │     │
│  │  │ Payment Agent (Domain-Independent)           │  │     │
│  │  └──────────────────────────────────────────────┘  │     │
│  └────────────────────────────────────────────────────┘     │
│                 │                                            │
│  ┌──────────────▼─────────────────────────────────────┐     │
│  │  Services: mandate • signature • monitoring        │     │
│  │           transaction • sse • bedrock              │     │
│  └──────────────┬─────────────────────────────────────┘     │
│                 │                                            │
│  ┌──────────────▼─────────────────────────────────────┐     │
│  │  Database (SQLite)                                  │     │
│  │  • mandates • monitoring_jobs                       │     │
│  │  • transactions • sessions                          │     │
│  └─────────────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────────────┘
```

## Data Flow: Human-Present Purchase

```
User: "Find coffee maker under $70"
  ↓
Frontend → /api/chat/stream (SSE)
  ↓
Supervisor Agent → HP Shopping Agent
  ↓
search_products() → Merchant API
  ↓
SSE: product_results → Frontend displays
  ↓
User selects product
  ↓
create_shopping_cart()
  ├─ Intent Mandate (unsigned)
  └─ Cart Mandate (needs signature)
  ↓
SSE: signature_requested → Modal appears
  ↓
User signs → /api/mandates/sign
  ↓
invoke_payment_processing()
  ├─ Payment Agent validates chain
  ├─ Retrieves credentials
  ├─ Processes payment
  └─ Creates Payment Mandate
  ↓
Transaction created
  ↓
SSE: payment_complete → Success screen
```

## Data Flow: Human-Not-Present Monitoring

```
User: "Buy AirPods if price < $180"
  ↓
Supervisor Agent → HNP Delegate Agent
  ↓
extract_monitoring_constraints()
  ↓
create_hnp_intent()
  └─ Intent Mandate (needs signature)
  ↓
SSE: signature_requested → Warning modal
  ↓
User signs Intent (pre-authorization)
  ↓
activate_monitoring_job()
  ├─ Creates job in database
  └─ Registers with APScheduler
  ↓
Background Loop (every 5 min):
  ├─ Check price & availability
  ├─ SSE: monitoring_check_complete
  └─ If conditions NOT met: continue
  ↓
When conditions MET:
  ├─ Create Cart (agent-signed)
  ├─ Payment Agent processes
  ├─ Transaction created
  └─ SSE: autonomous_purchase_complete
  ↓
User notified with details
```

## AP2 Protocol Mandate Chain

### Human-Present Flow
```
Intent (unsigned) → Cart (user-signed) → Payment → Transaction
                    ↑
              Authorization
```

### Human-Not-Present Flow
```
Intent (user-signed) → Cart (agent-signed) → Payment (HNP flag) → Transaction
       ↑                      ↑
  Pre-authorization    References Intent ID
```

## Key Components

### Frontend
- **React 18** with Vite build tool
- **Tailwind CSS** for styling
- **SSE** for real-time updates
- **Context API** for state management

### Backend
- **FastAPI** with async/await
- **AWS Strands SDK** for agent orchestration
- **SQLite** with SQLAlchemy ORM
- **APScheduler** for background jobs

### Infrastructure
- **ECS Fargate** - Serverless containers
- **ALB** - Load balancing & health checks
- **ECR** - Docker image registry
- **CloudWatch** - Logging & monitoring

### AI/ML
- **AWS Bedrock** - Claude Sonnet 4.5 model
- **Strands Agents** - Multi-agent orchestration
- **LLM Routing** - Intelligent request routing

## Technology Stack Summary

| Layer | Technologies |
|-------|-------------|
| Frontend | React 18, Vite, Tailwind CSS, SSE |
| Backend | FastAPI, Python 3.11, async/await |
| AI | AWS Bedrock, Claude Sonnet 4.5, Strands SDK |
| Database | SQLite, SQLAlchemy, aiosqlite |
| Scheduling | APScheduler |
| Infrastructure | ECS Fargate, ALB, ECR, CloudWatch |
| Protocol | AP2 v0.1 with HMAC-SHA256 signatures |

## Documentation Links

- [README.md](./README.md) - Project overview & quick start
- [ARCHITECTURE.md](./ARCHITECTURE.md) - Detailed technical architecture
- [backend/README.md](./backend/README.md) - Backend API & agents
- [frontend/README.md](./frontend/README.md) - Frontend components
- [infrastructure/README.md](./infrastructure/README.md) - AWS deployment

---

**Strands AP2 Payment Agent** - Demonstrating the future of AI-powered autonomous payments with AP2 Protocol
