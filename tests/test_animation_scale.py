"""Background Blender regression for the Animation Scale port (no external assets)."""
import argparse
import hashlib
import importlib.util
import json
import sys
from dataclasses import asdict
from pathlib import Path

import bpy
from mathutils import Matrix

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ue2rigify.core import animation_scale as scale

parser = argparse.ArgumentParser()
parser.add_argument('--report', type=Path)
parser.add_argument('--ozo-animation-scale', type=Path)
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
report = {'blender': bpy.app.version_string, 'checks': []}


def curves_snapshot(action, slot):
    return [(curve.data_path, curve.array_index,
             [(tuple(key.co), tuple(key.handle_left), tuple(key.handle_right)) for key in curve.keyframe_points])
            for curve in scale.action_curves(action, slot)]


def fixture():
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    data = bpy.data.armatures.new('ScaleTestArmature')
    rig = bpy.data.objects.new('ScaleTestRig', data)
    bpy.context.scene.collection.objects.link(rig)
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    root = data.edit_bones.new('root')
    root.head, root.tail = (0, 0, 0), (0, 0, 100)
    child = data.edit_bones.new('child')
    child.head, child.tail, child.parent = (0, 0, 100), (20, 0, 150), root
    bpy.ops.object.mode_set(mode='OBJECT')
    mesh_data = bpy.data.meshes.new('ScaleTestMesh')
    mesh_data.from_pydata([(-10, 0, 0), (10, 0, 0), (10, 0, 100), (-10, 0, 100)], [], [(0, 1, 2, 3)])
    mesh = bpy.data.objects.new('ScaleTestMesh', mesh_data)
    bpy.context.scene.collection.objects.link(mesh)
    mesh.parent = rig
    mesh.matrix_parent_inverse = Matrix.Identity(4)
    mesh.location.x = 4e-6  # Retain accepted FBX roundoff instead of clearing it.
    mesh.vertex_groups.new(name='root').add([0, 1, 2, 3], 1, 'REPLACE')
    modifier = mesh.modifiers.new('Deform', 'ARMATURE')
    modifier.object = rig
    rig.scale = (0.01,) * 3
    rig.rotation_euler = (0.1, 0.2, 0.3)
    root = rig.pose.bones['root']
    root.rotation_mode = 'XYZ'
    for frame, value in [(1, 2), (1.5, 4), (3, 8)]:
        root.location = (value, 2 * value, -value)
        root.rotation_euler.z = value * 0.05
        root.keyframe_insert('location', frame=frame)
        root.keyframe_insert('rotation_euler', frame=frame)
        rig.location = (value * 0.2, -1, 0.5)
        rig.keyframe_insert('location', frame=frame)
        rig.keyframe_insert('scale', frame=frame)
    bpy.context.scene.frame_set(2, subframe=0.25)
    return rig, mesh


rig, mesh = fixture()
old_armature, old_mesh = rig.data, mesh.data
old_action, old_slot = rig.animation_data.action, rig.animation_data.action_slot
original = curves_snapshot(old_action, old_slot)
old_bones = [(tuple(b.head_local), tuple(b.tail_local)) for b in old_armature.bones]
old_vertices = [tuple(vertex.co) for vertex in old_mesh.vertices]
assert scale.inspect_rig(bpy.context).ready
result = scale.normalize_scale(bpy.context)
assert not result.skipped and abs(result.factor - 0.01) < 1e-8 and result.location_curves == 3
assert result.bone_error <= scale.WORLD_TOLERANCE and result.vertex_error <= scale.WORLD_TOLERANCE
assert result.samples == 5  # 1, 1.5, 2, 2.25, 3
assert (bpy.context.scene.frame_current, bpy.context.scene.frame_subframe) == (2, 0.25)
assert rig.data != old_armature and mesh.data != old_mesh and rig.animation_data.action != old_action
assert curves_snapshot(old_action, old_slot) == original
assert [(tuple(b.head_local), tuple(b.tail_local)) for b in old_armature.bones] == old_bones
assert [tuple(vertex.co) for vertex in old_mesh.vertices] == old_vertices
assert old_action.use_fake_user
assert rig.data[scale.BINDING_KEY] == rig.animation_data.action[scale.BINDING_KEY]
report['normalization'] = asdict(result)
report['checks'].append('world bones/vertices, fractional samples, source preservation, frame restoration')

# A constant Scale 1 repeat neither copies data nor steps frames, even with a callback present.
callback_calls = []
def callback(*_):
    callback_calls.append(True)
bpy.app.handlers.frame_change_post.append(callback)
before = (rig.data, mesh.data, rig.animation_data.action, len(bpy.data.actions))
try:
    assert scale.normalize_scale(bpy.context).skipped
    assert not callback_calls
    assert before == (rig.data, mesh.data, rig.animation_data.action, len(bpy.data.actions))
finally:
    bpy.app.handlers.frame_change_post.remove(callback)
report['checks'].append('repeat is a no-op with no frame stepping')

# Provenance also rejects the original unnormalized Action on normalized rest data.
new_action = rig.animation_data.action
rig.animation_data.action, rig.animation_data.action_slot = old_action, old_slot
assert not scale.inspect_rig(bpy.context).ready
rig.animation_data.action = new_action
rig.animation_data.action_slot = new_action.slots[0]
report['checks'].append('mismatched original Action is rejected')

