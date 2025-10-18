"""
Signature Service for AP2 Mandate Signing

Implements HMAC-SHA256 signature generation and verification.
AP2 Compliance: Mocks production ECDSA with hardware-backed keys.
"""
import hmac
import hashlib
import json
from datetime import datetime
from typing import Dict, Any
from ..config import settings
from ..models.signatures import SignatureObject


def create_canonical_json(data: Dict[str, Any]) -> str:
    """
    Create canonical JSON representation for signing.

    Ensures consistent serialization:
    - Sorted keys
    - No whitespace
    - UTF-8 encoding
    """
    return json.dumps(data, sort_keys=True, separators=(',', ':'))


def sign_mandate(
    mandate_data: Dict[str, Any],
    signer_identity: str,
    secret_key: str
) -> SignatureObject:
    """
    Sign a mandate using HMAC-SHA256.

    Args:
        mandate_data: Mandate content as dictionary
        signer_identity: Who is signing (user ID, agent ID, payment agent ID)
        secret_key: HMAC secret key for this signer type

    Returns:
        SignatureObject with algorithm, signer, timestamp, and signature value

    AP2 Compliance:
    - Labeled as mocking production ECDSA
    - Provides cryptographic integrity verification
    - Timestamp prevents replay attacks
    """
    timestamp = datetime.utcnow()

    # Create canonical representation
    canonical_data = create_canonical_json(mandate_data)

    # Create message to sign: canonical_data + metadata
    message = f"{canonical_data}|{signer_identity}|{timestamp.isoformat()}"

    # Compute HMAC-SHA256
    signature_bytes = hmac.new(
        secret_key.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).digest()

    # Convert to hexadecimal
    signature_value = signature_bytes.hex()

    return SignatureObject(
        algorithm="HMAC-SHA256",
        signer_identity=signer_identity,
        timestamp=timestamp,
        signature_value=signature_value
    )


def verify_signature(
    mandate_data: Dict[str, Any],
    signature: SignatureObject,
    secret_key: str
) -> bool:
    """
    Verify mandate signature using constant-time comparison.

    Args:
        mandate_data: Mandate content as dictionary
        signature: SignatureObject to verify
        secret_key: HMAC secret key for this signer type

    Returns:
        True if signature valid, False otherwise

    AP2 Compliance:
    - Uses constant-time comparison to prevent timing attacks
    - Verifies signature matches mandate content
    """
    # Create canonical representation
    canonical_data = create_canonical_json(mandate_data)

    # Recreate message that was signed
    message = f"{canonical_data}|{signature.signer_identity}|{signature.timestamp.isoformat()}"

    # Compute expected signature
    expected_signature_bytes = hmac.new(
        secret_key.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).digest()

    expected_signature_value = expected_signature_bytes.hex()

    # Constant-time comparison
    return hmac.compare_digest(
        expected_signature_value,
        signature.signature_value
    )


def sign_user_mandate(mandate_data: Dict[str, Any], user_id: str) -> SignatureObject:
    """Sign mandate as user (HP Cart, HNP Intent)."""
    return sign_mandate(mandate_data, user_id, settings.user_signature_secret)


def sign_agent_mandate(mandate_data: Dict[str, Any], agent_id: str) -> SignatureObject:
    """Sign mandate as agent (HNP Cart when autonomous)."""
    return sign_mandate(mandate_data, agent_id, settings.agent_signature_secret)


def sign_payment_mandate(mandate_data: Dict[str, Any]) -> SignatureObject:
    """Sign mandate as payment agent (all Payment mandates)."""
    return sign_mandate(mandate_data, "payment_agent", settings.payment_agent_secret)


def verify_user_signature(mandate_data: Dict[str, Any], signature: SignatureObject) -> bool:
    """Verify user signature."""
    return verify_signature(mandate_data, signature, settings.user_signature_secret)


def verify_agent_signature(mandate_data: Dict[str, Any], signature: SignatureObject) -> bool:
    """Verify agent signature."""
    return verify_signature(mandate_data, signature, settings.agent_signature_secret)


def verify_payment_signature(mandate_data: Dict[str, Any], signature: SignatureObject) -> bool:
    """Verify payment agent signature."""
    return verify_signature(mandate_data, signature, settings.payment_agent_secret)
