# Option A: Supervisor-Only SessionManager Implementation

## Overview

**Decision:** ONLY the Supervisor Agent has SessionManager. Specialist agents (HP Shopping, HNP Delegate) are STATELESS and receive context from Supervisor's message history.

**Rationale:**
- Simpler architecture - one source of truth
- Aligned with Strands SDK design - agents can receive parent context
- Less storage overhead - only one conversation history persisted
- Clearer semantics - Supervisor is the "memory keeper"

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Request                              │
└────────────────────────────────┬────────────────────────────────┘
                                 ↓
                    ┌─────────────────────────┐
                    │  Supervisor Agent       │
                    │  ✅ SessionManager      │
                    │  ✅ ConversationManager │
                    │  📝 Persists history    │
                    └────────────┬────────────┘
                                 │
                    Passes full message history
                                 │
              ┌──────────────────┴──────────────────┐
              ↓                                     ↓
   ┌──────────────────────┐            ┌──────────────────────┐
   │  HP Shopping Agent   │            │  HNP Delegate Agent  │
   │  ❌ No SessionManager │            │  ❌ No SessionManager│
   │  📖 Receives context  │            │  📖 Receives context │
   │     from Supervisor   │            │     from Supervisor  │
   └──────────────────────┘            └──────────────────────┘
            STATELESS                          STATELESS
```

## How Context Flows

### Multi-Turn Conversation Example

```
Turn 1: User: "Find AirPods"
  ↓
1. Supervisor.stream_async("Find AirPods")
   - SessionManager loads history (empty for new session)
   - Supervisor decides to call shopping_assistant tool
2. shopping_assistant tool executes:
   - Gets Supervisor's message history: []
   - Passes to HP agent: hp_agent.stream_async("Find AirPods")
3. HP agent (stateless) processes request
   - Searches products
   - Returns: "I found 2 AirPods products..."
4. Supervisor completes
   - SessionManager saves updated history:
     * User: "Find AirPods"
     * Assistant: "I found 2 AirPods products..."

Turn 2: User: "Yes, the first one"
  ↓
1. Supervisor.stream_async("Yes, the first one")
   - SessionManager loads history:
     * User: "Find AirPods"
     * Assistant: "I found 2 AirPods products..."
     * User: "Yes, the first one"
   - Supervisor decides to call shopping_assistant tool again
2. shopping_assistant tool executes:
   - Gets Supervisor's FULL message history (all 3 messages above)
   - Passes to HP agent: hp_agent.stream_async(supervisor.messages)
3. HP agent (stateless) receives FULL CONTEXT
   - Sees previous "Find AirPods" request
   - Sees previous "I found 2 products" response
   - Understands "the first one" refers to previous search
   - Creates cart with first product
4. Supervisor completes
   - SessionManager saves updated history
```

**Key Insight:** HP agent is stateless but has full context because Supervisor passes its entire message history!

## Implementation Details

### 1. Session Manager Factory

**File:** `backend/src/services/session_manager_factory.py`

```python
from strands.session import FileSessionManager, SessionManager

def create_session_manager(session_id: str) -> SessionManager:
    """
    Create a SessionManager for the given session.

    Uses FileSessionManager for dev/single-server.
    Can switch to S3SessionManager for production/distributed systems.
    """
    storage_dir = os.environ.get('SESSION_STORAGE_DIR', './.sessions')

    return FileSessionManager(
        session_id=session_id,
        storage_dir=storage_dir
    )
```

### 2. Supervisor Agent (With SessionManager)

**File:** `backend/src/agents/supervisor_strands.py`

```python
from strands import Agent, tool
from strands.session import SessionManager
from strands.agent.conversation_manager import ConversationManager

def create_supervisor_agent(
    hp_shopping_agent: Agent,
    hnp_delegate_agent: Optional[Agent] = None,
    session_manager: Optional[SessionManager] = None,  # NEW
    ...
) -> Agent:
    # Store reference to supervisor (set after agent creation)
    supervisor_agent_ref = {'agent': None}

    @tool
    async def shopping_assistant(user_request: str) -> str:
        """Handle immediate purchase requests."""

        # Get Supervisor's full conversation history
        supervisor = supervisor_agent_ref['agent']
        messages_to_pass = user_request

        if supervisor and hasattr(supervisor, 'messages') and supervisor.messages:
            # Pass Supervisor's FULL message history to HP agent
            messages_to_pass = supervisor.messages
            logger.info(f"Passing {len(supervisor.messages)} messages to HP Shopping Agent")

        # Stream from HP agent with full context
        async for event in hp_shopping_agent.stream_async(messages_to_pass):
            # Process streaming events
            ...

        return full_response

    # Create Supervisor with SessionManager
    agent = Agent(
        model=bedrock_model,
        tools=[shopping_assistant, monitoring_assistant],
        system_prompt=SUPERVISOR_SYSTEM_PROMPT,
        conversation_manager=ConversationManager(),  # Manages conversation
        session_manager=session_manager  # Persists state
    )

    # Set agent reference for tool functions
    supervisor_agent_ref['agent'] = agent

    return agent
