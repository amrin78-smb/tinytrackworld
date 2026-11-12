"""
Tiny Tracks World - extra helpers for the environment models (nature, buildings, props).
Builds on tt_common (do not duplicate conventions here): front = Blender -Y, up = +Z, model right = -X, metres.

Main ideas:
  * part builders return plain Blender objects; `assemble()` applies them, gives each part a box-projected UV map whose
    V axis runs along the part's longest dimension (so wood grain follows planks/posts/beams) and joins them.
  * `place()` moves a group of parts built in a canonical frame (facing -Y at the origin) onto a wall.
  * extra palette colours are registered through `m()`.
"""
import math
import bmesh
import bpy
import numpy as np
from mathutils import Vector, Matrix, Euler

import tt_common as T

# ------------------------------------------------------------------------------------------------ extra palette
EXTRA = {
    "straw":       ("#F2C85B", "noise", 0.6),
    "straw_dark":  ("#D9A93E", "noise", 0.6),
    "birch":       ("#F4F1E8", "noise", 0.35),
    "roof_green":  ("#4E9E5A", "noise", 0.3),
    "roof_orange": ("#E7743C", "noise", 0.3),
    "roof_teal":   ("#2FA39A", "noise", 0.3),
    "roof_red2":   ("#C23E33", "noise", 0.3),
    "roof_blue2":  ("#34609F", "noise", 0.3),
    "roof_green2": ("#3E8549", "noise", 0.3),
    "roof_orange2":("#CF6430", "noise", 0.3),
    "roof_teal2":  ("#258B83", "noise", 0.3),
    "roof_grey2":  ("#5A5F70", "noise", 0.3),
    "wall_cream":  ("#FFF0C4", "noise", 0.15),
    "wall_yellow": ("#FFDD6E", "noise", 0.15),
    "wall_peach":  ("#FFC49A", "noise", 0.15),
    "wall_mint":   ("#B8EDCB", "noise", 0.15),
    "barn_red":    ("#D8433F", "grain", 0.5),
    "barn_red2":   ("#BF3A37", "grain", 0.5),
    "paint_green": ("#3E9B5C", "none", 0.0),
    "paint_blue":  ("#3C7FD1", "none", 0.0),
    "leaf_birch":  ("#9BD95A", "noise", 0.6),
    "leaf_birch2": ("#C2E86E", "noise", 0.6),
    "pine":        ("#2E9150", "noise", 0.6),
    "pine_light":  ("#4DB462", "noise", 0.6),
    "pine_dark":   ("#21703F", "noise", 0.6),
    "cloud":       ("#FFFFFF", "none", 0.0),
    "cloud_shade": ("#EEF4FF", "none", 0.0),
    "petal_white": ("#FFFFFF", "none", 0.0),
    "lavender":    ("#A77BE8", "none", 0.0),
    "lavender2":   ("#8357CC", "none", 0.0),
    "tulip_red":   ("#F2394A", "none", 0.0),
    "lamp_glow":   ("#FFE9A0", "none", 0.0),
    "moss":        ("#8FCB5A", "noise", 0.6),
}


def m(name):
    if bpy.data.materials.get(name) is not None:
        return bpy.data.materials[name]
    if name in EXTRA:
        h, k, s = EXTRA[name]
        return T.mat(name, h, k, s)
    return T.mat(name)


def _mat_arg(material):
    return m(material) if isinstance(material, str) else material


# thin wrappers so every primitive accepts extra palette names
def box(name, size, loc=(0, 0, 0), material=None, bevel=0.0, segments=1, rot=(0, 0, 0)):
    return T.rbox(name, size, loc, _mat_arg(material), bevel=bevel, segments=segments, rot=rot)


def cyl(name, r, depth, loc=(0, 0, 0), material=None, verts=12, rot=(0, 0, 0), bevel=0.0, segments=1, r_top=None):
    return T.cyl(name, r, depth, loc, _mat_arg(material), verts=verts, rot=rot, bevel=bevel, segments=segments,
                 radius_top=r_top)


def sph(name, r, loc=(0, 0, 0), material=None, scale=(1, 1, 1), segs=10, rings=6, rot=(0, 0, 0)):
    return T.sphere(name, r, loc, _mat_arg(material), scale=scale, segs=segs, rings=rings, rot=rot)


