from __future__ import annotations

import importlib


def test_mock_interface_read() -> None:
    interface_mod = importlib.import_module("dexim.realsense.interface")
    MockRealSenseInterface = interface_mod.MockRealSenseInterface
    RealSenseConfig = interface_mod.RealSenseConfig

    iface = MockRealSenseInterface(RealSenseConfig(mode="mock", preset="480p30"))
    assert iface.is_connected() is False
    iface.connect()
    assert iface.is_connected() is True
    frame = iface.read()

    assert frame.width == 640
    assert frame.height == 480
    assert len(frame.depth) == frame.width * frame.height * 2
    assert len(frame.color) == frame.width * frame.height * 3

    iface.disconnect()
    assert iface.is_connected() is False


def test_mock_interface_rgb_only() -> None:
    interface_mod = importlib.import_module("dexim.realsense.interface")
    MockRealSenseInterface = interface_mod.MockRealSenseInterface
    RealSenseConfig = interface_mod.RealSenseConfig

    iface = MockRealSenseInterface(
        RealSenseConfig(mode="mock", preset="480p30", enable_depth=False)
    )
    iface.connect()
    frame = iface.read()

    assert len(frame.color) == frame.width * frame.height * 3
    assert frame.depth == b""

    iface.disconnect()


def test_mock_interface_depth_only() -> None:
    interface_mod = importlib.import_module("dexim.realsense.interface")
    MockRealSenseInterface = interface_mod.MockRealSenseInterface
    RealSenseConfig = interface_mod.RealSenseConfig

    iface = MockRealSenseInterface(
        RealSenseConfig(mode="mock", preset="480p30", enable_color=False)
    )
    iface.connect()
    frame = iface.read()

    assert frame.color == b""
    assert len(frame.depth) == frame.width * frame.height * 2

    iface.disconnect()
