"""Click commands for the dexim-realsense CLI."""

# ruff: noqa: I001

from __future__ import annotations

from collections.abc import Callable
from types import ModuleType
from typing import Literal, cast

import numpy as np
import rich_click as click

from dexim.cli.common import get_console, handle_cli_error, make_table, status_badge
from dexim.realsense.interface import RealSenseConfig, build_interface
from dexim.realsense.interface.config import StreamPreset
from dexim.realsense.node import RealSenseNode, RealSenseNodeConfig, load_config


def _query_devices() -> list[dict[str, str]]:
    """Query connected RealSense devices.

    Returns:
        List of device dictionaries with serial/name/firmware.
    """
    try:
        import pyrealsense2 as rs  # type: ignore[import-not-found]
    except ImportError as exc:
        raise ImportError(
            "RealSense SDK missing. Install with: pip install dexim-realsense[hw]"
        ) from exc

    devices: list[dict[str, str]] = []
    for dev in rs.context().query_devices():
        devices.append(
            {
                "name": str(dev.get_info(rs.camera_info.name)),
                "serial": str(dev.get_info(rs.camera_info.serial_number)),
                "firmware": str(dev.get_info(rs.camera_info.firmware_version)),
            }
        )
    return devices


def _decode_color_for_preview(
    color_bytes: bytes,
    width: int,
    height: int,
    cv2_mod: ModuleType,
) -> np.ndarray:
    """Decode color bytes to BGR image for preview.

    Supports both JPEG payloads (hw mode) and raw uint8 BGR payloads
    (mock mode fallback).
    """
    imread_color = cast(int, getattr(cv2_mod, "IMREAD_COLOR"))
    imdecode = cast(
        Callable[[np.ndarray, int], np.ndarray | None],
        getattr(cv2_mod, "imdecode"),
    )

    encoded = np.frombuffer(color_bytes, dtype=np.uint8)
    image = imdecode(encoded, imread_color)
    if image is not None:
        return image

    expected = width * height * 3
    if encoded.size != expected:
        raise ValueError(
            f"Invalid raw color payload size {encoded.size}, expected {expected}"
        )
    return encoded.reshape((height, width, 3))


@click.command()
@click.option("--config", "config_path", type=click.Path(exists=True), default=None)
@click.option(
    "--mode",
    type=click.Choice(["mock", "hw"], case_sensitive=False),
    default="mock",
    show_default=True,
)
@click.option("--serial", default=None, help="RealSense serial number for hw mode.")
@click.option(
    "--preset",
    type=click.Choice(
        ["480p30", "480p60", "720p30", "1080p30"],
        case_sensitive=True,
    ),
    default="720p30",
    show_default=True,
)
@click.option("--node-id", default="realsense_0", show_default=True)
@click.option(
    "--endpoint",
    default=None,
    help="Override data endpoint, e.g. tcp://*:5568",
)
@click.option(
    "--rate",
    type=float,
    default=30.0,
    show_default=True,
    help="Publish rate in Hz.",
)
@handle_cli_error
def run(
    config_path: str | None,
    mode: str,
    serial: str | None,
    preset: str,
    node_id: str,
    endpoint: str | None,
    rate: float,
) -> None:
    """Start a RealSense publish-only sensor node."""
    console = get_console()

    if config_path:
        cfg = load_config(config_path)
    else:
        cfg = RealSenseNodeConfig(
            node_id=node_id,
            camera=RealSenseConfig(
                mode=cast(Literal["mock", "hw"], mode),
                serial_number=serial,
                preset=cast(StreamPreset, preset),
            ),
            rate_hz=rate,
        )

    if endpoint:
        cfg.data_endpoint = endpoint

    console.print("[info]Starting RealSense node...[/]")
    console.print(f"  Node ID:    [key]{cfg.node_id}[/key]")
    console.print(f"  Mode:       [key]{cfg.camera.mode}[/key]")
    console.print(f"  Preset:     [key]{cfg.camera.preset}[/key]")
    console.print(f"  Endpoint:   [key]{cfg.data_endpoint}[/key]")

    node = RealSenseNode(cfg)
    console.print("[success]● RealSense node running. Press Ctrl+C to stop.[/]")
    try:
        node.run()
    except KeyboardInterrupt:
        console.print("\n[warning]Stopping.[/]")


