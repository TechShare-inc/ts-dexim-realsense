"""Factory helpers for constructing RealSense interfaces."""

from __future__ import annotations

from dexim.core.messages import FrameObservation
from dexim.core.robot_interface import SensorInterface

from dexim.realsense.interface.config import RealSenseConfig
from dexim.realsense.interface.mock_interface import MockRealSenseInterface
from dexim.realsense.interface.realsense_interface import RealSenseInterface


def build_interface(config: RealSenseConfig) -> SensorInterface[FrameObservation]:
    """Build the appropriate interface implementation from config.

    Args:
        config: Interface configuration.

    Returns:
        MockRealSenseInterface or RealSenseInterface.
    """
    if config.mode == "mock":
        return MockRealSenseInterface(config=config)
    return RealSenseInterface(config=config)
