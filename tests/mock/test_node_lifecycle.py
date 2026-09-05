from __future__ import annotations

import importlib

import zmq


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

    try:
        initial = node.get_status_info()
        assert initial.interface_mode == "mock"
        assert initial.hardware_connected is False
        assert initial.data_rate_hz == 0.0
        assert node._pub.getsockopt(zmq.SNDHWM) == 10

        node.on_start()
        active = node.get_status_info()
        assert active.hardware_connected is True
        assert active.data_rate_hz == 0.0

        node._teleop_active = True
        before_first_frame = node.get_status_info()
        assert before_first_frame.data_rate_hz == 0.0

        node._main_loop_iteration()
        publishing = node.get_status_info()
        assert publishing.data_rate_hz > 0.0
        assert publishing.rate_limiter_stats["actual_rate"] == publishing.data_rate_hz
        assert publishing.rate_limiter_stats["target_rate"] == 5.0

        node.is_publishing = False
        publishing_paused = node.get_status_info()
        assert publishing_paused.data_rate_hz == 0.0

        node.on_pause()
        paused = node.get_status_info()
        assert paused.hardware_connected is True
        assert paused.data_rate_hz == 0.0

        node.on_stop()
        stopped = node.get_status_info()
        assert stopped.hardware_connected is False
        assert stopped.data_rate_hz == 0.0
    finally:
        node.on_shutdown()
