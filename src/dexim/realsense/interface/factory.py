"""Factory helpers for constructing RealSense interfaces."""

from __future__ import annotations

from typing import Protocol

from dexim.core.messages import FrameObservation
from dexim.core.robot_interface import SensorInterface

from dexim.realsense.interface.config import RealSenseConfig
from dexim.realsense.interface.mock_interface import MockRealSenseInterface
from dexim.realsense.interface.realsense_interface import RealSenseInterface


class _ConnectedSensorInterface(SensorInterface[FrameObservation], Protocol):
    """Sensor interface that can report its connection state."""

    def is_connected(self) -> bool: ...


def build_interface(config: RealSenseConfig) -> _ConnectedSensorInterface:
    """Build the appropriate interface implementation from config.

    Args:
        config: Interface configuration.

    Returns:
        MockRealSenseInterface or RealSenseInterface.
    """
    if config.mode == "mock":
        return MockRealSenseInterface(config=config)
    return RealSenseInterface(config=config)