def ico(name, r, loc=(0, 0, 0), material=None, scale=(1, 1, 1), subdiv=2, rot=(0, 0, 0), jitter=0.0, seed=0):
    return T.ico(name, r, loc, _mat_arg(material), scale=scale, subdiv=subdiv, rot=rot, jitter=jitter, seed=seed)


def prism(name, profile, depth, loc=(0, 0, 0), material=None, rot=(0, 0, 0), bevel=0.0, segments=1):
    return T.prism(name, profile, depth, loc, _mat_arg(material), rot=rot, bevel=bevel, segments=segments)


def lathe(name, profile, loc=(0, 0, 0), material=None, segs=16, rot=(0, 0, 0), radial=None, smooth_deg=60):
    """Revolve profile [(r, z)] around Z. radial(ring_index, angle) -> radius multiplier (scallops, wobble)."""
    bm = bmesh.new()
    rings = []
    for i, (r, z) in enumerate(profile):
        if r < 1e-5:
            rings.append([bm.verts.new((0, 0, z))])
            continue
        ring = []
        for s in range(segs):
            a = 2 * math.pi * s / segs
            k = radial(i, a) if radial else 1.0
            ring.append(bm.verts.new((r * k * math.cos(a), r * k * math.sin(a), z)))
        rings.append(ring)
    for i in range(len(rings) - 1):
        A, B = rings[i], rings[i + 1]
        if len(A) == 1 and len(B) == 1:
            continue
        for s in range(segs):
            s2 = (s + 1) % segs
            if len(A) == 1:
                bm.faces.new((A[0], B[s], B[s2]))
            elif len(B) == 1:
                bm.faces.new((A[s], A[s2], B[0]))
            else:
                bm.faces.new((A[s], A[s2], B[s2], B[s]))
    if len(rings[0]) > 1:
        bm.faces.new(list(reversed(rings[0])))
    if len(rings[-1]) > 1:
        bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = T._new_obj(name, bm)
    o.location = loc
    o.rotation_euler = Euler(rot)
    T._assign(o, _mat_arg(material))
    T.smooth(o, smooth_deg)
    return o


