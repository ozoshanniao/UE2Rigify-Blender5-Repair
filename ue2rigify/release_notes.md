## Local Repair 1.7.8 — 2026-10-26

* Added the separate **Male Manny Simple Ue5** template for the tested simplified Manny skeleton. Existing normal templates are preserved.
* Retained Twist mappings and added eight main-bone fallbacks for missing corrective roots; removed links to absent pectoral/corrective bones.
* Verified all 282 animation frames for 24 limb main/twist bones on Blender 5.2.2 LTS. Neck, finger-base and auxiliary-bone approximations remain documented in the template README.

## Upstream release notes (historical)

## Patch Changes
* Fixed addon preferences setter/getters to be compatible with Blender 5.0
  * [174](https://github.com/poly-hammer/BlenderTools/issues/174)

## Special Thanks
* @JoshQuake

## Tests Passing On
* Blender `3.6`, `4.2`  (installed from blender.org)
