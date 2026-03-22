# dexim-realsense

RealSense camera package for DexImitate.

This package provides:
- interface layer (`dexim.realsense.interface`) for real (`pyrealsense2`) and mock camera backends
- node layer (`dexim.realsense.node`) for publish-only sensor node
- CLI (`dexim-realsense`) to run and inspect camera devices

Published observation topic:
- `observation/<node_id>/video_frame`

Payload format:
- `FrameObservation` from `dexim.core.messages`