```

**Key Points:**
- ✅ Supervisor has `session_manager` parameter
- ✅ Supervisor has `conversation_manager`
- ✅ Tool functions access `supervisor.messages` to get full history
- ✅ Full history passed to nested agents via `stream_async(messages)`

### 3. HP Shopping Agent (Stateless)

**File:** `backend/src/agents/hp_shopping_strands.py`

```python
def create_hp_shopping_agent(
    search_products_fn,
    create_cart_fn,
    ...
    # ❌ NO session_manager parameter
) -> Agent:
    """
    Create HP Shopping Agent (STATELESS).

    Context Management:
    - HP agent receives context from Supervisor when called
    - Supervisor passes its full conversation history
    - No SessionManager needed
    """

    @tool
    def search_products(query: str) -> str:
        # Tool implementation
        ...

    # Create agent WITHOUT SessionManager
    agent = Agent(
        model=bedrock_model,
        tools=[search_products, create_shopping_cart, ...],
        system_prompt=HP_SHOPPING_SYSTEM_PROMPT
        # ❌ No conversation_manager
        # ❌ No session_manager
    )

    return agent
```

**Key Points:**
- ❌ NO `session_manager` parameter
- ❌ NO `conversation_manager`
- ✅ Receives context from parent (Supervisor)

### 4. Chat Endpoint (Creates SessionManager)

**File:** `backend/src/api/chat.py`

```python
async def event_generator() -> AsyncIterator[str]:
    try:
        # Load or create session
        if session_id:
            current_session_id = session_id
        else:
            session_data = await create_session_db(...)
            current_session_id = session_data["session_id"]

        # ====================================================================
        # Create Strands SessionManager (Option A - Supervisor Only)
        # ====================================================================

        from ..services.session_manager_factory import create_session_manager

        session_mgr = create_session_manager(current_session_id)
        logger.info(f"Created SessionManager for session: {current_session_id}")

        # Create agents
        payment_agent = create_payment_agent_with_mocks()

        # HP agent - STATELESS (no session_manager)
        hp_agent = create_hp_shopping_agent(
            search_products_fn=search_products,
            # ... other dependencies
            # ❌ No session_manager parameter
        )

        # HNP agent - STATELESS (no session_manager)
        hnp_agent = create_hnp_delegate_agent(
            search_products_func=search_products,
            # ... other dependencies
            # ❌ No session_manager parameter
        )

        # Supervisor - ONLY agent with SessionManager
        supervisor = create_supervisor_agent(
            hp_shopping_agent=hp_agent,
            hnp_delegate_agent=hnp_agent,
            session_manager=session_mgr,  # ✅ ONLY Supervisor has SessionManager
            event_queue=event_queue
        )

        # ====================================================================
        # Stream Agent Execution
        # ====================================================================

        # No manual context passing needed!
        # Just pass current message - SessionManager handles history automatically
        async for event in supervisor.stream_async(message):
            # Handle streaming events
            ...

        # ====================================================================
        # Session State Update (Automatic)
        # ====================================================================

        # Supervisor's SessionManager automatically saves conversation history
        # We still update database session for tracking purposes
        state["history"].append({"role": "user", "content": message})
        state["history"].append({"role": "assistant", "content": response_text})

        await update_session(db, current_session_id, context_data=state)

        yield format_sse_event("complete", {...})

    except Exception as e:
        yield format_sse_event("error", {...})
```

**Key Points:**
- ✅ Creates `SessionManager` once per request
- ✅ Passes to Supervisor ONLY
- ❌ Specialist agents don't get SessionManager
- ✅ Just pass current `message` to `stream_async` - history handled automatically

## Session Storage Structure

```
./.sessions/
└── session_sess_abc123/
    ├── session.json                    # Session metadata
    └── agents/
        └── agent_supervisor_001/
            ├── agent.json              # Supervisor metadata
            └── messages/
                ├── message_001.json    # Turn 1: "Find AirPods"
                ├── message_002.json    # Turn 1: Assistant response
                ├── message_003.json    # Turn 2: "Yes, the first one"
                └── message_004.json    # Turn 2: Assistant response
