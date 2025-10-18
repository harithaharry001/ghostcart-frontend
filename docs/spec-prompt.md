Build GhostCart proving Agent Payments Protocol v0.1 from https://ap2-protocol.org/specification/ achieves interoperability with AWS Strands SDK not just Google's Agent Development Kit reference implementation.

EXTERNAL CONSTRAINTS:
Must follow AP2 specification exactly. All mandate structures must match official schemas for Intent Mandate, Cart Mandate, and Payment Mandate. Mandate chain relationships per AP2: human-present flow uses user-signed Cart as authorization, human-not-present flow uses user-signed Intent as pre-authorization with agent-signed Cart referencing Intent. Role separation mandatory - shopping agents never access raw payment data. AP2 not yet adopted by real merchants so all services mocked locally.

HUMAN PRESENT FLOW - IMMEDIATE PURCHASE:
User types "Find me a coffee maker under 70 dollars". Messages stream in real-time showing "Analyzing your request", "Routing to shopping assistant", "Searching products". Screen displays 3 coffee makers with product images, names like Philips HD7462 Coffee Maker, prices around 69 dollars, delivery estimates like 2 day delivery. User clicks one product. Cart appears showing exact item name, price 69 dollars, delivery 2 days, total 69 dollars with blue Approve Purchase button.

User clicks Approve. Modal appears with frosted glass background, large fingerprint icon in center, text "Confirm with Touch ID", and smaller text "Authorizing purchase of Philips HD7462 for 69 dollars". User clicks Confirm button. Fingerprint icon pulses with 1 second scanning animation. Green checkmark appears with "Verified" text. Modal closes. Messages stream "Validating signature", "Processing payment of 69 dollars", "Payment authorized". Success screen shows "Payment Authorized! Transaction ID: txn_abc123, Authorization Code: AUTH_xy45z8" with green background and "View Chain" button.

User clicks View Chain. Visual timeline appears as connected boxes: "Intent Mandate" arrow "Cart Mandate" arrow "Payment Mandate" arrow "Transaction". Intent box has gray header "Context Only - Not Signed" with info icon showing tooltip "Intent captures what you wanted but is not the authorization in real-time purchases per AP2 human-present flow". Cart box has green header "User Signed - Authorization" with checkmark icon and tooltip "You approved this exact cart with your signature - this is the authorization per AP2". Payment box shows "Payment Agent Signed". Transaction box shows "Authorized" with green badge. User can click any box to expand and see JSON structure matching AP2 schema. Bottom has "Copy JSON" and "Download Chain" buttons.

What happens per AP2 protocol: Intent Mandate created capturing user query for audit trail but not requiring user signature in human-present flow. Cart Mandate created by merchant with exact items and totals. User signature required on Cart Mandate as this is the authorization per AP2 human-present specification. Payment Mandate created referencing Cart. Complete mandate chain stored forming audit trail from intent through transaction.

HUMAN NOT PRESENT FLOW - AUTONOMOUS MONITORING:
User types "Buy AirPods if price drops below 180 dollars and delivery is 2 days or less". Messages stream showing "Analyzing constraints", "Routing to monitoring assistant". Agent responds with message "I can monitor Apple AirPods Pro and automatically purchase when your conditions are met. Let me confirm: Maximum price 180 dollars, Maximum delivery 2 days. I will check every 5 minutes for 7 days. Shall I set up this monitoring?" with green "Yes, Monitor This" button.

User clicks Yes button. Modal appears with fingerprint icon, text "Confirm with Touch ID", warning text in orange "You are authorizing autonomous purchase. The agent will buy automatically when conditions are met without asking you again." User clicks Confirm. Scanning animation plays. Verification appears. Modal closes. Messages stream "Intent Mandate signed", "Monitoring activated", "First check in 5 minutes". Status card appears showing "Monitoring Active for Apple AirPods Pro, Checking every 5 minutes, Conditions: Price below 180 dollars and delivery within 2 days, Expires in 7 days" with Cancel Monitoring button.

Background monitoring begins. First check at 10:00 AM finds AirPods at 249 dollars. Status updates "Last checked: 10:00 AM, Current price: 249 dollars, Status: Conditions not met - price too high". Second check at 10:05 AM still 249 dollars. Status updates again. Third check at 10:10 AM finds AirPods at 175 dollars with 1 day delivery. Messages burst rapidly "Conditions met! Price 175 dollars, delivery 1 day", "Creating Cart Mandate automatically", "Processing payment autonomously", "Payment authorized!". 

Large notification appears "Autonomous Purchase Complete! Apple AirPods Pro purchased for 175 dollars. You authorized this purchase on [date] with constraints: price below 180 dollars, delivery within 2 days. Transaction ID: txn_def789" with "View Details" and "View Chain" buttons. Monitoring status card changes to "Monitoring Completed - Purchase successful".

