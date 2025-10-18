# Feature Specification: GhostCart - AP2 Protocol Demonstration

**Feature Branch**: `002-read-the-specification`
**Created**: 2025-10-17
**Status**: Draft
**Input**: User description: "Build GhostCart proving Agent Payments Protocol v0.1 from https://ap2-protocol.org/specification/ achieves interoperability with AWS Strands SDK"

## Clarifications

### Session 2025-10-17

- Q: Why is Intent Mandate signature optional for HP flow? It is captured by agent, right? → A: Intent Mandate is ALWAYS created and captured by the agent in both HP and HNP flows to record the user's original request. The difference is the signature requirement: In HP flow, user signature is NOT required on Intent because the Cart signature serves as the authorization (user approves specific items/prices). In HNP flow, user signature IS required on Intent because it serves as the pre-authorization for future autonomous action. Intent creation (captured) vs Intent signature (optional in HP, required in HNP) are distinct per AP2 specification.

### Session 2025-10-18

- Q: How do we implement "Strands Agent" when the SDK package name is unclear and not in requirements.txt? → A: Use Strands SDK from https://github.com/strands-agents/sdk-python. Install packages: `strands-agents` and `strands-agents-tools` (NOT "aws-strands-sdk"). Implementation pattern: (1) Import `Agent` from `strands` and `tool` decorator for custom functions, (2) Configure BedrockModel with `model_id="us.anthropic.claude-sonnet-4-20250514-v1:0"` and `streaming=True`, (3) Define tools using `@tool` decorator with type hints and docstrings, (4) Create agent instances with `Agent(model=bedrock_model, tools=[...])`, (5) For multi-agent orchestration, specialist agents can be invoked as tools by the Supervisor agent. Requires Python 3.10+ and AWS Bedrock credentials with Claude 4 Sonnet access in your configured region.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Human-Present Immediate Purchase (Priority: P1)

A user wants to find and buy a product right now. They search for an item, see results with clear product details, select one, review the cart, approve the purchase with biometric-style signature, and complete the transaction. They can view a complete cryptographic audit trail showing how their approval flowed through the system.

**Why this priority**: This is the foundational purchase flow that demonstrates AP2 protocol compliance for real-time transactions. It's the most common e-commerce pattern and must work flawlessly to validate the entire system.

**Independent Test**: Can be fully tested by performing a search, selecting a product, approving the cart with signature, and completing payment. Delivers a working e-commerce purchase flow with mandate chain visualization.

**Acceptance Scenarios**:

1. **Given** user is on the GhostCart home screen, **When** user types "Find me a coffee maker under 70 dollars", **Then** system streams real-time messages ("Analyzing your request", "Routing to shopping assistant", "Searching products") and displays 3 matching coffee makers with images, names, prices around $69, and delivery estimates like "2 day delivery"

2. **Given** user sees product results, **When** user clicks on "Philips HD7462 Coffee Maker", **Then** cart appears showing exact item name, price $69, delivery "2 days", total $69, and blue "Approve Purchase" button

3. **Given** user views cart, **When** user clicks "Approve Purchase", **Then** biometric-style modal appears with fingerprint icon, text "Confirm with Touch ID", description "Authorizing purchase of Philips HD7462 for $69", and "Confirm" button

4. **Given** signature modal is displayed, **When** user clicks "Confirm" button, **Then** fingerprint icon pulses with 1-second scanning animation, green checkmark appears with "Verified" text, modal closes, and messages stream "Validating signature", "Processing payment of $69", "Payment authorized"

5. **Given** payment is authorized, **When** transaction completes, **Then** success screen shows "Payment Authorized!", transaction ID like "txn_abc123", authorization code like "AUTH_xy45z8", green background, and "View Chain" button

