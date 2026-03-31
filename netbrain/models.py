"""Typed dataclasses representing NetBrain API objects."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Device:
    """A network device managed by NetBrain.

    Attributes:
        hostname: Device hostname (primary identifier in NetBrain).
        management_ip: Management IP address of the device.
        device_type: Device type / model string.
        first_discover_time: ISO-8601 timestamp of first discovery.
        last_discover_time: ISO-8601 timestamp of latest discovery.
        site: Full site path where the device belongs.
    """

    hostname: str
    management_ip: str = ""
    device_type: str = ""
    first_discover_time: str = ""
    last_discover_time: str = ""
    site: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "Device":
        return cls(
            hostname=data.get("hostname", ""),
            management_ip=data.get("mgmtIP", ""),
            device_type=data.get("deviceTypeName", ""),
            first_discover_time=data.get("firstDiscoverTime", ""),
            last_discover_time=data.get("lastDiscoverTime", ""),
            site=data.get("site", ""),
        )


@dataclass
class Interface:
    """A network interface on a device.

    Attributes:
        name: Interface name (e.g. ``GigabitEthernet0/0``).
        ip_address: IPv4 address configured on the interface.
        subnet_mask: Subnet mask for the IP address.
        description: Interface description from the device config.
        intf_status: Operational status (``UP`` / ``DOWN``).
    """

    name: str
    ip_address: str = ""
    subnet_mask: str = ""
    description: str = ""
    intf_status: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "Interface":
        return cls(
            name=data.get("name", ""),
            ip_address=data.get("ipAddr", ""),
            subnet_mask=data.get("subnetMask", ""),
            description=data.get("descr", ""),
            intf_status=data.get("intfStatus", ""),
        )


@dataclass
class Neighbor:
    """A CDP/LLDP neighbor entry.

    Attributes:
        local_interface: Local interface name.
        neighbor_hostname: Hostname of the neighboring device.
        neighbor_interface: Interface on the neighboring device.
    """

    local_interface: str
    neighbor_hostname: str = ""
    neighbor_interface: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "Neighbor":
        return cls(
            local_interface=data.get("localInterface", ""),
            neighbor_hostname=data.get("neighborHostname", ""),
            neighbor_interface=data.get("neighborInterface", ""),
        )


@dataclass
class Tenant:
    """A NetBrain tenant.

    Attributes:
        tenant_id: Unique tenant identifier (UUID).
        tenant_name: Human-readable tenant name.
        description: Optional tenant description.
    """

    tenant_id: str
    tenant_name: str = ""
    description: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "Tenant":
        return cls(
            tenant_id=data.get("tenantId", ""),
            tenant_name=data.get("tenantName", ""),
            description=data.get("description", ""),
        )


@dataclass
class Domain:
    """A NetBrain network domain within a tenant.

    Attributes:
        domain_id: Unique domain identifier (UUID).
        domain_name: Human-readable domain name.
        description: Optional domain description.
        tenant_id: ID of the parent tenant.
    """

    domain_id: str
    domain_name: str = ""
    description: str = ""
    tenant_id: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "Domain":
        return cls(
            domain_id=data.get("domainId", ""),
            domain_name=data.get("domainName", ""),
            description=data.get("description", ""),
            tenant_id=data.get("tenantId", ""),
        )


@dataclass
class DiagnosticTask:
    """A NetBrain diagnostic/runbook task result.

    Attributes:
        task_id: Unique task identifier.
        status: Task execution status string.
        result: Detailed result payload from the task.
    """

    task_id: str
    status: str = ""
    result: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "DiagnosticTask":
        return cls(
            task_id=data.get("taskId", ""),
            status=data.get("status", ""),
            result=data.get("result", {}),
        )


@dataclass
class Site:
    """A site (location) in the NetBrain site hierarchy.

    Attributes:
        site_id: Unique site identifier.
        site_name: Leaf name of the site.
        site_path: Full hierarchical path (e.g. ``My Network/US/NY``).
        site_type: ``0`` = container site, ``1`` = leaf site.
    """

    site_id: str
    site_name: str = ""
    site_path: str = ""
    site_type: int = 0

    @classmethod
    def from_dict(cls, data: dict) -> "Site":
        return cls(
            site_id=data.get("siteId", ""),
            site_name=data.get("siteName", ""),
            site_path=data.get("sitePath", ""),
            site_type=data.get("siteType", 0),
        )


@dataclass
class DeviceConfig:
    """Running / startup configuration snapshot for a device.

    Attributes:
        hostname: Device the config belongs to.
        config_content: Raw configuration text.
        retrieve_time: ISO-8601 timestamp when the config was fetched.
    """

    hostname: str
    config_content: str = ""
    retrieve_time: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "DeviceConfig":
        return cls(
            hostname=data.get("hostname", ""),
            config_content=data.get("configContent", ""),
            retrieve_time=data.get("retrieveTime", ""),
        )


@dataclass
class TopologyLink:
    """A single link in a NetBrain L3/L2 topology.

    Attributes:
        from_device: Source device hostname.
        from_interface: Source interface name.
        to_device: Destination device hostname.
        to_interface: Destination interface name.
        link_type: Topology layer (``\"L3\"`` / ``\"L2\"``).
    """

    from_device: str
    from_interface: str = ""
    to_device: str = ""
    to_interface: str = ""
    link_type: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "TopologyLink":
        return cls(
            from_device=data.get("fromDevice", ""),
            from_interface=data.get("fromInterface", ""),
            to_device=data.get("toDevice", ""),
            to_interface=data.get("toInterface", ""),
            link_type=data.get("linkType", ""),
        )
