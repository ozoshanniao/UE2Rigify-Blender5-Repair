# SPDX-License-Identifier: GPL-3.0-or-later
# Adapted from OZO_Tools 0.5.2 by OZO; namespaced for UE to Rigify 1.8.0.
"""Normalize a simple animated import without changing its world-space motion.

Only constant positive uniform object scale and one plain Action are supported.
All validation happens before copies are created. Verification failure rolls the
transaction back; no blend file is saved and the source Action is never edited.
"""

from dataclasses import dataclass, field
import ast
import hashlib
import inspect
import math
import textwrap
import uuid

import bpy
from bpy.props import BoolProperty, PointerProperty, StringProperty
from mathutils import Matrix
import numpy as np

TRANSFORMS = {
    "location": 3, "rotation_euler": 3, "rotation_quaternion": 4,
    "rotation_axis_angle": 4, "scale": 3,
}
MAX_BASELINE_BYTES = 512 * 1024 * 1024
WORLD_TOLERANCE = 2e-5  # Blender world units, not scene-display units.
MATRIX_IDENTITY_TOLERANCE = 1e-5  # Import roundoff only; world verification is unchanged.
# Preserve OZO's data provenance key so both tools detect mismatched rig/Action pairs.
# Operators, panels and scene settings use independent UE2Rigify names.
BINDING_KEY = "ozo_animation_scale_binding"

# Audited callbacks are allowed only while their work is inactive. Fingerprints
# include the function's AST, so matching an addon's name alone is insufficient.
INACTIVE_CALLBACKS = {
    ("amp_animate_pro.utils.handlers", "amp_on_frame_change_post"):
        "719747aa9af5ef0509563b54b211696d4094dcfce762271339b6be8fd96ca8ab",
    ("auto_rig_pro.src.rig_functions", "rig_layers_anim_update"):
        "95077b5b511766603168a4f790f4fe412bb634768789e60285af29713242ccbe",
}


def callback_fingerprint(callback):
    try:
        source = textwrap.dedent(inspect.getsource(callback))
        structure = ast.dump(ast.parse(source), include_attributes=False)
        return hashlib.sha256(structure.encode()).hexdigest()
    except (OSError, TypeError, SyntaxError):
        return None


def frame_callback_issues(context):
    issues, notes = [], []
    for phase in ("frame_change_pre", "frame_change_post"):
        for callback in getattr(bpy.app.handlers, phase):
            module = getattr(callback, "__module__", "")
            name = getattr(callback, "__name__", type(callback).__name__)
            label = f"{module}.{name}"
            profile = next((key for key in INACTIVE_CALLBACKS
                            if (module == key[0] or module.endswith("." + key[0]))
                            and name == key[1]), None)
            if phase == "frame_change_post" and profile and callback_fingerprint(callback) == INACTIVE_CALLBACKS[profile]:
                if profile[1] == "amp_on_frame_change_post" and not (
                    context.screen and context.screen.is_animation_playing
                ):
                    notes.append("AMP Animate Pro playback callback is inactive")
                    continue
                if profile[1] == "rig_layers_anim_update" and not getattr(context.scene, "arp_layers_animated", False):
                    notes.append("Auto-Rig Pro animated-layer callback is inactive")
                    continue
            issues.append(f"Unsupported {phase} callback: {label}")
    return issues, notes


@dataclass
class ScalePlan:
    source: object = None
    action: object = None
    slot: object = None
    meshes: list = field(default_factory=list)
    factor: float = 1.0
    curves: list = field(default_factory=list)
    samples: list = field(default_factory=list)
    issues: list = field(default_factory=list)
    notes: list = field(default_factory=list)

    @property
    def ready(self):
        return not self.issues

    @property
    def unit_scale(self):
        return self.factor == 1.0 and all(v == 1 for v in self.source.scale)

    def description(self):
        if self.issues:
            return "\n".join(self.issues)
        if self.unit_scale:
            return "Already at constant Scale 1\nNo data changes or frame stepping required\nFrame callbacks are left untouched"
        return (
            f"Armature: {self.source.name}\nAction: {self.action.name}\n"
            f"Uniform scale: {self.factor:.9g}\nMeshes: {len(self.meshes)}\n"
            f"Verification samples: {len(self.samples)}\n"
            "Every integer Action frame, fractional keys, and current frame\n"
            "Original Action is retained; copied data is used\n"
            "World-space bone endpoints and all evaluated mesh vertices are checked"
            + ("\n" + "\n".join(self.notes) if self.notes else "")
        )


