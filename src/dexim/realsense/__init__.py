"""dexim.realsense - RealSense camera sensor package."""

from dexim.realsense.interface import MockRealSenseInterface, RealSenseConfig
from dexim.realsense.node import RealSenseNode, RealSenseNodeConfig, load_config

__all__: list[str] = []

__all__ += [
    "MockRealSenseInterface",
    "RealSenseConfig",
    "RealSenseNode",
    "RealSenseNodeConfig",
    "load_config",
]

try:
    from dexim.realsense.interface import RealSenseInterface

    __all__ += ["RealSenseInterface"]
except ImportError:
    pass
