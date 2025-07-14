"""
Pydantic models for the Vaulta client.
These models mirror the API schemas for type safety and validation.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime


class ClientBase(BaseModel):
    """Base client model containing common client attributes."""

    id: Optional[UUID] = None
    name: str
    client_id: str
    secret_generated_at: Optional[datetime] = None


class ClientCreate(ClientBase):
    """Schema for creating a new client."""

    pass


class ClientUpdate(BaseModel):
    """Schema for updating an existing client. All fields are optional."""

    name: Optional[str] = None
    client_id: Optional[str] = None
    secret_generated_at: Optional[datetime] = None


class Client(ClientBase):
    """Schema for client data returned in API responses."""

    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ClientWithSecret(Client):
    """Schema for client data returned when creating a new client, includes the derived secret."""

    secret: str


class AssetBase(BaseModel):
    """Base asset model containing common asset attributes."""

    name: str
    filename: str
    mime_type: str
    size: int
    labels: Dict[str, Any] = Field(default_factory=dict)
    state: str
    state_message: Optional[str] = None


class AssetCreate(AssetBase):
    """Schema for creating a new asset."""

    pass


class AssetUpdate(BaseModel):
    """Schema for updating an existing asset. All fields are optional."""

    name: Optional[str] = None
    labels: Optional[Dict[str, Any]] = None
    state: Optional[str] = None
    state_message: Optional[str] = None


class Asset(AssetBase):
    """Schema for asset data returned in API responses."""

    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    human_readable_size: str

    class Config:
        from_attributes = True


class AssetUploadResponse(BaseModel):
    """Schema for asset upload response."""

    asset_id: UUID
    url: str
    serve_url: str
    name: str
    filename: str
    mime_type: str
    size: int
    human_readable_size: str
    labels: Dict[str, Any]
    state: str
    state_message: str

    class Config:
        from_attributes = True


class AssetSearchQuery(BaseModel):
    """Schema for asset search queries."""

    user_id: Optional[UUID] = None
    labels: Optional[Dict[str, Any]] = None
    state: Optional[str] = None
    skip: int = 0
    limit: int = 100


class AssetLabels(BaseModel):
    """Labels for asset search."""

    labels: Dict[str, Any]


class AssetQuery(BaseModel):
    """Query parameters for asset search."""

    query: AssetLabels
