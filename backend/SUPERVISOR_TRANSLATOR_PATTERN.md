# Supervisor as Translator Pattern - Implementation

## Problem Statement

When Supervisor passed its full message history to specialist agents (HP Shopping, HNP Delegate), it caused **tool_use/tool_result mismatch errors** because:

1. Supervisor's message history contains Supervisor's tool calls (`shopping_assistant`, `monitoring_assistant`)
2. Specialist agents don't have these tools - they have different tools (`search_products`, `create_shopping_cart`, etc.)
3. Claude's conversation format requires every `tool_use` block to have a matching `tool_result` block immediately after
4. Result: **Claude API rejects the conversation as malformed**

**Error example:**
```
messages.11: `tool_use` ids were found without `tool_result` blocks immediately after
```

## Solution: Supervisor as Intelligent Translator

Instead of passing raw message history, the Supervisor now acts as an **intelligent translator** that reformulates user requests with full context before calling specialist agents.

### Architecture Before (Broken)

```
User: "Yes!"
  ↓
Supervisor: [Passes entire message history including tool_use blocks]
  ↓
HP Shopping Agent: [Receives messages with unknown tool_use blocks]
  ↓
❌ ERROR: tool_use/tool_result mismatch
```

### Architecture After (Fixed)

```
User: "Yes!"
  ↓
Supervisor: [Checks conversation history: user was looking at Philips HD7462]
Supervisor: [Reformulates: "User wants to purchase Philips HD7462 (product_id: prod_philips_hd7462, price: $69)"]
  ↓
HP Shopping Agent: [Receives clear, self-contained instruction]
  ↓
✅ SUCCESS: No tool_use/tool_result issues
```

## Key Principles

### 1. Supervisor's Responsibilities

The Supervisor must:
- **Understand user intent** from full conversation context
- **Extract references** from conversation (e.g., "the first one" → actual product details)
- **Reformulate requests** with complete context (product names, IDs, prices, quantities)
- **Provide self-contained instructions** that specialists can execute independently

### 2. Specialist Agents are Stateless

Specialist agents (HP Shopping, HNP Delegate):
- **NO SessionManager** - they don't persist conversation history
- **NO message history** - they only receive reformulated requests
- **Self-contained execution** - each request has all needed context
- **Simpler reasoning** - focus on domain logic, not conversation tracking

### 3. Examples of Good Translation

#### Example 1: Affirmative Response
```
Supervisor conversation history:
- Supervisor: "I found 2 coffee makers: 1) Philips HD7462 ($69), 2) Keurig K-Mini ($59)"
- User: "The first one"

❌ BAD: shopping_assistant("The first one")
✅ GOOD: shopping_assistant("User wants to purchase the Philips HD7462 Coffee Maker (product_id: prod_philips_hd7462, price: $69, quantity: 1)")
```

#### Example 2: Generic Confirmation
```
Supervisor conversation history:
- Supervisor: "Would you like the AirPods Pro for $249?"
- User: "I'll take it"

❌ BAD: shopping_assistant("I'll take it")
✅ GOOD: shopping_assistant("User confirms purchase of AirPods Pro (product_id: prod_airpods_pro, price: $249, quantity: 1)")
```

#### Example 3: Initial Request (No Translation Needed)
```
User: "I need a coffee maker under $70"

✅ GOOD: shopping_assistant("I need a coffee maker under $70")
(Clear request, no ambiguity, passes through as-is)
```

## Implementation Details

### File: `backend/src/agents/supervisor_strands.py`

#### System Prompt Updates

Added section: **CRITICAL RULES FOR MULTI-TURN CONVERSATIONS**

```python
**Your Job as Orchestrator:**

You are the intelligent translator between the user and specialist agents. You must:
1. **Understand user intent** from conversation context
2. **Reformulate requests** with full clarity for specialist agents
3. **Extract references** from conversation (e.g., "the first one" → actual product name)
4. **Provide self-contained instructions** so specialists don't need your conversation history
```