@dataclass
class ScaleResult:
    skipped: bool = False
    factor: float = 1.0
    samples: int = 0
    meshes: int = 0
    location_curves: int = 0
    bone_error: float = 0.0
    vertex_error: float = 0.0
    original_action: str = ""
    action: str = ""

    def description(self):
        if self.skipped:
            return "Already at constant Scale 1; no data or Action was changed"
        return (
            f"Scale: {self.factor:.9g} -> 1\n"
            f"Original Action retained: {self.original_action}\nNew Action: {self.action}\n"
            f"Meshes copied: {self.meshes}\nBone location curves scaled: {self.location_curves}\n"
            f"Samples verified: {self.samples}\nMax bone error: {self.bone_error:.6g}\n"
            f"Max vertex error: {self.vertex_error:.6g}\n"
            f"Tolerance: {WORLD_TOLERANCE:g} Blender world units\n"
            "No blend file was saved"
        )


def action_curves(action, slot):
    bag = action.layers[0].strips[0].channelbag(slot)
    return list(bag.fcurves) if bag else []


def identity(matrix):
    return all(abs(matrix[i][j] - (i == j)) <= MATRIX_IDENTITY_TOLERANCE for i in range(4) for j in range(4))


def convert_mesh_offset(mesh, factor):
    """Conjugate tiny mesh-relative transforms by a uniform scale.

    For any affine M, S M S^-1 keeps its linear part and multiplies translation
    by s. Do not clear near-identity matrices: they can contain real offsets.
    """
    for prop in ("matrix_parent_inverse", "matrix_basis"):
        matrix = getattr(mesh, prop).copy()
        if any(matrix.translation):
            matrix.translation *= factor
            setattr(mesh, prop, matrix)


def plain_delta(obj):
    return (
        all(abs(v) <= 1e-7 for v in obj.delta_location)
        and all(abs(v) <= 1e-7 for v in obj.delta_rotation_euler)
        and all(abs(v - expected) <= 1e-7 for v, expected in zip(obj.delta_rotation_quaternion, (1, 0, 0, 0)))
        and all(abs(v - 1) <= 1e-7 for v in obj.delta_scale)
    )


def has_animation(data):
    anim = data.animation_data
    return anim is not None and (anim.action is not None or len(anim.drivers) or len(anim.nla_tracks))


def external_dependencies(source, meshes):
    """Reject object/pose constraints and driver inputs pointing into this rig."""
    affected = {source, source.data, *(mesh for mesh in meshes), *(mesh.data for mesh in meshes)}
    for obj in bpy.data.objects:
        if obj == source or obj in meshes:
            continue
        constraints = list(obj.constraints)
        if obj.type == "ARMATURE":
            constraints.extend(c for p in obj.pose.bones for c in p.constraints)
        for constraint in constraints:
            for prop in constraint.bl_rna.properties:
                if prop.type == "POINTER" and getattr(constraint, prop.identifier, None) in affected:
                    return f"External constraint references this rig: {obj.name} / {constraint.name}"
            for target in getattr(constraint, "targets", ()):
                if getattr(target, "target", None) in affected:
                    return f"External constraint references this rig: {obj.name} / {constraint.name}"
        for data in (obj, obj.data):
            if data is None or not hasattr(data, "animation_data") or not data.animation_data:
                continue
            for curve in data.animation_data.drivers:
                for variable in curve.driver.variables:
                    if any(target.id in affected for target in variable.targets):
                        return f"External driver references this rig: {obj.name}"
    # Also cover ID references from materials, worlds, node groups, etc.; a copy
    # of the rig's datablocks must not invalidate an unexamined external user.
    for users in bpy.data.user_map(subset=affected).values():
        for user in users:
            if user not in affected and not isinstance(user, (bpy.types.Collection, bpy.types.Scene)):
                return f"External data references this rig: {user.name}"
    return None


