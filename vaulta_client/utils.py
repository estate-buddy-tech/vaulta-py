"""
Utility functions for the Vaulta client.
"""

import hashlib
import hmac
import time


def sign_serve_url(
    asset_id: str,
    client_id: str,
    client_secret: str,
    expires_in: int = 7200,
    host_url: str = None,
) -> str:
    """
    Sign a serve URL with document ID, client ID, expiration time, and HMAC signature.

    Args:
        asset_id: The asset ID to serve
        client_id: The client ID used for secret derivation
        client_secret: The secret key for signing (should be the derived secret)
        expires_in: Number of seconds until the URL expires (default: 7200 seconds / 2 hours)
        host_url: Optional Vaulta host URL. If provided, returns complete URL instead of just path

    Returns:
        str: The signed URL path or complete URL if host_url is provided
    """
    expires_at = int(time.time()) + expires_in
    payload = f"{asset_id}.{client_id}.{expires_at}"
    signature = hmac.new(
        client_secret.encode(), payload.encode(), hashlib.sha256
    ).hexdigest()
    signed_path = f"{payload}.{signature}"

    if host_url:
        # Remove trailing slash from host_url if present
        host_url = host_url.rstrip("/")
        return f"{host_url}/assets/serve/{signed_path}"

    return signed_path