@click.command(name="list-devices")
@handle_cli_error
def list_devices() -> None:
    """List connected RealSense devices."""
    console = get_console()
    devices = _query_devices()

    if not devices:
        console.print("[warning]No RealSense devices detected.[/]")
        return

    rows = [[d["name"], d["serial"], d["firmware"]] for d in devices]
    table = make_table(
        title="RealSense Devices",
        columns=[("Name", "key"), ("Serial", "value"), ("Firmware", "muted")],
        rows=rows,
    )
    console.print(table)


@click.command()
@handle_cli_error
def status() -> None:
    """Show RealSense SDK availability and camera connection status."""
    console = get_console()

    try:
        devices = _query_devices()
        sdk_ok = True
    except ImportError:
        devices = []
        sdk_ok = False

    rows = [
        ["SDK available", status_badge(sdk_ok)],
        ["Connected devices", str(len(devices))],
    ]
    for dev in devices:
        rows.append([f"  - {dev['serial']}", dev["name"]])

    console.print(
        make_table(
            title="RealSense Status",
            columns=[("Metric", "key"), ("Value", "value")],
            rows=rows,
        )
    )


@click.command()
@click.option(
    "--mode",
    type=click.Choice(["mock", "hw"], case_sensitive=False),
    default="hw",
    show_default=True,
)
@click.option("--serial", default=None, help="RealSense serial number for hw mode.")
@click.option(
    "--preset",
    type=click.Choice(
        ["480p30", "480p60", "720p30", "1080p30"],
        case_sensitive=True,
    ),
    default="720p30",
    show_default=True,
)
@click.option(
    "--show-depth/--no-show-depth",
    default=False,
    show_default=True,
    help="Show depth colormap next to color frame.",
)
@click.option(
    "--max-frames",
    type=int,
    default=0,
    show_default=True,
    help="Stop automatically after N frames (0 = run until key press).",
)
@handle_cli_error
def preview(
    mode: str,
    serial: str | None,
    preset: str,
    show_depth: bool,
    max_frames: int,
) -> None:
    """Open a local OpenCV window for quick camera bring-up.

    Press 'q' or Esc to exit.
    """
    console = get_console()

    if max_frames < 0:
        raise ValueError("max_frames must be >= 0")

    try:
        import cv2  # type: ignore[import-not-found]
    except ImportError as exc:
        raise ImportError(
            "Preview requires OpenCV. Install with: pip install dexim-realsense[hw]"
        ) from exc

    config = RealSenseConfig(
        mode=cast(Literal["mock", "hw"], mode),
        serial_number=serial,
        preset=cast(StreamPreset, preset),
    )
    interface = build_interface(config)
    window_name = f"DexImitate RealSense Preview ({config.mode})"

    console.print("[info]Starting preview...[/]")
    console.print("[muted]Press q or Esc in the preview window to stop.[/]")

    frame_count = 0
    try:
        interface.connect()
        while True:
            frame = interface.read()
            color_img = _decode_color_for_preview(
                frame.color,
                frame.width,
                frame.height,
                cv2,
            )

            display_img = color_img
            if show_depth and frame.depth:
                depth = np.frombuffer(frame.depth, dtype=np.uint16)
                depth = depth.reshape((frame.height, frame.width))
                depth_scaled = cv2.convertScaleAbs(depth, alpha=0.03)
                depth_color = cv2.applyColorMap(depth_scaled, cv2.COLORMAP_JET)
                display_img = np.hstack((color_img, depth_color))

            cv2.imshow(window_name, display_img)
            key = cv2.waitKey(1) & 0xFF
            if key in (27, ord("q")):
                break

            frame_count += 1
            if max_frames > 0 and frame_count >= max_frames:
                break
    finally:
        try:
            interface.disconnect()
        finally:
            cv2.destroyAllWindows()

    console.print(f"[success]Preview stopped after {frame_count} frame(s).[/]")
