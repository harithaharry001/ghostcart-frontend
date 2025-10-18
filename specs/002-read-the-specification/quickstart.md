# Quickstart Guide: GhostCart AP2 Demonstration

**Feature**: GhostCart - AP2 Protocol Demonstration
**Date**: 2025-10-17
**Target Audience**: Developers setting up local development environment

## Overview

This guide walks through setting up GhostCart locally for development and testing. The application demonstrates Agent Payments Protocol (AP2) v0.1 compliance with AWS Strands SDK, featuring human-present and human-not-present purchase flows.

**Demo Objectives**:
- Prove AP2 works with AWS Strands SDK (not just Google Agent Development Kit)
- Demonstrate Payment Agent reusability (zero GhostCart domain coupling)
- Show complete mandate chain visualization (Intent → Cart → Payment → Transaction)
- Real-time agent transparency via Server-Sent Events

**Architecture**: FastAPI backend + React frontend, single process deployment via Uvicorn

## Prerequisites

### Required Software

- **Python 3.11+** (for backend with type hints, asyncio)
- **Node.js 18+** and npm (for frontend React app)
- **AWS Account** with Bedrock access (Claude Sonnet 4.5 model enabled in your AWS region)
- **Git** (for cloning repository)

### AWS Setup

1. **Enable Bedrock Model Access**:
   - Log in to AWS Console
   - Navigate to Amazon Bedrock service (your AWS region)
   - Go to "Model access" in left sidebar
   - Request access to `Claude Sonnet 4 (20250514)` model
   - Wait for approval (usually instant)

2. **Configure AWS Credentials**:
   ```bash
   # Install AWS CLI if not already installed
   brew install awscli  # macOS
   # or: pip install awscli

   # Configure credentials
   aws configure
   # AWS Access Key ID: <your-key>
   # AWS Secret Access Key: <your-secret>
   # Default region name: us-east-1
   # Default output format: json
   ```

3. **Verify Bedrock Access**:
   ```bash
   aws bedrock list-foundation-models --region us-east-1 --query 'modelSummaries[?contains(modelId, `claude-sonnet-4`)].modelId'
   ```
   Should return: `["us.anthropic.claude-sonnet-4-20250514-v1:0"]`

## Project Structure

```
ap2-hack/
├── backend/
│   ├── src/
│   │   ├── agents/           # Strands agents (Supervisor, HP, HNP)
│   │   │   ├── supervisor.py
│   │   │   ├── hp_shopping.py
│   │   │   ├── hnp_delegate.py
│   │   │   └── payment_agent/  # ← REUSABLE, zero coupling
│   │   ├── mocks/            # Mock services (merchant, credentials, processor)
│   │   ├── models/           # Pydantic mandate models (Intent, Cart, Payment)
│   │   ├── services/         # Business logic
│   │   ├── api/              # FastAPI routes
│   │   └── main.py           # Application entry point
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/       # React components
│   │   ├── pages/
│   │   ├── services/         # API client, SSE connection
│   │   └── App.jsx
│   ├── package.json
│   └── vite.config.js
└── ghostcart.db             # SQLite database (auto-created)
```

## Installation Steps

### Step 1: Clone Repository

```bash
git clone <repository-url>
cd ap2-hack
git checkout 002-read-the-specification  # Feature branch
```

### Step 2: Backend Setup

```bash
cd backend

# Create Python virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Expected packages:
# - fastapi==0.100.0+
# - uvicorn[standard]==0.23.0+
# - pydantic==2.0.0+
# - sqlalchemy==2.0.0+
# - apscheduler==3.10.0+
# - boto3==1.28.0+
# - aws-strands-sdk (check AWS documentation for latest)
```

### Step 3: Environment Configuration

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your settings
nano .env
```

**Required Environment Variables**:
```bash
# AWS Bedrock Configuration
AWS_REGION=us-east-1  # Use any AWS region where Claude Sonnet 4.5 is available
AWS_BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-20250514-v1:0

# Demo Configuration
DEMO_MODE=true                    # Enables accelerated monitoring (30s instead of 5min)
LOG_LEVEL=INFO                    # DEBUG for development, INFO for demo

# Cryptographic Secrets (HMAC-SHA256 demo keys)
USER_SIGNATURE_SECRET=user_secret_key_demo_only
AGENT_SIGNATURE_SECRET=agent_secret_key_demo_only
PAYMENT_AGENT_SECRET=payment_secret_key_demo_only

