# Strands SDK Context Management - Proper Implementation

## Current Implementation (Custom Thread-Local)

### What We're Doing Now ❌

**File:** `backend/src/agents/supervisor_strands.py`

```python
import threading

# Custom thread-local storage
_thread_local = threading.local()

@tool
async def shopping_assistant(user_request: str) -> str:
    # Manually check thread-local for conversation history
    if hasattr(_thread_local, 'conversation_messages'):
        shopping_messages = []
        for msg in _thread_local.conversation_messages:
            if msg.get('role') in ['user', 'assistant']:
                shopping_messages.append(msg)

        if len(shopping_messages) > 1:
            messages_to_send = shopping_messages

    # Pass messages manually to nested agent
    async for event in hp_shopping_agent.stream_async(messages_to_send):
        # ...
```

**File:** `backend/src/api/chat.py`

```python
# Manually set thread-local
from ..agents.supervisor_strands import _thread_local
_thread_local.conversation_messages = messages
```

### Problems with This Approach

1. **Not using Strands SDK features** - Reinventing the wheel
2. **Thread-local limitations** - Doesn't work well with async or distributed systems
3. **Manual context passing** - Error-prone, requires careful coordination
4. **No persistence** - Context lost when process restarts
5. **Hard to debug** - Thread-local state is implicit and hard to inspect

---

## Proper Implementation (Strands Built-In) ✅

### What Strands SDK Provides

#### 1. **SessionManager** - Persists agent state across invocations

Available implementations:
- `FileSessionManager` - Local filesystem storage
- `S3SessionManager` - AWS S3 storage
- `RepositorySessionManager` - Custom storage backend

#### 2. **ConversationManager** - Manages conversation history per agent

Features:
- `apply_management()` - Apply conversation management rules
- `reduce_context()` - Summarize/compress long conversations
- `get_state()` - Get current conversation state
- `restore_from_session()` - Restore from persisted session

#### 3. **Agent Constructor Parameters**

```python
Agent(
    model=bedrock_model,
    tools=[...],
    system_prompt="...",
    conversation_manager=ConversationManager(),  # Manages conversation
    session_manager=FileSessionManager(session_id="sess_123"),  # Persists state
    messages=[...]  # Initial conversation history
)
```

### How It Works

When you create an agent with a `session_manager`:

1. **Agent is created** → Loads state from session storage
2. **Agent invoked** → Uses loaded conversation history automatically
3. **Agent completes** → Saves updated state back to session storage
4. **Next invocation** → Automatically has full conversation history

**Key Insight:** You don't manually pass messages between invocations - the SessionManager does it for you!

---

## Recommended Implementation

### 1. Create Session Manager Factory

**New File:** `backend/src/services/session_manager_factory.py`

```python
"""
Session Manager Factory for Strands Agents

Creates appropriate SessionManager instances based on environment.
"""
from strands.session import FileSessionManager, SessionManager
from typing import Optional
import os

def create_session_manager(
    session_id: str,
    storage_dir: Optional[str] = None
) -> SessionManager:
    """
    Create a SessionManager for the given session.

    Args:
        session_id: Unique session identifier
        storage_dir: Directory for session storage (default: ./.sessions)

    Returns:
        Configured SessionManager instance

    Example:
        session_mgr = create_session_manager("sess_abc123")

        agent = Agent(
            model=model,
            tools=[...],
            session_manager=session_mgr
        )
    """
    if storage_dir is None:
        storage_dir = os.environ.get('SESSION_STORAGE_DIR', './.sessions')

    return FileSessionManager(
        session_id=session_id,
        storage_dir=storage_dir
    )
```

### 2. Update Agent Creation (Supervisor)

**File:** `backend/src/agents/supervisor_strands.py`

