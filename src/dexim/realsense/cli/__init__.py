"""dexim.realsense.cli - RealSense camera CLI command group."""

__version__ = "0.1.0"

import rich_click as click
from dexim.cli.common import configure_logging, print_banner, setup_error_handling

from dexim.realsense.cli.commands import (
    config_group,
    list_devices,
    preview,
    run,
    status,
)

click.rich_click.USE_RICH_MARKUP = True
click.rich_click.STYLE_COMMANDS_TABLE_COLUMN_WIDTH_RATIO = (1, 3)


@click.group(name="realsense")
@click.option(
    "--log-level",
    type=click.Choice(
        ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], case_sensitive=False
    ),
    default="INFO",
    show_default=True,
    envvar="DEXIM_LOG_LEVEL",
    help="Logging verbosity.",
)
def realsense_group(log_level: str) -> None:
    """Intel RealSense camera - run, status, list-devices, preview, config."""
    configure_logging(log_level)


realsense_group.add_command(run)
realsense_group.add_command(status)
realsense_group.add_command(list_devices)
realsense_group.add_command(preview)
realsense_group.add_command(config_group, name="config")


def standalone_app() -> None:
    """Entry point for standalone dexim-realsense CLI."""
    setup_error_handling()
    print_banner(app_name="DexImitate · RealSense", version=__version__)
    realsense_group(standalone_mode=True)
