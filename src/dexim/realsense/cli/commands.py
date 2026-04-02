"""Click commands for the dexim-realsense CLI."""

# ruff: noqa: I001

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import Literal, cast

import numpy as np
import rich_click as click

from dexim.cli.common import get_console, handle_cli_error, make_table, status_badge
from dexim.realsense.interface import RealSenseConfig, build_interface
from dexim.realsense.interface.config import StreamPreset
from dexim.realsense.node import RealSenseNode, RealSenseNodeConfig, load_config

from .config_utils import (
    create_config_yaml,
    edit_config_yaml,
    get_config_yaml_path,
    list_named_configs,
    remove_config_yaml,
    resolve_config_path,
)


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
@click.option(
    "--config",
    "-c",
    default=None,
    help="YAML config file or named config. Overrides other options if provided.",
)
@click.option(
    "--config-dir",
    type=click.Path(path_type=Path, file_okay=False),
    default=None,
    help="Config root directory (default: ./config or DEXIM_CONFIG_DIR).",
)
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
    config: str | None,
    config_dir: Path | None,
    mode: str,
    serial: str | None,
    preset: str,
    node_id: str,
    endpoint: str | None,
    rate: float,
) -> None:
    """Start a RealSense publish-only sensor node."""
    console = get_console()

    if config:
        cfg = load_config(str(resolve_config_path(config, _path_value(config_dir))))
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
    "--stream",
    type=click.Choice(["rgb", "depth", "both"], case_sensitive=False),
    default="rgb",
    show_default=True,
    help="Which stream(s) to display: rgb, depth, or both side-by-side.",
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
    stream: str,
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

    stream = stream.lower()
    enable_color = stream in ("rgb", "both")
    enable_depth = stream in ("depth", "both")

    config = RealSenseConfig(
        mode=cast(Literal["mock", "hw"], mode),
        serial_number=serial,
        preset=cast(StreamPreset, preset),
        enable_color=enable_color,
        enable_depth=enable_depth,
    )
    interface = build_interface(config)
    window_name = f"DexImitate RealSense Preview ({config.mode}, {stream})"

    console.print("[info]Starting preview...[/]")
    console.print(f"  Stream: [key]{stream}[/key]")
    console.print("[muted]Press q or Esc in the preview window to stop.[/]")

    frame_count = 0
    try:
        interface.connect()
        while True:
            frame = interface.read()

            if stream == "rgb":
                display_img = _decode_color_for_preview(
                    frame.color,
                    frame.width,
                    frame.height,
                    cv2,
                )
            elif stream == "depth":
                depth = np.frombuffer(frame.depth, dtype=np.uint16)
                depth = depth.reshape((frame.height, frame.width))
                depth_scaled = cv2.convertScaleAbs(depth, alpha=0.03)
                display_img = cv2.applyColorMap(depth_scaled, cv2.COLORMAP_JET)
            else:  # both
                color_img = _decode_color_for_preview(
                    frame.color,
                    frame.width,
                    frame.height,
                    cv2,
                )
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


# ── config group ──────────────────────────────────────────────────────────────


@click.group(name="config")
def config_group() -> None:
    """Manage named RealSense configuration files (CRUD)."""


@config_group.command(name="show")
@click.argument("config_name")
@click.option(
    "--config-dir",
    type=click.Path(path_type=Path, file_okay=False),
    default=None,
    help="Config root directory (default: ./config or DEXIM_CONFIG_DIR).",
)
@handle_cli_error
def config_show(config_name: str, config_dir: Path | None) -> None:
    """Pretty-print a resolved RealSense configuration file."""
    console = get_console()
    cfg = load_config(str(resolve_config_path(config_name, _path_value(config_dir))))
    from .display import render_config

    render_config(cfg, console)


@config_group.command(name="validate")
@click.argument("config_name")
@click.option(
    "--config-dir",
    type=click.Path(path_type=Path, file_okay=False),
    default=None,
    help="Config root directory (default: ./config or DEXIM_CONFIG_DIR).",
)
@handle_cli_error
def config_validate(config_name: str, config_dir: Path | None) -> None:
    """Validate a RealSense configuration file without starting the node."""
    console = get_console()
    resolved = resolve_config_path(config_name, _path_value(config_dir))
    load_config(str(resolved))
    console.print(f"[success]\u2713 Config is valid:[/] {resolved}")


@config_group.command(name="list")
@click.option(
    "--config-dir",
    type=click.Path(path_type=Path, file_okay=False),
    default=None,
    help="Config root directory (default: ./config or DEXIM_CONFIG_DIR).",
)
@handle_cli_error
def config_list(config_dir: Path | None) -> None:
    """List all named RealSense configuration files."""
    console = get_console()
    dir_value = _path_value(config_dir)
    names = list_named_configs(dir_value)
    if not names:
        console.print("[muted]No configs found.[/]")
        return
    rows = [[name, str(get_config_yaml_path(name, dir_value))] for name in names]
    console.print(
        make_table(
            title="Named RealSense Configs",
            columns=[("Name", "key"), ("Path", "value")],
            rows=rows,
        )
    )