def inspect_rig(context):
    plan = ScalePlan(source=context.active_object)
    src = plan.source
    if bpy.app.version < (4, 4, 0):
        plan.issues.append("Animation Scale requires Blender 4.4 or later")
        return plan
    if src is None or src.type != "ARMATURE":
        plan.issues.append("Select an armature")
        return plan
    if src.mode not in {"OBJECT", "POSE"}:
        plan.issues.append("Use Object or Pose Mode")
        return plan
    if not src.is_editable or not src.data.is_editable or src.library or src.override_library or src.data.override_library:
        plan.issues.append("Linked, overridden, or read-only armatures are not supported")
    if src.parent:
        plan.issues.append("Armature must have no parent")
    if src.data.users - int(src.data.use_fake_user) > 1:
        plan.issues.append("Armature data must not be shared")
    if src.instance_type != "NONE":
        plan.issues.append("Armature instancing is not supported")
    if not src.data.bones:
        plan.issues.append("Armature has no bones")
    if src.data.pose_position != "POSE":
        plan.issues.append("Set armature Pose Position to Pose")
    if has_animation(src.data):
        plan.issues.append("Animated armature datablocks are not supported")
    if src.constraints or any(p.constraints for p in src.pose.bones):
        plan.issues.append("Object and pose-bone constraints are not supported")
    if any(p.custom_shape for p in src.pose.bones) or any(b.bbone_segments > 1 for b in src.data.bones):
        plan.issues.append("Custom bone shapes and segmented B-Bones are not supported")
    if not plain_delta(src):
        plan.issues.append("Armature delta transforms must be identity")
    if context.scene.render.frame_map_old != context.scene.render.frame_map_new:
        plan.issues.append("Scene time remapping is not supported")
    plan.factor = float(src.scale.x)
    scale_eps = max(abs(plan.factor) * 1e-6, 1e-12)
    if not all(math.isfinite(v) and v > 0 and abs(v - plan.factor) <= scale_eps for v in src.scale):
        plan.issues.append("Object Scale must be positive and uniform on X/Y/Z")

    for child in src.children:
        if child.type != "MESH":
            plan.issues.append(f"Only direct mesh children are supported: {child.name}")
            continue
        plan.meshes.append(child)
        if child.name not in context.scene.objects:
            plan.issues.append(f"Mesh must be in the current scene: {child.name}")
        if (not child.is_editable or not child.data.is_editable or child.library
                or child.override_library or child.data.override_library):
            plan.issues.append(f"Linked/overridden mesh is not supported: {child.name}")
        if child.data.users - int(child.data.use_fake_user) > 1:
            plan.issues.append(f"Mesh data must not be shared: {child.name}")
        if child.parent_type != "OBJECT":
            plan.issues.append(f"Mesh needs Object parenting: {child.name}")
        for label, matrix in (("local", child.matrix_basis), ("parent-inverse", child.matrix_parent_inverse)):
            if not identity(matrix):
                deviation = max(abs(matrix[i][j] - (i == j)) for i in range(4) for j in range(4))
                plan.issues.append(f"Mesh {label} matrix differs from identity by {deviation:.6g} (limit {MATRIX_IDENTITY_TOLERANCE:g}): {child.name}")
            elif any(abs(matrix[i][j] - (i == j)) > 1e-7 for i in range(4) for j in range(4)):
                plan.notes.append(f"Near-identity {label} matrix accepted: {child.name}")
        if not plain_delta(child) or child.constraints or has_animation(child) or has_animation(child.data):
            plan.issues.append(f"Mesh animation, constraints, and delta transforms are not supported: {child.name}")
        if child.data.shape_keys:
            plan.issues.append(f"Shape keys are not supported: {child.name}")
        if child.children or child.rigid_body or child.rigid_body_constraint or child.instance_type != "NONE":
            plan.issues.append(f"Mesh children, physics, and instancing are not supported: {child.name}")
        mods = list(child.modifiers)
        if len(mods) != 1 or mods[0].type != "ARMATURE" or mods[0].object != src:
            plan.issues.append(f"Mesh needs exactly one Armature modifier targeting this rig: {child.name}")
        elif not mods[0].use_vertex_groups or mods[0].use_bone_envelopes or mods[0].use_multi_modifier:
            plan.issues.append(f"Use vertex-group deformation without envelopes/multi-modifier: {child.name}")
    for obj in bpy.data.objects:
        if obj.type == "MESH" and obj not in plan.meshes and any(
            mod.type == "ARMATURE" and mod.object == src for mod in obj.modifiers
        ):
            plan.issues.append(f"Bound mesh is not a supported direct child: {obj.name}")
    dependency = external_dependencies(src, plan.meshes)
    if dependency:
        plan.issues.append(dependency)

    anim = src.animation_data
    if anim is None or anim.action is None:
        plan.issues.append("One active Action is required")
        return plan
    plan.action, plan.slot = anim.action, anim.action_slot
    if anim.drivers or anim.nla_tracks or anim.use_tweak_mode:
        plan.issues.append("Drivers, NLA tracks, and NLA tweak mode are not supported")
    if anim.action_blend_type != "REPLACE" or abs(anim.action_influence - 1) > 1e-7:
        plan.issues.append("Action must use Replace with influence 1")
    action = plan.action
    binding = src.data.get(BINDING_KEY)
    action_binding = action.get(BINDING_KEY)
    if (binding or action_binding) and binding != action_binding:
        plan.issues.append("Rig and Action do not share the same normalization; restore the source rig or use its matching Action")
    elif binding and any(v != 1 for v in src.scale):
        plan.issues.append("Rest data was already normalized; restore the original rig before normalizing another scale")
    if action.library or action.override_library or not action.is_editable:
        plan.issues.append("Linked/overridden Actions are not supported")
    if (len(action.slots) != 1 or plan.slot is None or len(action.layers) != 1
            or len(action.layers[0].strips) != 1
            or action.layers[0].strips[0].type != "KEYFRAME"):
        plan.issues.append("Only one Action slot, layer, and keyframe strip are supported")
        return plan
    plan.curves = action_curves(action, plan.slot)
    if not plan.curves:
        plan.issues.append("Active Action has no curves in its assigned slot")
        return plan
    allowed = dict(TRANSFORMS)
    for bone in src.pose.bones:
        allowed.update({bone.path_from_id(prop): length for prop, length in TRANSFORMS.items()})
    seen = set()
    times = set()
    curve_issues = set()
    for curve in plan.curves:
        path, index = curve.data_path, curve.array_index
        if path not in allowed or not 0 <= index < allowed[path]:
            curve_issues.add("Only object/bone Location, Rotation, and Scale curves are supported")
        if (path, index) in seen:
            curve_issues.add("Duplicate animation channels are not supported")
        seen.add((path, index))
        if curve.modifiers or curve.sampled_points:
            curve_issues.add("FCurve modifiers and sampled curves are not supported")
        if curve.mute or (curve.group and curve.group.mute):
            curve_issues.add("Muted animation channels are not supported")
        for key in curve.keyframe_points:
            points = (key.co, key.handle_left, key.handle_right)
            if not all(math.isfinite(v) for point in points for v in point):
                curve_issues.add("Animation contains non-finite keys or handles")
                continue
            times.add(float(key.co.x))
            if path == "scale" and any(abs(point.y - plan.factor) > scale_eps for point in points):
                curve_issues.add("Object Scale animation must be constant, including Bezier handles")
    plan.issues.extend(sorted(curve_issues))
    if not times:
        plan.issues.append("Action contains no usable keyframes")
        return plan
    first, last = min(min(times), action.frame_range[0]), max(max(times), action.frame_range[1])
    if not math.isfinite(first) or not math.isfinite(last) or last - first > 100000:
        plan.issues.append("Action frame range is too large for full verification")
        return plan
    times.update(range(math.floor(first), math.ceil(last) + 1))
    times.add(float(context.scene.frame_current_final))
    plan.samples = sorted(times)
    count = 2 * len(src.data.bones) + sum(len(mesh.data.vertices) for mesh in plan.meshes)
    if not plan.unit_scale and len(plan.samples) * count * 3 * 8 > MAX_BASELINE_BYTES:
        plan.issues.append("Full verification would exceed the 512 MiB baseline limit")
    # Unit-scale inputs never call frame_set, so callbacks cannot affect a skip.
    if not plan.unit_scale:
        issues, notes = frame_callback_issues(context)
        plan.issues.extend(issues)
        plan.notes.extend(notes)
    return plan


