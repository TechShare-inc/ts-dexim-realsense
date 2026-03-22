from __future__ import annotations

import importlib


def test_node_lifecycle_hooks() -> None:
    node_mod = importlib.import_module("dexim.realsense.node")
    RealSenseNode = node_mod.RealSenseNode
    RealSenseNodeConfig = node_mod.RealSenseNodeConfig

    cfg = RealSenseNodeConfig(
        node_id="realsense_test",
        camera={"mode": "mock", "preset": "480p30"},
        data_endpoint="tcp://127.0.0.1:5688",
        bind_data=False,
        rate_hz=5.0,
    )
    node = RealSenseNode(cfg)

    node.on_start()
    node.on_pause()
    node.on_stop()
    node.on_shutdown()
