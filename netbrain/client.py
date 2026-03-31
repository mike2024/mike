"""NetBrain REST API client.

Typical usage::

    from netbrain import NetBrainClient

    with NetBrainClient("https://netbrain.example.com") as nb:
        nb.login("admin", "password")
        nb.set_current_domain(tenant_id="...", domain_id="...")
        devices = nb.get_all_devices()
        for d in devices:
            print(d.hostname, d.management_ip)
"""

from __future__ import annotations

import logging
from typing import List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .exceptions import (
    NetBrainAPIError,
    NetBrainAuthError,
    NetBrainNotFoundError,
    NetBrainSessionError,
)
from .models import (
    Device,
    DeviceConfig,
    DiagnosticTask,
    Domain,
    Interface,
    Neighbor,
    Site,
    Tenant,
    TopologyLink,
)

__all__ = ["NetBrainClient"]

logger = logging.getLogger(__name__)

_DEFAULT_PAGE_SIZE = 100
_SESSION_ENDPOINT = "/ServicesAPI/API/V1/Session"
_DOMAIN_ENDPOINT = "/ServicesAPI/API/V1/Session/CurrentDomain"


class NetBrainClient:
    """Client for the NetBrain REST API.

    Args:
        base_url: Base URL of the NetBrain server, e.g.
            ``https://netbrain.example.com``.
        verify_ssl: Whether to verify the server's TLS certificate.
            Set to ``False`` only in development/testing environments.
        timeout: HTTP request timeout in seconds.
        max_retries: Number of times to retry failed requests (5xx errors
            and connection failures only).

    Example::

        client = NetBrainClient("https://nb.example.com")
        client.login("admin", "secret")
        try:
            devices = client.get_all_devices()
        finally:
            client.logout()

    The client can also be used as a context manager, which calls
    :meth:`logout` automatically::

        with NetBrainClient("https://nb.example.com") as client:
            client.login("admin", "secret")
            devices = client.get_all_devices()
    """

    def __init__(
        self,
        base_url: str,
        verify_ssl: bool = True,
        timeout: int = 30,
        max_retries: int = 3,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._verify_ssl = verify_ssl
        self._timeout = timeout
        self._token: Optional[str] = None

        retry_strategy = Retry(
            total=max_retries,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET", "POST", "PUT", "DELETE"],
            backoff_factor=1,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self._session = requests.Session()
        self._session.mount("https://", adapter)
        self._session.mount("http://", adapter)
        self._session.headers.update(
            {"Content-Type": "application/json", "Accept": "application/json"}
        )

    # ------------------------------------------------------------------
    # Context-manager support
    # ------------------------------------------------------------------

    def __enter__(self) -> "NetBrainClient":
        return self

    def __exit__(self, *_: object) -> None:
        if self._token:
            try:
                self.logout()
            except NetBrainError:
                pass

    # ------------------------------------------------------------------
    # Authentication & session management
    # ------------------------------------------------------------------

    def login(
        self,
        username: str,
        password: str,
        authentication_id: str = "",
    ) -> str:
        """Authenticate with NetBrain and obtain a session token.

        Args:
            username: NetBrain username.
            password: NetBrain password.
            authentication_id: Optional external authentication provider
                identifier (e.g. ``"Tacacs"``).

        Returns:
            The session token string.

        Raises:
            NetBrainAuthError: If authentication fails.
        """
        body: dict = {"username": username, "password": password}
        if authentication_id:
            body["authentication_id"] = authentication_id

        response = self._request("POST", _SESSION_ENDPOINT, json=body, authenticated=False)
        token = response.get("token")
        if not token:
            raise NetBrainAuthError("Login succeeded but no token was returned.")
        self._token = token
        self._session.headers["token"] = token
        logger.debug("NetBrain login successful for user '%s'.", username)
        return token

    def logout(self) -> None:
        """Invalidate the current session token.

        Raises:
            NetBrainSessionError: If not logged in.
        """
        self._require_session()
        self._request("DELETE", _SESSION_ENDPOINT)
        self._token = None
        self._session.headers.pop("token", None)
        logger.debug("NetBrain logout successful.")

    def set_current_domain(self, tenant_id: str, domain_id: str) -> None:
        """Set the active tenant and domain for subsequent API calls.

        Args:
            tenant_id: UUID of the tenant to activate.
            domain_id: UUID of the domain to activate.

        Raises:
            NetBrainSessionError: If not logged in.
            NetBrainAPIError: If the tenant/domain IDs are invalid.
        """
        self._require_session()
        body = {"tenantId": tenant_id, "domainId": domain_id}
        self._request("PUT", _DOMAIN_ENDPOINT, json=body)
        logger.debug(
            "Active domain set to tenantId=%s domainId=%s.", tenant_id, domain_id
        )

    # ------------------------------------------------------------------
    # Tenant & domain discovery
    # ------------------------------------------------------------------

    def get_tenants(self) -> List[Tenant]:
        """Return all tenants accessible to the current user.

        Raises:
            NetBrainSessionError: If not logged in.
        """
        self._require_session()
        data = self._request("GET", "/ServicesAPI/API/V1/CMDB/Tenants")
        return [Tenant.from_dict(t) for t in data.get("tenants", [])]

    def get_domains(self, tenant_id: str) -> List[Domain]:
        """Return all domains within a tenant.

        Args:
            tenant_id: UUID of the tenant.

        Raises:
            NetBrainSessionError: If not logged in.
        """
        self._require_session()
        data = self._request(
            "GET",
            "/ServicesAPI/API/V1/CMDB/Domains",
            params={"tenantId": tenant_id},
        )
        return [Domain.from_dict(d) for d in data.get("domains", [])]

    # ------------------------------------------------------------------
    # Device APIs
    # ------------------------------------------------------------------

    def get_devices(
        self, hostname: Optional[str] = None, limit: int = _DEFAULT_PAGE_SIZE, skip: int = 0
    ) -> List[Device]:
        """Return a single page of devices.

        Args:
            hostname: Optional filter — return only this device.
            limit: Maximum number of devices to return (max 100).
            skip: Number of devices to skip for pagination.

        Raises:
            NetBrainSessionError: If not logged in.
        """
        self._require_session()
        params: dict = {"version": 1, "limit": min(limit, _DEFAULT_PAGE_SIZE), "skip": skip}
        if hostname:
            params["hostname"] = hostname
        data = self._request("GET", "/ServicesAPI/API/V1/CMDB/Devices", params=params)
        return [Device.from_dict(d) for d in data.get("devices", [])]

    def get_all_devices(self) -> List[Device]:
        """Return **all** devices, automatically handling pagination.

        Raises:
            NetBrainSessionError: If not logged in.
        """
        devices: List[Device] = []
        skip = 0
        while True:
            page = self.get_devices(limit=_DEFAULT_PAGE_SIZE, skip=skip)
            devices.extend(page)
            if len(page) < _DEFAULT_PAGE_SIZE:
                break
            skip += _DEFAULT_PAGE_SIZE
        return devices

    def get_device_by_hostname(self, hostname: str) -> Device:
        """Fetch a single device by hostname.

        Args:
            hostname: Exact hostname of the device.

        Raises:
            NetBrainNotFoundError: If no device with that hostname exists.
            NetBrainSessionError: If not logged in.
        """
        self._require_session()
        data = self._request(
            "GET",
            "/ServicesAPI/API/V1/CMDB/Devices",
            params={"version": 1, "hostname": hostname, "limit": 1, "skip": 0},
        )
        devices = data.get("devices", [])
        if not devices:
            raise NetBrainNotFoundError(
                f"Device '{hostname}' not found.",
                status_code=404,
            )
        return Device.from_dict(devices[0])

    def get_device_interfaces(self, hostname: str) -> List[Interface]:
        """Return all interfaces for a device.

        Args:
            hostname: Hostname of the device.

        Raises:
            NetBrainSessionError: If not logged in.
        """
        self._require_session()
        data = self._request(
            "GET",
            "/ServicesAPI/API/V1/CMDB/Devices/Interfaces",
            params={"hostname": hostname},
        )
        return [Interface.from_dict(i) for i in data.get("interfaces", [])]

    def get_device_neighbors(self, hostname: str) -> List[Neighbor]:
        """Return CDP/LLDP neighbors for a device.

        Args:
            hostname: Hostname of the device.

        Raises:
            NetBrainSessionError: If not logged in.
        """
        self._require_session()
        data = self._request(
            "GET",
            "/ServicesAPI/API/V1/CMDB/Devices/Neighbors",
            params={"hostname": hostname},
        )
        return [Neighbor.from_dict(n) for n in data.get("neighbors", [])]

    def get_device_config(self, hostname: str) -> DeviceConfig:
        """Fetch the running configuration of a device.

        Args:
            hostname: Hostname of the device.

        Raises:
            NetBrainSessionError: If not logged in.
            NetBrainNotFoundError: If the device is not found.
        """
        self._require_session()
        data = self._request(
            "GET",
            "/ServicesAPI/API/V1/CMDB/Devices/DeviceRawData",
            params={"hostname": hostname, "dataType": 1},
        )
        if not data.get("content"):
            raise NetBrainNotFoundError(
                f"No configuration data found for device '{hostname}'.",
                status_code=404,
            )
        return DeviceConfig(
            hostname=hostname,
            config_content=data.get("content", ""),
            retrieve_time=data.get("retrieveTime", ""),
        )

    # ------------------------------------------------------------------
    # Site APIs
    # ------------------------------------------------------------------

    def get_sites(self) -> List[Site]:
        """Return all sites in the current domain.

        Raises:
            NetBrainSessionError: If not logged in.
        """
        self._require_session()
        data = self._request("GET", "/ServicesAPI/API/V1/CMDB/Sites")
        return [Site.from_dict(s) for s in data.get("sites", [])]

    def get_site_devices(self, site_path: str) -> List[Device]:
        """Return all devices belonging to a site.

        Args:
            site_path: Full site path (e.g. ``"My Network/US/NY"``).

        Raises:
            NetBrainSessionError: If not logged in.
        """
        self._require_session()
        data = self._request(
            "GET",
            "/ServicesAPI/API/V1/CMDB/Sites/Devices",
            params={"sitePath": site_path},
        )
        return [Device.from_dict(d) for d in data.get("devices", [])]

    # ------------------------------------------------------------------
    # Topology APIs
    # ------------------------------------------------------------------

    def get_topology_links(
        self,
        hostname: str,
        topology_type: int = 3,
    ) -> List[TopologyLink]:
        """Return topology links (neighbors) for a device.

        Args:
            hostname: Hostname of the device.
            topology_type: ``1`` = L2, ``2`` = L3, ``3`` = both.

        Raises:
            NetBrainSessionError: If not logged in.
        """
        self._require_session()
        data = self._request(
            "GET",
            "/ServicesAPI/API/V1/CMDB/Topology/Devices/Neighbors",
            params={"hostname": hostname, "topoType": topology_type},
        )
        return [TopologyLink.from_dict(lnk) for lnk in data.get("neighbors", [])]

    # ------------------------------------------------------------------
    # Diagnostic / Runbook task APIs
    # ------------------------------------------------------------------

    def run_diagnostic_task(
        self,
        task_name: str,
        task_params: Optional[dict] = None,
    ) -> DiagnosticTask:
        """Trigger a diagnostic task (Qapp / runbook) by name.

        Args:
            task_name: Name of the runbook / Qapp to execute.
            task_params: Optional dictionary of task input parameters.

        Returns:
            A :class:`DiagnosticTask` instance with the execution result.

        Raises:
            NetBrainSessionError: If not logged in.
            NetBrainAPIError: If the task execution fails.
        """
        self._require_session()
        body: dict = {"taskName": task_name}
        if task_params:
            body["taskParams"] = task_params
        data = self._request(
            "POST",
            "/ServicesAPI/API/V1/Triggers/Run",
            json=body,
        )
        return DiagnosticTask.from_dict(data)

    def get_task_status(self, task_id: str) -> DiagnosticTask:
        """Poll the execution status of a previously triggered task.

        Args:
            task_id: Task identifier returned by :meth:`run_diagnostic_task`.

        Raises:
            NetBrainSessionError: If not logged in.
            NetBrainNotFoundError: If the task ID is not found.
        """
        self._require_session()
        data = self._request(
            "GET",
            "/ServicesAPI/API/V1/Triggers/Run",
            params={"taskId": task_id},
        )
        if not data:
            raise NetBrainNotFoundError(
                f"Task '{task_id}' not found.", status_code=404
            )
        return DiagnosticTask.from_dict(data)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _require_session(self) -> None:
        if not self._token:
            raise NetBrainSessionError(
                "No active session. Call login() before making API requests."
            )

    def _request(
        self,
        method: str,
        path: str,
        *,
        authenticated: bool = True,
        **kwargs: object,
    ) -> dict:
        """Make an HTTP request to the NetBrain API.

        Args:
            method: HTTP method string (``"GET"``, ``"POST"``, etc.).
            path: API path starting with ``/``.
            authenticated: If ``False``, skip the session-token check
                (used for login).
            **kwargs: Forwarded to :meth:`requests.Session.request`.

        Returns:
            Parsed JSON response body as a dictionary.

        Raises:
            NetBrainAuthError: On HTTP 401 responses.
            NetBrainNotFoundError: On HTTP 404 responses.
            NetBrainAPIError: On other non-2xx responses or API-level
                errors reported in the response body.
        """
        url = f"{self._base_url}{path}"
        logger.debug("%s %s", method, url)

        response = self._session.request(
            method,
            url,
            verify=self._verify_ssl,
            timeout=self._timeout,
            **kwargs,
        )

        if response.status_code == 401:
            raise NetBrainAuthError(
                f"Authentication failed: {response.text}"
            )
        if response.status_code == 404:
            raise NetBrainNotFoundError(
                f"Resource not found: {path}",
                status_code=404,
            )

        try:
            body: dict = response.json()
        except ValueError:
            response.raise_for_status()
            return {}

        # NetBrain encodes API-level errors inside a 200 OK response using
        # a ``statusCode`` field that is non-zero on failure.
        api_status = body.get("statusCode", 0)
        if api_status != 0:
            description = body.get("statusDescription", "")
            raise NetBrainAPIError(
                f"NetBrain API error {api_status}: {description}",
                status_code=api_status,
                status_description=description,
            )

        response.raise_for_status()
        return body


# Convenience import so callers can do: from netbrain.exceptions import …
from .exceptions import NetBrainError  # noqa: E402  (avoid circular at top)
