"""
Tiny Tracks World - shared Blender helpers for the scripted, original 3D models.

CONVENTIONS (verified with an axis probe against Unity 6 - do not change):
  * Blender Z is up, 1 unit = 1 metre.
  * A model's FRONT faces Blender -Y (the Blender "Front" view looks at it). Unity: -Y -> +Z (forward).
  * The model's own RIGHT side is Blender -X (Unity +X).  Blender +Z -> Unity +Y.
  * Models stand on z = 0 with their origin at the ground contact centre unless a script says otherwise.
  * Animated parts (wheels, windmill sails, ...) are separate objects parented to the root; their object origin
    is the pivot (wheel axle centre, etc.). Unity keeps the object names.

LOOK: every mesh gets one colour attribute "Col" (sRGB bytes): the material colour of each face multiplied by
ambient occlusion baked with Cycles. Alpha holds a detail code read by the Unity shader TinyTracks/ToyLit:
  alpha 0            -> plain colour
  alpha (0, 0.5]     -> soft "noise" speckle, strength = alpha*2       (grass, stone, fabric, fur)
  alpha (0.5, 1]     -> wood grain, strength = (alpha-0.5)*2           (needs a UV map running along the grain)
Materials only exist in Blender; Unity uses ONE shared material for everything (SRP batcher friendly).
"""
import bpy
import bmesh
import math
import os
import sys
from mathutils import Vector, Matrix, Euler

import numpy as np

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
MODELS = os.path.join(REPO, "Assets", "_Project", "Art", "Models")
PREVIEWS = os.path.join(REPO, "Logs", "Blender")

# ------------------------------------------------------------------------------------------------ palette
# name: (sRGB hex, detail kind, detail strength)
PALETTE = {
    # wood
    "beech":      ("#E9C48C", "grain", 0.7),
    "beech_dark": ("#C9965A", "grain", 0.8),
    "oak":        ("#B07A45", "grain", 0.8),
    "walnut":     ("#7A4E2D", "grain", 0.8),
    "groove":     ("#A87A48", "grain", 0.4),
    # nature
    "grass":      ("#86CF5E", "noise", 0.5),
    "grass_dark": ("#5FB043", "noise", 0.5),
    "leaf":       ("#4FB548", "noise", 0.6),
    "leaf_light": ("#7FD35A", "noise", 0.6),
    "leaf_dark":  ("#2F8F45", "noise", 0.6),
    "bark":       ("#8A5A3B", "noise", 0.7),
    "rock":       ("#A8A9B4", "noise", 0.8),
    "rock_dark":  ("#7F8191", "noise", 0.8),
    "dirt":       ("#B98355", "noise", 0.7),
    "sand":       ("#EBD49B", "noise", 0.6),
    "water":      ("#4FB7E8", "none", 0.0),
    "snow":       ("#FFFFFF", "noise", 0.2),
    # paints (toy colours)
    "red":        ("#F2474B", "none", 0.0),
    "red_dark":   ("#C42F3A", "none", 0.0),
    "blue":       ("#2E8BE6", "none", 0.0),
    "blue_dark":  ("#1E5FAF", "none", 0.0),
    "sky":        ("#8FD3FF", "none", 0.0),
    "green":      ("#3DBA5A", "none", 0.0),
    "green_dark": ("#24894A", "none", 0.0),
    "yellow":     ("#FFCC2E", "none", 0.0),
    "yellow_dark":("#E7A419", "none", 0.0),
    "orange":     ("#FF8A2B", "none", 0.0),
    "purple":     ("#9B6BE0", "none", 0.0),
    "pink":       ("#FF8FB8", "none", 0.0),
    "white":      ("#FAFAF5", "none", 0.0),
    "cream":      ("#FFF1D6", "none", 0.0),
    "black":      ("#2B2B33", "none", 0.0),
    "charcoal":   ("#3E4150", "none", 0.0),
    "grey":       ("#9DA3AE", "none", 0.0),
    "grey_light": ("#D5D9E0", "none", 0.0),
    "metal":      ("#B8BEC8", "none", 0.0),
    "gold":       ("#F5C542", "none", 0.0),
    "brick":      ("#D2694B", "noise", 0.4),
    "roof_red":   ("#D9483B", "noise", 0.3),
    "roof_blue":  ("#3F6FC9", "noise", 0.3),
    "roof_grey":  ("#6B7184", "noise", 0.3),
    "stone":      ("#C9C3B6", "noise", 0.8),
    "stone_dark": ("#9E978A", "noise", 0.8),
    "glass":      ("#9BDCF5", "none", 0.0),
    "glass_dark": ("#4E7FA8", "none", 0.0),
    # faces / animals
    "skin":       ("#F6C9A0", "none", 0.0),
    "skin_dark":  ("#B57A55", "none", 0.0),
    "eye_white":  ("#FFFFFF", "none", 0.0),
    "eye_black":  ("#1E1E28", "none", 0.0),
    "cheek":      ("#FF9AA8", "none", 0.0),
    "nose_pink":  ("#F59AA6", "none", 0.0),
    "fur_white":  ("#F7F4EE", "noise", 0.35),
    "fur_brown":  ("#9A6038", "noise", 0.35),
    "fur_tan":    ("#D9A066", "noise", 0.35),
    "fur_black":  ("#3A3640", "noise", 0.35),
    "fur_grey":   ("#A9A6AE", "noise", 0.35),
    "fur_orange": ("#F09A3E", "noise", 0.35),
    "wool":       ("#FBF8F0", "noise", 0.6),
    "hoof":       ("#4A3A33", "none", 0.0),
    "beak":       ("#FFB330", "none", 0.0),
    "comb":       ("#E8364A", "none", 0.0),
}


def srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def detail_alpha(kind, strength):
    if kind == "noise":
        return max(0.01, min(0.5, 0.5 * strength))
    if kind == "grain":
        return 0.5 + max(0.01, min(0.5, 0.5 * strength))
    return 0.0


# ------------------------------------------------------------------------------------------------ scene
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    if scene.world is None:
        scene.world = bpy.data.worlds.new("World")
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 1.0
    return scene


def mat(name, hexstr=None, detail=None, strength=None):
    """Material by palette name (or a custom hex). Custom props drive the vertex colour bake."""
    key = name if hexstr is None else f"{name}"
    m = bpy.data.materials.get(key)
    if m is not None:
        return m
    if hexstr is None:
        hexstr, detail, strength = PALETTE[name]
    m = bpy.data.materials.new(key)
    r, g, b = hex_rgb(hexstr)
    m["tt_srgb"] = (r, g, b)
    m["tt_alpha"] = detail_alpha(detail or "none", strength or 0.0)
    m.diffuse_color = (srgb_to_linear(r), srgb_to_linear(g), srgb_to_linear(b), 1.0)
    try:
        bsdf = m.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs["Base Color"].default_value = m.diffuse_color
    except Exception:
        pass
    return m


def _assign(obj, material):
    if material is None:
        return obj
    if isinstance(material, str):
        material = mat(material)
    obj.data.materials.clear()
    obj.data.materials.append(material)
    return obj


def _link(obj):
    bpy.context.scene.collection.objects.link(obj)
    return obj


def _new_obj(name, bm):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return _link(bpy.data.objects.new(name, me))


