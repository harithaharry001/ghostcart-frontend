"""
Pydantic SignatureObject Model

Represents cryptographic signature metadata for AP2 mandates.
AP2 Compliance: Matches signature structure from AP2 specification.
"""
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from typing import Literal


class SignatureObject(BaseModel):
    """
    Cryptographic signature metadata per AP2 specification.

    AP2 Compliance Notes:
    - Algorithm field identifies signature method (HMAC-SHA256 for demo)
    - Signer identity tracks who signed (user, agent, or payment agent)
    - Timestamp prevents replay attacks
    - Signature value contains HMAC digest
    """

    algorithm: Literal["HMAC-SHA256"] = Field(
        description="Signature algorithm (mocking production ECDSA)"
    )
    signer_identity: str = Field(
        description="Who signed: user ID, agent ID, or payment agent ID"
    )
    timestamp: datetime = Field(
        description="When signature was created (ISO 8601 format)"
    )
    signature_value: str = Field(
        description="HMAC-SHA256 digest in hexadecimal",
        pattern="^[0-9a-f]{64}$"
    )

    @field_validator("timestamp")
    @classmethod
    def timestamp_not_future(cls, v: datetime) -> datetime:
        """Ensure timestamp is not in the future."""
        if v > datetime.utcnow():
            raise ValueError("Signature timestamp cannot be in the future")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "algorithm": "HMAC-SHA256",
                "signer_identity": "user_demo_001",
                "timestamp": "2025-10-17T14:30:00Z",
                "signature_value": "a1b2c3d4e5f67890abcdef1234567890abcdef1234567890abcdef1234567890"
            }
        }
    }