for case in ('nonuniform', 'animated_scale', 'nla', 'callback'):
    rig, mesh = fixture()
    if case == 'nonuniform':
        rig.scale.y = 0.02
    elif case == 'animated_scale':
        curve = next(c for c in scale.action_curves(rig.animation_data.action, rig.animation_data.action_slot)
                     if c.data_path == 'scale')
        curve.keyframe_points[-1].co.y = 0.02
    elif case == 'nla':
        rig.animation_data.nla_tracks.new()
    else:
        bpy.app.handlers.frame_change_post.append(callback)
    before = (rig.data, mesh.data, rig.animation_data.action, len(bpy.data.actions), len(bpy.data.armatures))
    try:
        plan = scale.inspect_rig(bpy.context)
        assert not plan.ready, case
        try:
            scale.normalize_scale(bpy.context)
        except ValueError:
            pass
        else:
            raise AssertionError(case + ' was not rejected')
        assert before == (rig.data, mesh.data, rig.animation_data.action, len(bpy.data.actions), len(bpy.data.armatures))
    finally:
        if case == 'callback':
            bpy.app.handlers.frame_change_post.remove(callback)
report['checks'].append('unsupported nonuniform/animated scale, NLA and callbacks do not mutate data')

# Force a post-swap verification error and check complete transactional rollback.
rig, mesh = fixture()
old_action, old_slot = rig.animation_data.action, rig.animation_data.action_slot
original = curves_snapshot(old_action, old_slot)
before = (rig.data, mesh.data, old_action, tuple(mesh.matrix_basis.translation),
          len(bpy.data.actions), len(bpy.data.armatures), len(bpy.data.meshes))
old_capture = scale.capture_world
sample_count = len(scale.inspect_rig(bpy.context).samples)
calls = 0
def incorrect_capture(*parameters):
    global calls
    calls += 1
    bones, vertices = old_capture(*parameters)
    if calls > sample_count:
        bones = bones + 1
    return bones, vertices
scale.capture_world = incorrect_capture
try:
    try:
        scale.normalize_scale(bpy.context)
    except RuntimeError as error:
        assert 'verification failed' in str(error)
    else:
        raise AssertionError('Expected verification failure')
finally:
    scale.capture_world = old_capture
assert before == (rig.data, mesh.data, rig.animation_data.action, tuple(mesh.matrix_basis.translation),
                  len(bpy.data.actions), len(bpy.data.armatures), len(bpy.data.meshes))
assert curves_snapshot(old_action, old_slot) == original
assert all(abs(value - 0.01) < 1e-8 for value in rig.scale)
assert (bpy.context.scene.frame_current, bpy.context.scene.frame_subframe) == (2, 0.25)
report['checks'].append('verification failure restores data and removes only transaction copies')

rig, mesh = fixture()
bpy.ops.object.mode_set(mode='POSE')
pose_result = scale.normalize_scale(bpy.context)
assert not pose_result.skipped and bpy.context.mode == 'POSE'
assert pose_result.bone_error <= scale.WORLD_TOLERANCE and pose_result.vertex_error <= scale.WORLD_TOLERANCE
bpy.ops.object.mode_set(mode='OBJECT')
report['checks'].append('Pose Mode normalization preserves mode and world motion')

# Optional coexistence check with the actual, unmodified OZO module supplied by the user.
if args.ozo_animation_scale:
    path = args.ozo_animation_scale.resolve()
    old_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location('ozo_original_animation_scale', path)
    original_module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = original_module
    spec.loader.exec_module(original_module)
    class OZO_PT_tools(bpy.types.Panel):
        bl_space_type = 'VIEW_3D'
        bl_region_type = 'UI'
        bl_label = 'OZO Tools test parent'
        def draw(self, context):
            pass
    from ue2rigify.ui import view_3d
    view_3d.register()
    bpy.utils.register_class(OZO_PT_tools)
    original_module.register()
    scale.register()
    try:
        assert hasattr(bpy.types.Scene, 'ozo_animation_scale')
        assert hasattr(bpy.types.Scene, 'ue2rigify_animation_scale')
        assert scale.UE2RIGIFY_PT_animation_scale.bl_category == 'UE to Rigify'
        assert bpy.ops.ue2rigify.check_animation_scale() == {'FINISHED'}
        # Use another raw import to test the new operator's mutation path too.
        rig, mesh = fixture()
        assert bpy.ops.ue2rigify.normalize_animation_scale() == {'FINISHED'}
        assert original_module.inspect_rig(bpy.context).unit_scale
        assert bpy.ops.ozo.check_animation_scale() == {'FINISHED'}
    finally:
        scale.unregister()
        original_module.unregister()
        bpy.utils.unregister_class(OZO_PT_tools)
        view_3d.unregister()
    assert hashlib.sha256(path.read_bytes()).hexdigest() == old_hash
    report['ozo_source_sha256'] = old_hash
    report['checks'].append('original OZO and new operators/settings coexist and recognize shared provenance')

if args.report:
    args.report.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print('ANIMATION_SCALE_REGRESSION_PASS', json.dumps(report))
