# Blender 5 Repair (local build 1.8.0)

Based on UE to Rigify 1.7.6. This is a local compatibility repair, not an official upstream release.

## 1.8.0: OZO Animation Scale

Port OZO_Tools 0.5.2 Animation Scale into a child panel under the UE to Rigify Toolkit. Check and normalize the active imported armature before Convert. Keep separate operator/class/settings names so the original OZO add-on remains unchanged and can be enabled together. Preserve OZO's normalization provenance key for interoperability.

The algorithm copies rest/mesh/Action data, normalizes positive constant uniform scale and bone location keys, verifies world-space bone endpoints and mesh vertices at every integer frame, fractional key and current frame, and rolls back on failure. Unsupported rig structures are reported instead of modified. The original Action is retained; no file is saved and Convert does not run normalization automatically. Blender 4.4+ is required for this feature; 5.2.2 LTS was tested.

The new module retains its GPL-3.0-or-later SPDX notice. The combined 1.8.0 package includes GPL v3 and the unchanged upstream MIT notice. See `OZO_ANIMATION_SCALE_NOTICE.md`.

## 1.7.8: separate Manny Simple template

Bundle `male_manny_simple_ue5` as **Male Manny Simple Ue5** in the Blender 4+ template resources. Preserve all existing templates. Use main limb bones in place of eight absent corrective-root mappings, retain Twist mappings, and omit absent pectoral/reverse-corrective links. Node sockets are updated alongside the links.

Tested the bundled template on Blender 5.2.2 LTS with the supplied 88-bone Manny Simple FBX and all 282 frames. All 24 limb main/twist bones passed; maximum position difference was 0.00038835 cm and measured rotation difference was zero. Existing neck, finger-base and auxiliary-bone approximations remain; see the template README and `tests/manny_simple_validation_results.json` in the repository. No Blender 3.6 version of this template is claimed.

## 1.7.7: animation API compatibility repair

- Read and edit F-Curves through Action layers, keyframe strips, and channelbags on Blender 4.4+ / 5.x; retain the legacy access path for older Blender.
- Bind Action slots explicitly on both active Actions and NLA strips. Scope curve operations to the rig's slot to avoid changing another object's animation in a shared Action.
- Use PoseBone selection on Blender 5, with a legacy Bone selection fallback. Apply this to baking, remapping nodes, and metarig error navigation.
- Bake mapped Rigify controls instead of generated mechanism/deform bones. Baking the internals duplicated root motion on the supplied UEFN animation.
- Keep the original `ue2rigify` module name for compatibility with saved files and operators. The installed display name is **UE to Rigify (Blender 5 Repair)**.

Validated on Blender 5.2.2 LTS with the supplied 90-bone UEFN mannequin and frames 1–77. Tested conversion, active/NLA slot assignment, full/sparse control baking, bake back to source, and shared-Action slot isolation. Older Blender compatibility paths are retained but were not runtime-tested here. Apart from Manny Simple in 1.7.8, other character templates were not runtime-tested.

API references:
- https://developer.blender.org/docs/release_notes/5.0/python_api/
- https://developer.blender.org/docs/release_notes/4.4/python_api/
