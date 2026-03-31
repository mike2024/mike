"""NetBrain API client package.

Exposes the primary :class:`~netbrain.client.NetBrainClient` class and
all custom exceptions at the package level for convenient imports::

    from netbrain import NetBrainClient
    from netbrain import NetBrainAuthError, NetBrainAPIError
"""

from .client import NetBrainClient
from .exceptions import (
    NetBrainAPIError,
    NetBrainAuthError,
    NetBrainError,
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

__all__ = [
    "NetBrainClient",
    # Exceptions
    "NetBrainError",
    "NetBrainAuthError",
    "NetBrainAPIError",
    "NetBrainNotFoundError",
    "NetBrainSessionError",
    # Models
    "Device",
    "DeviceConfig",
    "DiagnosticTask",
    "Domain",
    "Interface",
    "Neighbor",
    "Site",
    "Tenant",
    "TopologyLink",
]
