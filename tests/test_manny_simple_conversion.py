"""Optional Blender integration test. Supply your own Manny Simple FBX after --fbx."""
import argparse
import json
import math
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path

import addon_utils
import bpy

parser = argparse.ArgumentParser()
parser.add_argument('--fbx', type=Path, required=True)
parser.add_argument('--report', type=Path)
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
addon_utils.enable('rigify', default_set=True)
import ue2rigify
assert Path(ue2rigify.__file__).parent == ROOT / 'ue2rigify'

# Registration must not copy templates over a user's live default cache.
copy_defaults = ue2rigify.templates.copy_default_templates
ue2rigify.templates.copy_default_templates = lambda: None
try:
    addon_utils.enable('ue2rigify', default_set=True)
finally:
    ue2rigify.templates.copy_default_templates = copy_defaults
from ue2rigify.core import animation, animation_scale, scene, templates, utilities

with tempfile.TemporaryDirectory(prefix='.tmp_manny_simple_', dir=ROOT / 'tests') as scratch:
    assert Path(scratch).resolve().is_relative_to((ROOT / 'tests').resolve())
    bpy.context.preferences.addons['ue2rigify'].preferences.custom_rig_template_path = scratch
    items = templates.get_rig_templates()
    entry = next(item for item in items if item[0] == 'male_manny_simple_ue5')
    assert entry[1] == 'Male Manny Simple Ue5'
    assert any(item[0] == 'male_mannequin_UE5' for item in items)
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.ops.import_scene.fbx(filepath=str(args.fbx.resolve()))
    source = next(obj for obj in bpy.context.scene.objects if obj.type == 'ARMATURE')
    action = source.animation_data.action
    sc = bpy.context.scene
    start, end = (round(frame) for frame in action.frame_range)
    sc.frame_start, sc.frame_end = start, end
    sc.frame_set(start)

    # Exercise the actual 1.8 Animation Scale port before the retargeting flow.
    bpy.context.view_layer.objects.active = source
    source.select_set(True)
    normalized = animation_scale.normalize_scale(bpy.context)
    assert normalized.skipped or normalized.samples > 0
    sc.frame_set(start)
    folder = ROOT / 'ue2rigify/resources/rig_templates/b4_0/male_manny_simple_ue5'
    links = json.loads((folder / 'source_to_deform_links.json').read_text())
    needed = {link['from_socket'] for link in links} - {'object'}
    assert needed <= set(source.pose.bones.keys()), sorted(needed - set(source.pose.bones.keys()))
    limb_names = {name for name in needed if name.startswith(('upperarm_', 'lowerarm_', 'thigh_', 'calf_'))}
    assert len(limb_names) == 24  # Both main bones and both twist segments on each limb.

    properties = sc.ue2rigify
    properties['selected_mode'] = 0
    properties.previous_mode = 'SOURCE'
    properties.source_rig = source
    properties['selected_rig_template'] = entry[4]
    templates.set_template_files(properties)
    properties.bake_every_bone = True
    properties.overwrite_control_animations = True
    sc.frame_set(0)
    utilities.save_source_mode_context(properties)
    reference = {}
    for frame in range(start, end + 1):
        sc.frame_set(frame)
        reference[frame] = {name: (source.matrix_world @ source.pose.bones[name].matrix).copy() for name in needed}
    sc.frame_set(0)
    control = next(item for item in scene.get_modes() if item[0] == 'CONTROL')
    properties['selected_mode'] = control[4]
    scene.switch_modes()  # Direct call propagates errors instead of swallowing RNA callback failures.
    rig = bpy.data.objects['rig']
    assert rig.animation_data.action and rig.animation_data.action_slot
    assert animation.iter_fcurves(rig.animation_data.action, rig)

    per_frame = []
    for frame in range(start, end + 1):
        sc.frame_set(frame)
        errors = []
        for name in needed:
            actual = source.matrix_world @ source.pose.bones[name].matrix
            expected = reference[frame][name]
            angle = math.degrees(actual.to_quaternion().rotation_difference(expected.to_quaternion()).angle)
            errors.append({'bone': name, 'position_error_cm': (actual.translation - expected.translation).length * 100,
                           'rotation_error_deg': min(angle, 360 - angle)})
        per_frame.append(errors)
    limb_errors = [error for frame in per_frame for error in frame if error['bone'] in limb_names]
    report = {
        'blender': bpy.app.version_string, 'template': properties.selected_rig_template,
        'template_display_name': entry[1], 'source_bones': len(source.data.bones), 'rig_bones': len(rig.data.bones),
        'frames': [start, end], 'frames_checked': end - start + 1, 'mapped_source_bones': len(needed),
        'limb_bones_verified': sorted(limb_names),
        'limb_max_position_error_cm': max(error['position_error_cm'] for error in limb_errors),
        'limb_max_rotation_error_deg': max(error['rotation_error_deg'] for error in limb_errors),
        'all_mapped_max_position_error_cm': max(error['position_error_cm'] for frame in per_frame for error in frame),
        'all_mapped_max_rotation_error_deg': max(error['rotation_error_deg'] for frame in per_frame for error in frame),
        'limitations': 'Existing ik_hand_gun, finger-base and neck approximations remain; this is not a lossless full-skeleton test.'
    }
    report['scale_normalization'] = asdict(normalized)
    assert report['limb_max_position_error_cm'] < 0.05, report
    assert report['limb_max_rotation_error_deg'] < 0.1, report
    if args.report:
        args.report.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print('MANNY_SIMPLE_CONVERSION_PASS', json.dumps(report))
