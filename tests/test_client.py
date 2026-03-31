"""Unit tests for the NetBrain API client."""

import json
import unittest
from unittest.mock import MagicMock, patch

from netbrain import (
    NetBrainAPIError,
    NetBrainAuthError,
    NetBrainClient,
    NetBrainNotFoundError,
    NetBrainSessionError,
)
from netbrain.models import (
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

_BASE_URL = "https://netbrain.example.com"
_TOKEN = "test-token-abc123"


def _mock_response(status_code: int = 200, body: dict = None) -> MagicMock:
    """Build a mock :class:`requests.Response` object."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = body or {}
    resp.text = json.dumps(body or {})
    resp.raise_for_status = MagicMock()
    return resp


class TestNetBrainClientAuth(unittest.TestCase):
    """Tests for login / logout / session management."""

    def _make_client(self) -> NetBrainClient:
        return NetBrainClient(_BASE_URL)

    @patch("netbrain.client.requests.Session")
    def test_login_sets_token(self, mock_session_cls):
        mock_session = mock_session_cls.return_value
        mock_session.request.return_value = _mock_response(
            200, {"statusCode": 0, "token": _TOKEN}
        )
        mock_session.headers = {}

        client = NetBrainClient(_BASE_URL)
        client._session = mock_session

        token = client.login("admin", "secret")
        self.assertEqual(token, _TOKEN)
        self.assertEqual(client._token, _TOKEN)
        self.assertEqual(mock_session.headers["token"], _TOKEN)

    @patch("netbrain.client.requests.Session")
    def test_login_raises_on_401(self, mock_session_cls):
        mock_session = mock_session_cls.return_value
        mock_session.request.return_value = _mock_response(401, {})
        mock_session.headers = {}

        client = NetBrainClient(_BASE_URL)
        client._session = mock_session

        with self.assertRaises(NetBrainAuthError):
            client.login("bad", "creds")

    @patch("netbrain.client.requests.Session")
    def test_login_raises_on_api_error(self, mock_session_cls):
        mock_session = mock_session_cls.return_value
        mock_session.request.return_value = _mock_response(
            200, {"statusCode": 100, "statusDescription": "Invalid credentials"}
        )
        mock_session.headers = {}

        client = NetBrainClient(_BASE_URL)
        client._session = mock_session

        with self.assertRaises(NetBrainAPIError) as ctx:
            client.login("admin", "wrong")
        self.assertEqual(ctx.exception.status_code, 100)

    @patch("netbrain.client.requests.Session")
    def test_logout_clears_token(self, mock_session_cls):
        mock_session = mock_session_cls.return_value
        mock_session.request.return_value = _mock_response(
            200, {"statusCode": 0}
        )
        mock_session.headers = {"token": _TOKEN}

        client = NetBrainClient(_BASE_URL)
        client._session = mock_session
        client._token = _TOKEN

        client.logout()
        self.assertIsNone(client._token)

    def test_requires_session_raises_when_not_logged_in(self):
        client = NetBrainClient(_BASE_URL)
        with self.assertRaises(NetBrainSessionError):
            client.logout()

    @patch("netbrain.client.requests.Session")
    def test_context_manager_calls_logout(self, mock_session_cls):
        mock_session = mock_session_cls.return_value
        mock_session.request.return_value = _mock_response(
            200, {"statusCode": 0}
        )
        mock_session.headers = {"token": _TOKEN}

        client = NetBrainClient(_BASE_URL)
        client._session = mock_session
        client._token = _TOKEN

        with client:
            pass

        mock_session.request.assert_called_once()


class TestNetBrainClientDevices(unittest.TestCase):
    """Tests for device-related API methods."""

    def _make_client(self) -> NetBrainClient:
        client = NetBrainClient(_BASE_URL)
        client._token = _TOKEN
        client._session = MagicMock()
        client._session.headers = {"token": _TOKEN}
        return client

    def test_get_devices_returns_device_list(self):
        client = self._make_client()
        client._session.request.return_value = _mock_response(
            200,
            {
                "statusCode": 0,
                "devices": [
                    {
                        "hostname": "router1",
                        "mgmtIP": "10.0.0.1",
                        "deviceTypeName": "Cisco IOS Router",
                        "site": "My Network/US",
                    }
                ],
            },
        )
        devices = client.get_devices()
        self.assertEqual(len(devices), 1)
        self.assertIsInstance(devices[0], Device)
        self.assertEqual(devices[0].hostname, "router1")
        self.assertEqual(devices[0].management_ip, "10.0.0.1")

    def test_get_all_devices_paginates(self):
        client = self._make_client()
        full_page = [{"hostname": f"router{i}", "mgmtIP": f"10.0.0.{i}"} for i in range(100)]
        partial_page = [{"hostname": "router100", "mgmtIP": "10.0.1.0"}]

        responses = [
            _mock_response(200, {"statusCode": 0, "devices": full_page}),
            _mock_response(200, {"statusCode": 0, "devices": partial_page}),
        ]
        client._session.request.side_effect = responses

        devices = client.get_all_devices()
        self.assertEqual(len(devices), 101)
        self.assertEqual(client._session.request.call_count, 2)

    def test_get_device_by_hostname_found(self):
        client = self._make_client()
        client._session.request.return_value = _mock_response(
            200,
            {
                "statusCode": 0,
                "devices": [{"hostname": "sw1", "mgmtIP": "192.168.1.1"}],
            },
        )
        device = client.get_device_by_hostname("sw1")
        self.assertEqual(device.hostname, "sw1")

    def test_get_device_by_hostname_not_found(self):
        client = self._make_client()
        client._session.request.return_value = _mock_response(
            200, {"statusCode": 0, "devices": []}
        )
        with self.assertRaises(NetBrainNotFoundError):
            client.get_device_by_hostname("nonexistent")

    def test_get_device_interfaces(self):
        client = self._make_client()
        client._session.request.return_value = _mock_response(
            200,
            {
                "statusCode": 0,
                "interfaces": [
                    {
                        "name": "GigabitEthernet0/0",
                        "ipAddr": "10.1.1.1",
                        "subnetMask": "255.255.255.0",
                        "descr": "Uplink",
                        "intfStatus": "UP",
                    }
                ],
            },
        )
        interfaces = client.get_device_interfaces("router1")
        self.assertEqual(len(interfaces), 1)
        self.assertIsInstance(interfaces[0], Interface)
        self.assertEqual(interfaces[0].name, "GigabitEthernet0/0")
        self.assertEqual(interfaces[0].intf_status, "UP")

    def test_get_device_neighbors(self):
        client = self._make_client()
        client._session.request.return_value = _mock_response(
            200,
            {
                "statusCode": 0,
                "neighbors": [
                    {
                        "localInterface": "Gi0/0",
                        "neighborHostname": "switch1",
                        "neighborInterface": "Gi1/0/1",
                    }
                ],
            },
        )
        neighbors = client.get_device_neighbors("router1")
        self.assertEqual(len(neighbors), 1)
        self.assertIsInstance(neighbors[0], Neighbor)
        self.assertEqual(neighbors[0].neighbor_hostname, "switch1")

    def test_get_device_config(self):
        client = self._make_client()
        client._session.request.return_value = _mock_response(
            200,
            {
                "statusCode": 0,
                "content": "hostname router1\n...",
                "retrieveTime": "2024-01-01T00:00:00Z",
            },
        )
        config = client.get_device_config("router1")
        self.assertIsInstance(config, DeviceConfig)
        self.assertIn("hostname router1", config.config_content)

    def test_get_device_config_not_found(self):
        client = self._make_client()
        client._session.request.return_value = _mock_response(
            200, {"statusCode": 0, "content": ""}
        )
        with self.assertRaises(NetBrainNotFoundError):
            client.get_device_config("ghost-device")


class TestNetBrainClientTenantsDomains(unittest.TestCase):
    """Tests for tenant / domain API methods."""

    def _make_client(self) -> NetBrainClient:
        client = NetBrainClient(_BASE_URL)
        client._token = _TOKEN
        client._session = MagicMock()
        client._session.headers = {"token": _TOKEN}
        return client

    def test_get_tenants(self):
        client = self._make_client()
        client._session.request.return_value = _mock_response(
            200,
            {
                "statusCode": 0,
                "tenants": [{"tenantId": "t1", "tenantName": "Default"}],
            },
        )
        tenants = client.get_tenants()
        self.assertEqual(len(tenants), 1)
        self.assertIsInstance(tenants[0], Tenant)
        self.assertEqual(tenants[0].tenant_id, "t1")

    def test_get_domains(self):
        client = self._make_client()
        client._session.request.return_value = _mock_response(
            200,
            {
                "statusCode": 0,
                "domains": [
                    {
                        "domainId": "d1",
                        "domainName": "Production",
                        "tenantId": "t1",
                    }
                ],
            },
        )
        domains = client.get_domains("t1")
        self.assertEqual(len(domains), 1)
        self.assertIsInstance(domains[0], Domain)
        self.assertEqual(domains[0].domain_id, "d1")

    def test_set_current_domain(self):
        client = self._make_client()
        client._session.request.return_value = _mock_response(
            200, {"statusCode": 0}
        )
        client.set_current_domain("t1", "d1")
        client._session.request.assert_called_once()


class TestNetBrainClientSites(unittest.TestCase):
    """Tests for site-related API methods."""

    def _make_client(self) -> NetBrainClient:
        client = NetBrainClient(_BASE_URL)
        client._token = _TOKEN
        client._session = MagicMock()
        client._session.headers = {"token": _TOKEN}
        return client

    def test_get_sites(self):
        client = self._make_client()
        client._session.request.return_value = _mock_response(
            200,
            {
                "statusCode": 0,
                "sites": [
                    {
                        "siteId": "s1",
                        "siteName": "NY",
                        "sitePath": "My Network/US/NY",
                        "siteType": 1,
                    }
                ],
            },
        )
        sites = client.get_sites()
        self.assertEqual(len(sites), 1)
        self.assertIsInstance(sites[0], Site)
        self.assertEqual(sites[0].site_path, "My Network/US/NY")

    def test_get_site_devices(self):
        client = self._make_client()
        client._session.request.return_value = _mock_response(
            200,
            {
                "statusCode": 0,
                "devices": [{"hostname": "nyc-rtr1", "mgmtIP": "10.10.0.1"}],
            },
        )
        devices = client.get_site_devices("My Network/US/NY")
        self.assertEqual(len(devices), 1)
        self.assertEqual(devices[0].hostname, "nyc-rtr1")


class TestNetBrainClientTopology(unittest.TestCase):
    """Tests for topology API methods."""

    def _make_client(self) -> NetBrainClient:
        client = NetBrainClient(_BASE_URL)
        client._token = _TOKEN
        client._session = MagicMock()
        client._session.headers = {"token": _TOKEN}
        return client

    def test_get_topology_links(self):
        client = self._make_client()
        client._session.request.return_value = _mock_response(
            200,
            {
                "statusCode": 0,
                "neighbors": [
                    {
                        "fromDevice": "router1",
                        "fromInterface": "Gi0/0",
                        "toDevice": "switch1",
                        "toInterface": "Gi1/0/1",
                        "linkType": "L3",
                    }
                ],
            },
        )
        links = client.get_topology_links("router1")
        self.assertEqual(len(links), 1)
        self.assertIsInstance(links[0], TopologyLink)
        self.assertEqual(links[0].to_device, "switch1")


class TestNetBrainClientDiagnostics(unittest.TestCase):
    """Tests for diagnostic task APIs."""

    def _make_client(self) -> NetBrainClient:
        client = NetBrainClient(_BASE_URL)
        client._token = _TOKEN
        client._session = MagicMock()
        client._session.headers = {"token": _TOKEN}
        return client

    def test_run_diagnostic_task(self):
        client = self._make_client()
        client._session.request.return_value = _mock_response(
            200,
            {
                "statusCode": 0,
                "taskId": "task-001",
                "status": "running",
                "result": {},
            },
        )
        task = client.run_diagnostic_task("CheckBGP", {"device": "router1"})
        self.assertIsInstance(task, DiagnosticTask)
        self.assertEqual(task.task_id, "task-001")

    def test_get_task_status(self):
        client = self._make_client()
        client._session.request.return_value = _mock_response(
            200,
            {
                "statusCode": 0,
                "taskId": "task-001",
                "status": "completed",
                "result": {"output": "BGP OK"},
            },
        )
        task = client.get_task_status("task-001")
        self.assertEqual(task.status, "completed")

    def test_get_task_status_not_found(self):
        client = self._make_client()
        client._session.request.return_value = _mock_response(200, None)
        with self.assertRaises(NetBrainNotFoundError):
            client.get_task_status("nonexistent-task")


class TestModels(unittest.TestCase):
    """Tests for model dataclasses."""

    def test_device_from_dict(self):
        d = Device.from_dict(
            {
                "hostname": "rtr1",
                "mgmtIP": "1.2.3.4",
                "deviceTypeName": "Cisco IOS",
                "firstDiscoverTime": "2024-01-01",
                "lastDiscoverTime": "2024-06-01",
                "site": "Corp/HQ",
            }
        )
        self.assertEqual(d.hostname, "rtr1")
        self.assertEqual(d.management_ip, "1.2.3.4")
        self.assertEqual(d.device_type, "Cisco IOS")
        self.assertEqual(d.site, "Corp/HQ")

    def test_device_from_dict_missing_fields(self):
        d = Device.from_dict({"hostname": "rtr2"})
        self.assertEqual(d.hostname, "rtr2")
        self.assertEqual(d.management_ip, "")

    def test_interface_from_dict(self):
        i = Interface.from_dict(
            {
                "name": "Gi0/1",
                "ipAddr": "192.168.1.1",
                "subnetMask": "255.255.255.0",
                "descr": "LAN",
                "intfStatus": "UP",
            }
        )
        self.assertEqual(i.name, "Gi0/1")
        self.assertEqual(i.intf_status, "UP")

    def test_topology_link_from_dict(self):
        lnk = TopologyLink.from_dict(
            {
                "fromDevice": "A",
                "fromInterface": "Gi0",
                "toDevice": "B",
                "toInterface": "Gi1",
                "linkType": "L2",
            }
        )
        self.assertEqual(lnk.from_device, "A")
        self.assertEqual(lnk.link_type, "L2")

    def test_tenant_from_dict(self):
        t = Tenant.from_dict({"tenantId": "tid", "tenantName": "Corp"})
        self.assertEqual(t.tenant_id, "tid")
        self.assertEqual(t.tenant_name, "Corp")

    def test_domain_from_dict(self):
        d = Domain.from_dict(
            {"domainId": "did", "domainName": "Prod", "tenantId": "tid"}
        )
        self.assertEqual(d.domain_id, "did")
        self.assertEqual(d.tenant_id, "tid")


if __name__ == "__main__":
    unittest.main()