User clicks View Chain. Timeline shows Intent box with green header "User Signed - Pre-Authorization" and tooltip "You granted the agent authority to act when conditions met per AP2 human-not-present flow". Cart box has blue header "Agent Signed - Autonomous Action" with robot icon and tooltip "Agent acted on your behalf based on Intent authority per AP2 specification" plus displays "References Intent ID: intent_hnp_xyz123" showing the mandate chain link required by AP2. Payment box shows "Payment Agent Signed" with badge "Human Not Present Flag Set". Transaction shows "Authorized".

What happens per AP2 protocol: Intent Mandate created with user constraints and expiration. User signature required on Intent as this is the pre-authorization per AP2 human-not-present specification. Background job monitors conditions. When conditions met, Cart Mandate created by agent with agent signature not user signature per AP2 human-not-present flow. Cart Mandate must reference Intent Mandate ID per AP2 chain requirement. Payment Mandate created with human-not-present flag set per AP2 specification signaling autonomous transaction to payment network.

INTELLIGENT ROUTING:
Supervisor Agent receives user message and analyzes using LLM reasoning not hardcoded rules. Routes to HP Shopping Agent when message indicates immediate action with present tense and no conditional logic. Examples: "Find running shoes under 100", "Show me laptops", "I want headphones now".

Routes to HNP Delegate Agent when message indicates future action with conditional logic or monitoring intent. Examples: "Buy AirPods if price drops", "Monitor for laptop deals under 800", "Alert when smartwatch available", "Let me know when cheaper than 150".

If message ambiguous like "Get me AirPods" with no clear timing or conditions, Supervisor streams clarifying question "I can help you with AirPods. Would you like to: 1) Buy now at current price of 249 dollars, or 2) Set up monitoring to purchase automatically when price drops?" User response determines routing. Never routes user directly to Payment Agent per AP2 architecture where only merchant or shopping agents interact with payment processing.

PAYMENT AGENT REQUIREMENTS:
Payment Agent must be completely separate reusable component demonstrating AP2 protocol portability. Zero knowledge of GhostCart products, categories, pricing, merchants, or UI. Only understands AP2 mandate primitives as defined in specification. Accepts mandate objects as input following AP2 schemas. Returns payment result as output. Can be extracted to separate folder and used for any commerce scenario like travel bookings, subscriptions, B2B procurement without modification. This proves AP2 works as universal protocol not tied to specific implementation.

Payment Agent must validate mandate chains per AP2 rules. For human-present flow must verify Cart Mandate has user signature as required by AP2. For human-not-present flow must verify Intent Mandate has user signature and Cart Mandate references Intent ID as required by AP2 chain validation. Must retrieve tokenized credentials not raw payment data per AP2 role separation. Must create Payment Mandate with appropriate flags. Must submit to processor with complete mandate chain.

Must return AP2 standard error codes on failures: ap2:mandate:chain_invalid when mandate chain broken, ap2:mandate:signature_invalid when signature verification fails, ap2:mandate:expired when mandate past expiration, ap2:mandate:constraints_violated when Cart exceeds Intent limits, ap2:credentials:unavailable when payment method not available, ap2:payment:declined when processor rejects transaction.

MOCK SERVICES REQUIREMENTS:
Product catalog with approximately 15 products across Electronics, Kitchen, Fashion, Home categories. Price range from around 30 dollars to 700 dollars to enable various constraint testing. Include products mentioned in user journey examples like Coffee Maker around 70 dollars and AirPods around 250 dollars for demo consistency. Some products must be in stock and some out of stock to enable testing monitoring scenarios where conditions not immediately met requiring multiple check iterations.

Credentials Provider simulating digital wallet must return 2 to 3 payment methods per user demonstrating multiple payment option support. Must return tokenized credentials following AP2 specification never exposing raw PCI data demonstrating proper role separation per protocol.

Payment Processor must have realistic approval rate around 90 percent to test both success and failure paths. Must simulate various decline reasons matching real world scenarios like insufficient funds, card expired, transaction declined by issuer, fraud suspected on high value transactions. Must return transaction identifiers and authorization codes on success. Must return specific decline reasons on failure enabling proper error handling demonstration.

REAL-TIME STREAMING REQUIREMENTS:
Stream messages in real-time via Server-Sent Events so user sees agent progress without page refresh demonstrating transparency principle. Show messages like "Analyzing your request", "Searching for products", "Found 3 matching items", "Creating Cart Mandate", "Waiting for your approval", "Validating signature", "Processing payment", "Payment authorized" with transaction details.