def capture_world(context, source, meshes):
    depsgraph = context.evaluated_depsgraph_get()
    armature = source.evaluated_get(depsgraph)
    bones = np.asarray([
        tuple(armature.matrix_world @ point)
        for bone in armature.pose.bones for point in (bone.head, bone.tail)
    ], dtype=np.float64)
    vertices = []
    for mesh in meshes:
        evaluated = mesh.evaluated_get(depsgraph)
        data = evaluated.to_mesh()
        try:
            coordinates = np.empty(len(data.vertices) * 3, dtype=np.float32)
            data.vertices.foreach_get("co", coordinates)
            coordinates = coordinates.reshape((-1, 3)).astype(np.float64)
            matrix = np.asarray(evaluated.matrix_world, dtype=np.float64)
            vertices.append(coordinates @ matrix[:3, :3].T + matrix[:3, 3])
        finally:
            evaluated.to_mesh_clear()
    return bones, vertices


def set_sample(scene, frame):
    integer = math.floor(frame)
    scene.frame_set(integer, subframe=frame - integer)


def pose_channels(source):
    return {
        bone.name: {prop: tuple(getattr(bone, prop)) for prop in TRANSFORMS}
        for bone in source.pose.bones
    }


def set_pose_channels(source, values, factor=1.0):
    for name, properties in values.items():
        bone = source.pose.bones[name]
        for prop, value in properties.items():
            setattr(bone, prop, tuple(v * factor for v in value) if prop == "location" else value)


