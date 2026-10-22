"""Blender 5 regression: shared Actions must preserve per-owner slot isolation."""
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ue2rigify.core import animation, utilities

shared = bpy.data.actions.new('SharedSlotRegression')
objects = []
for index in range(2):
    obj = bpy.data.objects.new('SlotOwner' + str(index), None)
    bpy.context.scene.collection.objects.link(obj)
    slot = shared.slots.new(id_type=obj.id_type, name=obj.name)
    animation.assign_action(obj, shared, slot)
    obj.location.x = 10.0 * (index + 1)
    obj.keyframe_insert('location', index=0, frame=1)
    obj.location.x += 3.0
    obj.keyframe_insert('location', index=0, frame=2)
    objects.append(obj)

assert len(shared.slots) == 2
assert all(len(animation.iter_fcurves(shared, obj)) == 1 for obj in objects)
utilities.set_action_transform_offsets(shared, {'location': [5, 0, 0]}, 'ADD', owner=objects[0])
assert animation.iter_fcurves(shared, objects[0])[0].keyframe_points[0].co.y == 15
assert animation.iter_fcurves(shared, objects[1])[0].keyframe_points[0].co.y == 20

# Reproduce an Action referenced only by an NLA strip, with no active Action.
track = objects[1].animation_data.nla_tracks.new()
strip = track.strips.new('NlaOnly', 1, shared)
animation.bind_strip_slot(strip, objects[1])
expected_slot = objects[1].animation_data.action_slot
assert strip.action_slot == expected_slot
objects[1].animation_data.action = None
assert animation.get_action_slot(shared, objects[1]) == expected_slot

animation.clear_fcurves(shared, objects[0])
assert not animation.iter_fcurves(shared, objects[0])
assert len(animation.iter_fcurves(shared, objects[1])) == 1
curve = animation.iter_fcurves(shared, objects[1])[0]
animation.remove_fcurve(shared, curve, objects[1])
assert not animation.iter_fcurves(shared, objects[1])

# A newly created Blender 5 Action has no legacy fcurves, even when it is empty.
empty = bpy.data.actions.new('EmptyActionRegression')
assert not animation.iter_fcurves(empty)
slot = animation.assign_action(objects[0], empty)
assert slot is not None and objects[0].animation_data.action_slot == slot
print('ACTION_SLOT_REGRESSION_PASS', bpy.app.version_string)