# ------------------------------------------------------------------------------------------------ primitives
def rbox(name, size, loc=(0, 0, 0), material=None, bevel=0.05, segments=2, rot=(0, 0, 0)):
    """Rounded box: size (x, y, z) full extents, centred at loc."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts)
    o = _new_obj(name, bm)
    o.location = loc
    o.rotation_euler = Euler(rot)
    _assign(o, material)
    if bevel > 0:
        b = min(bevel, min(size) * 0.49)
        mod = o.modifiers.new("bevel", 'BEVEL')
        mod.width = b
        mod.segments = segments
        mod.limit_method = 'NONE'
        mod.harden_normals = False
    return o


def cyl(name, radius, depth, loc=(0, 0, 0), material=None, verts=20, rot=(0, 0, 0), bevel=0.0, segments=2,
        radius_top=None):
    """Cylinder along local Z (use rot to lay it down). radius_top makes a cone/frustum."""
    bm = bmesh.new()
    r2 = radius if radius_top is None else radius_top
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=verts, radius1=radius, radius2=r2, depth=depth)
    o = _new_obj(name, bm)
    o.location = loc
    o.rotation_euler = Euler(rot)
    _assign(o, material)
    if bevel > 0:
        mod = o.modifiers.new("bevel", 'BEVEL')
        mod.width = min(bevel, depth * 0.45, radius * 0.45)
        mod.segments = segments
        mod.limit_method = 'ANGLE'
        mod.angle_limit = math.radians(50)
    smooth(o, 50)
    return o


def sphere(name, radius, loc=(0, 0, 0), material=None, scale=(1, 1, 1), segs=16, rings=10, rot=(0, 0, 0)):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=rings, radius=radius)
    o = _new_obj(name, bm)
    o.location = loc
    o.scale = scale
    o.rotation_euler = Euler(rot)
    _assign(o, material)
    smooth(o, 180)
    return o


def ico(name, radius, loc=(0, 0, 0), material=None, scale=(1, 1, 1), subdiv=2, rot=(0, 0, 0), jitter=0.0, seed=0):
    """Icosphere, optionally jittered (rocks, bushes, leaf clumps)."""
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=radius)
    if jitter > 0:
        rng = np.random.default_rng(seed)
        for v in bm.verts:
            v.co += v.co.normalized() * float(rng.uniform(-jitter, jitter)) * radius
    o = _new_obj(name, bm)
    o.location = loc
    o.scale = scale
    o.rotation_euler = Euler(rot)
    _assign(o, material)
    smooth(o, 180)
    return o


def torus(name, major, minor, loc=(0, 0, 0), material=None, rot=(0, 0, 0), major_segs=24, minor_segs=10):
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor, major_segments=major_segs,
                                     minor_segments=minor_segs, location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = name
    _assign(o, material)
    smooth(o, 180)
    return o


def capsule(name, radius, length, loc=(0, 0, 0), material=None, rot=(0, 0, 0), segs=16):
    """Capsule along local Z: total length includes the hemispherical ends."""
    bm = bmesh.new()
    rings = 8
    half = max(0.0, length / 2 - radius)
    bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=rings * 2, radius=radius)
    for v in bm.verts:
        v.co.z += half if v.co.z > 1e-6 else (-half if v.co.z < -1e-6 else 0)
    o = _new_obj(name, bm)
    o.location = loc
    o.rotation_euler = Euler(rot)
    _assign(o, material)
    smooth(o, 180)
    return o


def prism(name, profile, depth, loc=(0, 0, 0), material=None, rot=(0, 0, 0), bevel=0.0, segments=2):
    """Extrudes a closed 2D profile (list of (x, z) in the XZ plane) along Y by depth, centred.
    Handy for roofs (triangles), arches, signs."""
    bm = bmesh.new()
    front = [bm.verts.new((p[0], -depth / 2, p[1])) for p in profile]
    back = [bm.verts.new((p[0], depth / 2, p[1])) for p in profile]
    n = len(profile)
    bm.faces.new(list(reversed(front)))
    bm.faces.new(back)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((front[i], front[j], back[j], back[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = _new_obj(name, bm)
    o.location = loc
    o.rotation_euler = Euler(rot)
    _assign(o, material)
    if bevel > 0:
        mod = o.modifiers.new("bevel", 'BEVEL')
        mod.width = bevel
        mod.segments = segments
        mod.limit_method = 'ANGLE'
    return o


def sweep(name, path, profile, material=None, closed_profile=True, cap=True, uv_scale=1.0, up=(0, 0, 1)):
    """Sweeps a 2D profile [(across, up), ...] along a 3D polyline (Blender coords). UV: u = across,
    v = distance along the path * uv_scale (so wood grain runs along the path)."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    up = Vector(up)
    path = [Vector(p) for p in path]
    rings = []
    dist = [0.0]
    for i in range(1, len(path)):
        dist.append(dist[-1] + (path[i] - path[i - 1]).length)
    for i, p in enumerate(path):
        if i == 0:
            t = (path[1] - path[0])
        elif i == len(path) - 1:
            t = (path[-1] - path[-2])
        else:
            t = (path[i + 1] - path[i - 1])
        t.normalize()
        side = t.cross(up)
        if side.length < 1e-6:
            side = Vector((1, 0, 0))
        side.normalize()
        nup = side.cross(t).normalized()
        rings.append([bm.verts.new(p + side * a + nup * b) for (a, b) in profile])
    n = len(profile)
    seg = n if closed_profile else n - 1
    for i in range(len(path) - 1):
        for k in range(seg):
            k2 = (k + 1) % n
            f = bm.faces.new((rings[i][k], rings[i][k2], rings[i + 1][k2], rings[i + 1][k]))
            for loop in f.loops:
                vi = (rings[i] + rings[i + 1]).index(loop.vert)
                ring = 0 if vi < n else 1
                kk = vi % n
                loop[uv].uv = (profile[kk][0] * uv_scale + profile[kk][1] * uv_scale, dist[i + ring] * uv_scale)
    if cap and closed_profile:
        bm.faces.new(list(reversed(rings[0])))
        bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = _new_obj(name, bm)
    _assign(o, material)
    return o