def ring_frame(name, w, h, border, depth, loc=(0, 0, 0), material="white", rot=(0, 0, 0), bevel=0.012):
    """Rectangular picture-frame (window/door surround) in the XZ plane, depth along Y, centred at loc."""
    bm = bmesh.new()
    ow, oh, iw, ih = w / 2, h / 2, w / 2 - border, h / 2 - border
    layers = []
    for y in (-depth / 2, depth / 2):
        outer = [bm.verts.new(p) for p in ((-ow, y, -oh), (ow, y, -oh), (ow, y, oh), (-ow, y, oh))]
        inner = [bm.verts.new(p) for p in ((-iw, y, -ih), (iw, y, -ih), (iw, y, ih), (-iw, y, ih))]
        layers.append((outer, inner))
    (fo, fi), (bo, bi) = layers
    for k in range(4):
        k2 = (k + 1) % 4
        bm.faces.new((fo[k], fo[k2], fi[k2], fi[k]))
        bm.faces.new((bo[k], bi[k], bi[k2], bo[k2]))
        bm.faces.new((fo[k], bo[k], bo[k2], fo[k2]))
        bm.faces.new((fi[k], fi[k2], bi[k2], bi[k]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = T._new_obj(name, bm)
    o.location = loc
    o.rotation_euler = Euler(rot)
    T._assign(o, _mat_arg(material))
    if bevel > 0:
        mod = o.modifiers.new("bevel", 'BEVEL')
        mod.width = bevel
        mod.segments = 1
        mod.limit_method = 'ANGLE'
    return o


def strip_mesh(name, bottom, top, thickness, material=None):
    """Thin plate in the XZ plane from paired point lists bottom[i]=(x,z), top[i]=(x,z) (same x usually),
    thickness along Y. Built from quads only, so concave outlines (scallops, arches) triangulate safely."""
    bm = bmesh.new()
    n = len(bottom)
    F = [[bm.verts.new((b[0], -thickness / 2, b[1])), bm.verts.new((t[0], -thickness / 2, t[1]))]
         for b, t in zip(bottom, top)]
    B = [[bm.verts.new((b[0], thickness / 2, b[1])), bm.verts.new((t[0], thickness / 2, t[1]))]
         for b, t in zip(bottom, top)]
    for i in range(n - 1):
        bm.faces.new((F[i][0], F[i + 1][0], F[i + 1][1], F[i][1]))
        bm.faces.new((B[i][0], B[i][1], B[i + 1][1], B[i + 1][0]))
        bm.faces.new((F[i][0], B[i][0], B[i + 1][0], F[i + 1][0]))   # bottom edge
        bm.faces.new((F[i][1], F[i + 1][1], B[i + 1][1], B[i][1]))   # top edge
    bm.faces.new((F[0][0], F[0][1], B[0][1], B[0][0]))
    bm.faces.new((F[-1][0], B[-1][0], B[-1][1], F[-1][1]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = T._new_obj(name, bm)
    T._assign(o, _mat_arg(material))
    return o


def blade(name, base, height, lean, width, material, seed=0, segs=4):
    """Curved, tapered grass blade (triangular section) from base point leaning along the (dx, dy) lean vector."""
    bm = bmesh.new()
    lean = Vector((lean[0], lean[1], 0))
    side = Vector((-lean.y, lean.x, 0)).normalized() if lean.length > 1e-6 else Vector((1, 0, 0))
    rings = []
    for i in range(segs + 1):
        t = i / segs
        c = Vector(base) + Vector((0, 0, height * t)) + lean * (t * t)
        wv = width * (1 - t) + 0.004
        if i == segs:
            rings.append([bm.verts.new(c)])
            break
        fwd = lean.normalized() if lean.length > 1e-6 else Vector((0, 1, 0))
        rings.append([bm.verts.new(c + side * wv), bm.verts.new(c - side * wv), bm.verts.new(c + fwd * wv * 0.6)])
    for i in range(segs):
        A, B = rings[i], rings[i + 1]
        for k in range(3):
            k2 = (k + 1) % 3
            if len(B) == 1:
                bm.faces.new((A[k], A[k2], B[0]))
            else:
                bm.faces.new((A[k], A[k2], B[k2], B[k]))
    bm.faces.new(rings[0])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = T._new_obj(name, bm)
    T._assign(o, _mat_arg(material))
    T.smooth(o, 80)
    return o


# ------------------------------------------------------------------------------------------------ transforms
def place(parts, pos=(0, 0, 0), yaw_deg=0.0, local=(0, 0, 0)):
    """Moves parts (built facing -Y around the origin) by `local`, a yaw about Z, then a translation to pos."""
    M = Matrix.Translation(Vector(pos)) @ Matrix.Rotation(math.radians(yaw_deg), 4, 'Z') @ \
        Matrix.Translation(Vector(local))
    for p in parts:
        p.matrix_basis = M @ p.matrix_basis
    return parts


def mirror_parts(parts, axis=0):
    """Returns mirrored copies (geometry applied) across X=0 (axis 0) or Y=0 (axis 1)."""
    out = []
    for p in parts:
        c = p.copy()
        c.data = p.data.copy()
        T._link(c)
        T.apply(c)
        S = Matrix.Diagonal((-1, 1, 1, 1)) if axis == 0 else Matrix.Diagonal((1, -1, 1, 1))
        c.data.transform(S)
        c.data.flip_normals()
        out.append(c)
    return out


# ------------------------------------------------------------------------------------------------ uv + recolour
def grain_uv(obj, scale=0.5):
    """Box-projected UV (world units) whose V runs along the part's longest axis (wood grain direction)."""
    me = obj.data
    if me.uv_layers:
        return
    if not me.vertices:
        return
    co = np.array([v.co[:] for v in me.vertices])
    ext = co.max(0) - co.min(0)
    g = int(np.argmax(ext))
    bm = bmesh.new()
    bm.from_mesh(me)
    uv = bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        n = f.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        others = [i for i in range(3) if i != ax]
        if g in others:
            vax = g
            uax = [i for i in others if i != g][0]
        else:
            uax, vax = others[0], others[1]
            if vax != 2 and 2 in others:
                uax, vax = vax, 2
        for loop in f.loops:
            c = loop.vert.co
            loop[uv].uv = (c[uax] * scale, c[vax] * scale)
    bm.to_mesh(me)
    bm.free()


def assemble(parts, name):
    parts = [p for p in parts if p is not None]
    for p in parts:
        T.apply(p)
        grain_uv(p)
    return T.join(parts, name)


def tone_by_normal(obj, material, nz_min=None, nz_max=None, axis=2):
    """Re-assigns faces whose normal component (world, after apply) lies in range to `material`."""
    T.apply(obj)
    me = obj.data
    mt = _mat_arg(material)
    idx = list(me.materials).index(mt) if mt.name in [x.name for x in me.materials if x] else None
    if idx is None:
        me.materials.append(mt)
        idx = len(me.materials) - 1
    for p in me.polygons:
        n = p.normal[axis]
        if (nz_min is None or n >= nz_min) and (nz_max is None or n <= nz_max):
            p.material_index = idx
    return obj


def tone_faces(obj, material, pred):
    """pred(polygon) -> bool selects faces to recolour."""
    T.apply(obj)
    me = obj.data
    mt = _mat_arg(material)
    names = [x.name for x in me.materials if x]
    if mt.name in names:
        idx = names.index(mt.name)
    else:
        me.materials.append(mt)
        idx = len(me.materials) - 1
    for p in me.polygons:
        if pred(p):
            p.material_index = idx
    return obj


def attach(child, parent, pivot):
    """Makes an assembled child a sub-object of parent with its origin (pivot) at the world point `pivot`."""
    T.set_origin(child, pivot)
    child.parent = parent
    child.matrix_parent_inverse = parent.matrix_world.inverted()
    return child


# ------------------------------------------------------------------------------------------------ architecture kits
def window(w=0.6, h=0.75, frame="white", glass="glass", shutters=None, flowerbox=None, cross=True, sill=True,
           seed=0, border=0.07, depth=0.09):
    """Window facing -Y centred at the origin (wall surface at y = 0). Returns parts."""
    p = []
    p.append(box("glass", (w - border * 1.4, 0.03, h - border * 1.4), (0, -0.012, 0), glass))
    p.append(ring_frame("frame", w, h, border, depth, (0, -0.015, 0), frame))
    if cross:
        p.append(box("mul_v", (0.045, 0.05, h - border * 1.6), (0, -0.03, 0), frame))
        p.append(box("mul_h", (w - border * 1.6, 0.05, 0.045), (0, -0.03, h * 0.08), frame))
    if sill:
        p.append(box("sill", (w + 0.16, 0.13, 0.055), (0, -0.05, -h / 2 - 0.02), frame, bevel=0.015))
    if shutters:
        sw = w * 0.48
        for sx in (-1, 1):
            x = sx * (w / 2 + sw / 2 + 0.03)
            p.append(box("shutter", (sw, 0.045, h), (x, -0.03, 0), shutters, bevel=0.012))
            for zz in (-h * 0.25, h * 0.25):
                p.append(box("shutter_in", (sw * 0.62, 0.02, h * 0.36), (x, -0.06, zz), shutters, bevel=0.006))
    if flowerbox:
        bz = -h / 2 - 0.15
        p.append(box("fbox", (w + 0.06, 0.18, 0.15), (0, -0.14, bz), "beech_dark", bevel=0.02))
        seed = abs(int(seed))
        rng = np.random.default_rng(seed)
        n = max(3, int(w / 0.17))
        for i in range(n):
            x = -w / 2 + 0.06 + (w - 0.12) * i / (n - 1)
            p.append(ico("leaves", 0.085, (x, -0.15, bz + 0.1), "leaf", subdiv=2, jitter=0.12, seed=seed + i,
                         scale=(1.1, 1, 0.8)))
            if i % 2 == 0 or n <= 3:
                p.append(sph("bloom", 0.042, (x + rng.uniform(-0.03, 0.03), -0.2, bz + 0.15),
                             flowerbox[i % len(flowerbox)], segs=6, rings=4))
    return p


def round_window(r=0.25, frame="white", glass="glass"):
    p = [cyl("rglass", r * 0.86, 0.03, (0, -0.012, 0), glass, verts=16, rot=(math.pi / 2, 0, 0))]
    t = T.torus("rframe", r * 0.92, r * 0.1, (0, -0.02, 0), _mat_arg(frame), rot=(math.pi / 2, 0, 0),
                major_segs=16, minor_segs=6)
    p.append(t)
    p.append(box("rmul_v", (0.04, 0.04, r * 1.7), (0, -0.03, 0), frame))
    p.append(box("rmul_h", (r * 1.7, 0.04, 0.04), (0, -0.03, 0), frame))
    return p


def door(w=0.8, h=1.6, color="red", frame="white", planks=4, handle="gold", step="stone", top_window=False,
         canopy=None):
    """Plank door facing -Y, bottom centre at the origin (wall surface y=0). Returns parts."""
    p = []
    pw = w / planks
    for i in range(planks):
        x = -w / 2 + pw * (i + 0.5)
        p.append(box("plank", (pw - 0.012, 0.05, h), (x, -0.005, h / 2), color, bevel=0.01))
    # z-brace battens
    for zz in (h * 0.2, h * 0.75):
        p.append(box("batten", (w - 0.08, 0.035, 0.08), (0, -0.045, zz), color, bevel=0.01))
    if top_window:
        p.append(box("dglass", (w * 0.5, 0.02, h * 0.18), (0, -0.065, h * 0.88), "glass"))
    bw = 0.08
    p.append(box("jamb", (bw, 0.1, h + bw), (-w / 2 - bw / 2, -0.03, (h + bw) / 2), frame, bevel=0.012))
    p.append(box("jamb", (bw, 0.1, h + bw), (w / 2 + bw / 2, -0.03, (h + bw) / 2), frame, bevel=0.012))
    p.append(box("lintel", (w + bw * 2 + 0.08, 0.12, bw + 0.02), (0, -0.04, h + bw / 2 + 0.01), frame, bevel=0.015))
    p.append(sph("knob", 0.04, (-w / 2 + 0.12, -0.08, h * 0.48), handle, segs=8, rings=6))
    p.append(box("knob_plate", (0.05, 0.02, 0.14), (-w / 2 + 0.12, -0.055, h * 0.48), handle, bevel=0.008))
    if step:
        p.append(box("step", (w + 0.4, 0.38, 0.12), (0, -0.2, 0.06), step, bevel=0.03, segments=2))
    if canopy:
        cw = w + 0.5
        p.append(box("dcanopy", (cw, 0.55, 0.06), (0, -0.3, h + 0.28), canopy, bevel=0.02, rot=(-0.3, 0, 0)))
        for sx in (-1, 1):
            p.append(prism("bracket", [(0, 0), (0.06, 0), (0.06, 0.06), (0, 0.32)], 0.4,
                           (sx * (cw / 2 - 0.1), -0.2, h + 0.0), frame, rot=(0, 0, math.pi / 2)))
    return p


def gable_body(w, d, wall_h, ridge_h, material, ridge_axis="X", bevel=0.03, loc=(0, 0, 0)):
    """House body: box walls + triangular gables in one convex pentagon prism. Footprint w (X) x d (Y)."""
    if ridge_axis == "Y":
        prof = [(-w / 2, 0), (w / 2, 0), (w / 2, wall_h), (0, wall_h + ridge_h), (-w / 2, wall_h)]
        o = prism("body", prof, d, loc, material, bevel=bevel)
    else:
        prof = [(-d / 2, 0), (d / 2, 0), (d / 2, wall_h), (0, wall_h + ridge_h), (-d / 2, wall_h)]
        o = prism("body", prof, w, loc, material, bevel=bevel, rot=(0, 0, math.pi / 2))
    return o


def roof_plane(p_top, p_bot, L, tiles=("roof_red", "roof_red2"), under="oak", thick=0.1, rows=None, eave=0.0,
               barge="white", tile_th=0.05, row_len=0.36, top_ext=0.0):
    """One roof slope in the canonical frame (ridge along X): p_top/p_bot = (y, z) points of the slope's underside
    line (wall-top line). Builds a wooden slab, overlapping tile rows (alternating shades) and barge boards at both
    gable ends. eave extends the slope past p_bot, top_ext past p_top. Returns parts."""
    a = Vector((0, p_top[0], p_top[1]))
    b = Vector((0, p_bot[0], p_bot[1]))
    d = (b - a).normalized()
    a = a - d * top_ext
    b = b + d * eave
    n = Vector((0, -d.z, d.y))
    if n.z < 0:
        n = -n
    slope = (b - a).length
    parts = []
    th = math.atan2(d.z, d.y)
    parts.append(box("roofslab", (L, slope, thick), a + d * (slope / 2) + n * (thick / 2), under, bevel=0.025,
                     rot=(th, 0, 0)))
    if tiles:
        nr = rows or max(3, int(round(slope / row_len)))
        rl = slope / nr
        delta = math.radians(4.0)
        # tilt each row a little flatter than the slope so its lower edge lifts (overlapping shingle look)
        sgn = 1 if d.y >= 0 else -1
        ang = math.atan2(-d.z, abs(d.y)) - delta
        d2 = Vector((0, sgn * math.cos(ang), -math.sin(ang)))
        n2 = Vector((0, -d2.z, d2.y))
        if n2.z < 0:
            n2 = -n2
        for i in range(nr):
            s0 = i * rl - (0.02 if i else 0.0)
            up_pt = a + d * s0 + n * thick
            rlen = rl * 1.18 + (0.03 if i == nr - 1 else 0)
            cc = up_pt + d2 * (rlen / 2) + n2 * (tile_th / 2)
            parts.append(box("tiles", (L + 0.06, rlen, tile_th), cc, tiles[i % 2], bevel=0.02, segments=1,
                             rot=(math.atan2(d2.z, d2.y), 0, 0)))
    if barge:
        for sx in (-1, 1):
            bc = a + d * (slope / 2) + n * (thick * 0.5)
            bc.x = sx * (L / 2 + 0.03)
            parts.append(box("barge", (0.06, slope + 0.04, 0.2), bc, barge, bevel=0.015, rot=(th, 0, 0)))
    return parts


def gable_roof(length, span, wall_h, pitch_deg, overhang=0.3, eave=0.35, ridge_axis="X", tiles=("roof_red",
               "roof_red2"), under="oak", rows=None, trim="white", thick=0.1, centre=(0, 0), ridge_cap=True,
               barge=True, z0=0.0):
    """Gable roof. length = building length along the ridge, span = building width across the ridge.
    Wooden slab per side, overlapping tile rows, ridge cap and barge boards. Returns (parts, ridge_z)."""
    a = math.radians(pitch_deg)
    hd = span / 2
    ridge_z = wall_h + hd * math.tan(a)
    L = length + overhang * 2
    parts = []
    for sgn in (-1, 1):
        parts += roof_plane((0, ridge_z), (sgn * hd, wall_h), L, tiles, under, thick, rows, eave,
                            trim if barge else None)
    if ridge_cap:
        parts.append(cyl("ridge", 0.1, L + 0.12, (0, 0, ridge_z + thick / math.cos(a) + 0.03), tiles[1], verts=10,
                         rot=(0, math.pi / 2, 0)))
    place(parts, (centre[0], centre[1], z0), 90 if ridge_axis == "Y" else 0)
    return parts, ridge_z + z0


def chimney(x, y, z_base, height, w=0.42, material="brick", cap="stone"):
    p = [box("chimney", (w, w, height), (x, y, z_base + height / 2), material, bevel=0.025)]
    p.append(box("chimcap", (w + 0.12, w + 0.12, 0.1), (x, y, z_base + height + 0.03), cap, bevel=0.03))
    p.append(cyl("chimpot", 0.09, 0.2, (x, y, z_base + height + 0.16), "roof_red2", verts=10, bevel=0.02))
    return p


def plinth(w, d, h=0.3, material="stone", out=0.06):
    return box("plinth", (w + out * 2, d + out * 2, h), (0, 0, h / 2), material, bevel=0.04, segments=2)


def corner_trims(w, d, z0, z1, material="white", t=0.1, cx=0.0, cy=0.0):
    p = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            p.append(box("cornertrim", (t, t, z1 - z0), (cx + sx * (w / 2), cy + sy * (d / 2), (z0 + z1) / 2),
                         material, bevel=0.015))
    return p


# ------------------------------------------------------------------------------------------------ preview
_GROUND = None


def preview(objs, name, high=True, size=(640, 480), ground=True, dist=1.2):
    """3/4 render plus a high game-camera render (pitch 50) of the given roots, on a soft grass disc."""
    g = None
    if ground:
        mn, mx = T._bounds([x for o in objs for x in [o] + list(o.children_recursive)])
        r = max(mx.x - mn.x, mx.y - mn.y) * 1.0 + 1.0
        bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=r, depth=0.02,
                                            location=((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, -0.012))
        g = bpy.context.active_object
        g.name = "__preview_ground"
        gm = bpy.data.materials.get("__ground") or bpy.data.materials.new("__ground")
        gm.diffuse_color = (0.32, 0.62, 0.20, 1)
        try:
            gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.30, 0.60, 0.18, 1)
            gm.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.9
        except Exception:
            pass
        g.data.materials.append(gm)
    out = [T.render(objs, T.preview_path(name), size=size, distance_scale=dist)]
    if high:
        out.append(T.render(objs, T.preview_path(name + "_High"), size=size, pitch_deg=50, yaw_deg=-25,
                            distance_scale=dist))
    if g is not None:
        bpy.data.objects.remove(g, do_unlink=True)
    return out


# ------------------------------------------------------------------------------------------------ smooth blobs
def _ray_ellipsoid_far(o, d, c, r, s):
    """Far intersection distance of ray o + t d with an axis-aligned ellipsoid (centre c, radius r, scale s)."""
    S = np.array(s) * r
    oo = (o - c) / S
    dd = d / S
    a = dd @ dd
    b = 2 * oo @ dd
    cc = oo @ oo - 1
    disc = b * b - 4 * a * cc
    if disc < 0:
        return None
    return (-b + math.sqrt(disc)) / (2 * a)


def blob(name, spheres, material, subdiv=3, centre=None, smooth_iter=3, noise=0.0, seed=0, flat_bottom=None,
         bottom_squash=0.0):
    """One smooth, seamless mesh shaped like the union of ellipsoids [(centre, radius, scale)] (a 'cloud' of clumps).
    A regular icosphere is pushed out along rays from `centre` to the union surface, then the radial distances are
    relaxed `smooth_iter` times so the creases between clumps become soft rounded valleys. Optional per-vertex noise.
    flat_bottom: z below which the surface is squashed toward that plane (clouds, rocks)."""
    sp = [(np.array(c, float), float(r), np.array(s, float)) for c, r, s in spheres]
    if centre is None:
        w = np.array([r ** 3 for _, r, _ in sp])
        centre = sum(c * wi for (c, _, _), wi in zip(sp, w)) / w.sum()
    centre = np.array(centre, float)
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=1.0)
    bm.verts.ensure_lookup_table()
    dirs = np.array([v.co.normalized()[:] for v in bm.verts])
    dist = np.zeros(len(dirs))
    for i, d in enumerate(dirs):
        best = 0.05
        for c, r, s in sp:
            t = _ray_ellipsoid_far(centre, d, c, r, s)
            if t is not None and t > best:
                best = t
        dist[i] = best
    nbr = [[e.other_vert(v).index for e in v.link_edges] for v in bm.verts]
    for _ in range(smooth_iter):
        nd = dist.copy()
        for i, nb in enumerate(nbr):
            avg = sum(dist[j] for j in nb) / len(nb)
            nd[i] = dist[i] * 0.45 + avg * 0.55 if avg > dist[i] else dist[i] * 0.8 + avg * 0.2
        dist = nd
    if noise > 0:
        R = np.random.default_rng(seed)
        dist *= 1.0 + R.uniform(-noise, noise, len(dist))
    for v, d, t in zip(bm.verts, dirs, dist):
        p = centre + d * t
        if flat_bottom is not None and p[2] < flat_bottom:
            p[2] = flat_bottom + (p[2] - flat_bottom) * bottom_squash
        v.co = Vector(p)
    o = T._new_obj(name, bm)
    T._assign(o, _mat_arg(material))
    for p in o.data.polygons:
        p.use_smooth = True
    return o


def gradient(obj, bottom=0.78, top=1.12, z0=None, z1=None, normal_mix=0.5, tint_top=None, only_mat=None):
    """Multiplies the finalized 'Col' rgb by a soft light gradient (height + normal facing up) - stylised foliage
    shading without hard face-colour borders. Call after T.finalize()."""
    me = obj.data
    n = len(me.loops)
    c = np.zeros(n * 4, dtype=np.float32)
    me.color_attributes["Col"].data.foreach_get("color", c)
    c = c.reshape(n, 4)
    zs = np.array([me.vertices[l.vertex_index].co.z for l in me.loops]) + obj.matrix_world.translation.z
    nz = np.array([me.vertices[l.vertex_index].normal.z for l in me.loops])
    lo = zs.min() if z0 is None else z0
    hi = zs.max() if z1 is None else z1
    h = np.clip((zs - lo) / max(hi - lo, 1e-4), 0, 1)
    f = (1 - normal_mix) * h + normal_mix * (nz * 0.5 + 0.5)
    f = f * f * (3 - 2 * f)
    k = bottom + (top - bottom) * f
    mask = np.ones(n, dtype=bool)
    if only_mat is not None:
        names = [mm.name if mm else "" for mm in me.materials]
        pm = np.zeros(n, dtype=bool)
        for p in me.polygons:
            if names[p.material_index] == only_mat:
                pm[p.loop_start:p.loop_start + p.loop_total] = True
        mask = pm
    c0 = c.copy()
    c[:, :3] = np.clip(c[:, :3] * k[:, None], 0, 1)
    if tint_top is not None:
        t = np.array(tint_top, dtype=np.float32)
        w = np.clip((f - 0.6) / 0.4, 0, 1)[:, None] * 0.35
        c[:, :3] = c[:, :3] * (1 - w) + t[None, :] * w
    c[~mask] = c0[~mask]
    me.color_attributes["Col"].data.foreach_set("color", c.ravel())


# ------------------------------------------------------------------------------------------------ wall placement
YAW = {"-y": 0, "+y": 180, "+x": 90, "-x": -90}


def put(parts, wall, w, d, u, z, cx=0.0, cy=0.0, out=0.0):
    """Puts parts built facing -Y at the origin onto a wall of a w x d footprint centred at (cx, cy).
    wall: '-y' front, '+y' back, '+x', '-x'. u = offset along the wall (local X), z = height, out = push outwards."""
    fp = {"-y": (cx, cy - d / 2), "+y": (cx, cy + d / 2), "+x": (cx + w / 2, cy), "-x": (cx - w / 2, cy)}[wall]
    return place(parts, (fp[0], fp[1], 0), YAW[wall], (u, -out, z))


def sweep_fix(name, path, profile, material=None, side=(1, 0, 0)):
    """Sweeps a 2D profile [(a, b)] along a polyline lying in a plane, with a FIXED side axis (no twisting):
    a runs along `side`, b along side x tangent. Caps both ends. UV v = distance along the path (grain)."""
    side = Vector(side).normalized()
    path = [Vector(p) for p in path]
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    dist = [0.0]
    for i in range(1, len(path)):
        dist.append(dist[-1] + (path[i] - path[i - 1]).length)
    rings = []
    for i, p in enumerate(path):
        t = (path[min(i + 1, len(path) - 1)] - path[max(i - 1, 0)]).normalized()
        nrm = side.cross(t).normalized()
        rings.append([bm.verts.new(p + side * a + nrm * b) for (a, b) in profile])
    n = len(profile)
    for i in range(len(path) - 1):
        for k in range(n):
            k2 = (k + 1) % n
            f = bm.faces.new((rings[i][k], rings[i][k2], rings[i + 1][k2], rings[i + 1][k]))
            for loop, (kk, ii) in zip(f.loops, ((k, i), (k2, i), (k2, i + 1), (k, i + 1))):
                loop[uv].uv = ((profile[kk][0] + profile[kk][1]) * 0.5, dist[ii] * 0.5)
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = T._new_obj(name, bm)
    T._assign(o, _mat_arg(material))
    T.smooth(o, 40)
    return o