```python
from strands import Agent, tool
from strands.models import BedrockModel
from strands.session import SessionManager
from strands.agent.conversation_manager import ConversationManager
from typing import Optional

def create_supervisor_agent(
    hp_shopping_agent: Agent,
    hnp_delegate_agent: Optional[Agent] = None,
    model_id: Optional[str] = None,
    region_name: Optional[str] = None,
    session_manager: Optional[SessionManager] = None,  # NEW: Accept session manager
    event_queue: Optional[Any] = None
) -> Agent:
    """
    Create Supervisor Agent with proper Strands context management.

    Args:
        hp_shopping_agent: HP Shopping Agent instance
        hnp_delegate_agent: HNP Delegate Agent instance
        model_id: Bedrock model ID
        region_name: AWS region
        session_manager: SessionManager for persisting state (NEW)
        event_queue: Queue for custom tool events

    Returns:
        Supervisor Agent with automatic context management
    """
    from ..config import settings

    # Tool functions remain the same - NO manual context passing needed!
    @tool
    async def shopping_assistant(user_request: str) -> str:
        """Handle immediate purchase requests."""

        # No need to manually check thread-local or pass conversation history!
        # The hp_shopping_agent has its own session_manager that handles context.

        # Just call the nested agent - it already has conversation context
        full_response = ""
        final_result = None

        async for event in hp_shopping_agent.stream_async(user_request):
            if "data" in event:
                chunk = event["data"]
                full_response += chunk

            if "result" in event:
                final_result = event["result"]

        if final_result:
            if hasattr(final_result, 'message'):
                msg = final_result.message
                if isinstance(msg, dict) and 'content' in msg:
                    content = msg['content']
                    if isinstance(content, list) and len(content) > 0:
                        full_response = content[0].get('text', str(msg))
                    else:
                        full_response = str(content)
                else:
                    full_response = str(msg)

        return full_response if full_response else "HP Shopping Agent completed."

    @tool
    async def monitoring_assistant(user_request: str) -> str:
        """Handle monitoring setup requests."""

        # Same here - no manual context passing!
        # The hnp_delegate_agent manages its own context via session_manager

        if hnp_delegate_agent is None:
            return "Monitoring setup is not yet available."

        full_response = ""
        final_result = None

        async for event in hnp_delegate_agent.stream_async(user_request):
            if "data" in event:
                chunk = event["data"]
                full_response += chunk

            if "result" in event:
                final_result = event["result"]

        if final_result:
            if hasattr(final_result, 'message'):
                msg = final_result.message
                if isinstance(msg, dict) and 'content' in msg:
                    content = msg['content']
                    if isinstance(content, list) and len(content) > 0:
                        full_response = content[0].get('text', str(msg))
                    else:
                        full_response = str(content)
                else:
                    full_response = str(msg)

        return full_response if full_response else "HNP Delegate Agent completed."

    # Create Bedrock model
    bedrock_model = BedrockModel(
        model_id=model_id or settings.aws_bedrock_model_id,
        region_name=region_name or settings.aws_region,
        temperature=0.7
    )

    # Create Supervisor Agent with session management
    agent = Agent(
        model=bedrock_model,
        tools=[shopping_assistant, monitoring_assistant],
        system_prompt=SUPERVISOR_SYSTEM_PROMPT,
        conversation_manager=ConversationManager(),  # NEW: Manages conversation
        session_manager=session_manager  # NEW: Persists state
    )

    return agent
```

**Key Changes:**
- ❌ Removed `import threading` and `_thread_local`
- ✅ Added `session_manager` parameter
- ✅ Added `conversation_manager` to Agent constructor
- ❌ Removed manual context checking in tool functions
- ✅ Nested agents manage their own context automatically

### 3. Update Agent Creation (HP Shopping, HNP Delegate)

**File:** `backend/src/agents/hp_shopping_strands.py`

