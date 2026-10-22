# Copyright Epic Games, Inc. All Rights Reserved.
"""Action access shared by legacy Blender and the slotted Action API (4.4+)."""


def get_action_slot(action, owner=None, slot=None):
    """Resolve the owner's slot without mixing curves from other animated objects."""
    if not hasattr(action, 'slots') or (hasattr(action, 'fcurves') and getattr(action, 'is_action_legacy', False)):
        return None
    if slot is not None:
        return slot
    animation_data = getattr(owner, 'animation_data', None)
    if animation_data:
        if animation_data.action == action and animation_data.action_slot:
            return animation_data.action_slot
        slots = {
            strip.action_slot.handle: strip.action_slot
            for track in animation_data.nla_tracks for strip in track.strips
            if strip.action == action and strip.action_slot
        }
        if len(slots) == 1:
            return next(iter(slots.values()))
        if len(slots) > 1:
            raise ValueError('The rig uses multiple slots of the same Action; select a slot explicitly.')
    if len(action.slots) == 1:
        return action.slots[0]
    if owner is not None and len(action.slots) > 1:
        raise ValueError('Cannot determine the Action slot for ' + owner.name)
    return None


def fcurve_collections(action, owner=None, slot=None):
    """Yield mutable curve collections, scoped to a slot when an owner is supplied."""
    if action is None:
        return
    if not hasattr(action, 'layers') or (hasattr(action, 'fcurves') and getattr(action, 'is_action_legacy', False)):
        yield action.fcurves
        return
    slot = get_action_slot(action, owner, slot)
    for layer in action.layers:
        for strip in layer.strips:
            for channelbag in getattr(strip, 'channelbags', ()):
                if slot is None or channelbag.slot_handle == slot.handle:
                    yield channelbag.fcurves


def iter_fcurves(action, owner=None, slot=None):
    """Snapshot the curves so callers can safely remove them during iteration."""
    return [curve for curves in fcurve_collections(action, owner, slot) for curve in curves]


def remove_fcurve(action, curve, owner=None, slot=None):
    for curves in fcurve_collections(action, owner, slot):
        if any(candidate == curve for candidate in curves):
            curves.remove(curve)
            return


def clear_fcurves(action, owner=None, slot=None):
    for curves in fcurve_collections(action, owner, slot):
        for curve in list(curves):
            curves.remove(curve)


def assign_action(owner, action, slot=None):
    """Bind both the Action and its slot; assignment alone can leave the rig unanimated."""
    animation_data = owner.animation_data_create()
    if hasattr(action, 'slots') and not (hasattr(action, 'fcurves') and getattr(action, 'is_action_legacy', False)):
        slot = get_action_slot(action, owner, slot)
        if slot is None:
            slot = action.slots.new(id_type=owner.id_type, name=owner.name)
    animation_data.action = action
    if slot is not None:
        animation_data.action_slot = slot
    return slot


def bind_strip_slot(strip, owner):
    """Keep NLA evaluation on the same slot as the rig's active Action."""
    if hasattr(strip, 'action_slot'):
        slot = get_action_slot(strip.action, owner)
        if slot is not None:
            strip.action_slot = slot
