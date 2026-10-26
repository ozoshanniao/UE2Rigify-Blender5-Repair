# Blender 5 Repair (local build 1.7.8)

Based on UE to Rigify 1.7.6. This is a local compatibility repair, not an official upstream release.

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
