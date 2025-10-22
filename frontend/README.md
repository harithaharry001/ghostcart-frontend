# GhostCart Frontend

React frontend for the GhostCart AP2 Protocol demonstration with real-time agent interaction.

## Architecture Overview

The frontend is built with React 18 and Vite, featuring:
- Real-time chat interface with SSE streaming
- Biometric-style signature modals
- Interactive mandate chain visualization
- Autonomous monitoring status displays

```
frontend/src/
├── components/      # Reusable UI components
├── context/         # React Context providers
├── pages/           # Page components
└── services/        # API and SSE clients
```

## Key Components

### ChatInterface (`components/ChatInterface.jsx`)
**Purpose**: Main chat interface for user-agent interaction

**Features**:
- Real-time message streaming via SSE
- Markdown rendering for agent responses
- Auto-scroll to latest messages
- Message history display
- Loading states and error handling

**SSE Events Handled**:
- `agent_message` - Display agent responses
- `product_results` - Show product cards
- `cart_created` - Display cart summary
- `signature_requested` - Trigger signature modal
- `monitoring_activated` - Show monitoring status
- `monitoring_check_complete` - Update monitoring status
- `autonomous_purchase_complete` - Show purchase notification

### SignatureModal (`components/SignatureModal.jsx`)
**Purpose**: Biometric-style mandate signing interface

**Features**:
- Fingerprint icon with pulse animation
- 1-second scanning animation
- Green checkmark on verification
- Mandate summary display
- Warning text for HNP pre-authorization
- Calls `/api/mandates/sign` endpoint

**Props**:
- `isOpen` - Modal visibility
- `mandateType` - "cart" or "intent"
- `mandateId` - ID of mandate to sign
- `mandateData` - Mandate details for display
- `onSign` - Callback after successful signature
- `onClose` - Callback to close modal

### MandateChainViz (`components/MandateChainViz.jsx`)
**Purpose**: Visual timeline of mandate chain

**Features**:
- Connected boxes showing Intent → Cart → Payment → Transaction
- Color-coded headers:
  - Gray: Context only (HP Intent)
  - Green: User signed (authorization)
  - Blue: Agent signed (autonomous action)
- Expandable boxes showing complete JSON
- Tooltips explaining AP2 flow
- Copy JSON and Download Chain buttons

**Props**:
- `transactionId` - Transaction to visualize
- `mandateChain` - Array of mandates in order

### MonitoringStatusCard (`components/MonitoringStatusCard.jsx`)
**Purpose**: Real-time monitoring job status display

**Features**:
- Active/Completed/Expired status badges
- Last check timestamp
- Current price and conditions
- Reason why conditions not met
- Cancel monitoring button
- Countdown to expiration

**Props**:
- `jobId` - Monitoring job ID
- `status` - Job status
- `productName` - Product being monitored
- `constraints` - Price and delivery limits
- `lastCheck` - Last check result
- `expiresAt` - Expiration timestamp

### ProductCard (`components/ProductCard.jsx`)
**Purpose**: Display product information

**Features**:
- Product image
- Name and description
- Price display
- Delivery estimate
- Stock status badge
- Select button

**Props**:
- `product` - Product object
- `onSelect` - Callback when selected

### CartDisplay (`components/CartDisplay.jsx`)
**Purpose**: Shopping cart summary

**Features**:
- Line items with quantities
- Subtotal, tax, shipping breakdown
- Grand total
- Delivery estimate
- Approve Purchase button

**Props**:
- `cartData` - Cart mandate data
- `onApprove` - Callback to approve cart

### NotificationBanner (`components/NotificationBanner.jsx`)
**Purpose**: Display important notifications

**Features**:
- Success/Warning/Error styling
- Auto-dismiss after timeout
- Close button
- Action buttons (View Details, View Chain)

**Props**:
- `type` - "success" | "warning" | "error"
- `message` - Notification text
- `actions` - Array of action buttons
- `onClose` - Callback to dismiss

## Context Providers

### SessionContext (`context/SessionContext.jsx`)
**Purpose**: Manage user session state

**Provides**:
- `sessionId` - Current session ID
- `userId` - Current user ID
- `createSession()` - Initialize new session
- `updateSession()` - Update session data

**Usage**:
```jsx
import { useSession } from '../context/SessionContext';

function MyComponent() {
  const { sessionId, userId } = useSession();
  // ...
}
```

### SSEContext (`context/SSEContext.jsx`)
**Purpose**: Manage Server-Sent Events connection

**Provides**:
- `connected` - Connection status
- `subscribe(eventType, callback)` - Subscribe to events
- `unsubscribe(eventType, callback)` - Unsubscribe from events
- `emit(eventType, data)` - Emit event to subscribers

**Usage**:
```jsx
import { useSSE } from '../context/SSEContext';

function MyComponent() {
  const { subscribe, unsubscribe } = useSSE();
  
  useEffect(() => {
    const handler = (data) => console.log(data);
    subscribe('agent_message', handler);
    return () => unsubscribe('agent_message', handler);
  }, []);
}
```

## Services

### API Service (`services/api.js`)
**Purpose**: HTTP client for REST API calls

