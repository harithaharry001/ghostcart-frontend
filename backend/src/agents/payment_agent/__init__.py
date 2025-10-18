"""
Payment Agent - Isolated AP2 Payment Processing Module

⚠️ CRITICAL ISOLATION REQUIREMENT ⚠️

This module MUST maintain ZERO dependencies on parent project directories.

Constitution Principle II: "The Payment Agent MUST have ZERO knowledge of:
- Merchant product catalogs
- User shopping behavior
- Application-specific business logic"

Import Rules:
✅ ALLOWED:
   - Python standard library (json, datetime, hashlib, hmac, etc.)
   - Pydantic (data validation only)
   - Type hints from typing module

❌ FORBIDDEN:
   - from src.models import ...
   - from src.services import ...
   - from src.mocks import ...
   - from .. import ... (parent directory imports)
   - Any GhostCart-specific code

Reusability Goal:
This entire directory should be copy-pasteable to ANY e-commerce project
with ZERO modifications. It implements pure AP2 protocol validation and
payment processing with no domain coupling.

Extraction Test:
cp -r backend/src/agents/payment_agent/ /path/to/new/project/
# Should work immediately with only environment variables configured

Files in this module:
- models.py: Pydantic models for AP2 mandates (redefined, not imported)
- crypto.py: HMAC-SHA256 signature verification (stdlib only)
- tools.py: Validation tools for HP/HNP chains and payment processing
- agent.py: Strands Agent definition with AP2 compliance system prompt
"""

__version__ = "0.1.0"
__all__ = ["agent", "tools", "models", "crypto"]