For monitoring flow show "Setting up monitoring", "Checking every 5 minutes", "Will monitor for 7 days or until conditions met". During monitoring show "Checking prices at timestamp", "Current price X - conditions not met because reason". When conditions met show "Conditions met at price X", "Processing automatically without user interaction", "Purchase complete".

For errors show clear actionable messages like "Payment declined: Insufficient funds. [Try Another Payment Method]" with clickable button, or "Product unavailable. [View Alternatives] or [Set Up Monitoring]" with clear options enabling user to recover from error state.

ERROR SCENARIOS TO HANDLE:
Payment declined: Display specific reason from processor with option to select different payment method and retry purchase.

Product out of stock in human-present flow: Show message product unavailable with two options - view similar products in same category and price range enabling alternate purchase, or transition to human-not-present flow to set up monitoring for when product back in stock.

Product out of stock in human-not-present flow: Continue monitoring checking both price constraint and availability status every iteration. When product becomes available and price meets constraint proceed with automatic purchase. If monitoring expires after 7 days before product available notify user monitoring period ended.

Monitoring conditions never met: After 7 days when Intent Mandate reaches expiration send notification that conditions were not met during monitoring period, show current price for reference, offer option to set up new monitoring with same or adjusted constraints.

Invalid signature: Display error explaining signature verification failed with specific details about which mandate signature invalid enabling debugging, with option to retry signing flow.

Agent unclear on intent: Ask clarifying questions rather than making assumptions. Examples: "Did you mean buy now or set up monitoring?", "Which model - Pro or Max?", "Did you mean total price or per item?" Never guess user intent.

SIGNATURE USER EXPERIENCE:
User signatures via modal dialog with biometric-style interface matching familiar patterns like Touch ID or Face ID. Show fingerprint icon, confirmation message, mandate summary explaining what user authorizing. When user confirms show brief scanning animation approximately 1 second giving tactile feedback. Show verification checkmark before modal closes. Clearly label as demo implementation with explanation production would use device hardware-backed cryptographic keys. Agent signatures happen automatically in background with no user interaction required per autonomous flow design.

DATA PERSISTENCE REQUIREMENTS:
Store all mandates with complete metadata for audit trail reconstruction. Store monitoring jobs in way that survives server restarts ensuring reliability. Store transaction results with status codes and authorization details. Store user sessions for conversation continuity. Do not store raw payment credentials only tokenized references per AP2 role separation. Do not store PCI sensitive data maintaining security boundaries.

QUALITY REQUIREMENTS:
Agent responses must stream within 500 milliseconds of user input providing responsive feel. Real-time updates must appear immediately with no perceived lag in message display. Monitoring checks must complete in under 2 seconds per iteration. System must handle at least 10 concurrent monitoring jobs demonstrating scalability. Interface must work on laptop as primary target with mobile as stretch goal. Error messages must be clear and actionable with no technical jargon for end users. Provide plain English explanations alongside technical details for different audience needs.

REVIEW CHECKPOINT - SPECIFICATION PHASE:
Before moving to planning phase, review this specification and confirm:
Does this capture complete user journey for both human-present and human-not-present flows?
Are all error scenarios covered with clear expected behavior?
Do the mandate chain requirements align with official AP2 specification from external reference?
Is the Payment Agent reusability requirement clear and testable?
Are the mock service requirements sufficient to demonstrate protocol without external dependencies?
Are acceptance criteria specific enough to validate implementation completeness?

ACCEPTANCE CRITERIA:
This implementation is complete when HP flow works end-to-end from user search through product selection, cart approval with signature, payment processing, to viewing complete mandate chain visualization. HNP flow works end-to-end from user setting constraints with signature through multiple monitoring check iterations where conditions not initially met, to autonomous purchase when conditions finally met, to user notification with mandate chain access. Payment Agent can be extracted to separate folder and successfully used in completely different commerce project without any GhostCart-specific code modifications demonstrating true reusability. Mandate chain visualization clearly displays all three mandate types with signature validation status and explains chain relationships in plain English. System demonstrates both successful payment authorization and payment decline scenarios with proper error handling. All mandate structures validate against official AP2 specification schemas with all required fields present. Server restart does not lose active monitoring jobs proving persistence implementation. Error messages are understandable and actionable for non-technical users. Complete demonstration from both flows can be completed in under 3 minutes for hackathon judges.

This implementation proves AP2 protocol achieves interoperability with AWS Strands SDK beyond Google's Agent Development Kit, demonstrates both human-present and human-not-present flows with correct mandate signature patterns per official specification, shows Payment Agent as truly reusable standalone component working with any commerce platform, and provides complete transparency through mandate chain visualization with audit trail.