**Methods**:
- `searchProducts(query, maxPrice)` - Search product catalog
- `signMandate(mandateId, userId)` - Sign a mandate
- `getMandate(mandateId)` - Get mandate details
- `getPaymentMethods(userId)` - Get tokenized payment methods
- `getTransactions(userId)` - Get transaction history
- `getTransaction(transactionId)` - Get transaction details
- `getMonitoringStatus(userId)` - Get active monitoring jobs
- `cancelMonitoring(jobId)` - Cancel monitoring job

**Configuration**:
```javascript
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'\;
```

### SSE Service (`services/sse.js`)
**Purpose**: Server-Sent Events client

**Methods**:
- `connect(sessionId, userId)` - Establish SSE connection
- `disconnect()` - Close SSE connection
- `onMessage(callback)` - Handle incoming messages
- `onError(callback)` - Handle connection errors

**Event Format**:
```javascript
{
  event: 'agent_message',
  data: {
    message: 'Searching for products...',
    timestamp: '2025-10-22T08:00:00Z'
  }
}
```

## Pages

### Home (`pages/Home.jsx`)
**Purpose**: Main application page

**Layout**:
- Header with GhostCart branding
- AP2 Info Section (protocol explanation)
- Chat Interface (main interaction area)
- Orders Section (transaction history)

## Styling

### Tailwind CSS Configuration
- Custom color palette for AP2 branding
- Responsive breakpoints
- Custom animations (pulse, fade-in)
- Typography scale

### Key Classes:
- `btn-primary` - Primary action buttons
- `btn-secondary` - Secondary action buttons
- `card` - Card container
- `badge` - Status badges
- `modal-overlay` - Modal backdrop
- `timeline` - Mandate chain timeline

## State Management

### Local Component State
- Form inputs
- Modal visibility
- Loading states
- Error messages

### Context State
- User session
- SSE connection
- Global notifications

### Server State (via API)
- Products
- Mandates
- Transactions
- Monitoring jobs

## Real-Time Updates

### SSE Event Flow:
```
1. User sends message
2. Backend processes with agents
3. Backend emits SSE events
4. Frontend receives events
5. UI updates in real-time
```

### Event Types:
- **agent_message**: Agent responses
- **product_results**: Search results
- **cart_created**: Cart mandate created
- **signature_requested**: Trigger signature modal
- **monitoring_activated**: Monitoring started
- **monitoring_check_started**: Check beginning
- **monitoring_check_complete**: Check result
- **autonomous_purchase_starting**: HNP purchase triggered
- **autonomous_purchase_complete**: HNP purchase done

## Environment Variables

Create `.env` file:
```bash
VITE_API_URL=http://localhost:8000
```

For production:
```bash
VITE_API_URL=https://your-alb-url.amazonaws.com
```

## Running Locally

### Install Dependencies
```bash
npm install
```

### Development Server
```bash
npm run dev
```

Runs on http://localhost:5173

### Build for Production
```bash
npm run build
```

Output in `dist/` directory

### Preview Production Build
```bash
npm run preview
```

### Linting
```bash
npm run lint
```

### Format Code
```bash
npm run format
```

## Testing

### Component Testing
```bash
npm test
```

### E2E Testing
```bash
npm run test:e2e
```

## Build & Deployment

### Vite Build
```bash
npm run build
```

Creates optimized production build in `dist/`:
- Minified JavaScript
- Optimized CSS
- Asset hashing for cache busting
- Source maps (optional)

### Docker Build
Frontend is built and served by backend in production:
```dockerfile
# Frontend build stage
FROM node:18-alpine AS frontend-builder
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Backend serves frontend static files
COPY --from=frontend-builder /frontend/dist /app/frontend/dist
```

### AWS Amplify Deployment
Alternative deployment via Amplify:
```bash
chmod +x deploy-amplify.sh
./deploy-amplify.sh
```

## Performance Optimization

### Code Splitting
- Lazy load routes
- Dynamic imports for large components
- Vendor chunk separation

### Asset Optimization
- Image lazy loading
- WebP format for images
- SVG for icons
- Font subsetting

### Caching Strategy
- Service worker for offline support
- Cache API responses
- LocalStorage for session data

### Bundle Size
- Tree shaking unused code
- Minification
- Gzip compression
- Current bundle: ~150KB gzipped

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Accessibility

- ARIA labels on interactive elements
- Keyboard navigation support
- Screen reader friendly
- Color contrast compliance (WCAG AA)
- Focus indicators

## Troubleshooting

### SSE Connection Fails
- Check API_URL environment variable
- Verify CORS configuration on backend
- Check browser console for errors
- Ensure backend is running

### Signature Modal Not Appearing
- Check SSE event subscription
- Verify `signature_requested` event received
- Check modal state management
- Look for JavaScript errors

### Products Not Loading
- Verify `/api/products/search` endpoint
- Check network tab for API calls
- Verify backend is running
- Check for CORS errors

### Mandate Chain Not Displaying
- Verify transaction has complete mandate chain
- Check `/api/transactions/{id}` response
- Ensure all mandate IDs are valid
- Check for missing mandate data

## Additional Resources

- [React Documentation](https://react.dev/)
- [Vite Documentation](https://vitejs.dev/)
- [Tailwind CSS](https://tailwindcss.com/)
- [Server-Sent Events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events)

---

For backend documentation, see [backend/README.md](../backend/README.md)
