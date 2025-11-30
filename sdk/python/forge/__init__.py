"""
Forge SDK - Python client for Forge infrastructure platform
"""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("forge-sdk")
except PackageNotFoundError:
    # Package not installed (running from source)
    __version__ = "0.1.0"

from .client import Forge
from .db import DatabaseClient
from .cache import CacheClient
from .observe import LogsClient, MetricsClient, TracesClient

__all__ = [
    "Forge",
    "DatabaseClient",
    "CacheClient",
    "LogsClient",
    "MetricsClient",
    "TracesClient",
    "__version__",
]

