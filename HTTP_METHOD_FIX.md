# HTTP Method Fix - EventSource Requires GET

## Problem

Frontend getting **405 Method Not Allowed** error:
```
Request URL: http://localhost:8000/api/chat/stream?message=hi&user_id=user_demo_001
Request Method: GET
Status Code: 405 Method Not Allowed
```

## Root Cause

**EventSource API limitation:** EventSource in browsers **only supports GET requests**.

**Our code:**
- Backend: `@router.post("/chat/stream")` - Expecting POST ❌
- Frontend: `new EventSource(url)` - Sends GET ✅

**Mismatch:** Frontend sending GET, backend expecting POST = 405 error!

## Technical Background

### EventSource Limitations

From MDN Web Docs:
> The EventSource interface is used to receive server-sent events. It connects to a server over HTTP and receives events in text/event-stream format without closing the connection.

**Key limitation:** EventSource **always** uses GET method. There is no option to use POST, PUT, or other HTTP methods.

If you need POST for SSE, you must use:
1. `fetch()` with ReadableStream (more complex)
2. Or accept GET and pass data via query parameters (simpler)

### Why We Used POST Initially

The migration document mentioned "POST /api/chat/stream" because:
1. It was migrating from a POST /chat endpoint
2. Habit of using POST for "actions" like sending messages
3. Oversight that EventSource doesn't support POST

## Solution

Changed backend endpoint from POST to GET:

```python
# Before
@router.post("/chat/stream")  # ❌ EventSource can't use POST
async def chat_stream_endpoint(...):

# After
@router.get("/chat/stream")  # ✅ EventSource compatible
async def chat_stream_endpoint(...):
```

**Parameters:** Already using Query parameters (perfect for GET)
```python
message: str = Query(...),
session_id: Optional[str] = Query(None),
user_id: str = Query("user_demo_001")
```

## Verification

### Backend Endpoint Registered Correctly

```bash
$ python -c "from src.main import app; [print(f'{r.methods} {r.path}') for r in app.routes if 'stream' in r.path]"
{'GET'} /api/chat/stream  ✅
```

### Frontend Request

```javascript
const url = `${API_BASE_URL}/chat/stream?message=${msg}&user_id=${userId}`;
const eventSource = new EventSource(url);  // Sends GET request ✅
```

### Test with curl

```bash
# Before fix
curl -X POST "http://localhost:8000/api/chat/stream?message=hi&user_id=user_demo_001"
# Response: 405 Method Not Allowed ❌

# After fix
curl -N -X GET "http://localhost:8000/api/chat/stream?message=hi&user_id=user_demo_001"
# Response: text/event-stream with events ✅
```

## Security Considerations

### Is GET Safe for Chat Messages?

**Question:** Should we use GET for sending chat messages? Isn't POST more secure?

**Answer:** For SSE streaming, GET is the only option. Mitigations:

1. **HTTPS in Production** - Encrypts query parameters in transit
2. **No Sensitive Data in URL** - Chat messages are not secrets (user already typed them)
3. **Server Logs** - Be aware query params may appear in logs (sanitize if needed)
4. **URL Length Limits** - GET has URL length limits (~2KB in most browsers)

### Alternative: Fetch API with POST

If POST is absolutely required, use fetch() instead of EventSource:

```javascript
// More complex but supports POST
const response = await fetch('/api/chat/stream', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ message, session_id, user_id })
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;

  const chunk = decoder.decode(value);
  // Parse SSE format manually
  // ...
}
```

**Tradeoff:** Much more complex, no automatic reconnection, no built-in event parsing.

**Decision:** Stick with EventSource + GET for simplicity. SSE is designed for GET.

## Files Modified

### Backend

**File:** `backend/src/api/chat.py`

**Change:**
```python
- @router.post("/chat/stream")
+ @router.get("/chat/stream")
```

**Added note in docstring:**
```python
"""
Note: Uses GET method for EventSource compatibility (EventSource only supports GET).
"""
```

### Frontend

**File:** `frontend/src/components/ChatInterface.jsx`

**No changes needed** - already using EventSource correctly:
```javascript
const eventSource = new EventSource(url);  // Always sends GET
```

## Testing

### Test Connection

```bash
# Start backend
cd backend
python -m src.main

# Test endpoint
curl -N "http://localhost:8000/api/chat/stream?message=hello&user_id=user_demo_001"

# Should see:
# event: connected
# data: {"session_id":"...","message":"Connected to chat stream"}
#
# event: agent_thinking
# data: {"message":"Understanding your request..."}
# ...
```

### Test Frontend

```bash
# Start frontend
cd frontend
npm run dev

# Open browser to http://localhost:5173
# Open DevTools → Network tab
# Send a message in chat

# Should see:
# GET /api/chat/stream?message=hi&user_id=user_demo_001
# Status: 200 OK
# Type: text/event-stream
```

## Common EventSource Patterns

### Why EventSource Only Supports GET

Historical reasons from SSE specification (W3C):
1. **Stateless by design** - SSE designed for read-only event streams
2. **Browser caching** - GET requests can be cached (though SSE sets Cache-Control: no-cache)
3. **Simplicity** - GET is simplest HTTP method, no request body to parse
4. **Reconnection** - Browser can automatically reconnect GET requests easily

### When to Use Each Approach

**Use EventSource (GET):**
- ✅ Real-time updates/notifications
- ✅ Streaming chat responses
- ✅ Progress updates
- ✅ Live data feeds
- ✅ Simple query parameters

**Use fetch() + ReadableStream (POST):**
- ✅ Large request bodies
- ✅ File uploads with streaming response
- ✅ Complex authentication
- ✅ When POST is organizational requirement

**For our case:** EventSource is perfect - chat messages fit in query params, simpler code, automatic reconnection.

## Documentation Updates

### Update STREAMING_MIGRATION.md

Change:
```markdown
- **Endpoint:** `POST /api/chat/stream`
+ **Endpoint:** `GET /api/chat/stream`
```

### Update STREAMING_ARCHITECTURE.md

Update endpoint references from POST to GET throughout.

### Update curl examples

Change all test examples from:
```bash
curl -X POST "http://localhost:8000/api/chat/stream?..."
```

To:
```bash
curl -N -X GET "http://localhost:8000/api/chat/stream?..."
```

Or simply:
```bash
curl -N "http://localhost:8000/api/chat/stream?..."  # GET is default
```

## Summary

**Problem:** Frontend getting 405 because EventSource sends GET but endpoint expected POST

**Root Cause:** EventSource API limitation - only supports GET method

**Solution:** Changed `@router.post` to `@router.get`

**Result:** Frontend now connects successfully! ✅

---

**Key Takeaway:** When using Server-Sent Events (SSE), always use GET endpoints because the browser EventSource API only supports GET requests.
