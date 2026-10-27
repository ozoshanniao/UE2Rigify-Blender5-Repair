# OZO Animation Scale attribution and changes

`core/animation_scale.py` is adapted from the user's OZO_Tools **0.5.2** module
`animation_scale.py`, authored by **OZO** and marked **GPL-3.0-or-later**.
Its original SPDX notice is retained. The supplied original file has SHA-256:

`4872a4b2d47854c796610d40966a69e6f5715533b9908bbe1c2638db185f252a`

The port in UE to Rigify **1.8.0** changes operator/class/scene-setting names,
moves the panel under the UE to Rigify Toolkit, adds an active-object label and
a Blender 4.4+ availability check, and registers/unregisters the module with the
toolkit. The normalization and verification algorithm is retained. No separate
OZO add-on installation is required. The original OZO_Tools files are not changed.

The normalization provenance key is intentionally shared with OZO_Tools so either
tool can detect an incompatible original Action on already-normalized rest data.
UI settings and operator IDs are separate and both tools can be enabled together.

## Supported operation

Select an imported armature in Object or Pose Mode **before Convert**. Use
**Check**, then **Normalize Scale** under **UE to Rigify → Animation Scale**.
The operation works on the **active armature**, its direct supported child meshes,
and its one active Action. It does not automatically run during Convert.

The tool supports constant positive uniform object scale and one Action slot,
layer and keyframe strip. It checks the input before changing data, copies rest
data, mesh geometry and the Action, and preserves the original Action. Animated
bone location keys and their handles are scaled; constant object scale keys
become 1; object location/rotation motion is retained.

Every integer Action frame, fractional keyframe time and the current frame are
checked against world-space bone endpoints and evaluated mesh vertices. A failed
verification rolls back the data swap. Repeating an already normalized input is
a no-op. No blend file is saved by this tool.

Drivers, NLA, constraints, nonuniform/varying scale, shape keys, shared/linked data
and unsupported mesh transforms are rejected. The UI's **Scope** and **Details**
explain the particular limitation. Baseline storage is limited to 512 MiB.
This is scale normalization, not height matching or animation retargeting.

## Licensing

The newly combined 1.8.0 add-on is distributed under **GPL-3.0-or-later**; see
`LICENSE.md` for the GPL v3 text. The original Epic Games/community upstream code
retains its MIT notices and permissions, preserved in `LICENSE_UPSTREAM_MIT.md`.
Earlier 1.7.x installer archives and the standalone template archive are unchanged.