def convert_action(action, slot, factor):
    locations = 0
    for curve in action_curves(action, slot):
        if not curve.keyframe_points:
            continue
        if curve.data_path == "scale":
            multiplier = None
        elif curve.data_path.startswith("pose.bones[") and curve.data_path.endswith(".location"):
            multiplier = factor
            locations += 1
        else:
            continue
        points = [(key, key.co.copy(), key.handle_left.copy(), key.handle_right.copy())
                  for key in curve.keyframe_points]
        for key, co, left, right in points:
            co.y = co.y * multiplier if multiplier is not None else 1.0
            left.y = left.y * multiplier if multiplier is not None else 1.0
            right.y = right.y * multiplier if multiplier is not None else 1.0
            key.co, key.handle_left, key.handle_right = co, left, right
        curve.update()
    return locations


def max_distance(before, after):
    if before.shape != after.shape:
        raise RuntimeError("Evaluated topology changed during verification")
    if not np.isfinite(before).all() or not np.isfinite(after).all():
        raise RuntimeError("Non-finite world-space coordinates detected")
    return float(np.linalg.norm(before - after, axis=1).max()) if len(before) else 0.0


def normalize_scale(context, progress=None):
    plan = inspect_rig(context)
    if not plan.ready:
        raise ValueError("\n".join(plan.issues))
    src, scene = plan.source, context.scene
    if plan.unit_scale:
        return ScaleResult(skipped=True)
    original_frame, original_subframe = scene.frame_current, scene.frame_subframe
    old_armature, old_action = src.data, plan.action
    old_meshes = [(mesh, mesh.data) for mesh in plan.meshes]
    old_mesh_channels = {mesh: {prop: tuple(getattr(mesh, prop)) for prop in TRANSFORMS} for mesh in plan.meshes}
    old_mesh_inverses = {mesh: mesh.matrix_parent_inverse.copy() for mesh in plan.meshes}
    old_scale = src.scale.copy()
    old_pose = pose_channels(src)
    old_fake = old_action.use_fake_user
    old_slot_id = plan.slot.identifier
    new_armature = new_action = None
    new_meshes = []
    baseline = []
    switched = False
    result = ScaleResult(factor=plan.factor, samples=len(plan.samples), meshes=len(plan.meshes),
                         original_action=old_action.name)
    try:
        # Baseline collection is read-only; no new datablocks exist yet.
        for index, frame in enumerate(plan.samples):
            set_sample(scene, frame)
            baseline.append(capture_world(context, src, plan.meshes))
            if progress:
                progress(index + 1, 2 * len(plan.samples))
        scene.frame_set(original_frame, subframe=original_subframe)
        new_armature = old_armature.copy()
        new_armature.name = old_armature.name + "_Scale1"
        transform = Matrix.Scale(plan.factor, 4)
        new_armature.transform(transform)
        for mesh, data in old_meshes:
            new_data = data.copy()
            new_meshes.append((mesh, new_data))
            new_data.name = data.name + "_Scale1"
            new_data.transform(transform)
            new_data.update()
        new_action = old_action.copy()
        new_action.name = old_action.name + "_Scale1"
        new_slot = new_action.slots.get(old_slot_id)
        if new_slot is None:
            raise RuntimeError("Copied Action lost its assigned slot")
        result.location_curves = convert_action(new_action, new_slot, plan.factor)
        binding = uuid.uuid4().hex
        new_armature[BINDING_KEY] = binding
        new_action[BINDING_KEY] = binding
        # Begin the swap only after all independent copies are prepared.
        switched = True
        src.data = new_armature
        for mesh, data in new_meshes:
            mesh.data = data
            convert_mesh_offset(mesh, plan.factor)
        set_pose_channels(src, old_pose, plan.factor)
        src.animation_data.action = new_action
        src.animation_data.action_slot = new_slot
        src.scale = (1, 1, 1)
        for index, (frame, (before_bones, before_vertices)) in enumerate(zip(plan.samples, baseline)):
            set_sample(scene, frame)
            after_bones, after_vertices = capture_world(context, src, plan.meshes)
            result.bone_error = max(result.bone_error, max_distance(before_bones, after_bones))
            for before, after in zip(before_vertices, after_vertices):
                result.vertex_error = max(result.vertex_error, max_distance(before, after))
            if any(abs(v - 1) > 1e-6 for v in src.evaluated_get(context.evaluated_depsgraph_get()).scale):
                raise RuntimeError("Object Scale did not remain 1 during animation")
            if max(result.bone_error, result.vertex_error) > WORLD_TOLERANCE:
                raise RuntimeError(
                    f"World-space verification failed at frame {frame:g}: "
                    f"bone {result.bone_error:.6g}, vertex {result.vertex_error:.6g}"
                )
            if progress:
                progress(len(plan.samples) + index + 1, 2 * len(plan.samples))
        old_action.use_fake_user = True
        new_action.use_fake_user = True
        result.action = new_action.name
        return result
    except Exception:
        if switched:
            src.data = old_armature
            for mesh, data in old_meshes:
                mesh.data = data
                mesh.matrix_parent_inverse = old_mesh_inverses[mesh]
                for prop, value in old_mesh_channels[mesh].items():
                    setattr(mesh, prop, value)
            src.animation_data.action = old_action
            src.animation_data.action_slot = old_action.slots.get(old_slot_id)
            src.scale = old_scale
            set_pose_channels(src, old_pose)
        old_action.use_fake_user = old_fake
        # Delete only this transaction's copies after releasing their users.
        for _, data in new_meshes:
            bpy.data.meshes.remove(data)
        if new_armature is not None:
            bpy.data.armatures.remove(new_armature)
        if new_action is not None:
            bpy.data.actions.remove(new_action)
        raise
    finally:
        baseline.clear()
        scene.frame_set(original_frame, subframe=original_subframe)


