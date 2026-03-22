from __future__ import annotations

import importlib

import pytest


def test_realsense_config_mock_defaults() -> None:
    interface_mod = importlib.import_module("dexim.realsense.interface")
    RealSenseConfig = interface_mod.RealSenseConfig

    cfg = RealSenseConfig(mode="mock")
    assert cfg.width == 1280
    assert cfg.height == 720
    assert cfg.fps == 30


def test_realsense_config_hw_requires_serial() -> None:
    interface_mod = importlib.import_module("dexim.realsense.interface")
    RealSenseConfig = interface_mod.RealSenseConfig

    with pytest.raises(ValueError, match="serial_number"):
        RealSenseConfig(mode="hw")


def test_node_config_accepts_nested_camera_dict() -> None:
    node_mod = importlib.import_module("dexim.realsense.node")
    RealSenseNodeConfig = node_mod.RealSenseNodeConfig

    cfg = RealSenseNodeConfig(camera={"mode": "mock", "preset": "480p30"})
    assert cfg.camera.preset == "480p30"
