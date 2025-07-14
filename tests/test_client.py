"""
Unit tests for the Vaulta client.
"""

import pytest
from unittest.mock import Mock, patch, mock_open
from pathlib import Path
import json
from datetime import datetime
from uuid import uuid4

from vaulta_client import VaultaClient
from vaulta_client.models import ClientCreate, ClientUpdate, AssetQuery, AssetLabels
from vaulta_client.exceptions import (
    VaultaError,
    VaultaClientError,
    VaultaServerError,
    VaultaAuthenticationError,
    VaultaNotFoundError,
    VaultaValidationError,
)


class TestVaultaClient:
    """Test cases for the VaultaClient class."""

    @pytest.fixture
    def client(self):
        """Create a test client instance."""
        return VaultaClient(base_url="https://api.vaulta.com", api_token="test-token")

    @pytest.fixture
    def mock_response(self):
        """Create a mock response object."""
        response = Mock()
        response.status_code = 200
        response.json.return_value = {"id": "test-id", "name": "Test Client"}
        return response

    def test_client_initialization(self):
        """Test client initialization with various parameters."""
        # Test basic initialization
        client = VaultaClient("https://api.vaulta.com", "test-token")
        assert client.base_url == "https://api.vaulta.com"
        assert client.api_token == "test-token"
        assert client.timeout == 30

        # Test with custom parameters
        client = VaultaClient(
            base_url="https://api.vaulta.com",
            api_token="test-token",
            timeout=60,
            max_retries=5,
        )
        assert client.timeout == 60

        # Test URL normalization
        client = VaultaClient("https://api.vaulta.com/", "test-token")
        assert client.base_url == "https://api.vaulta.com"

    def test_get_version(self, client):
        """Test version retrieval."""
        version = client._get_version()
        assert version in ["0.1.0", "unknown"]

    def test_make_request_success(self, client, mock_response):
        """Test successful request handling."""
        with patch.object(client.session, "request", return_value=mock_response):
            response = client._make_request("GET", "/test")
            assert response == mock_response

    def test_make_request_authentication_error(self, client):
        """Test authentication error handling."""
        mock_response = Mock()
        mock_response.status_code = 401

        with patch.object(client.session, "request", return_value=mock_response):
            with pytest.raises(VaultaAuthenticationError):
                client._make_request("GET", "/test")

    def test_make_request_not_found_error(self, client):
        """Test not found error handling."""
        mock_response = Mock()
        mock_response.status_code = 404

        with patch.object(client.session, "request", return_value=mock_response):
            with pytest.raises(VaultaNotFoundError):
                client._make_request("GET", "/test")

    def test_make_request_validation_error(self, client):
        """Test validation error handling."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"detail": "Validation failed"}

        with patch.object(client.session, "request", return_value=mock_response):
            with pytest.raises(VaultaValidationError) as exc_info:
                client._make_request("GET", "/test")
            assert "Validation failed" in str(exc_info.value)

    def test_make_request_server_error(self, client):
        """Test server error handling."""
        mock_response = Mock()
        mock_response.status_code = 500

        with patch.object(client.session, "request", return_value=mock_response):
            with pytest.raises(VaultaServerError):
                client._make_request("GET", "/test")

    @patch.object(VaultaClient, "_make_request")
    def test_get_clients(self, mock_make_request, client):
        """Test getting clients list."""
        # Create proper UUIDs and datetime for the mock data
        client_id_1 = str(uuid4())
        client_id_2 = str(uuid4())
        now = datetime.now().isoformat()

        mock_response = Mock()
        mock_response.json.return_value = [
            {
                "id": client_id_1,
                "name": "Client 1",
                "client_id": "client1",
                "created_at": now,
                "updated_at": now,
            },
            {
                "id": client_id_2,
                "name": "Client 2",
                "client_id": "client2",
                "created_at": now,
                "updated_at": now,
            },
        ]
        mock_make_request.return_value = mock_response

        clients = client.get_clients(skip=0, limit=10)

        assert len(clients) == 2
        assert clients[0].name == "Client 1"
        assert clients[1].name == "Client 2"

        # Verify the request was made with correct parameters
        mock_make_request.assert_called_once_with(
            "GET", "/clients", params={"skip": 0, "limit": 10}
        )

    @patch.object(VaultaClient, "_make_request")
    def test_create_client(self, mock_make_request, client):
        """Test creating a client."""
        # Create proper UUID and datetime for the mock data
        client_id = str(uuid4())
        now = datetime.now().isoformat()

        mock_response = Mock()
        mock_response.json.return_value = {
            "id": client_id,
            "name": "Test Client",
            "client_id": "test-client",
            "secret": "test-secret",
            "created_at": now,
            "updated_at": now,
        }
        mock_make_request.return_value = mock_response

        client_data = ClientCreate(name="Test Client", client_id="test-client")
        result = client.create_client(client_data)

        assert result.name == "Test Client"
        assert result.secret == "test-secret"

        # Verify the request was made with correct data
        mock_make_request.assert_called_once_with(
            "POST", "/clients", data=client_data.model_dump()
        )

    @patch.object(VaultaClient, "_make_request")
    def test_update_client(self, mock_make_request, client):
        """Test updating a client."""
        # Create proper UUID and datetime for the mock data
        client_id = str(uuid4())
        now = datetime.now().isoformat()

        mock_response = Mock()
        mock_response.json.return_value = {
            "id": client_id,
            "name": "Updated Client",
            "client_id": "test-client",
            "created_at": now,
            "updated_at": now,
        }
        mock_make_request.return_value = mock_response

        update_data = ClientUpdate(name="Updated Client")
        result = client.update_client("test-id", update_data)

        assert result.name == "Updated Client"

        # Verify the request was made with correct data
        mock_make_request.assert_called_once_with(
            "PUT", "/clients/test-id", data=update_data.model_dump(exclude_unset=True)
        )

    @patch.object(VaultaClient, "_make_request")
    def test_delete_client(self, mock_make_request, client):
        """Test deleting a client."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_make_request.return_value = mock_response

        result = client.delete_client("test-id")

        assert result is True
        mock_make_request.assert_called_once_with("DELETE", "/clients/test-id")

    @patch.object(VaultaClient, "_make_request")
    def test_upload_asset(self, mock_make_request, client):
        """Test uploading an asset."""
        # Create proper UUID and datetime for the mock data
        asset_id = str(uuid4())
        now = datetime.now().isoformat()

        mock_response = Mock()
        mock_response.json.return_value = {
            "asset_id": asset_id,
            "name": "Test Asset",
            "filename": "test.txt",
            "size": 100,
            "url": "https://example.com/download",
            "serve_url": "https://example.com/serve",
            "mime_type": "text/plain",
            "human_readable_size": "100 B",
            "labels": {"category": "test"},
            "state": "ready",
            "state_message": "Asset uploaded successfully",
        }
        mock_make_request.return_value = mock_response

        # Test with file path
        with patch("builtins.open", mock_open(read_data=b"test content")):
            with patch("pathlib.Path.exists", return_value=True):
                result = client.upload_asset(
                    file_path="test.txt", name="Test Asset", labels={"category": "test"}
                )

        assert result.name == "Test Asset"
        assert str(result.asset_id) == asset_id

        # Verify the request was made with multipart data
        mock_make_request.assert_called_once()
        call_args = mock_make_request.call_args
        assert call_args[0][0] == "POST"
        assert call_args[0][1] == "/assets"
        assert call_args[1]["files"] is not None
        assert call_args[1]["data"] is not None

    @patch.object(VaultaClient, "_make_request")
    def test_search_assets(self, mock_make_request, client):
        """Test searching assets."""
        # Create proper UUIDs and datetime for the mock data
        asset_id = str(uuid4())
        user_id = str(uuid4())
        now = datetime.now().isoformat()

        mock_response = Mock()
        mock_response.json.return_value = [
            {
                "id": asset_id,
                "name": "Asset 1",
                "filename": "asset1.txt",
                "size": 100,
                "labels": {"category": "test"},
                "mime_type": "text/plain",
                "state": "ready",
                "user_id": user_id,
                "created_at": now,
                "updated_at": now,
                "human_readable_size": "100 B",
            }
        ]
        mock_make_request.return_value = mock_response

        result = client.search_assets(labels={"category": "test"}, skip=0, limit=10)

        assert len(result) == 1
        assert result[0].name == "Asset 1"

        # Verify the request was made with correct data
        expected_query = AssetQuery(query=AssetLabels(labels={"category": "test"}))
        mock_make_request.assert_called_once_with(
            "POST",
            "/assets/search",
            data=expected_query.model_dump(),
            params={"skip": 0, "limit": 10},
        )

    def test_search_assets_no_labels(self, client):
        """Test that search_assets raises error when no labels provided."""
        with pytest.raises(VaultaValidationError):
            client.search_assets(labels={})

    def test_get_asset_download_url(self, client):
        """Test getting asset download URL."""
        url = client.get_asset_download_url("test-token")
        assert url == "https://api.vaulta.com/assets/download/test-token"

    def test_get_asset_serve_url(self, client):
        """Test getting asset serve URL."""
        url = client.get_asset_serve_url("test-payload")
        assert url == "https://api.vaulta.com/assets/serve/test-payload"

    def test_download_asset(self, client):
        """Test downloading an asset."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"test content"

        with patch.object(client.session, "get", return_value=mock_response):
            # Test downloading to bytes
            content = client.download_asset("test-token")
            assert content == b"test content"

            # Test downloading to file
            with patch("builtins.open", mock_open()) as mock_file:
                with patch("pathlib.Path.mkdir"):
                    result = client.download_asset("test-token", save_path="test.txt")
                    assert result == Path("test.txt")
                    mock_file.assert_called_once()

    def test_download_asset_error(self, client):
        """Test downloading an asset with error."""
        mock_response = Mock()
        mock_response.status_code = 404

        with patch.object(client.session, "get", return_value=mock_response):
            with pytest.raises(VaultaError):
                client.download_asset("test-token")