```python
from strands import Agent, tool
from strands.models import BedrockModel
from strands.session import SessionManager
from strands.agent.conversation_manager import ConversationManager
from typing import Optional, Callable

def create_hp_shopping_agent(
    search_products_fn: Callable,
    create_intent_fn: Callable,
    create_cart_fn: Callable,
    request_signature_fn: Callable,
    payment_agent: Agent,
    product_lookup_fn: Optional[Callable] = None,
    sse_emit_fn: Optional[Callable] = None,
    session_manager: Optional[SessionManager] = None,  # NEW
    model_id: Optional[str] = None,
    region_name: Optional[str] = None
) -> Agent:
    """
    Create HP Shopping Agent with proper context management.

    Args:
        ... (existing args)
        session_manager: SessionManager for persisting state (NEW)
    """
    from ..config import settings

    # Tool functions remain the same...
    @tool
    def search_products(query: str, max_results: int = 5) -> str:
        # ... existing implementation
        pass

    # Create Bedrock model
    bedrock_model = BedrockModel(
        model_id=model_id or settings.aws_bedrock_model_id,
        region_name=region_name or settings.aws_region,
        temperature=0.7
    )

    # Create agent with session management
    agent = Agent(
        model=bedrock_model,
        tools=[
            search_products,
            create_cart_mandate,
            request_user_signature,
            call_payment_agent
        ],
        system_prompt=HP_SHOPPING_SYSTEM_PROMPT,
        conversation_manager=ConversationManager(),  # NEW
        session_manager=session_manager  # NEW
    )

    return agent
```

**Same changes for:** `backend/src/agents/hnp_delegate_strands.py`

### 4. Update Chat Endpoint

**File:** `backend/src/api/chat.py`

```python
from ..services.session_manager_factory import create_session_manager

async def event_generator() -> AsyncIterator[str]:
    try:
        # ====================================================================
        # Session Management
        # ====================================================================

        if session_id:
            current_session_id = session_id
            session_data = await get_session(db, session_id)

            if not session_data:
                session_data = await create_session_db(
                    db=db,
                    user_id=user_id,
                    initial_flow_type="none"
                )
                current_session_id = session_data["session_id"]
        else:
            session_data = await create_session_db(
                db=db,
                user_id=user_id,
                initial_flow_type="none"
            )
            current_session_id = session_data["session_id"]

        # ====================================================================
        # Create Strands SessionManager
        # ====================================================================

        # NEW: Create session manager for this session
        session_mgr = create_session_manager(current_session_id)

        # Send connection event
        yield format_sse_event("connected", {
            "session_id": current_session_id,
            "message": "Connected to chat stream"
        })

        # ====================================================================
        # Create Agents with Session Management
        # ====================================================================

        # Create Payment Agent
        payment_agent = create_payment_agent_with_mocks()

        # Create event queue for custom events
        event_queue = asyncio.Queue()

        def sync_sse_emit(event_type: str, data: Dict[str, Any]):
            try:
                asyncio.create_task(event_queue.put((event_type, data)))
            except Exception as e:
                logger.error(f"Failed to queue SSE event {event_type}: {e}")

        # Create HP Shopping Agent WITH session manager
        hp_agent = create_hp_shopping_agent(
            search_products_fn=search_products,
            create_intent_fn=create_intent_mandate,
            create_cart_fn=create_cart_mandate,
            request_signature_fn=request_user_signature_wrapper,
            payment_agent=payment_agent,
            product_lookup_fn=get_product_by_id,
            sse_emit_fn=sync_sse_emit,
            session_manager=session_mgr  # NEW: Each agent gets same session manager
        )

        # Create HNP Delegate Agent WITH session manager
        hnp_agent = create_hnp_delegate_agent(
            search_products_func=search_products,
            create_intent_func=create_hnp_intent_wrapper,
            request_signature_func=request_intent_signature_wrapper,
            activate_monitoring_func=activate_monitoring_wrapper,
            session_manager=session_mgr  # NEW
        )

        # Create Supervisor Agent WITH session manager
        supervisor = create_supervisor_agent(
            hp_shopping_agent=hp_agent,
            hnp_delegate_agent=hnp_agent,
            session_manager=session_mgr,  # NEW
            event_queue=event_queue
        )

        # ====================================================================
        # Stream Agent Execution (NO manual context passing needed!)
        # ====================================================================

        # ❌ REMOVE THIS - No longer needed!
        # from ..agents.supervisor_strands import _thread_local
        # _thread_local.conversation_messages = messages

        # Emit thinking event
        yield format_sse_event("agent_thinking", {
            "message": "Understanding your request..."
        })

        response_text = ""
        final_result = None

        # Stream events from Supervisor
        # The supervisor automatically has conversation history from session_manager!
        async for event in supervisor.stream_async(message):  # Just pass current message!

            # Check for custom tool events
            while not event_queue.empty():
                try:
                    custom_event_type, custom_event_data = await asyncio.wait_for(
                        event_queue.get(), timeout=0.001
                    )
                    yield format_sse_event(custom_event_type, custom_event_data)
                except asyncio.TimeoutError:
                    break

            # Handle Strands SDK events
            if "data" in event:
                text_chunk = event["data"]
                response_text += text_chunk
                yield format_sse_event("agent_chunk", {
                    "text": text_chunk,
                    "complete": False
                })

            if "current_tool_use" in event:
                tool_info = event["current_tool_use"]
                yield format_sse_event("tool_use", {
                    "tool_name": tool_info.get("name"),
                    "tool_input": tool_info.get("input"),
                    "message": f"Executing {tool_info.get('name')}..."
                })

            if "result" in event:
                final_result = event["result"]

        # Extract final response
        # ...

        # ❌ NO need to manually update session - SessionManager does it automatically!
        # await update_session(db, current_session_id, context_data=state)

        # Send completion event
        yield format_sse_event("complete", {
            "session_id": current_session_id,
            "response": response_text,
            "flow_type": "supervisor"
        })

    except Exception as e:
        logger.error(f"Chat stream error: {e}", exc_info=True)
        yield format_sse_event("error", {
            "message": f"Error: {str(e)}",
            "error_type": type(e).__name__
        })
```