# Database
DATABASE_PATH=../ghostcart.db     # SQLite file location

# Server
HOST=0.0.0.0
PORT=8000
```

### Step 4: Frontend Setup

```bash
cd ../frontend

# Install dependencies
npm install

# Expected packages:
# - react@18+
# - react-dom@18+
# - vite@4+
# - tailwindcss@3+
```

**Frontend Environment** (create `frontend/.env`):
```bash
VITE_API_BASE_URL=http://localhost:8000/api
```

### Step 5: Database Initialization

```bash
cd ../backend

# Run database migrations (creates tables)
python -m src.db.init_db

# Expected output:
# Creating tables: mandates, monitoring_jobs, transactions, sessions
# Database initialized at ../ghostcart.db
```

**Tables Created**:
- `mandates` - Stores Intent, Cart, Payment mandates
- `monitoring_jobs` - Stores HNP monitoring job metadata
- `transactions` - Stores transaction results
- `sessions` - Stores user session data
- `apscheduler_jobs` - APScheduler job store (auto-created)

## Running the Application

### Development Mode (Separate Terminals)

**Terminal 1: Backend Server**
```bash
cd backend
source venv/bin/activate
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Expected output:
# INFO: Started server process
# INFO: Waiting for application startup.
# INFO: Application startup complete.
# INFO: Uvicorn running on http://0.0.0.0:8000
```

**Terminal 2: Frontend Dev Server**
```bash
cd frontend
npm run dev

# Expected output:
# VITE v4.x.x  ready in X ms
# ➜  Local:   http://localhost:5173/
# ➜  Network: http://192.168.x.x:5173/
```

**Access Application**: Open browser to `http://localhost:5173`

### Production Mode (Single Process)

```bash
# Build frontend
cd frontend
npm run build

# Frontend build output goes to: frontend/dist/

# Start backend (serves API + static frontend)
cd ../backend
source venv/bin/activate
uvicorn src.main:app --host 0.0.0.0 --port 8000

# Backend mounts frontend/dist/ at root path
# Access: http://localhost:8000
```

## Testing the Demo Flows

### Human-Present Flow (Immediate Purchase)

1. **Start Chat**: Type in chat input: `"Find me a coffee maker under 70 dollars"`

2. **Observe Agent Routing** (SSE messages):
   ```
   agent_thought: "Analyzing your request..."
   agent_thought: "Routing to shopping assistant"
   product_results: [3 coffee makers displayed]
   ```

3. **Select Product**: Click "Philips HD7462 Coffee Maker" card

4. **Review Cart**:
   - Item: Philips HD7462
   - Price: $69.00
   - Delivery: 2 days
   - Total: $74.00 (includes tax)
   - Blue "Approve Purchase" button appears

5. **Sign Cart** (authorization):
   - Click "Approve Purchase"
   - Biometric modal appears with fingerprint icon
   - Click "Confirm"
   - 1-second scanning animation plays
   - Green checkmark "Verified"

6. **Payment Processing** (SSE messages):
   ```
   mandate_created: "Cart Mandate signed"
   payment_processing: "Validating signature..."
   payment_processing: "Processing payment..."
   result: "Payment authorized! Transaction ID: txn_abc123"
   ```

7. **View Mandate Chain**:
   - Click "View Chain" button
   - Timeline visualization appears:
     - Intent (gray header "Context Only - Not Signed")
     - Cart (green header "User Signed - Authorization") ← YOU SIGNED THIS
     - Payment (Payment Agent signed)
     - Transaction (green "Authorized" badge)
   - Click any box to expand and see JSON
   - "Copy JSON" and "Download Chain" buttons available

**Expected Result**: Complete HP flow in under 90 seconds (SC-001)

### Human-Not-Present Flow (Autonomous Monitoring)

1. **Start Monitoring Request**: Type: `"Buy AirPods if price drops below 180 dollars and delivery is 2 days or less"`

2. **Observe Agent Routing** (SSE messages):
   ```
   agent_thought: "Analyzing constraints..."
   agent_thought: "Routing to monitoring assistant"
   ```