Key rules:
1. Be an Intelligent Translator, Not a Messenger
2. Extract Context from Affirmative Responses
3. Use Examples of Good Translation
4. Provide Self-Contained Instructions

#### Tool Implementation Updates

**Before:**
```python
async def shopping_assistant(user_request: str) -> str:
    # Get Supervisor's full conversation history
    supervisor = supervisor_agent_ref['agent']
    messages_to_pass = user_request

    if supervisor and hasattr(supervisor, 'messages') and supervisor.messages:
        # Pass Supervisor's full message history to HP agent
        messages_to_pass = supervisor.messages

    async for event in hp_shopping_agent.stream_async(messages_to_pass):
```

**After:**
```python
async def shopping_assistant(user_request: str) -> str:
    # Supervisor has already reformulated user_request with full context
    # HP agent is STATELESS - it receives self-contained, clear instructions
    # No need to pass Supervisor's message history - avoids tool_use/tool_result mismatch

    async for event in hp_shopping_agent.stream_async(user_request):
```

Same change applied to `monitoring_assistant` tool.

## Context Management Architecture (Option A)

This pattern works with our **Option A** architecture:

```
┌─────────────────────────────────────────────┐
│           Supervisor Agent                   │
│  ✅ Has SessionManager (conversation state)  │
│  ✅ Has full conversation history            │
│  ✅ Translates user intent → clear requests  │
└─────────────────────────────────────────────┘
                    │
        ┌───────────┴──────────┐
        ▼                      ▼
┌──────────────┐      ┌──────────────┐
│ HP Shopping  │      │ HNP Delegate │
│   Agent      │      │    Agent     │
│ ❌ Stateless  │      │ ❌ Stateless  │
│ ❌ No history │      │ ❌ No history │
│ ✅ Clear reqs │      │ ✅ Clear reqs │
└──────────────┘      └──────────────┘
```

## Benefits

1. **No tool_use/tool_result mismatch** - Specialist agents never see Supervisor's tool calls
2. **Clearer specialist reasoning** - Agents receive explicit, detailed instructions
3. **Simpler architecture** - Specialist agents are truly stateless
4. **Better debugging** - Tool inputs show full context, easier to trace issues
5. **Follows Strands patterns** - Aligns with SDK's agent-as-tools design

## Testing

### Test Case 1: Affirmative Response
```
User: "Find coffee makers"
Supervisor: [Shows products]
User: "Yes"
Expected: Supervisor reformulates to "User wants to purchase [first product with full details]"
```

### Test Case 2: Numbered Selection
```
User: "Show me laptops"
Supervisor: [Shows 3 laptops]
User: "The second one"
Expected: Supervisor extracts second laptop details and reformulates
```

### Test Case 3: Generic Confirmation
```
User: "Get me AirPods"
Supervisor: "AirPods Pro at $249?"
User: "I'll take it"
Expected: Supervisor reformulates with product_id, price, quantity
```

## Migration Notes

**Files Changed:**
- `backend/src/agents/supervisor_strands.py` - System prompt and tool implementations

**No Changes Needed:**
- `backend/src/agents/hp_shopping_strands.py` - Already stateless
- `backend/src/agents/hnp_delegate_strands.py` - Already stateless
- `backend/src/api/chat.py` - Context management already correct

**Breaking Changes:** None - this is an internal architectural improvement

## Related Documentation

- `CONTEXT_MANAGEMENT.md` - Overview of Option A architecture
- `HTTP_METHOD_FIX.md` - EventSource GET requirement
- `STREAMING_ARCHITECTURE.md` - SSE streaming design

## Summary

**Problem:** Passing Supervisor's message history caused tool_use/tool_result mismatch errors

**Solution:** Supervisor acts as intelligent translator, reformulating ambiguous requests with full context

**Result:** Specialist agents receive clear, self-contained instructions without message history pollution

**Key Insight:** Supervisor has conversation context - use it to make specialist agents' jobs easier!