class UE2RIGIFY_PG_animation_scale(bpy.types.PropertyGroup):
    show_scope: BoolProperty(name="Scope", default=False, options={"SKIP_SAVE"}, translation_context="UE2Rigify")
    last_status: StringProperty(options={"SKIP_SAVE"})
    last_details: StringProperty(options={"SKIP_SAVE"})


class ScaleOperator:
    bl_translation_context = "UE2Rigify"

    @classmethod
    def poll(cls, context):
        if bpy.app.version < (4, 4, 0):
            cls.poll_message_set("Animation Scale requires Blender 4.4 or later")
            return False
        obj = context.active_object
        if obj is None or obj.type != "ARMATURE":
            cls.poll_message_set("Select an armature")
            return False
        if obj.mode not in {"OBJECT", "POSE"}:
            cls.poll_message_set("Use Object or Pose Mode")
            return False
        return True


class UE2RIGIFY_OT_check_animation_scale(ScaleOperator, bpy.types.Operator):
    bl_idname = "ue2rigify.check_animation_scale"
    bl_label = "Check"
    bl_description = "Check supported structure and animation without modifying the rig"

    def execute(self, context):
        plan = inspect_rig(context)
        settings = context.scene.ue2rigify_animation_scale
        settings.last_status = (
            "Already Scale 1" if plan.ready and plan.unit_scale else
            "Ready" if plan.ready else f"Unsupported: {len(plan.issues)} issue(s)"
        )
        settings.last_details = plan.description()
        self.report({"INFO"} if plan.ready else {"WARNING"}, settings.last_status + "; view Details")
        return {"FINISHED"}