**Key Changes:**
- ✅ Create SessionManager once per request
- ✅ Pass same session_manager to all agents
- ✅ Remove thread-local import and usage
- ✅ Remove manual session state updates
- ✅ Just pass current message to stream_async - history handled automatically!

---

## How Context Flows (New Implementation)

### Multi-Turn Conversation Example

```
Turn 1: User: "Find AirPods"
  ↓
1. Chat endpoint creates FileSessionManager(session_id="sess_123")
2. All agents created with same session_manager
3. Supervisor.stream_async("Find AirPods") called
   - Supervisor loads its state from session storage (empty first time)
   - Supervisor calls shopping_assistant tool
   - HP Shopping Agent.stream_async("Find AirPods")
     - HP agent loads its state from session storage (empty first time)
     - HP agent searches products
     - HP agent saves state (message history) to session storage
   - Supervisor saves its state to session storage
4. Response: "I found 2 AirPods products..."

Turn 2: User: "Yes, the first one"
  ↓
1. Chat endpoint creates FileSessionManager(session_id="sess_123")  # Same session!
2. All agents created with same session_manager
3. Supervisor.stream_async("Yes, the first one") called
   - Supervisor loads state from session storage
     ✅ Automatically has Turn 1 conversation!
   - Supervisor calls shopping_assistant tool
   - HP Shopping Agent.stream_async("Yes, the first one")
     - HP agent loads state from session storage
       ✅ Automatically has "Find AirPods" and product results!
     - HP agent understands "the first one" refers to previous products
     - HP agent creates cart
     - HP agent saves updated state
   - Supervisor saves updated state
4. Response: "Created cart with AirPods Pro for $249.99"
```

### Session Storage Structure

```
./.sessions/
└── session_sess_123/
    ├── session.json                    # Session metadata
    └── agents/
        ├── agent_supervisor_001/
        │   ├── agent.json              # Supervisor metadata
        │   └── messages/
        │       ├── message_001.json    # Turn 1: "Find AirPods"
        │       ├── message_002.json    # Turn 1: Assistant response
        │       ├── message_003.json    # Turn 2: "Yes, the first one"
        │       └── message_004.json    # Turn 2: Assistant response
        │
        ├── agent_hp_shopping_001/
        │   ├── agent.json              # HP Shopping Agent metadata
        │   └── messages/
        │       ├── message_001.json    # "Find AirPods"
        │       ├── message_002.json    # Product search results
        │       ├── message_003.json    # "Yes, the first one"
        │       └── message_004.json    # Cart creation
        │
        └── agent_hnp_delegate_001/
            ├── agent.json              # HNP Delegate metadata (unused in this flow)
            └── messages/
```

