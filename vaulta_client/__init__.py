"""
Vaulta Client - A Python client for the Vaulta API.

This package provides a convenient interface for interacting with the Vaulta API,
including client management and asset management functionality.
"""

from .client import VaultaClient
from .exceptions import VaultaError, VaultaClientError, VaultaServerError
from .models import Client, ClientCreate, ClientUpdate, Asset, AssetUploadResponse
from .utils import (
    sign_serve_url,
)

__version__ = "0.1.0"
__author__ = "Vaulta Team"

__all__ = [
    "VaultaClient",
    "VaultaError",
    "VaultaClientError",
    "VaultaServerError",
    "Client",
    "ClientCreate",
    "ClientUpdate",
    "Asset",
    "AssetUploadResponse",
    "sign_serve_url",
]
