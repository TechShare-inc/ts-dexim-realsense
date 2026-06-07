"""RealSense publish-only sensor node implementation."""

from __future__ import annotations

import time

import zmq
from dexim.core.messages import StatusInfo, TopicBuilder, pack_data_message
from dexim.core.nodes import PublisherDeviceNode, RateLimiter
from loguru import logger

from dexim.realsense.interface import build_interface
from dexim.realsense.node.config import RealSenseNodeConfig


class RealSenseNode(PublisherDeviceNode):
    """Publish-only node that streams RealSense frame observations."""

    def __init__(self, config: RealSenseNodeConfig) -> None:
        super().__init__(
            node_id=config.node_id,
            control_endpoint=config.control_endpoint,
            status_endpoint=config.status_endpoint,
        )
        self.config = config
        self.interface = build_interface(config.camera)

        self._ctx = zmq.Context.instance()
        self._pub: zmq.Socket = self._ctx.socket(zmq.PUB)
        self._pub.setsockopt(zmq.LINGER, 0)
        self._pub.setsockopt(zmq.SNDHWM, 10)  # Frames are large; keep HWM low
        if config.bind_data:
            self._pub.bind(config.data_endpoint)
        else:
            self._pub.connect(config.data_endpoint)

        self._topic = TopicBuilder().observation.video_frame(self.node_id)
        self._active = False
        self._rate_limiter = RateLimiter(config.rate_hz) if config.rate_hz else None

    def on_start(self) -> None:
        self.interface.connect()
        self._active = True
        logger.info(f"{self.node_id} started streaming")

    def on_pause(self) -> None:
        self._active = False
        logger.info(f"{self.node_id} paused streaming")

    def on_stop(self) -> None:
        self._active = False
        try:
            self.interface.disconnect()
        except Exception as exc:  # noqa: BLE001
            logger.debug(f"{self.node_id} disconnect error on stop: {exc}")
        logger.info(f"{self.node_id} stopped streaming")

    def on_shutdown(self) -> None:
        self._active = False
        self._pub.close(linger=0)
        super().on_shutdown()

    def on_start_recording(self) -> None:
        logger.info(f"{self.node_id} recording started")

    def on_stop_recording(self) -> None:
        logger.info(f"{self.node_id} recording stopped")

    # ------------------------------------------------------------------
    # Status info
    # ------------------------------------------------------------------

    def get_status_info(self) -> StatusInfo:
        """Return a snapshot of RealSense-specific runtime state."""
        info = super().get_status_info()
        info.interface_mode = self.config.camera.mode
        try:
            info.hardware_connected = self.interface.is_connected()
        except Exception:
            info.hardware_connected = None
        info.data_rate_hz = self.config.rate_hz if self._active else 0.0
        return info

    def _main_loop_iteration(self) -> None:
        if not self._teleop_active or not self._active:
            time.sleep(0.01)
            return

        try:
            frame = self.interface.read()
            if self.is_publishing:
                topic, payload = pack_data_message(
                    self._topic,
                    frame.timestamp,
                    frame.to_dict(),
                )
                self._pub.send_multipart([topic, payload], flags=zmq.DONTWAIT)
        except zmq.Again:
            pass
        except Exception as exc:  # noqa: BLE001
            logger.debug(f"{self.node_id} frame publish skipped: {exc}")

        if self._rate_limiter is not None:
            self._rate_limiter.sleep()
