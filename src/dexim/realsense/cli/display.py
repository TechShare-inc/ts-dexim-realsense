"""Rich display helpers for the dexim-realsense CLI."""

from __future__ import annotations

from typing import TYPE_CHECKING

from dexim.cli.common import make_table
from rich.console import Console
from rich.rule import Rule

if TYPE_CHECKING:
    from dexim.realsense.node import RealSenseNodeConfig


def render_config(cfg: RealSenseNodeConfig, console: Console) -> None:
    """Render a RealSenseNodeConfig as a Rich table.

    Args:
        cfg: Resolved RealSenseNodeConfig instance.
        console: Rich Console to print to.
    """
    console.print(Rule("RealSense Configuration", style="brand.dim"))

    rows = [
        ["node_id", cfg.node_id],
        ["mode", cfg.camera.mode],
        ["serial_number", cfg.camera.serial_number or "(auto)"],
        ["preset", cfg.camera.preset],
        ["jpeg_quality", str(cfg.camera.jpeg_quality)],
        ["enable_color", str(cfg.camera.enable_color)],
        ["enable_depth", str(cfg.camera.enable_depth)],
        ["align_depth_to_color", str(cfg.camera.align_depth_to_color)],
        ["rate_hz", str(cfg.rate_hz)],
        ["data_endpoint", cfg.data_endpoint],
        ["bind_data", str(cfg.bind_data)],
    ]

    console.print(
        make_table(
            title="",
            columns=[("Key", "key"), ("Value", "value")],
            rows=rows,
        )
    )
