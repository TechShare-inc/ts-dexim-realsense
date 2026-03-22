"""dexim.realsense.cli - RealSense camera CLI command group."""

__version__ = "0.1.0"

import rich_click as click
from dexim.cli.common import print_banner, setup_error_handling

from dexim.realsense.cli.commands import list_devices, preview, run, status

click.rich_click.USE_RICH_MARKUP = True
click.rich_click.STYLE_COMMANDS_TABLE_COLUMN_WIDTH_RATIO = (1, 3)


@click.group(name="realsense")
def realsense_group() -> None:
    """Intel RealSense camera - run, status, list-devices, preview."""


realsense_group.add_command(run)
realsense_group.add_command(status)
realsense_group.add_command(list_devices)
realsense_group.add_command(preview)


def standalone_app() -> None:
    """Entry point for standalone dexim-realsense CLI."""
    setup_error_handling()
    print_banner(app_name="DexImitate · RealSense", version=__version__)
    realsense_group(standalone_mode=True)
