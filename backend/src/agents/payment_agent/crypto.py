"""
Cryptographic Signature Verification for AP2 Mandates

⚠️ NO IMPORTS FROM PARENT PROJECT ⚠️

Uses Python stdlib only (hmac, hashlib, json, os) for HMAC-SHA256 verification.
Secrets loaded from environment variables for portability.

AP2 Compliance:
- HMAC-SHA256 for demo (mocks production ECDSA with hardware-backed keys)
- Constant-time comparison to prevent timing attacks
- Canonical JSON serialization for signature consistency
"""
import hmac
import hashlib
import json
import os
from typing import Dict, Any


def get_secret(secret_type: str) -> str:
    """
    Load HMAC secret from environment variables.

    Args:
        secret_type: "user", "agent", or "payment_agent"

    Returns:
        HMAC secret key

    Raises:
        RuntimeError: If secret not configured

    Environment Variables:
        USER_SIGNATURE_SECRET: For user mandate signatures
        AGENT_SIGNATURE_SECRET: For agent mandate signatures
        PAYMENT_AGENT_SECRET: For payment agent mandate signatures
    """
    env_var_map = {
        "user": "USER_SIGNATURE_SECRET",
        "agent": "AGENT_SIGNATURE_SECRET",
        "payment_agent": "PAYMENT_AGENT_SECRET",
    }

    if secret_type not in env_var_map:
        raise ValueError(f"Invalid secret_type: {secret_type}. Must be user, agent, or payment_agent.")

    env_var = env_var_map[secret_type]
    secret = os.environ.get(env_var)

    if not secret:
        raise RuntimeError(
            f"Missing required environment variable: {env_var}. "
            f"Payment Agent cannot verify signatures without configured secrets."
        )

    return secret


def create_canonical_json(data: Dict[str, Any]) -> str:
    """
    Create canonical JSON representation for signature verification.

    Ensures consistent serialization:
    - Sorted keys
    - No whitespace
    - UTF-8 encoding

    Args:
        data: Dictionary to serialize

    Returns:
        Canonical JSON string
    """
    return json.dumps(data, sort_keys=True, separators=(',', ':'))


def verify_signature(
    mandate_data: Dict[str, Any],
    signature_value: str,
    signer_identity: str,
    timestamp_iso: str,
    secret_type: str
) -> bool:
    """
    Verify HMAC-SHA256 signature for a mandate.

    Args:
        mandate_data: Mandate content as dictionary (without signature field)
        signature_value: Hex-encoded signature to verify
        signer_identity: Who signed (user_id, agent_id, or "payment_agent")
        timestamp_iso: ISO 8601 timestamp from signature
        secret_type: "user", "agent", or "payment_agent"

    Returns:
        True if signature valid, False otherwise

    AP2 Compliance:
    - Uses constant-time comparison to prevent timing attacks
    - Verifies signature matches mandate content exactly
    - Recreates signing message: {canonical_json}|{signer}|{timestamp}
    """
    try:
        # Get secret for this signer type
        secret_key = get_secret(secret_type)

        # Create canonical representation
        canonical_data = create_canonical_json(mandate_data)

        # Recreate message that was signed
        message = f"{canonical_data}|{signer_identity}|{timestamp_iso}"

        # Compute expected signature
        expected_signature_bytes = hmac.new(
            secret_key.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).digest()

        expected_signature_value = expected_signature_bytes.hex()

        # Constant-time comparison (prevents timing attacks)
        return hmac.compare_digest(expected_signature_value, signature_value)

    except Exception as e:
        # Log error but don't raise - verification failure should return False
        print(f"Signature verification error: {e}")
        return False


def verify_user_signature(
    mandate_data: Dict[str, Any],
    signature_value: str,
    signer_identity: str,
    timestamp_iso: str
) -> bool:
    """Verify user signature (HP Cart, HNP Intent)."""
    return verify_signature(
        mandate_data,
        signature_value,
        signer_identity,
        timestamp_iso,
        "user"
    )


def verify_agent_signature(
    mandate_data: Dict[str, Any],
    signature_value: str,
    signer_identity: str,
    timestamp_iso: str
) -> bool:
    """Verify agent signature (HNP Cart when autonomous)."""
    return verify_signature(
        mandate_data,
        signature_value,
        signer_identity,
        timestamp_iso,
        "agent"
    )


def verify_payment_signature(
    mandate_data: Dict[str, Any],
    signature_value: str,
    signer_identity: str,
    timestamp_iso: str
) -> bool:
    """Verify payment agent signature (all Payment mandates)."""
    return verify_signature(
        mandate_data,
        signature_value,
        signer_identity,
        timestamp_iso,
        "payment_agent"
    )
