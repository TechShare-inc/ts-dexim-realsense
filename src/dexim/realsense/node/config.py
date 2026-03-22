"""Configuration dataclasses for the RealSense sensor node."""

# ruff: noqa: I001

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from dexim.core.messages import CTRL_PUB_ENDPOINT, STATUS_PULL_ENDPOINT
from dexim.core.utility.ports import NODE_DATA_PORTS
from dexim.realsense.interface import RealSenseConfig


__all__ = ["RealSenseNodeConfig", "load_config", "get_default_data_endpoint"]


def get_default_data_endpoint() -> str:
    """Return default data PUB endpoint for RealSense node."""
    port = NODE_DATA_PORTS.get("realsense", NODE_DATA_PORTS.get("camera", 5557))
    return f"tcp://*:{port}"


@dataclass
class RealSenseNodeConfig:
    """Aggregated configuration for the RealSense publish-only sensor node."""

    node_id: str = "realsense_0"
    camera: RealSenseConfig = field(default_factory=RealSenseConfig)
    control_endpoint: str = CTRL_PUB_ENDPOINT
    status_endpoint: str = STATUS_PULL_ENDPOINT
    data_endpoint: str = field(default_factory=get_default_data_endpoint)
    bind_data: bool = True
    rate_hz: float | None = 30.0

    def __post_init__(self) -> None:
        if isinstance(self.camera, dict):
            self.camera = RealSenseConfig(**self.camera)
        if self.rate_hz is not None and self.rate_hz <= 0:
            raise ValueError("rate_hz must be > 0 or None")


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge override into base and return a new dictionary."""
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config(path: str | Path) -> RealSenseNodeConfig:
    """Load RealSenseNodeConfig from a YAML file.

    Args:
        path: Path to YAML configuration file.

    Returns:
        Parsed RealSenseNodeConfig object.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with path.open("r", encoding="utf-8") as fh:
        raw: dict[str, Any] = yaml.safe_load(fh) or {}

    defaults = {
        "node_id": "realsense_0",
        "camera": {"mode": "mock"},
        "control_endpoint": CTRL_PUB_ENDPOINT,
        "status_endpoint": STATUS_PULL_ENDPOINT,
        "data_endpoint": get_default_data_endpoint(),
        "bind_data": True,
        "rate_hz": 30.0,
    }
    merged = _deep_merge(defaults, raw)
    return RealSenseNodeConfig(**merged)