6. **Given** transaction is complete, **When** user clicks "View Chain", **Then** visual timeline displays connected boxes: Intent Mandate (gray header "Context Only - Not Signed" with tooltip explaining it's for audit trail only per AP2 human-present flow), Cart Mandate (green header "User Signed - Authorization" with checkmark and tooltip explaining this is the authorization per AP2), Payment Mandate (showing "Payment Agent Signed"), and Transaction (showing "Authorized" with green badge)

7. **Given** mandate chain is displayed, **When** user clicks any mandate box, **Then** box expands showing complete JSON structure matching AP2 schema with "Copy JSON" and "Download Chain" buttons at bottom

**AP2 Protocol Flow Explanation** (defines valid behavior per external specification):

In the human-present flow per AP2 specification:
- Intent Mandate is created capturing the user's search query for audit trail purposes but does NOT require user signature
- Cart Mandate is created by the merchant with exact items and totals and MUST have user signature as this is the authorization per AP2 human-present specification
- Payment Mandate is created by the Payment Agent referencing the Cart Mandate
- Complete mandate chain is stored forming cryptographic audit trail from intent through transaction
- User signature on Cart is the authorization mechanism, not Intent

---

### User Story 2 - Human-Not-Present Autonomous Monitoring (Priority: P2)

A user wants to set up autonomous purchasing when specific conditions are met in the future. They define price and delivery constraints, pre-authorize the agent with signature, and let the system monitor continuously. When conditions are met, the agent autonomously completes the purchase without further user interaction. The user is notified and can verify the agent acted within their pre-authorized constraints.

**Why this priority**: This demonstrates the innovative autonomous agent capability and AP2's human-not-present flow with Intent-based pre-authorization. It's the differentiator that showcases AI agent value beyond traditional e-commerce.

**Independent Test**: Can be fully tested by setting up monitoring with constraints, waiting for conditions to be met (can be simulated), verifying autonomous purchase occurs without user interaction, and confirming mandate chain shows proper Intent→Cart relationship per AP2 specification.

**Acceptance Scenarios**:

1. **Given** user is on GhostCart, **When** user types "Buy AirPods if price drops below 180 dollars and delivery is 2 days or less", **Then** messages stream showing "Analyzing constraints", "Routing to monitoring assistant", and agent responds with confirmation message "I can monitor Apple AirPods Pro and automatically purchase when your conditions are met. Let me confirm: Maximum price $180, Maximum delivery 2 days. I will check every 5 minutes for 7 days. Shall I set up this monitoring?" with green "Yes, Monitor This" button

2. **Given** user sees monitoring confirmation, **When** user clicks "Yes, Monitor This" button, **Then** modal appears with fingerprint icon, text "Confirm with Touch ID", warning text in orange "You are authorizing autonomous purchase. The agent will buy automatically when conditions are met without asking you again.", and "Confirm" button

3. **Given** pre-authorization modal is displayed, **When** user clicks "Confirm", **Then** scanning animation plays, verification appears, modal closes, messages stream "Intent Mandate signed", "Monitoring activated", "First check in 5 minutes", and status card appears showing "Monitoring Active for Apple AirPods Pro, Checking every 5 minutes, Conditions: Price below $180 and delivery within 2 days, Expires in 7 days" with "Cancel Monitoring" button

4. **Given** monitoring is active, **When** first check occurs at 10:00 AM and finds AirPods at $249, **Then** status updates to show "Last checked: 10:00 AM, Current price: $249, Status: Conditions not met - price too high"

5. **Given** monitoring continues with multiple checks, **When** check at 10:10 AM finds AirPods at $175 with 1 day delivery, **Then** messages burst rapidly "Conditions met! Price $175, delivery 1 day", "Creating Cart Mandate automatically", "Processing payment autonomously", "Payment authorized!"

6. **Given** autonomous purchase completes, **When** user sees notification, **Then** large notification displays "Autonomous Purchase Complete! Apple AirPods Pro purchased for $175. You authorized this purchase on [date] with constraints: price below $180, delivery within 2 days. Transaction ID: txn_def789" with "View Details" and "View Chain" buttons, and monitoring status card changes to "Monitoring Completed - Purchase successful"

7. **Given** autonomous purchase notification is displayed, **When** user clicks "View Chain", **Then** timeline shows Intent box (green header "User Signed - Pre-Authorization" with tooltip "You granted the agent authority to act when conditions met per AP2 human-not-present flow"), Cart box (blue header "Agent Signed - Autonomous Action" with robot icon, tooltip "Agent acted on your behalf based on Intent authority per AP2 specification", and displays "References Intent ID: intent_hnp_xyz123" showing required mandate chain link), Payment box (showing "Payment Agent Signed" with badge "Human Not Present Flag Set"), and Transaction (showing "Authorized")

**AP2 Protocol Flow Explanation** (defines valid behavior per external specification):

In the human-not-present flow per AP2 specification:
- Intent Mandate is created with user's constraints and expiration time and MUST have user signature as this is the pre-authorization per AP2 human-not-present specification
- Background job monitors conditions continuously
- When conditions are met, Cart Mandate is created by the agent with agent signature (NOT user signature) per AP2 human-not-present flow
- Cart Mandate MUST reference Intent Mandate ID per AP2 chain validation requirement
- Payment Mandate is created with human-not-present flag set per AP2 specification, signaling to payment network this is an autonomous transaction
- Complete mandate chain proves agent acted within pre-authorized constraints

---

### User Story 3 - Intelligent Agent Routing (Priority: P3)

The supervisor agent analyzes user messages using LLM reasoning to determine whether the user wants immediate purchase or future monitoring, and routes to the appropriate specialist agent. For ambiguous requests, the agent asks clarifying questions before routing.

**Why this priority**: This demonstrates the AWS Strands agent architecture and LLM-based reasoning instead of brittle keyword matching. It's essential for user experience but can be tested after core payment flows work.

**Independent Test**: Can be tested by sending various phrasings of immediate and monitoring intents, verifying correct agent routing, and testing ambiguous cases receive clarifying questions.

**Acceptance Scenarios**:

1. **Given** user types immediate intent with present tense, **When** user sends "Find running shoes under 100", **Then** Supervisor Agent routes to HP Shopping Agent and user sees product search results

2. **Given** user types monitoring intent with conditional logic, **When** user sends "Buy AirPods if price drops below 180", **Then** Supervisor Agent routes to HNP Delegate Agent and user sees monitoring setup confirmation

3. **Given** user types future monitoring intent, **When** user sends "Monitor for laptop deals under 800", **Then** Supervisor Agent routes to HNP Delegate Agent

4. **Given** user types ambiguous request, **When** user sends "Get me AirPods" with no timing or conditions, **Then** Supervisor streams clarifying question "I can help you with AirPods. Would you like to: 1) Buy now at current price of $249, or 2) Set up monitoring to purchase automatically when price drops?" and waits for user response before routing

5. **Given** routing decision is made, **When** Supervisor Agent routes to specialist, **Then** Supervisor never executes domain logic itself, only orchestrates and delegates per Strands pattern

---

### Edge Cases

- What happens when payment is declined? Display specific decline reason (insufficient funds, card expired, fraud suspected) with "Try Another Payment Method" button allowing user to select different payment method and retry purchase.

- What happens when product is out of stock in human-present flow? Show message "Product unavailable" with two options: "View Alternatives" (shows similar products in same category/price range) or "Set Up Monitoring" (transitions to HNP flow to monitor when back in stock).

- What happens when product is out of stock during human-not-present monitoring? Continue monitoring checking both price constraint AND availability status every iteration. When product becomes available and price meets constraint, proceed with automatic purchase. If monitoring expires after 7 days before product available, notify user monitoring period ended.

- What happens when monitoring conditions are never met? After 7 days when Intent Mandate reaches expiration, send notification "Conditions were not met during monitoring period", show current price for reference, offer option to set up new monitoring with same or adjusted constraints.

- What happens when signature verification fails? Display error "Signature verification failed" with specific details about which mandate signature is invalid (for debugging), with "Retry" button to retry signing flow.

- What happens when agent is unclear on user intent? Ask clarifying questions rather than guessing. Examples: "Did you mean buy now or set up monitoring?", "Which model - Pro or Max?", "Did you mean total price or per item?" Never assume.

- What happens when server restarts during active monitoring? Active monitoring jobs survive restart because they are persisted with complete state, and resume checking on schedule without user having to re-authorize.

## Requirements *(mandatory)*

### Functional Requirements

#### Core Purchase Flow (Human-Present)

- **FR-001**: System MUST accept natural language product search queries and display matching products with images, names, prices, and delivery estimates
- **FR-002**: System MUST allow user to select a product and view cart with exact item details, price, delivery estimate, and total
- **FR-003**: System MUST present biometric-style signature interface with fingerprint icon, confirmation message, mandate summary, and clear visual feedback (scanning animation, verification checkmark)
- **FR-004**: System MUST create Intent Mandate capturing user search query for audit trail (without requiring user signature in human-present flow per AP2)
- **FR-005**: System MUST create Cart Mandate with exact items and totals requiring user signature as the authorization per AP2 human-present specification
- **FR-006**: System MUST create Payment Mandate referencing Cart Mandate
- **FR-007**: System MUST validate complete mandate chain from Intent through Cart to Payment to Transaction
- **FR-008**: System MUST display transaction result with transaction ID, authorization code, and "View Chain" button
- **FR-009**: System MUST visualize mandate chain as connected timeline showing Intent (gray "Context Only - Not Signed"), Cart (green "User Signed - Authorization"), Payment (agent signed), and Transaction (status badge)
- **FR-010**: System MUST allow user to expand any mandate box to view complete JSON structure matching AP2 schema
- **FR-011**: System MUST provide "Copy JSON" and "Download Chain" buttons for audit trail export

#### Autonomous Monitoring Flow (Human-Not-Present)

- **FR-012**: System MUST parse user monitoring requests with price constraints, delivery constraints, and monitoring duration
- **FR-013**: System MUST present monitoring confirmation with clear constraint summary, check frequency (5 minutes), and monitoring duration (7 days default)
- **FR-014**: System MUST display pre-authorization modal with orange warning "You are authorizing autonomous purchase. The agent will buy automatically when conditions are met without asking you again."
- **FR-015**: System MUST create Intent Mandate with user constraints and expiration requiring user signature as the pre-authorization per AP2 human-not-present specification
- **FR-016**: System MUST execute background monitoring checking conditions every 5 minutes
- **FR-017**: System MUST display monitoring status card showing "Monitoring Active", product name, check frequency, conditions, expiration, and "Cancel Monitoring" button
- **FR-018**: System MUST update status card after each check with timestamp, current price, and reason why conditions not met (if applicable)
- **FR-019**: System MUST create Cart Mandate with agent signature (NOT user signature) when conditions are met per AP2 human-not-present flow
- **FR-020**: System MUST include Intent Mandate ID reference in Cart Mandate per AP2 chain validation requirement
- **FR-021**: System MUST set human-not-present flag in Payment Mandate per AP2 specification
- **FR-022**: System MUST validate that Cart Mandate does not exceed Intent Mandate constraints before processing payment
- **FR-023**: System MUST display large notification when autonomous purchase completes showing product, price, original authorization date and constraints, and transaction ID
- **FR-024**: System MUST show mandate chain for HNP flow with Intent (green "User Signed - Pre-Authorization"), Cart (blue "Agent Signed - Autonomous Action" with Intent ID reference), Payment (with HNP flag badge), and Transaction

#### Agent Architecture (Strands Patterns)

- **FR-025**: System MUST implement Supervisor Agent that orchestrates and never executes domain logic
- **FR-026**: System MUST implement HP Shopping Agent that only handles immediate purchases
- **FR-027**: System MUST implement HNP Delegate Agent that only handles monitoring setup
- **FR-028**: System MUST implement Payment Agent as reusable component with zero GhostCart domain coupling
- **FR-029**: System MUST use LLM (Claude Sonnet 4.5 via Bedrock) for routing decisions based on linguistic analysis, not hardcoded keyword matching
- **FR-030**: System MUST route immediate purchase requests (present tense, no conditionals) to HP Shopping Agent
- **FR-031**: System MUST route monitoring requests (future action, conditional logic) to HNP Delegate Agent
- **FR-032**: System MUST ask clarifying questions for ambiguous requests before routing
- **FR-033**: System MUST prevent direct user interaction with Payment Agent (only called by specialist agents)

#### Payment Agent Reusability

- **FR-034**: Payment Agent MUST have zero knowledge of products, categories, pricing, merchants, or UI
- **FR-035**: Payment Agent MUST accept only AP2 mandate primitives as input following official schemas
- **FR-036**: Payment Agent MUST return payment results as output with no GhostCart-specific data
- **FR-037**: Payment Agent MUST be extractable to separate folder and usable in different commerce scenarios (travel, subscriptions, B2B) without code modifications
- **FR-038**: Payment Agent MUST validate mandate chains per AP2 rules: for HP flow verify Cart has user signature, for HNP flow verify Intent has user signature and Cart references Intent ID
- **FR-039**: Payment Agent MUST retrieve tokenized credentials, never raw payment data, per AP2 role separation
- **FR-040**: Payment Agent MUST return AP2 standard error codes: `ap2:mandate:chain_invalid`, `ap2:mandate:signature_invalid`, `ap2:mandate:expired`, `ap2:mandate:constraints_violated`, `ap2:credentials:unavailable`, `ap2:payment:declined`

#### Real-Time Transparency

- **FR-041**: System MUST stream agent messages in real-time via Server-Sent Events without page refresh
- **FR-042**: System MUST show progress messages like "Analyzing your request", "Searching for products", "Creating Cart Mandate", "Waiting for your approval", "Validating signature", "Processing payment", "Payment authorized"
- **FR-043**: System MUST show monitoring progress messages like "Setting up monitoring", "Checking every 5 minutes", "Will monitor for 7 days", "Checking prices at [timestamp]", "Current price X - conditions not met because [reason]"
- **FR-044**: System MUST show rapid message burst when autonomous purchase triggers: "Conditions met at price X", "Processing automatically", "Purchase complete"
- **FR-045**: System MUST display signature validation status with visual indicators (checkmarks for valid, X for invalid)

#### Error Handling

- **FR-046**: System MUST handle payment declined with specific reason and "Try Another Payment Method" button
- **FR-047**: System MUST handle out of stock in HP flow with "View Alternatives" and "Set Up Monitoring" options
- **FR-048**: System MUST handle out of stock during HNP monitoring by continuing to monitor both price and availability
- **FR-049**: System MUST handle monitoring expiration after 7 days with notification showing final price and option to create new monitoring
- **FR-050**: System MUST handle signature validation failure with specific error details and "Retry" option
- **FR-051**: System MUST display clear, actionable error messages with no technical jargon for end users

#### Mock Services

- **FR-052**: System MUST provide mock product catalog with approximately 15 products across Electronics, Kitchen, Fashion, Home categories
- **FR-053**: System MUST include products from user journey examples (Coffee Maker around $70, AirPods around $250) for demo consistency
- **FR-054**: System MUST have products with price range from $30 to $700 to enable constraint testing
- **FR-055**: System MUST have mix of in-stock and out-of-stock products to test monitoring scenarios
- **FR-056**: System MUST provide mock Credentials Provider returning 2-3 tokenized payment methods per user (never raw PCI data per AP2 role separation)
- **FR-057**: System MUST provide mock Payment Processor with approximately 90% approval rate to test both success and failure paths
- **FR-058**: System MUST simulate realistic decline reasons (insufficient funds, card expired, transaction declined by issuer, fraud suspected on high value)
- **FR-059**: System MUST return transaction identifiers and authorization codes on successful payments
- **FR-060**: System MUST return specific decline reasons on payment failures

#### Data Persistence

- **FR-061**: System MUST store all mandates with complete metadata for audit trail reconstruction
- **FR-062**: System MUST store monitoring jobs in a way that survives server restarts
- **FR-063**: System MUST store transaction results with status codes and authorization details
- **FR-064**: System MUST store user sessions for conversation continuity
- **FR-065**: System MUST NOT store raw payment credentials, only tokenized references per AP2 role separation
- **FR-066**: System MUST NOT store PCI sensitive data

### Key Entities

- **Intent Mandate**: Captures user's original request (search query or monitoring constraints). In HP flow, created for audit trail only without user signature. In HNP flow, requires user signature as pre-authorization. Contains constraint details (price, delivery), expiration time, and signature status.

- **Cart Mandate**: Represents exact items to be purchased with prices and totals. In HP flow, requires user signature as the authorization. In HNP flow, has agent signature and must reference Intent Mandate ID. Contains line items, merchant info, delivery details, and totals.

- **Payment Mandate**: Created by Payment Agent to process payment. References Cart Mandate. Contains tokenized payment credentials, amount, and human-not-present flag (when applicable). Never contains raw payment data.

- **Transaction**: Final result of payment processing. Contains transaction ID, authorization code (on success) or decline reason (on failure), timestamp, and status.

- **Monitoring Job**: Represents active HNP monitoring. Contains product identifier, constraints (price, delivery), check frequency (5 minutes), expiration (7 days), Intent Mandate reference, and current status (active/completed/expired/cancelled).

- **Product**: Item available for purchase. Contains product ID, name, description, category, price, stock status, delivery estimate, and image reference.

- **Mandate Chain**: Complete audit trail linking Intent → Cart → Payment → Transaction. Shows signature validation status at each step and demonstrates cryptographic proof of authorization flow.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can complete human-present purchase flow from search through transaction in under 90 seconds
- **SC-002**: Users can set up human-not-present monitoring with constraint definition and pre-authorization in under 60 seconds
- **SC-003**: System streams agent messages to user interface within 500 milliseconds of agent action
- **SC-004**: Monitoring checks complete in under 2 seconds per iteration
- **SC-005**: System handles at least 10 concurrent monitoring jobs without degradation
- **SC-006**: Complete demonstration of both HP and HNP flows can be completed in under 3 minutes for hackathon judges
- **SC-007**: Payment Agent can be extracted to separate folder and successfully integrated into a different commerce project (travel booking demo or subscription service demo) without any code modifications
- **SC-008**: All mandate structures validate against official AP2 specification JSON schemas with 100% field compliance
- **SC-009**: Server restart does not lose any active monitoring jobs (100% job persistence)
- **SC-010**: Mandate chain visualization loads and displays in under 1 second after transaction completes
- **SC-011**: Error messages are understandable by non-technical users (tested with 3 non-developer testers who can explain error and recovery action)
- **SC-012**: System demonstrates successful payment authorization AND payment decline scenarios with proper error handling in demo
- **SC-013**: Users can trace complete mandate chain from Intent through Cart to Payment to Transaction for every transaction
- **SC-014**: Biometric-style signature flow provides tactile feedback (1-second animation) and clear verification confirmation

### Acceptance Criteria Summary

This implementation is complete when:

1. HP flow works end-to-end: user search → product selection → cart approval with signature → payment processing → mandate chain visualization
2. HNP flow works end-to-end: constraint definition with signature → multiple monitoring iterations where conditions not initially met → autonomous purchase when conditions met → user notification with mandate chain access
3. Payment Agent is extractable and reusable without GhostCart-specific code
4. Mandate chain visualization clearly displays Intent, Cart, Payment, Transaction with signature status and explains relationships in plain English with tooltips
5. System demonstrates both successful authorization and payment decline with proper error handling
6. All mandates validate against official AP2 schemas
7. Active monitoring survives server restart
8. Error messages are clear and actionable for non-technical users
9. Complete demo from both flows completes in under 3 minutes

## External Protocol Constraints

### AP2 Specification Compliance

This feature MUST comply with Agent Payments Protocol v0.1 from https://ap2-protocol.org/specification/. The following are external protocol requirements that define valid behavior:

#### Mandate Structure Requirements

- All Intent, Cart, and Payment mandates MUST match official AP2 JSON schemas
- Mandate chain relationships MUST follow AP2 specification:
  - Human-present flow: user-signed Cart is the authorization
  - Human-not-present flow: user-signed Intent is pre-authorization, agent-signed Cart references Intent ID
- Role separation is mandatory: shopping agents never access raw payment data, only tokenized credentials from Credentials Provider

#### Human-Present Flow Requirements (per AP2)

- Intent Mandate captures user query for audit trail but does NOT require user signature
- Cart Mandate MUST have user signature as this is the authorization mechanism per AP2
- Payment Mandate references Cart Mandate
- User signature on Cart is what authorizes the payment

#### Human-Not-Present Flow Requirements (per AP2)

- Intent Mandate MUST have user signature as this is the pre-authorization mechanism per AP2
- Cart Mandate has agent signature (NOT user signature) when agent acts autonomously
- Cart Mandate MUST reference Intent Mandate ID for chain validation per AP2
- Payment Mandate MUST have human-not-present flag set to signal autonomous transaction to payment network
- Agent must validate Cart does not exceed Intent constraints before processing

#### Error Code Requirements (per AP2)

All errors must use AP2 standard error codes:
- `ap2:mandate:chain_invalid` - Mandate chain validation failed
- `ap2:mandate:signature_invalid` - Signature verification failed
- `ap2:mandate:expired` - Mandate past expiration time
- `ap2:mandate:constraints_violated` - Cart exceeds Intent limits
- `ap2:credentials:unavailable` - Payment credentials not accessible
- `ap2:payment:declined` - Payment processor declined transaction

### Interoperability Demonstration

- System proves AP2 works with AWS Strands SDK, not just Google's Agent Development Kit reference implementation
- Payment Agent reusability demonstrates AP2 as universal protocol independent of implementation
- All services are mocked locally as AP2 not yet adopted by real merchants

## Assumptions

1. **Demo Context**: This is a hackathon demonstration, not production software. Security measures (HMAC-SHA256) mock production requirements (ECDSA with hardware-backed keys) and are clearly labeled as such.

2. **Target Platform**: Primary target is laptop/desktop interface. Mobile interface is stretch goal.

3. **Authentication**: User authentication is assumed to exist but is not specified in detail. Focus is on payment flow demonstration, not account management.

4. **Currency**: All monetary values in USD for consistency in demo.

5. **Monitoring Defaults**: Check frequency defaults to 5 minutes, monitoring duration defaults to 7 days unless user specifies otherwise.

6. **Product Data**: Mock product catalog is sufficient for demo and does not need real merchant integrations.

7. **Network**: All services run locally. No external API dependencies except AWS Bedrock for LLM.

8. **Payment Processing**: All payment processing is mocked. No actual financial transactions occur.

9. **Signature Simulation**: Biometric-style interface simulates device-based signatures. Production would use actual device hardware-backed cryptographic keys.

10. **Scalability**: System demonstrates 10 concurrent monitoring jobs. Production scalability is not a goal for hackathon demo.
