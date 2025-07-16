"""
Main Vaulta client for interacting with the Vaulta API.
"""

import json
import logging
from typing import Optional, List, Dict, Any, BinaryIO, Union
from pathlib import Path
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .exceptions import (
    VaultaError,
    VaultaClientError,
    VaultaServerError,
    VaultaAuthenticationError,
    VaultaNotFoundError,
    VaultaValidationError,
)
from .models import (
    Client,
    ClientCreate,
    ClientUpdate,
    ClientWithSecret,
    Asset,
    AssetUploadResponse,
    AssetSearchQuery,
    AssetQuery,
    AssetLabels,
)
from .utils import sign_serve_url

logger = logging.getLogger(__name__)


class VaultaClient:
    """
    A client for interacting with the Vaulta API.

    This client provides methods for managing clients and assets through the Vaulta API.
    """

    def __init__(
        self,
        base_url: str,
        api_token: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
        session: Optional[requests.Session] = None,
    ):
        """
        Initialize the Vaulta client.

        Args:
            base_url: The base URL of the Vaulta API (e.g., "https://api.vaulta.com")
            api_token: Optional API token for authentication
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for failed requests
            session: Optional requests.Session instance to use
        """
        self.base_url = base_url.rstrip("/")
        self.api_token = api_token
        self.timeout = timeout

        # Create or use provided session
        self.session = session or requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=max_retries,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST", "PUT", "DELETE"],
            backoff_factor=1,
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Set default headers
        self.session.headers.update(
            {
                "Content-Type": "application/json",
                "User-Agent": f"vaulta-client/{self._get_version()}",
            }
        )

        if api_token:
            self.session.headers.update(
                {
                    "Authorization": f"Bearer {api_token}",
                }
            )

    def _get_version(self) -> str:
        """Get the client version."""
        try:
            from . import __version__

            return __version__
        except ImportError:
            return "unknown"

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> requests.Response:
        """
        Make an HTTP request to the Vaulta API.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            endpoint: API endpoint path (e.g., "/clients")
            data: Request data for JSON requests
            files: Files for multipart requests
            params: Query parameters
            headers: Additional headers

        Returns:
            requests.Response object

        Raises:
            VaultaClientError: For 4xx status codes
            VaultaServerError: For 5xx status codes
            VaultaError: For other errors
        """
        url = f"{self.base_url}{endpoint}"

        request_headers = {}
        if headers:
            request_headers.update(headers)

        try:
            if files:
                # For file uploads, don't set Content-Type header
                if "Content-Type" in request_headers:
                    del request_headers["Content-Type"]
                response = self.session.request(
                    method=method,
                    url=url,
                    data=data,
                    files=files,
                    params=params,
                    headers=request_headers,
                    timeout=self.timeout,
                )
            else:
                response = self.session.request(
                    method=method,
                    url=url,
                    json=data,
                    params=params,
                    headers=request_headers,
                    timeout=self.timeout,
                )

            # Handle different status codes
            if response.status_code < 400:
                return response
            elif response.status_code == 401:
                raise VaultaAuthenticationError("Authentication failed")
            elif response.status_code == 404:
                raise VaultaNotFoundError("Resource not found")
            elif response.status_code == 400:
                try:
                    error_data = response.json()
                    detail = error_data.get("detail", "Bad request")
                except (ValueError, KeyError):
                    detail = "Bad request"
                raise VaultaValidationError(detail)
            elif 400 <= response.status_code < 500:
                raise VaultaClientError(
                    f"Client error: {response.status_code}",
                    response.status_code,
                )
            elif 500 <= response.status_code < 600:
                raise VaultaServerError(
                    f"Server error: {response.status_code}",
                    response.status_code,
                )
            else:
                raise VaultaError(f"Unexpected status code: {response.status_code}")

        except requests.exceptions.RequestException as e:
            raise VaultaError(f"Request failed: {str(e)}")

    # Client Management Methods

    def get_clients(self, skip: int = 0, limit: int = 100) -> List[Client]:
        """
        Get a list of clients with pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of Client objects
        """
        params = {"skip": skip, "limit": limit}
        response = self._make_request("GET", "/clients", params=params)
        return [Client(**client_data) for client_data in response.json()]

    def get_client(self, client_id: str) -> Client:
        """
        Get a specific client by UUID.

        Args:
            client_id: The client UUID

        Returns:
            Client object

        Raises:
            VaultaNotFoundError: If client is not found
        """
        response = self._make_request("GET", f"/clients/{client_id}")
        return Client(**response.json())

    def get_client_by_client_id(self, client_id: str) -> Client:
        """
        Get a specific client by client_id (slug).

        Args:
            client_id: The client ID slug

        Returns:
            Client object

        Raises:
            VaultaNotFoundError: If client is not found
        """
        response = self._make_request("GET", f"/clients/by-client-id/{client_id}")
        return Client(**response.json())

    def create_client(self, client: ClientCreate) -> ClientWithSecret:
        """
        Create a new client.

        Args:
            client: ClientCreate object with client data

        Returns:
            ClientWithSecret object containing the new client and secret

        Raises:
            VaultaValidationError: If client_id already exists
        """
        response = self._make_request("POST", "/clients", data=client.model_dump())
        return ClientWithSecret(**response.json())

    def update_client(self, client_id: str, client: ClientUpdate) -> Client:
        """
        Update an existing client.

        Args:
            client_id: The client UUID
            client: ClientUpdate object with updated data

        Returns:
            Updated Client object

        Raises:
            VaultaNotFoundError: If client is not found
            VaultaValidationError: If client_id already exists
        """
        response = self._make_request(
            "PUT", f"/clients/{client_id}", data=client.model_dump(exclude_unset=True)
        )
        return Client(**response.json())

    def delete_client(self, client_id: str) -> bool:
        """
        Delete a client.

        Args:
            client_id: The client UUID

        Returns:
            True if successful

        Raises:
            VaultaNotFoundError: If client is not found
        """
        response = self._make_request("DELETE", f"/clients/{client_id}")
        return response.status_code == 200

    def regenerate_client_secret(self, client_id: str) -> ClientWithSecret:
        """
        Regenerate the secret for a client.

        Args:
            client_id: The client UUID

        Returns:
            ClientWithSecret object with the new secret

        Raises:
            VaultaNotFoundError: If client is not found
        """
        response = self._make_request("POST", f"/clients/{client_id}/regenerate-secret")
        return ClientWithSecret(**response.json())

    # Asset Management Methods

    def upload_asset(
        self,
        file_path: Union[str, Path, BinaryIO],
        name: Optional[str] = None,
        labels: Optional[Dict[str, Any]] = None,
    ) -> AssetUploadResponse:
        """
        Upload an asset.

        Args:
            file_path: Path to the file or file-like object
            name: Optional custom name for the asset
            labels: Optional dictionary of labels

        Returns:
            AssetUploadResponse object

        Raises:
            VaultaError: If upload fails
        """
        # Prepare the multipart form data
        files = {}
        data = {}

        if isinstance(file_path, (str, Path)):
            file_path = Path(file_path)
            if not file_path.exists():
                raise VaultaError(f"File not found: {file_path}")
            files["file"] = open(file_path, "rb")
        else:
            files["file"] = file_path  # type: ignore

        if name:
            data["name"] = name

        if labels:
            data["labels"] = json.dumps(labels)

        try:
            response = self._make_request("POST", "/assets", data=data, files=files)
            return AssetUploadResponse(**response.json())
        finally:
            # Close the file if we opened it
            if isinstance(file_path, Path) and "file" in files:
                files["file"].close()

    def search_assets(
        self,
        labels: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        state: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Asset]:
        """
        Search for assets based on criteria.

        Args:
            labels: Dictionary of labels to search for
            user_id: Optional user ID to filter by
            state: Optional state to filter by
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of Asset objects
        """
        if not labels:
            raise VaultaValidationError("Labels must be provided for asset search")

        query = AssetQuery(query=AssetLabels(labels=labels))
        params = {"skip": skip, "limit": limit}

        response = self._make_request(
            "POST", "/assets/search", data=query.model_dump(), params=params
        )
        return [Asset(**asset_data) for asset_data in response.json()]

    def get_asset_download_url(self, token: str) -> str:
        """
        Get the download URL for an asset using a token.

        Args:
            token: The download token

        Returns:
            Download URL
        """
        return f"{self.base_url}/assets/download/{token}"

    def get_asset_serve_url(self, payload: str) -> str:
        """
        Get the serve URL for an asset using a signed payload.

        Args:
            payload: The signed URL payload

        Returns:
            Serve URL
        """
        return f"{self.base_url}/assets/serve/{payload}"

    def download_asset(
        self, token: str, save_path: Optional[Union[str, Path]] = None
    ) -> Union[bytes, Path]:
        """
        Download an asset using a token.

        Args:
            token: The download token
            save_path: Optional path to save the file to

        Returns:
            File content as bytes if save_path is None, otherwise the path where file was saved
        """
        url = self.get_asset_download_url(token)
        response = self.session.get(url, timeout=self.timeout)

        if response.status_code != 200:
            raise VaultaError(f"Download failed: {response.status_code}")

        if save_path:
            save_path = Path(save_path)
            save_path.parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, "wb") as f:
                f.write(response.content)
            return save_path
        else:
            return response.content

    def serve_asset(
        self, payload: str, save_path: Optional[Union[str, Path]] = None
    ) -> Union[bytes, Path]:
        """
        Serve an asset using a signed payload.

        Args:
            payload: The signed URL payload
            save_path: Optional path to save the file to

        Returns:
            File content as bytes if save_path is None, otherwise the path where file was saved
        """
        url = self.get_asset_serve_url(payload)
        response = self.session.get(url, timeout=self.timeout)

        if response.status_code != 200:
            raise VaultaError(f"Serve failed: {response.status_code}")

        if save_path:
            save_path = Path(save_path)
            save_path.parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, "wb") as f:
                f.write(response.content)
            return save_path
        else:
            return response.content

    def delete_asset(self, asset_id: str) -> bool:
        """
        Delete an asset.

        Args:
            asset_id: The asset UUID

        Returns:
            True if successful

        Raises:
            VaultaNotFoundError: If asset is not found
        """
        response = self._make_request("DELETE", f"/assets/{asset_id}")
        return response.status_code == 200

    def generate_signed_serve_url(
        self, asset_id: str, client_id: str, secret: str, expires_in: int = 3600
    ) -> str:
        """
        Generate a signed serve URL for an asset.

        Args:
            asset_id: The asset ID to serve
            client_id: The client ID used for secret derivation
            secret: The secret key for signing (should be the derived secret)
            expires_in: Number of seconds until the URL expires (default: 3600 seconds / 1 hour)

        Returns:
            Signed serve URL
        """
        signed_payload = sign_serve_url(asset_id, client_id, secret, expires_in)
        return self.get_asset_serve_url(signed_payload)
