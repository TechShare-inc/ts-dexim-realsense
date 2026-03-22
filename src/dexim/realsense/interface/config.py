"""Configuration dataclasses for the RealSense interface layer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

StreamPreset = Literal["480p30", "480p60", "720p30", "1080p30"]

PRESET_TABLE: dict[StreamPreset, tuple[int, int, int]] = {
    "480p30": (640, 480, 30),
    "480p60": (640, 480, 60),
    "720p30": (1280, 720, 30),
    "1080p30": (1920, 1080, 30),
}


@dataclass
class RealSenseConfig:
    """Configuration for RealSense camera interface implementations.

    Attributes:
        mode: Interface mode: mock or hardware.
        serial_number: Camera serial number. Required for hardware mode.
        preset: Resolution and frame-rate preset.
        enable_color: Whether to enable the color stream.
        enable_depth: Whether to enable the depth stream.
        jpeg_quality: JPEG quality used for color compression (1-100).
        align_depth_to_color: Align depth frame into color camera coordinates.
        frame_timeout_ms: Timeout for frame acquisition.
    """

    mode: Literal["mock", "hw"] = "mock"
    serial_number: str | None = None
    preset: StreamPreset = "720p30"
    enable_color: bool = True
    enable_depth: bool = True
    jpeg_quality: int = 90
    align_depth_to_color: bool = True
    frame_timeout_ms: int = 1000

    def __post_init__(self) -> None:
        if self.mode not in {"mock", "hw"}:
            raise ValueError("mode must be 'mock' or 'hw'")
        if self.mode == "hw" and not self.serial_number:
            raise ValueError("hardware mode requires serial_number")
        if self.preset not in PRESET_TABLE:
            raise ValueError(f"unsupported preset: {self.preset}")
        if not (self.enable_color or self.enable_depth):
            raise ValueError("at least one stream must be enabled")
        if self.jpeg_quality < 1 or self.jpeg_quality > 100:
            raise ValueError("jpeg_quality must be in [1, 100]")
        if self.frame_timeout_ms <= 0:
            raise ValueError("frame_timeout_ms must be > 0")

    @property
    def width(self) -> int:
        return PRESET_TABLE[self.preset][0]

    @property
    def height(self) -> int:
        return PRESET_TABLE[self.preset][1]

    @property
    def fps(self) -> int:
        return PRESET_TABLE[self.preset][2]