3. **Review Monitoring Confirmation**:
   - Agent message: "I can monitor Apple AirPods Pro and automatically purchase when conditions met."
   - Constraints summary:
     - Maximum price: $180
     - Maximum delivery: 2 days
     - Check frequency: Every 5 minutes (or 30 seconds in DEMO_MODE)
     - Monitoring duration: 7 days
   - Green "Yes, Monitor This" button

4. **Sign Intent** (pre-authorization):
   - Click "Yes, Monitor This"
   - Biometric modal appears
   - Orange warning: "You are authorizing autonomous purchase. Agent will buy automatically without asking again."
   - Click "Confirm"
   - Scanning animation → Verification

5. **Monitoring Activated** (SSE messages):
   ```
   mandate_created: "Intent Mandate signed"
   agent_thought: "Monitoring activated"
   agent_thought: "First check in 5 minutes" (or 30 seconds in DEMO_MODE)
   ```

6. **Monitoring Status Card Appears**:
   ```
   Monitoring Active: Apple AirPods Pro
   Checking every: 5 minutes
   Conditions: Price below $180, Delivery within 2 days
   Expires in: 7 days
   [Cancel Monitoring] button
   ```

7. **Background Checks Running**:
   - Status updates every check:
     ```
     Last checked: 10:00 AM
     Current price: $249
     Status: Conditions not met - price too high
     ```

8. **Conditions Met** (simulated after a few checks):
   - Status updates rapidly (SSE messages):
     ```
     agent_thought: "Conditions met! Price $175, delivery 1 day"
     mandate_created: "Creating Cart Mandate automatically"
     payment_processing: "Processing payment autonomously"
     result: "Payment authorized!"
     ```

9. **Autonomous Purchase Notification**:
   - Large banner appears:
     ```
     Autonomous Purchase Complete!
     Apple AirPods Pro purchased for $175
     You authorized this on [date] with constraints: price below $180, delivery within 2 days
     Transaction ID: txn_def789
     [View Details] [View Chain] buttons
     ```
   - Monitoring status changes to "Monitoring Completed - Purchase successful"

10. **View Mandate Chain**:
    - Click "View Chain"
    - Timeline shows:
      - Intent (green "User Signed - Pre-Authorization") ← YOU PRE-AUTHORIZED THIS
      - Cart (blue "Agent Signed - Autonomous Action", shows "References Intent ID: intent_hnp_xyz")
      - Payment (badge "Human Not Present Flag Set")
      - Transaction (green "Authorized")

**Expected Result**: HNP setup in under 60 seconds (SC-002), autonomous purchase when conditions met

### Verifying Payment Agent Reusability

**Test**: Extract `backend/src/agents/payment_agent/` folder and verify zero coupling

```bash
cd backend/src/agents/payment_agent

# Check imports (should only be: Python stdlib, Pydantic, Strands SDK)
grep -r "from src\." *.py
# Expected: NO RESULTS (no imports from parent GhostCart modules)

grep -r "import.*agents\." *.py
# Expected: NO RESULTS (no imports from other agents)

grep -r "import.*mocks\." *.py
# Expected: NO RESULTS (no imports from mock services)

# Payment Agent should only know about AP2 mandate primitives
grep -r "product\|merchant\|ghostcart" *.py
# Expected: NO RESULTS (no domain-specific knowledge)
```

**Constitution Compliance**: ✅ Payment Agent has zero GhostCart coupling (Principle II)

## Troubleshooting

### Backend Won't Start

**Issue**: `ModuleNotFoundError: No module named 'fastapi'`
**Solution**:
```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
```

**Issue**: `boto3.exceptions.NoCredentialsError`
**Solution**:
```bash
aws configure
# Enter your AWS credentials
```

**Issue**: `Bedrock model not found`
**Solution**:
- Check AWS Bedrock model access in Console (your configured region)
- Verify model ID in `.env` matches enabled model

### Frontend Won't Connect to Backend

**Issue**: CORS errors in browser console
**Solution**: Backend FastAPI should have CORS middleware configured:
```python
# In backend/src/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Issue**: API calls fail with 404
**Solution**: Verify `VITE_API_BASE_URL=http://localhost:8000/api` in `frontend/.env`

### Monitoring Jobs Not Running