class UE2RIGIFY_OT_normalize_animation_scale(ScaleOperator, bpy.types.Operator):
    bl_idname = "ue2rigify.normalize_animation_scale"
    bl_label = "Normalize Scale"
    bl_description = "Copy and normalize the active Action/rig; verify world motion and size; keep the original Action"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        settings = context.scene.ue2rigify_animation_scale
        manager = context.window_manager
        manager.progress_begin(0, 1)
        try:
            result = normalize_scale(context, lambda step, total: manager.progress_update(step / total))
        except Exception as error:
            settings.last_status = "Not applied"
            settings.last_details = str(error)
            self.report({"ERROR"}, str(error).splitlines()[0] + "; view Details")
            return {"CANCELLED"}
        finally:
            manager.progress_end()
        settings.last_status = "Already Scale 1" if result.skipped else f"Scale 1 / Verified {result.samples} samples"
        settings.last_details = result.description()
        print("[UE2Rigify Animation Scale] " + settings.last_details.replace("\n", " | "))
        self.report({"INFO"}, settings.last_status)
        return {"FINISHED"}


class UE2RIGIFY_OT_animation_scale_report(bpy.types.Operator):
    bl_idname = "ue2rigify.animation_scale_report"
    bl_label = "Animation Scale Details"
    bl_translation_context = "UE2Rigify"

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=650)

    def execute(self, context):
        return {"FINISHED"}

    def draw(self, context):
        for line in context.scene.ue2rigify_animation_scale.last_details.splitlines():
            self.layout.label(text=line, translate=False)


class UE2RIGIFY_PT_animation_scale(bpy.types.Panel):
    bl_idname = "UE2RIGIFY_PT_animation_scale"
    bl_label = "Animation Scale"
    bl_translation_context = "UE2Rigify"
    bl_parent_id = "UE_RIGIFY_PT_RigTemplatePanel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "UE to Rigify"
    bl_order = 3

    def draw(self, context):
        outer = self.layout.row()
        spacer = outer.column()
        spacer.ui_units_x = 1.0
        spacer.label(text="")
        layout = outer.column()
        layout.use_property_decorate = False
        settings = context.scene.ue2rigify_animation_scale
        layout.label(text="Use on the imported rig before Convert.", translate=False)
        obj = context.active_object
        layout.label(text="Active: " + (obj.name if obj else "None"), translate=False)
        layout.label(text="Keep animation and world size.", translate=False)
        header = layout.row()
        header.alignment = "LEFT"
        header.prop(settings, "show_scope", text="Scope", translate=False,
                    icon="TRIA_DOWN" if settings.show_scope else "TRIA_RIGHT", emboss=False, toggle=True)
        if settings.show_scope:
            for line in (
                "Active rig + direct child meshes.", "Constant positive uniform scale.",
                "One Action; no constraints/drivers/NLA.", "Near-identity mesh transforms.",
                "No shape keys or shared geometry.", "Copies data; verifies every frame.",
                "Not height matching or retargeting.",
            ):
                layout.label(text=line, translate=False)
        row = layout.row(align=True)
        row.operator("ue2rigify.check_animation_scale", text="Check", translate=False)
        row.operator("ue2rigify.normalize_animation_scale", text="Normalize Scale", translate=False)
        if settings.last_status:
            row = layout.row(align=True)
            row.label(text=settings.last_status, translate=False)
            row.operator("ue2rigify.animation_scale_report", text="", icon="INFO")


CLASSES = (
    UE2RIGIFY_PG_animation_scale, UE2RIGIFY_OT_check_animation_scale, UE2RIGIFY_OT_normalize_animation_scale,
    UE2RIGIFY_OT_animation_scale_report, UE2RIGIFY_PT_animation_scale,
)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.ue2rigify_animation_scale = PointerProperty(type=UE2RIGIFY_PG_animation_scale)


def unregister():
    del bpy.types.Scene.ue2rigify_animation_scale
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