def lathe(name, profile, loc=(0, 0, 0), material=None, segs=24, rot=(0, 0, 0)):
    """Revolves a profile [(radius, z), ...] (bottom to top) around Z. Great for funnels, domes, bells, pots."""
    bm = bmesh.new()
    rings = []
    for (r, z) in profile:
        ring = []
        for s in range(segs):
            a = 2 * math.pi * s / segs
            ring.append(bm.verts.new((r * math.cos(a), r * math.sin(a), z)))
        rings.append(ring)
    for i in range(len(rings) - 1):
        for s in range(segs):
            s2 = (s + 1) % segs
            bm.faces.new((rings[i][s], rings[i][s2], rings[i + 1][s2], rings[i + 1][s]))
    if profile[0][0] > 1e-4:
        bm.faces.new(list(reversed(rings[0])))
    if profile[-1][0] > 1e-4:
        bm.faces.new(rings[-1])
    bmesh.remove_doubles(bm, verts=bm.verts, dist=1e-5) if hasattr(bmesh, "remove_doubles") else \
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = _new_obj(name, bm)
    o.location = loc
    o.rotation_euler = Euler(rot)
    _assign(o, material)
    smooth(o, 60)
    return o


# ------------------------------------------------------------------------------------------------ mesh ops
def smooth(obj, angle_deg=40):
    """Smooth shading with sharp edges above the angle (Blender 4.1+ API)."""
    me = obj.data
    for p in me.polygons:
        p.use_smooth = True
    try:
        bpy.context.view_layer.objects.active = obj
        for o in bpy.context.selected_objects:
            o.select_set(False)
        obj.select_set(True)
        bpy.ops.object.shade_smooth_by_angle(angle=math.radians(angle_deg))
    except Exception:
        pass
    return obj


def apply(obj):
    """Applies modifiers and the object transform into the mesh (origin stays at the world origin)."""
    bpy.context.view_layer.objects.active = obj
    for o in bpy.context.selected_objects:
        o.select_set(False)
    obj.select_set(True)
    for m in list(obj.modifiers):
        try:
            bpy.ops.object.modifier_apply(modifier=m.name)
        except Exception as e:
            print("modifier apply failed", obj.name, m.name, e)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    return obj


def boolean(target, cutter, op='DIFFERENCE', keep_cutter=False):
    mod = target.modifiers.new("bool", 'BOOLEAN')
    mod.operation = op
    mod.object = cutter
    mod.solver = 'EXACT'
    bpy.context.view_layer.objects.active = target
    for o in bpy.context.selected_objects:
        o.select_set(False)
    target.select_set(True)
    bpy.ops.object.modifier_apply(modifier=mod.name)
    if not keep_cutter:
        bpy.data.objects.remove(cutter, do_unlink=True)
    return target


def mirror_x(obj):
    """Duplicate mirrored across X=0 (for symmetric pairs like eyes, ears, legs). Returns the copy."""
    c = obj.copy()
    c.data = obj.data.copy()
    _link(c)
    c.location.x = -obj.location.x
    c.rotation_euler = Euler((obj.rotation_euler.x, -obj.rotation_euler.y, -obj.rotation_euler.z))
    c.scale = obj.scale.copy()
    c.name = obj.name + "_R"
    for m in obj.modifiers:
        pass
    return c


def join(objs, name):
    """Applies everything and joins into one mesh object named `name` (origin at world origin)."""
    objs = [o for o in objs if o is not None]
    for o in objs:
        apply(o)
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    if len(objs) > 1:
        bpy.ops.object.join()
    o = bpy.context.active_object
    o.name = name
    o.data.name = name
    return o


def set_origin(obj, point):
    """Moves the object origin to a world point without moving the geometry (pivot for animated parts)."""
    p = Vector(point)
    obj.data.transform(Matrix.Translation(obj.location - p))
    obj.location = p
    return obj


def cube_uv(obj, scale=1.0):
    """Box-projected UVs in world units (for grain/noise detail on parts without a UV map)."""
    me = obj.data
    if me.uv_layers:
        return
    bm = bmesh.new()
    bm.from_mesh(me)
    uv = bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        n = f.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        for loop in f.loops:
            co = loop.vert.co
            if ax == 0:
                loop[uv].uv = (co.y * scale, co.z * scale)
            elif ax == 1:
                loop[uv].uv = (co.x * scale, co.z * scale)
            else:
                loop[uv].uv = (co.x * scale, co.y * scale)
    bm.to_mesh(me)
    bm.free()