def _config_dir_option(func):
    return click.option(
        "--config-dir",
        type=click.Path(path_type=Path, file_okay=False),
        default=None,
        help="Config root directory (default: ./config or DEXIM_CONFIG_DIR).",
    )(func)


def _config_field_options(func):
    """Shared CLI options for config new / config edit."""
    func = click.option(
        "--mode",
        type=click.Choice(["mock", "hw"]),
        default=None,
        help="Interface mode.",
    )(func)
    func = click.option(
        "--serial",
        default=None,
        help="RealSense serial number (hw mode).",
    )(func)
    func = click.option(
        "--preset",
        type=click.Choice(["480p30", "480p60", "720p30", "1080p30"]),
        default=None,
        help="Resolution and frame-rate preset.",
    )(func)
    func = click.option(
        "--node-id",
        default=None,
        help="Node identifier.",
    )(func)
    func = click.option(
        "--endpoint",
        default=None,
        help="Data PUB endpoint, e.g. tcp://*:5568.",
    )(func)
    func = click.option(
        "--rate-hz",
        type=float,
        default=None,
        help="Publish rate in Hz.",
    )(func)
    return func


def _build_config_dict(
    *,
    mode: str | None,
    serial: str | None,
    preset: str | None,
    node_id: str | None,
    endpoint: str | None,
    rate_hz: float | None,
) -> dict:
    """Build a config dict from CLI option values, omitting None fields."""
    data: dict = {}
    camera: dict = {"mode": mode or "mock"}
    if serial is not None:
        camera["serial_number"] = serial
    if preset is not None:
        camera["preset"] = preset
    data["camera"] = camera
    if node_id is not None:
        data["node_id"] = node_id
    if endpoint is not None:
        data["data_endpoint"] = endpoint
    if rate_hz is not None:
        data["rate_hz"] = rate_hz
    return data


def _collect_updates(
    *,
    mode: str | None,
    serial: str | None,
    preset: str | None,
    node_id: str | None,
    endpoint: str | None,
    rate_hz: float | None,
) -> dict:
    """Build a partial update dict from non-None CLI option values."""
    updates: dict = {}
    if mode is not None:
        updates.setdefault("camera", {})["mode"] = mode
    if serial is not None:
        updates.setdefault("camera", {})["serial_number"] = serial
    if preset is not None:
        updates.setdefault("camera", {})["preset"] = preset
    if node_id is not None:
        updates["node_id"] = node_id
    if endpoint is not None:
        updates["data_endpoint"] = endpoint
    if rate_hz is not None:
        updates["rate_hz"] = rate_hz
    return updates


@config_group.command(name="new")
@click.argument("config_name")
@_config_field_options
@_config_dir_option
@handle_cli_error
def config_new(
    config_name: str,
    config_dir: Path | None,
    mode: str | None,
    serial: str | None,
    preset: str | None,
    node_id: str | None,
    endpoint: str | None,
    rate_hz: float | None,
) -> None:
    """Create a new named RealSense configuration file."""
    console = get_console()
    data = _build_config_dict(
        mode=mode,
        serial=serial,
        preset=preset,
        node_id=node_id,
        endpoint=endpoint,
        rate_hz=rate_hz,
    )
    path = create_config_yaml(config_name, data, _path_value(config_dir))
    console.print(f"[success]\u2713 Created config '{config_name}':[/] {path}")


@config_group.command(name="edit")
@click.argument("config_name")
@_config_field_options
@_config_dir_option
@handle_cli_error
def config_edit(
    config_name: str,
    config_dir: Path | None,
    mode: str | None,
    serial: str | None,
    preset: str | None,
    node_id: str | None,
    endpoint: str | None,
    rate_hz: float | None,
) -> None:
    """Update fields in an existing named RealSense configuration file."""
    console = get_console()
    updates = _collect_updates(
        mode=mode,
        serial=serial,
        preset=preset,
        node_id=node_id,
        endpoint=endpoint,
        rate_hz=rate_hz,
    )
    if not updates:
        raise click.UsageError("Specify at least one field to change.")
    path = edit_config_yaml(config_name, updates, _path_value(config_dir))
    console.print(f"[success]\u2713 Updated config '{config_name}':[/] {path}")


@config_group.command(name="remove")
@click.argument("config_name")
@click.option(
    "--yes",
    is_flag=True,
    default=False,
    help="Confirm deletion without prompting.",
)
@_config_dir_option
@handle_cli_error
def config_remove(
    config_name: str,
    yes: bool,
    config_dir: Path | None,
) -> None:
    """Delete a named RealSense configuration file."""
    console = get_console()
    if not yes:
        raise click.UsageError(
            f"This will permanently delete config '{config_name}'. "
            f"Pass --yes to confirm."
        )
    path = remove_config_yaml(config_name, _path_value(config_dir))
    console.print(f"[success]\u2713 Removed config '{config_name}':[/] {path}")


# ── helpers ───────────────────────────────────────────────────────────────────


def _path_value(path: Path | None) -> str | None:
    return str(path) if path is not None else None
