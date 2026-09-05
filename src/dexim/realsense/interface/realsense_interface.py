"""Hardware RealSense interface implemented with pyrealsense2."""

from __future__ import annotations

import time
from typing import Any

import numpy as np
from dexim.core.messages import FrameObservation
from dexim.core.robot_interface import SensorInterface

from dexim.realsense.interface.config import RealSenseConfig


class RealSenseInterface(SensorInterface[FrameObservation]):
    """Read-only sensor interface for RealSense color/depth streams."""

    def __init__(self, config: RealSenseConfig) -> None:
        self._config = config
        self._connected = False
        self._start_time = 0.0

        self._rs: Any = None
        self._cv2: Any = None
        self._pipeline: Any = None
        self._align: Any = None
        self._depth_scale = 0.001

    def connect(self) -> None:
        """Start the RealSense pipeline using configured streams."""
        if self._connected:
            return

        try:
            import cv2
            import pyrealsense2 as rs
        except ImportError as exc:
            raise ImportError(
                "RealSense hardware mode requires extras: "
                "pip install dexim-realsense[hw]"
            ) from exc

        self._cv2 = cv2
        self._rs = rs

        cfg = rs.config()
        if self._config.serial_number:
            cfg.enable_device(self._config.serial_number)

        width, height, fps = self._config.width, self._config.height, self._config.fps
        if self._config.enable_color:
            cfg.enable_stream(rs.stream.color, width, height, rs.format.bgr8, fps)
        if self._config.enable_depth:
            cfg.enable_stream(rs.stream.depth, width, height, rs.format.z16, fps)

        self._pipeline = rs.pipeline()
        profile = self._pipeline.start(cfg)

        if self._config.enable_depth:
            depth_sensor = profile.get_device().first_depth_sensor()
            self._depth_scale = float(depth_sensor.get_depth_scale())

        if self._config.align_depth_to_color and self._config.enable_depth:
            self._align = rs.align(rs.stream.color)

        self._connected = True
        self._start_time = time.time()

    def disconnect(self) -> None:
        if self._pipeline is not None:
            self._pipeline.stop()
        self._pipeline = None
        self._align = None
        self._connected = False

    def is_connected(self) -> bool:
        """Return whether the RealSense pipeline is connected."""
        return self._connected

    def read(self) -> FrameObservation:
        """Read one synchronized frame pair and return FrameObservation."""
        if not self._connected or self._pipeline is None:
            raise RuntimeError("RealSenseInterface is not connected")

        frames = self._pipeline.wait_for_frames(
            timeout_ms=self._config.frame_timeout_ms
        )
        if self._align is not None:
            frames = self._align.process(frames)

        color_frame = frames.get_color_frame() if self._config.enable_color else None
        depth_frame = frames.get_depth_frame() if self._config.enable_depth else None

        if self._config.enable_color and color_frame is None:
            raise RuntimeError("Failed to read color frame")
        if self._config.enable_depth and depth_frame is None:
            raise RuntimeError("Failed to read depth frame")

        width = self._config.width
        height = self._config.height

        color_bytes = b""
        intrinsics: dict[str, float] = {}
        if color_frame is not None:
            color_image = np.asanyarray(color_frame.get_data())
            ok, encoded = self._cv2.imencode(
                ".jpg",
                color_image,
                [int(self._cv2.IMWRITE_JPEG_QUALITY), int(self._config.jpeg_quality)],
            )
            if not ok:
                raise RuntimeError("JPEG encoding failed for color frame")
            color_bytes = encoded.tobytes()

            color_intrinsics = color_frame.profile.as_video_stream_profile().intrinsics
            intrinsics = {
                "fx": float(color_intrinsics.fx),
                "fy": float(color_intrinsics.fy),
                "ppx": float(color_intrinsics.ppx),
                "ppy": float(color_intrinsics.ppy),
            }
            width = int(color_intrinsics.width)
            height = int(color_intrinsics.height)

        depth_bytes = b""
        if depth_frame is not None:
            depth_image = np.asanyarray(depth_frame.get_data())
            depth_bytes = depth_image.astype(np.uint16, copy=False).tobytes()
            if not intrinsics:
                depth_intrinsics = (
                    depth_frame.profile.as_video_stream_profile().intrinsics
                )
                intrinsics = {
                    "fx": float(depth_intrinsics.fx),
                    "fy": float(depth_intrinsics.fy),
                    "ppx": float(depth_intrinsics.ppx),
                    "ppy": float(depth_intrinsics.ppy),
                }
                width = int(depth_intrinsics.width)
                height = int(depth_intrinsics.height)

        return FrameObservation(
            device_id=self._config.serial_number or "realsense",
            timestamp=time.time(),
            color=color_bytes,
            depth=depth_bytes,
            width=width,
            height=height,
            depth_scale=self._depth_scale,
            intrinsics=intrinsics,
        )

    def time(self) -> float:
        if not self._connected:
            return 0.0
        return time.time() - self._start_time
