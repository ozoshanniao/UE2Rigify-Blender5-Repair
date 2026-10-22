# Blender 5 Repair (local build 1.7.7)

Based on UE to Rigify 1.7.6. This is a local compatibility repair, not an official upstream release.

- Read and edit F-Curves through Action layers, keyframe strips, and channelbags on Blender 4.4+ / 5.x; retain the legacy access path for older Blender.
- Bind Action slots explicitly on both active Actions and NLA strips. Scope curve operations to the rig's slot to avoid changing another object's animation in a shared Action.
- Use PoseBone selection on Blender 5, with a legacy Bone selection fallback. Apply this to baking, remapping nodes, and metarig error navigation.
- Bake mapped Rigify controls instead of generated mechanism/deform bones. Baking the internals duplicated root motion on the supplied UEFN animation.
- Keep the original `ue2rigify` module name for compatibility with saved files and operators. The installed display name is **UE to Rigify (Blender 5 Repair)**.

Validated on Blender 5.2.2 LTS with the supplied 90-bone UEFN mannequin and frames 1–77. Tested conversion, active/NLA slot assignment, full/sparse control baking, bake back to source, and shared-Action slot isolation. Older Blender compatibility paths are retained but were not runtime-tested here. Other character templates were not runtime-tested.

API references:
- https://developer.blender.org/docs/release_notes/5.0/python_api/
- https://developer.blender.org/docs/release_notes/4.4/python_api/
