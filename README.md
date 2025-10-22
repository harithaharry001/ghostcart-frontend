# GhostCart - AP2 Protocol Demonstration

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![React 18](https://img.shields.io/badge/react-18.2-blue.svg)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)

**GhostCart** is a full-stack demonstration of the [Agent Payments Protocol (AP2) v0.1](https://ap2-protocol.org/specification/), showcasing mandate-based payments with intelligent AI agent orchestration using AWS Bedrock and Strands SDK.

## 🎯 What is GhostCart?

GhostCart proves that AP2 achieves true interoperability by implementing the protocol with AWS Strands SDK (not just Google's reference implementation). It demonstrates two revolutionary purchase flows:

### 🛒 Human-Present (HP) Flow
Traditional e-commerce with a twist: users search for products, approve purchases with biometric-style signatures, and get complete cryptographic audit trails showing exactly how their authorization flowed through the system.

### 🤖 Human-Not-Present (HNP) Flow
The future of shopping: users pre-authorize AI agents to monitor products and purchase autonomously when conditions are met. Set your constraints ("buy AirPods if price drops below $180"), sign once, and let the agent work for you 24/7.

## ✨ Key Features

- **🧠 Multi-Agent Orchestration**: Supervisor agent intelligently routes requests to specialist agents using LLM reasoning
- **🔐 AP2 Protocol Compliance**: Complete mandate chain (Intent → Cart → Payment) with cryptographic signatures
- **⚡ Real-Time Transparency**: Server-Sent Events stream every agent action and decision
- **🔄 Autonomous Monitoring**: Background jobs check conditions every 5 minutes and purchase automatically
- **📊 Mandate Chain Visualization**: Interactive timeline showing the complete authorization flow
- **♻️ Reusable Payment Agent**: Domain-independent payment processor extractable to any commerce project
- **🚀 Production-Ready**: Deployed on AWS ECS Fargate with Application Load Balancer

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

**2. Deploy Application:**
```bash
chmod +x deploy-ecs.sh
./deploy-ecs.sh
```

This:
- Builds Docker image with frontend + backend
- Pushes to Amazon ECR
- Updates ECS service
- Provides ALB URL

**3. Optional: Configure HTTPS:**
```bash
chmod +x infrastructure/configure-https-route53.sh
./infrastructure/configure-https-route53.sh
```

## 📚 Documentation

- **[ARCHITECTURE.md](./ARCHITECTURE.md)** - Comprehensive technical architecture and data flows
- **[backend/README.md](./backend/README.md)** - Backend API, agents, and services documentation
- **[frontend/README.md](./frontend/README.md)** - Frontend components and UI architecture
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
│   └── configure-https-route53.sh
├── specs/                  # AP2 specification and requirements
├── docs/                   # Additional documentation
├── Dockerfile              # Multi-stage Docker build
├── ecs-task-definition.json
└── deploy-ecs.sh          # Deployment script
```

## 🎬 Demo Scenarios

### Scenario 1: Human-Present Purchase
```
User: "Find me a coffee maker under $70"
→ Supervisor routes to HP Shopping Agent
→ Agent searches products, shows results
→ User selects product
→ Agent creates cart, requests signature
→ User signs with biometric modal
→ Payment Agent processes payment
→ Transaction complete with mandate chain
```

### Scenario 2: Human-Not-Present Monitoring
```
User: "Buy AirPods if price drops below $180 and delivery is 2 days or less"
→ Supervisor routes to HNP Delegate Agent
→ Agent extracts constraints, confirms with user
→ User signs Intent Mandate (pre-authorization)
→ Background monitoring activates
→ Checks every 5 minutes for 7 days
→ When conditions met: autonomous purchase
→ User notified with transaction details
```

## 🔧 Technology Stack

### Backend
- **Framework**: FastAPI 0.100+ with async/await
- **AI/ML**: AWS Bedrock (Claude Sonnet 4), Strands Agents SDK
- **Database**: SQLite with SQLAlchemy ORM
- **Scheduling**: APScheduler for background monitoring
- **Real-time**: Server-Sent Events (SSE)

### Frontend
- **Framework**: React 18 with hooks
- **Build Tool**: Vite 4
- **Styling**: Tailwind CSS 3
- **State**: React Context API
- **Markdown**: react-markdown for agent messages

### Infrastructure
- **Compute**: AWS ECS Fargate
- **Load Balancer**: Application Load Balancer
- **Container Registry**: Amazon ECR
- **Logging**: CloudWatch
- **DNS**: Route 53 (optional)

## 🔐 AP2 Protocol Implementation

GhostCart implements the complete AP2 v0.1 specification:

### Mandate Types
- **Intent Mandate**: Captures user's original request (HP: context only, HNP: requires signature)
- **Cart Mandate**: Exact items and prices (HP: user-signed, HNP: agent-signed with Intent reference)
- **Payment Mandate**: Payment processing (references Cart, includes HNP flag when applicable)
- **Transaction**: Final outcome with authorization code or decline reason

### Signature Validation
- HMAC-SHA256 signatures (demo - production would use ECDSA)
- Complete audit trail with signature metadata
- Chain validation before payment processing

### Error Codes
- `ap2:mandate:chain_invalid`
- `ap2:mandate:signature_invalid`
- `ap2:mandate:expired`
- `ap2:mandate:constraints_violated`
- `ap2:credentials:unavailable`
- `ap2:payment:declined`

## 🧪 Testing

### Backend Tests
```bash
cd backend
pytest tests/ -v
```

### Frontend Tests
```bash
cd frontend
npm test
```

### Integration Testing
1. Start backend: `cd backend && python -m uvicorn src.main:app --reload`
2. Start frontend: `cd frontend && npm run dev`
3. Test HP flow with product search
4. Test HNP flow with monitoring setup
5. Verify mandate chain visualization
6. Test error scenarios (out of stock, payment decline)

## 🤝 Contributing

This is a hackathon demonstration project. For production use:
1. Replace HMAC-SHA256 with ECDSA signatures
2. Use hardware-backed key storage
3. Implement proper user authentication
4. Replace SQLite with PostgreSQL/RDS
5. Add comprehensive error handling
6. Implement rate limiting
7. Add monitoring and alerting

## 📄 License

MIT License - see LICENSE file for details

## 🙏 Acknowledgments

- [Agent Payments Protocol (AP2)](https://ap2-protocol.org/) specification
- [AWS Bedrock](https://aws.amazon.com/bedrock/) for Claude Sonnet 4
- [Strands Agents SDK](https://github.com/strands-agents/sdk-python) for agent orchestration
- FastAPI and React communities

## 📞 Support

For questions or issues:
1. Check [ARCHITECTURE.md](./ARCHITECTURE.md) for technical details
2. Review component-specific READMEs
3. Check AWS CloudWatch logs for deployment issues
4. Verify AWS Bedrock access and quotas

---

**Built for the Global Hackathon 2025** - Demonstrating the future of AI-powered autonomous payments
