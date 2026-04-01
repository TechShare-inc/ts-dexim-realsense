"""Mock RealSense interface for tests and development without hardware."""

from __future__ import annotations

import time

import numpy as np
from dexim.core.messages import FrameObservation
from dexim.core.robot_interface import SensorInterface

from dexim.realsense.interface.config import RealSenseConfig


class MockRealSenseInterface(SensorInterface[FrameObservation]):
    """In-memory mock implementation of a RealSense-like camera source."""

    def __init__(self, config: RealSenseConfig | None = None) -> None:
        self._config = config or RealSenseConfig(mode="mock")
        self._connected = False
        self._start_time = 0.0
        self._rng = np.random.default_rng(seed=42)

    def connect(self) -> None:
        self._connected = True
        self._start_time = time.time()

    def disconnect(self) -> None:
        self._connected = False

    def read(self) -> FrameObservation:
        if not self._connected:
            raise RuntimeError("MockRealSenseInterface is not connected")

        width, height = self._config.width, self._config.height
        stamp = time.time()

        color_bytes = b""
        if self._config.enable_color:
            color = self._rng.integers(0, 255, size=(height, width, 3), dtype=np.uint8)
            color_bytes = color.tobytes()

        depth_bytes = b""
        if self._config.enable_depth:
            depth = np.full((height, width), 1000, dtype=np.uint16)
            depth_bytes = depth.tobytes()

        return FrameObservation(
            device_id=self._config.serial_number or "mock",
            timestamp=stamp,
            color=color_bytes,
            depth=depth_bytes,
            width=width,
            height=height,
            depth_scale=0.001,
            intrinsics={
                "fx": 600.0,
                "fy": 600.0,
                "ppx": width / 2.0,
                "ppy": height / 2.0,
            },
        )

    def time(self) -> float:
        if not self._connected:
            return 0.0
        return time.time() - self._start_time