```

**Note:** Only Supervisor's messages are persisted. HP and HNP agents don't create their own session storage.

## Benefits of Option A

### 1. Simplicity
- ✅ One source of truth for conversation state
- ✅ Fewer moving parts
- ✅ Easier to debug (inspect one session directory)

### 2. Performance
- ✅ Less storage overhead (one conversation history vs three)
- ✅ Faster session loading (load once vs load three times)
- ✅ No session synchronization issues

### 3. Clarity
- ✅ Clear architecture: Supervisor manages state, specialists execute
- ✅ Explicit context passing (can see in logs)
- ✅ Aligned with Strands SDK design

### 4. Flexibility
- ✅ Easy to switch from FileSessionManager to S3SessionManager
- ✅ Can inspect Supervisor's messages to see full conversation
- ✅ Specialists can be swapped out without affecting session storage

## Comparison: Option A vs Option B

| Aspect | Option A (Implemented) | Option B (All agents) |
|--------|------------------------|----------------------|
| **SessionManagers** | 1 (Supervisor only) | 3 (Supervisor + HP + HNP) |
| **Storage** | .sessions/session_X/agents/supervisor/ | .sessions/session_X/agents/{supervisor,hp,hnp}/ |
| **Context Passing** | Explicit (Supervisor passes messages) | Implicit (each agent loads own history) |
| **Complexity** | Lower | Higher |
| **Debugging** | Easier (one history to inspect) | Harder (three histories to correlate) |
| **Performance** | Faster (one session load) | Slower (three session loads) |
| **State Sync** | N/A (one source of truth) | Required (sync across agents) |

## Testing

### Test Multi-Turn Context

```bash
# Turn 1
curl -N -X POST "http://localhost:8000/api/chat/stream?message=Find%20AirPods&user_id=user_demo_001"

# Turn 2 (use session_id from Turn 1)
curl -N -X POST "http://localhost:8000/api/chat/stream?message=Yes%2C%20the%20first%20one&user_id=user_demo_001&session_id=sess_abc123"
```

**Expected Behavior:**
- Turn 1: Supervisor searches products, HP agent shows results
- Turn 2: HP agent understands "the first one" refers to previous search
- Inspect `.sessions/session_sess_abc123/` to see persisted messages

### Verify Context Passing

Check logs for:
```
Supervisor routing to HP Shopping Agent: Yes, the first one...
Passing 3 messages from Supervisor to HP Shopping Agent
```

This confirms full context is being passed!

### Inspect Session Storage

```bash
# View persisted messages
cat .sessions/session_sess_abc123/agents/agent_supervisor_001/messages/message_001.json

# Should show:
{
  "role": "user",
  "content": [{"text": "Find AirPods"}]
}
```

## Configuration

### Environment Variables

```bash
# Session storage directory
SESSION_STORAGE_DIR=./.sessions

# Session storage type (file or s3)
SESSION_STORAGE_TYPE=file

# For S3 storage (production)
# SESSION_STORAGE_TYPE=s3
# SESSION_S3_BUCKET=ghostcart-sessions
# SESSION_S3_PREFIX=sessions/
```

### Production Configuration

For distributed systems, switch to S3:

```python
# backend/src/services/session_manager_factory.py

if os.environ.get('SESSION_STORAGE_TYPE') == 's3':
    return S3SessionManager(
        session_id=session_id,
        bucket=os.environ['SESSION_S3_BUCKET'],
        prefix='sessions/'
    )
```

## Migration Path

If you later decide you need per-agent session management (Option B):

1. Add `session_manager` parameter to `create_hp_shopping_agent` and `create_hnp_delegate_agent`
2. Pass the same `session_mgr` to all agents in chat.py
3. Remove context passing logic from Supervisor tool functions
4. Each agent will maintain independent history in shared session

**But for now, Option A is sufficient and simpler!**

## Summary

**Option A Implementation:**
- ✅ Only Supervisor has SessionManager
- ✅ Specialist agents are stateless
- ✅ Supervisor passes full message history to specialists
- ✅ Single source of truth for conversation state
- ✅ Simpler, faster, easier to debug
- ✅ Aligned with Strands SDK best practices

**Files Modified:**
1. ✅ `backend/src/services/session_manager_factory.py` - Created
2. ✅ `backend/src/agents/supervisor_strands.py` - Added SessionManager, context passing
3. ✅ `backend/src/agents/hp_shopping_strands.py` - Kept stateless (no SessionManager)
4. ✅ `backend/src/api/chat.py` - Creates SessionManager, passes to Supervisor only

**Result:** Clean, simple, Strands SDK-compliant context management! 🎉
