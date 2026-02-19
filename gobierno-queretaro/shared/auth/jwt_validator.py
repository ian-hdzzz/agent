"""
Paco JWT Token Validator

Validates JWT tokens issued by the Paco backend (HS256).
Used by the orchestrator to accept Paco admin tokens alongside X-Admin-Key.
"""

from datetime import datetime, timezone

from jose import JWTError, jwt


def validate_paco_jwt(token: str, secret: str) -> dict:
    """
    Validate a Paco-issued JWT token.

    Args:
        token: JWT token string (without "Bearer " prefix)
        secret: The shared HS256 secret key (must match Paco's SECRET_KEY)

    Returns:
        Dict with claims: {"sub": str, "role": str, "exp": datetime}

    Raises:
        ValueError: If the token is invalid, expired, or missing required claims
    """
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
    except JWTError as e:
        raise ValueError(f"Invalid JWT: {e}")

    sub = payload.get("sub")
    if not sub:
        raise ValueError("Invalid JWT: missing 'sub' claim")

    role = payload.get("role", "viewer")

    exp_ts = payload.get("exp")
    if exp_ts is None:
        raise ValueError("Invalid JWT: missing 'exp' claim")

    exp = datetime.fromtimestamp(exp_ts, tz=timezone.utc)
    if exp < datetime.now(timezone.utc):
        raise ValueError("JWT token has expired")

    return {"sub": sub, "role": role, "exp": exp}