---

## Benefits of Proper Strands Context Management

### 1. **Automatic Context Persistence**
- ✅ No manual save/load code
- ✅ Survives process restarts
- ✅ Each agent maintains independent history

### 2. **Clean Architecture**
- ✅ No thread-local hacks
- ✅ No manual context passing
- ✅ Explicit session management
- ✅ Easy to test and debug

### 3. **Scalability**
- ✅ FileSessionManager for dev/single-server
- ✅ S3SessionManager for distributed systems
- ✅ Custom RepositorySessionManager for databases

### 4. **Multi-Agent Coordination**
- ✅ Each agent has independent conversation history
- ✅ All agents share same session
- ✅ Easy to inspect agent state
- ✅ No context leakage between agents

### 5. **Debugging**
- ✅ Inspect session files to see conversation history
- ✅ Replay sessions for testing
- ✅ Clear separation of agent contexts

---

## Migration Steps

### Phase 1: Add Session Manager (Non-Breaking)

1. Create `session_manager_factory.py`
2. Add `session_manager` parameter to agent creation functions (with default `None`)
3. Test with session_manager enabled for new sessions

### Phase 2: Remove Thread-Local (Breaking)

1. Remove `_thread_local` from supervisor_strands.py
2. Remove thread-local setting from chat.py
3. Update all agent creation to require session_manager
4. Update tests

### Phase 3: Cleanup

1. Remove manual session state management in chat.py
2. Add session cleanup job (delete old session files)
3. Add monitoring for session storage usage

---

## Testing

### Test Session Persistence

```python
# Test that conversation history persists across requests
def test_session_persistence():
    session_id = "test_session_123"
    session_mgr = create_session_manager(session_id)

    # Turn 1
    agent = Agent(
        model=BedrockModel(...),
        session_manager=session_mgr
    )
    result1 = await agent.invoke_async("Find AirPods")

    # Turn 2 - Create new agent instance with same session
    agent2 = Agent(
        model=BedrockModel(...),
        session_manager=create_session_manager(session_id)  # Same session!
    )
    result2 = await agent2.invoke_async("Yes, the first one")

    # Agent2 should understand "the first one" refers to products from Turn 1
    assert "AirPods" in result2.message
```

### Test Multi-Agent Context Isolation

```python
def test_agent_context_isolation():
    session_id = "test_session_456"

    # Create supervisor and HP agent with same session
    session_mgr = create_session_manager(session_id)

    hp_agent = create_hp_shopping_agent(
        ...,
        session_manager=session_mgr
    )

    supervisor = create_supervisor_agent(
        hp_shopping_agent=hp_agent,
        session_manager=session_mgr
    )

    # Supervisor and HP agent should have independent message histories
    # but share same session storage
```

---

## Configuration

### Environment Variables

```bash
# Session storage directory
SESSION_STORAGE_DIR=./.sessions

# Session cleanup interval (days)
SESSION_CLEANUP_DAYS=7

# Use S3 for production
# SESSION_STORAGE_TYPE=s3
# SESSION_S3_BUCKET=ghostcart-sessions
```

### Production Considerations

For production, use S3SessionManager:

```python
from strands.session import S3SessionManager

def create_session_manager(session_id: str) -> SessionManager:
    if os.environ.get('SESSION_STORAGE_TYPE') == 's3':
        return S3SessionManager(
            session_id=session_id,
            bucket=os.environ['SESSION_S3_BUCKET'],
            prefix='sessions/'
        )
    else:
        return FileSessionManager(
            session_id=session_id,
            storage_dir=os.environ.get('SESSION_STORAGE_DIR', './.sessions')
        )
```

---

## Summary

**Current:** Custom thread-local storage, manual context passing ❌

**Proper:** Strands SessionManager + ConversationManager ✅

**Key Changes:**
1. Create SessionManager per request (same session_id)
2. Pass session_manager to all agent creation functions
3. Remove thread-local import and usage
4. Remove manual context passing in tool functions
5. Remove manual session state updates

**Result:** Clean, scalable, proper use of Strands SDK features!