**Issue**: Background monitoring not checking prices
**Solution**:
```bash
# Check APScheduler logs
grep "APScheduler" backend/logs/app.log

# Verify demo mode enabled for faster checks (30s not 5min)
cat backend/.env | grep DEMO_MODE
# Should be: DEMO_MODE=true

# Check database for active jobs
sqlite3 ../ghostcart.db "SELECT job_id, active, expires_at FROM monitoring_jobs WHERE active=1;"
```

**Issue**: Jobs don't survive server restart
**Solution**: Verify APScheduler using SQLAlchemyJobStore (not in-memory):
```python
# In backend/src/services/scheduler.py
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

jobstores = {
    'default': SQLAlchemyJobStore(url='sqlite:///../ghostcart.db')
}
scheduler = BackgroundScheduler(jobstores=jobstores)
```

### SSE Connection Issues

**Issue**: Real-time messages not appearing
**Solution**:
- Check browser DevTools → Network → filter for "stream"
- EventSource connection should be open with `text/event-stream` content type
- Backend should have SSE endpoint returning `StreamingResponse`:
  ```python
  from fastapi.responses import StreamingResponse

  @app.get("/api/stream")
  async def stream_events(session_id: str):
      return StreamingResponse(
          event_generator(session_id),
          media_type="text/event-stream"
      )
  ```

## Demo Mode Configuration

For hackathon judging, enable demo mode for accelerated monitoring:

**Backend `.env`**:
```bash
DEMO_MODE=true  # Monitoring checks every 30 seconds instead of 5 minutes
```

**Effect**:
- HNP monitoring checks run every 30 seconds
- Allows demo to show autonomous purchase within 2-3 minutes
- Production would use 5-minute intervals (or configurable per Intent)

## Validating AP2 Compliance

### Check Mandate Structures Match AP2 Schemas

```bash
cd backend

# Run Pydantic schema validation tests
pytest tests/test_mandates.py -v

# Expected output:
# test_intent_mandate_hp_valid PASSED
# test_intent_mandate_hnp_valid PASSED
# test_cart_mandate_hp_valid PASSED
# test_cart_mandate_hnp_valid PASSED
# test_payment_mandate_valid PASSED
# test_mandate_chain_hp_valid PASSED
# test_mandate_chain_hnp_valid PASSED
```

### Verify Mandate Chain Validation

```bash
# Test HP flow chain validation
pytest tests/test_payment_agent.py::test_validate_hp_chain -v

# Test HNP flow chain validation
pytest tests/test_payment_agent.py::test_validate_hnp_chain -v

# Test error codes match AP2 specification
pytest tests/test_error_codes.py -v
```

### Check Payment Agent Isolation

```bash
cd backend/src/agents/payment_agent

# Static analysis: no parent imports
python -m pylint --disable=all --enable=import-error *.py

# Should pass with no import errors

# Verify import linter rules (if configured in pyproject.toml)
ruff check --select I *.py
```

## Performance Validation

From spec Success Criteria:

- **SC-003**: Agent messages stream within 500ms
  - Monitor Network tab → SSE events should appear instantly after actions

- **SC-004**: Monitoring checks complete in <2 seconds
  - Check backend logs: `grep "Monitoring check completed" logs/app.log`

- **SC-005**: System handles 10 concurrent monitoring jobs
  - Create 10 HNP monitoring jobs, verify all run without degradation

- **SC-010**: Mandate chain visualization loads in <1 second
  - Network tab → `/api/transactions/{id}/chain` should respond <1s

## Next Steps

After local validation:

1. **Run Full Test Suite**:
   ```bash
   cd backend
   pytest tests/ -v --cov=src --cov-report=html
   ```

2. **Proceed to `/speckit.tasks`**: Generate implementation task breakdown

3. **Review Constitution Compliance**: Ensure all 7 principles met

4. **Prepare Demo Script**: Practice both HP and HNP flows for judges (target: <3 minutes total per SC-006)

## Support

**Documentation**:
- Feature Spec: `specs/002-read-the-specification/spec.md`
- Data Model: `specs/002-read-the-specification/data-model.md`
- API Contracts: `specs/002-read-the-specification/contracts/openapi.yaml`

**External References**:
- AP2 Specification: https://ap2-protocol.org/specification/
- AP2 Reference Implementation: https://github.com/google-agentic-commerce/AP2
- AWS Strands SDK Docs: (check AWS documentation)
- AWS Bedrock Claude Models: https://docs.aws.amazon.com/bedrock/latest/userguide/model-ids-arns.html