# ------------------------------------------------------------------------------------------------ colour + AO bake
def _ensure_cycles(samples=32):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = samples
    try:
        sc.cycles.use_denoising = False
    except Exception:
        pass
    return sc


def paint_vertex_colors(obj):
    """Writes the "Col" corner attribute (linear values; stored as sRGB bytes) from each face's material."""
    me = obj.data
    for a in list(me.color_attributes):
        me.color_attributes.remove(a)
    col = me.color_attributes.new("Col", 'BYTE_COLOR', 'CORNER')
    mats = me.materials
    n = len(me.loops)
    data = np.zeros((n, 4), dtype=np.float32)
    lut = []
    for m in mats:
        if m is None or "tt_srgb" not in m:
            lut.append((0.8, 0.8, 0.8, 0.0))
            continue
        r, g, b = m["tt_srgb"]
        lut.append((srgb_to_linear(r), srgb_to_linear(g), srgb_to_linear(b), float(m["tt_alpha"])))
    if not lut:
        lut = [(0.8, 0.8, 0.8, 0.0)]
    for p in me.polygons:
        c = lut[min(p.material_index, len(lut) - 1)]
        for li in range(p.loop_start, p.loop_start + p.loop_total):
            data[li] = c
    col.data.foreach_set("color", data.ravel())
    me.color_attributes.active_color = col
    me.color_attributes.render_color_index = me.color_attributes.find("Col")
    return col


def bake_ao(objs, samples=48, distance=0.6, strength=0.85, ground=True, ground_z=0.0):
    """Bakes ambient occlusion into a temporary attribute and multiplies it into "Col" (rgb only)."""
    sc = _ensure_cycles(samples)
    sc.world.light_settings.distance = distance
    plane = None
    if ground:
        bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, ground_z - 0.002))
        plane = bpy.context.active_object
        plane.name = "__ao_ground"
    for obj in objs:
        me = obj.data
        if "Col" not in me.color_attributes:
            paint_vertex_colors(obj)
        ao = me.color_attributes.new("AO", 'BYTE_COLOR', 'CORNER')
        me.color_attributes.active_color = ao
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        sc.render.bake.target = 'VERTEX_COLORS'
        try:
            bpy.ops.object.bake(type='AO', target='VERTEX_COLORS')
        except Exception as e:
            print("AO bake failed for", obj.name, e)
            me.color_attributes.remove(ao)
            continue
        n = len(me.loops)
        a = np.zeros(n * 4, dtype=np.float32)
        me.color_attributes["AO"].data.foreach_get("color", a)
        c = np.zeros(n * 4, dtype=np.float32)
        me.color_attributes["Col"].data.foreach_get("color", c)
        a = a.reshape(n, 4)
        c = c.reshape(n, 4)
        occ = 1.0 - strength * (1.0 - np.clip(a[:, 0], 0.0, 1.0))
        c[:, :3] *= occ[:, None]
        me.color_attributes["Col"].data.foreach_set("color", c.ravel())
        me.color_attributes.remove(me.color_attributes["AO"])
        me.color_attributes.active_color = me.color_attributes["Col"]
    if plane is not None:
        bpy.data.objects.remove(plane, do_unlink=True)


def finalize(objs, ao=True, ao_samples=48, ao_distance=0.6, ao_strength=0.85, ground=True, uv_scale=0.5):
    """Paints vertex colours on each final object (after joins), bakes AO with all of them in the scene."""
    for o in objs:
        cube_uv(o, uv_scale)
        paint_vertex_colors(o)
    if ao:
        bake_ao(objs, samples=ao_samples, distance=ao_distance, strength=ao_strength, ground=ground)
    return objs


def stats(objs):
    v = sum(len(o.data.vertices) for o in objs if o.type == 'MESH')
    t = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs if o.type == 'MESH')
    return v, t


