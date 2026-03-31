# NetBrain API Client

A Python client for the [NetBrain REST API](https://github.com/NetBrainAPI/NetBrain-REST-API-R12.1),
providing a clean, typed interface to authenticate, query network devices,
interfaces, neighbours, topology, sites, and diagnostic tasks.

## Requirements

- Python 3.8+
- `requests` ≥ 2.28.0

Install dependencies:

```bash
pip install -r requirements.txt
```

## Quick Start

```python
from netbrain import NetBrainClient

# Use as a context manager — logout is called automatically
with NetBrainClient("https://netbrain.example.com") as nb:
    nb.login("admin", "password")
    nb.set_current_domain(tenant_id="<tenant-uuid>", domain_id="<domain-uuid>")

    # List all devices (handles pagination automatically)
    devices = nb.get_all_devices()
    for device in devices:
        print(device.hostname, device.management_ip)
```

## Features

| Area | Methods |
|------|---------|
| **Authentication** | `login()`, `logout()` |
| **Session** | `set_current_domain()` |
| **Tenants / Domains** | `get_tenants()`, `get_domains()` |
| **Devices** | `get_devices()`, `get_all_devices()`, `get_device_by_hostname()` |
| **Interfaces** | `get_device_interfaces()` |
| **Neighbours** | `get_device_neighbors()` |
| **Configuration** | `get_device_config()` |
| **Sites** | `get_sites()`, `get_site_devices()` |
| **Topology** | `get_topology_links()` |
| **Diagnostics** | `run_diagnostic_task()`, `get_task_status()` |

## Examples

### Fetch interfaces for a device

```python
with NetBrainClient("https://nb.example.com") as nb:
    nb.login("admin", "password")
    nb.set_current_domain("tenant-id", "domain-id")

    interfaces = nb.get_device_interfaces("router1")
    for intf in interfaces:
        print(f"{intf.name}: {intf.ip_address}/{intf.subnet_mask} [{intf.intf_status}]")
```

### List devices in a site

```python
with NetBrainClient("https://nb.example.com") as nb:
    nb.login("admin", "password")
    nb.set_current_domain("tenant-id", "domain-id")

    devices = nb.get_site_devices("My Network/US/New York")
    for device in devices:
        print(device.hostname)
```

### Run a diagnostic task

```python
with NetBrainClient("https://nb.example.com") as nb:
    nb.login("admin", "password")
    nb.set_current_domain("tenant-id", "domain-id")

    task = nb.run_diagnostic_task("CheckBGPNeighbors", {"device": "router1"})
    print(task.task_id, task.status)
```

### External authentication (e.g. TACACS)

```python
with NetBrainClient("https://nb.example.com") as nb:
    nb.login("admin", "password", authentication_id="Tacacs")
    ...
```

## Error Handling

```python
from netbrain import (
    NetBrainAuthError,
    NetBrainAPIError,
    NetBrainNotFoundError,
    NetBrainSessionError,
)

try:
    with NetBrainClient("https://nb.example.com") as nb:
        nb.login("admin", "wrong-password")
except NetBrainAuthError as e:
    print("Login failed:", e)
except NetBrainNotFoundError as e:
    print("Resource not found:", e)
except NetBrainAPIError as e:
    print(f"API error {e.status_code}: {e.status_description}")
```

## Running Tests

```bash
python -m pytest tests/ -v
```