# ------------------------------------------------------------------------------------------------ export
def export_fbx(rel_path, objs):
    """Exports the given objects (with children) to Assets/_Project/Art/Models/<rel_path>.fbx."""
    path = os.path.join(MODELS, rel_path + ".fbx")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
        for c in o.children_recursive:
            c.select_set(True)
    bpy.ops.export_scene.fbx(
        filepath=path, use_selection=True, object_types={'MESH', 'EMPTY'},
        apply_scale_options='FBX_SCALE_ALL', bake_space_transform=True,
        mesh_smooth_type='FACE', use_mesh_modifiers=True, colors_type='SRGB', prioritize_active_color=True,
        add_leaf_bones=False, bake_anim=False, use_custom_props=False, path_mode='STRIP', embed_textures=False)
    v, t = stats([o for o in objs] + [c for o in objs for c in o.children_recursive])
    print(f"[TT] exported {rel_path}.fbx verts={v} tris={t}")
    return path


# ------------------------------------------------------------------------------------------------ preview / icons
def _preview_material():
    m = bpy.data.materials.get("__preview")
    if m:
        return m
    m = bpy.data.materials.new("__preview")
    nt = m.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    attr = nt.nodes.new("ShaderNodeVertexColor")
    attr.layer_name = "Col"
    nt.links.new(attr.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.6
    return m


def _bounds(objs):
    pts = []
    for o in objs:
        if o.type != 'MESH':
            continue
        for c in o.bound_box:
            pts.append(o.matrix_world @ Vector(c))
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return mn, mx


def render(objs, out_png, size=(640, 480), yaw_deg=-35.0, pitch_deg=28.0, transparent=False, samples=24,
           use_vertex_colors=True, distance_scale=1.0, ortho=False, sky_color=(0.62, 0.80, 1.0)):
    """Renders the objects with a 3/4 camera that frames them. With use_vertex_colors the render shows exactly the
    baked "Col" colours (what Unity will show). Front of a model (-Y) faces the camera when yaw_deg = 0."""
    sc = _ensure_cycles(samples)
    bpy.context.view_layer.update()
    try:
        sc.cycles.use_denoising = True
    except Exception:
        pass
    sc.render.resolution_x, sc.render.resolution_y = size
    sc.render.film_transparent = transparent
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGBA' if transparent else 'RGB'
    sc.view_settings.view_transform = 'Standard'
    world = sc.world
    world.use_nodes = True if hasattr(world, "use_nodes") else None
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs[0].default_value = (*sky_color, 1.0)
        bg.inputs[1].default_value = 0.9
    saved = {}
    if use_vertex_colors:
        pm = _preview_material()
        for o in objs:
            for x in [o] + list(o.children_recursive):
                if x.type == 'MESH' and "Col" in x.data.color_attributes:
                    saved[x.name] = list(x.data.materials)
                    x.data.materials.clear()
                    x.data.materials.append(pm)
    mn, mx = _bounds([x for o in objs for x in [o] + list(o.children_recursive)])
    centre = (mn + mx) / 2
    radius = max((mx - mn).length / 2, 0.1)
    aspect = size[0] / size[1]
    if aspect < 1.0:
        radius /= aspect
    cam_data = bpy.data.cameras.new("__cam")
    cam_data.lens = 50
    if ortho:
        cam_data.type = 'ORTHO'
        cam_data.ortho_scale = radius * 2.2
    cam = bpy.data.objects.new("__cam", cam_data)
    _link(cam)
    yaw = math.radians(yaw_deg)
    pitch = math.radians(pitch_deg)
    d = radius * 2.9 * distance_scale
    direction = Vector((math.sin(yaw) * math.cos(pitch), -math.cos(yaw) * math.cos(pitch), math.sin(pitch)))
    cam.location = centre + direction * d
    cam.rotation_euler = (-direction).to_track_quat('-Z', 'Y').to_euler()
    sc.camera = cam
    sun_data = bpy.data.lights.new("__sun", 'SUN')
    sun_data.energy = 3.2
    sun_data.angle = math.radians(8)
    sun = bpy.data.objects.new("__sun", sun_data)
    _link(sun)
    sun.rotation_euler = Euler((math.radians(40), math.radians(10), math.radians(-35)))
    os.makedirs(os.path.dirname(out_png), exist_ok=True)
    sc.render.filepath = out_png
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam, do_unlink=True)
    bpy.data.objects.remove(sun, do_unlink=True)
    for o in objs:
        for x in [o] + list(o.children_recursive):
            if x.name in saved:
                x.data.materials.clear()
                for m in saved[x.name]:
                    x.data.materials.append(m)
    print("[TT] rendered", out_png)
    return out_png


def preview_path(name):
    return os.path.join(PREVIEWS, name + ".png")


def args():
    """Arguments after '--' on the blender command line."""
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
