"""
Tiny Tracks World - extra modelling helpers for the animal / people figures (build_creatures.py).
Builds on tt_common (same conventions: front = -Y, up = +Z, model's right = -X, metres).

Main tool is `loft`: smooth organic tubes (bodies, necks, legs, tails, arms) from a few key cross-sections,
interpolated with Catmull-Rom, with optional rounded (dome) ends and per-face paint callbacks (stripes etc.).
"""
import math
import bmesh
import bpy
from mathutils import Vector, Matrix, Euler

import tt_common as T


# ------------------------------------------------------------------------------------------------ palette extras
EXTRA = {
    "navy":        ("#27407A", "noise", 0.15),
    "navy_dark":   ("#1B2D57", "noise", 0.15),
    "denim":       ("#4A78C2", "noise", 0.35),
    "straw":       ("#F2D27A", "noise", 0.7),
    "straw_dark":  ("#D9AE4E", "noise", 0.6),
    "plaid_red":   ("#E04848", "noise", 0.3),
    "skin_mid":    ("#E2A57B", "none", 0.0),
    "hair_brown":  ("#5A3A26", "noise", 0.3),
    "hair_black":  ("#2A2228", "noise", 0.3),
    "hair_ginger": ("#D9772E", "noise", 0.3),
    "boot":        ("#5B3B2A", "none", 0.0),
    "shoe_black":  ("#2E2C33", "none", 0.0),
    "cow_patch":   ("#33302F", "noise", 0.3),
    "cow_muzzle":  ("#F7B3B8", "none", 0.0),
    "horn":        ("#F3E6C8", "none", 0.0),
    "horse":       ("#9A5A33", "noise", 0.3),
    "horse_dark":  ("#4A2E22", "noise", 0.4),
    "ginger":      ("#F2A04C", "noise", 0.35),
    "ginger_dark": ("#D16F25", "noise", 0.35),
    "puppy":       ("#E8B57A", "noise", 0.35),
    "puppy_dark":  ("#A8683C", "noise", 0.35),
    "sheep_face":  ("#4A4148", "noise", 0.2),
    "hen_white":   ("#FBF7EE", "noise", 0.3),
    "hen_leg":     ("#F7B53A", "none", 0.0),
    "bluebird":    ("#3E8FE8", "noise", 0.25),
    "bluebird_dk": ("#2563C0", "noise", 0.25),
    "robin_belly": ("#FF9E5A", "noise", 0.25),
    "mouth":       ("#8E3B46", "none", 0.0),
    "tongue":      ("#FF7A8C", "none", 0.0),
    "collar":      ("#E8423F", "none", 0.0),
    "child_yellow":("#FFD23F", "none", 0.0),
    "child_teal":  ("#2BBFB0", "none", 0.0),
    "child_pink":  ("#FF7FB0", "none", 0.0),
    "hen":         ("#C8743A", "noise", 0.3),
    "hen_dark":    ("#8E4A26", "noise", 0.3),
    "hen_chest":   ("#E39A5C", "noise", 0.3),
    "cat_eye":     ("#8BCB4A", "none", 0.0),
}


def mat(name):
    """Material from the tt_common palette or the creature extras."""
    if name in T.PALETTE:
        return T.mat(name)
    hx, kind, s = EXTRA[name]
    return T.mat(name, hx, kind, s)


def _mats(obj, names):
    obj.data.materials.clear()
    for n in names:
        obj.data.materials.append(mat(n))


# ------------------------------------------------------------------------------------------------ interpolation
def _catmull(p0, p1, p2, p3, t):
    t2, t3 = t * t, t * t * t
    return 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3)


def _interp(keys, res):
    """keys: [(pos, w, h)], returns dense list of (Vector pos, w, h) with `res` steps per span."""
    P = [Vector(k[0]) for k in keys]
    W = [float(k[1]) for k in keys]
    H = [float(k[2]) for k in keys]
    n = len(keys)
    if n == 1:
        return [(P[0], W[0], H[0])]
    out = []
    for i in range(n - 1):
        i0, i3 = max(0, i - 1), min(n - 1, i + 2)
        p0 = P[i0] if i0 != i else P[i] * 2 - P[i + 1]
        p3 = P[i3] if i3 != i + 1 else P[i + 1] * 2 - P[i]
        w0 = W[i0] if i0 != i else W[i]
        w3 = W[i3] if i3 != i + 1 else W[i + 1]
        h0 = H[i0] if i0 != i else H[i]
        h3 = H[i3] if i3 != i + 1 else H[i + 1]
        steps = res if i < n - 2 else res + 1
        for s in range(steps):
            t = s / res
            pos = _catmull(p0, P[i], P[i + 1], p3, t)
            w = max(0.0, _catmull(w0, W[i], W[i + 1], w3, t))
            h = max(0.0, _catmull(h0, H[i], H[i + 1], h3, t))
            out.append((pos, w, h))
    return out


def _se(c, e):
    """superellipse helper: sign(c)*|c|^(2/e)"""
    return math.copysign(abs(c) ** (2.0 / e), c)


def loft(name, keys, segs=16, res=3, materials=("white",), up=(0, 0, 1), dome_start=0.0, dome_end=0.0,
         dome_rings=4, paint=None, exp=2.0, smooth_angle=180, roll=0.0):
    """Smooth tube through key sections.
    keys: [((x,y,z), w, h), ...]  w = half-width along the 'side' axis, h = half-height along the 'up'-ish axis.
    up: reference vector giving the orientation of h (use (0,-1,0) for vertical legs so h is front/back).
    dome_start/_end: length of the rounded end caps (0 = flat cap).
    paint(ring_index, ring_count, seg_index, centre Vector) -> material slot index (into `materials`).
    exp: superellipse exponent (2 = ellipse, >2 = boxier)."""
    rings = _interp(keys, res)
    up = Vector(up)
    # tangents
    tans = []
    for i in range(len(rings)):
        a = rings[max(0, i - 1)][0]
        b = rings[min(len(rings) - 1, i + 1)][0]
        t = (b - a)
        tans.append(t.normalized() if t.length > 1e-9 else Vector((0, -1, 0)))
    # parallel-transported frames (no twisting on curved paths such as tails)
    frames = []
    side = tans[0].cross(up)
    if side.length < 1e-6:
        side = Vector((1, 0, 0)).cross(tans[0])
    side.normalize()
    prev_t = tans[0]
    for t in tans:
        q = prev_t.rotation_difference(t)
        side = (q @ side)
        side = (side - t * side.dot(t)).normalized()
        nup = side.cross(t).normalized()
        prev_t = t
        if roll:
            c, s = math.cos(roll), math.sin(roll)
            frames.append((side * c + nup * s, -side * s + nup * c))
        else:
            frames.append((side, nup))

    # assemble sections incl. domes: list of (centre, side, nup, w, h)
    secs = []
    if dome_start > 0:
        c, w, h = rings[0]
        side, nup = frames[0]
        t = tans[0]
        for k in range(dome_rings, 0, -1):
            ang = (math.pi / 2) * k / dome_rings
            secs.append((c - t * dome_start * math.sin(ang), side, nup, w * math.cos(ang), h * math.cos(ang)))
    for i, (c, w, h) in enumerate(rings):
        secs.append((c, frames[i][0], frames[i][1], w, h))
    if dome_end > 0:
        c, w, h = rings[-1]
        side, nup = frames[-1]
        t = tans[-1]
        for k in range(1, dome_rings + 1):
            ang = (math.pi / 2) * k / dome_rings
            secs.append((c + t * dome_end * math.sin(ang), side, nup, w * math.cos(ang), h * math.cos(ang)))

    bm = bmesh.new()
    vrings = []
    for (c, side, nup, w, h) in secs:
        if w < 1e-5 and h < 1e-5:
            vrings.append([bm.verts.new(c)])
            continue
        ring = []
        for s in range(segs):
            a = 2 * math.pi * s / segs
            x, y = _se(math.cos(a), exp), _se(math.sin(a), exp)
            ring.append(bm.verts.new(c + side * (w * x) + nup * (h * y)))
        vrings.append(ring)
    nr = len(vrings)
    for i in range(nr - 1):
        A, B = vrings[i], vrings[i + 1]
        for s in range(segs):
            s2 = (s + 1) % segs
            if len(A) == 1 and len(B) == 1:
                continue
            if len(A) == 1:
                f = bm.faces.new((A[0], B[s], B[s2]))
            elif len(B) == 1:
                f = bm.faces.new((A[s], A[s2], B[0]))
            else:
                f = bm.faces.new((A[s], A[s2], B[s2], B[s]))
            if paint:
                f.material_index = int(paint(i, nr - 1, s, f.calc_center_median()))
    if len(vrings[0]) > 1:
        f = bm.faces.new(list(reversed(vrings[0])))
        if paint:
            f.material_index = int(paint(0, nr - 1, 0, f.calc_center_median()))
    if len(vrings[-1]) > 1:
        f = bm.faces.new(vrings[-1])
        if paint:
            f.material_index = int(paint(nr - 2, nr - 1, 0, f.calc_center_median()))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    idx = [f.material_index for f in bm.faces]
    o = T._new_obj(name, bm)
    _mats(o, materials)
    # material slots must exist before indices are written (clearing slots resets them)
    o.data.polygons.foreach_set("material_index", idx)
    o.data.update()
    T.smooth(o, smooth_angle)
    return o


# ------------------------------------------------------------------------------------------------ simple shapes
def ell(name, loc, radii, material, segs=16, rings=10, rot=(0, 0, 0)):
    """Ellipsoid (UV sphere scaled), smooth."""
    o = T.sphere(name, 1.0, loc=loc, material=None, scale=radii, segs=segs, rings=rings, rot=rot)
    _mats(o, [material])
    return o


def torus(name, major, minor, loc=(0, 0, 0), material=None, rot=(0, 0, 0), major_segs=24, minor_segs=8):
    o = T.torus(name, major, minor, loc=loc, material=None, rot=rot, major_segs=major_segs, minor_segs=minor_segs)
    if material:
        _mats(o, [material])
    return o


def lathe_solid(name, profile, loc, material, rot=(0, 0, 0), segs=24):
    """Revolved solid (hats, caps) from [(radius, z)] relative to loc; last point on the axis closes the top."""
    o = T.lathe(name, profile, loc=loc, material=None, segs=segs, rot=rot)
    _mats(o, [material])
    return o


def ball(name, loc, r, material, segs=12, rings=8):
    return ell(name, loc, (r, r, r), material, segs, rings)


def tube(name, path, radius, material, segs=8, radius_end=None, dome_start=0.0, dome_end=0.0, res=2,
         up=(0, 0, 1), dome_rings=3):
    """Loft along a path with a constant (or linearly tapering) circular section."""
    n = len(path)
    re = radius if radius_end is None else radius_end
    keys = []
    for i, p in enumerate(path):
        t = i / (n - 1) if n > 1 else 0
        r = radius + (re - radius) * t
        keys.append((p, r, r))
    return loft(name, keys, segs=segs, res=res, materials=(material,), dome_start=dome_start, dome_end=dome_end,
                up=up, dome_rings=dome_rings)


def eye(prefix, loc, r, look, sclera=True, iris="eye_black", pupil_scale=0.72, up=(0, 0, 1)):
    """Big friendly toy eye: (white) + dark pupil + glossy highlight. look = viewing direction (world)."""
    loc = Vector(loc)
    look = Vector(look).normalized()
    upv = Vector(up)
    side = look.cross(upv).normalized()
    upv = side.cross(look).normalized()
    parts = []
    if sclera:
        parts.append(ball(prefix + "_white", loc, r, "eye_white", 12, 7))
        rp = r * pupil_scale
        pc = loc + look * (r * 0.42)
    else:
        rp = r
        pc = loc
    pupil = ball(prefix + "_pupil", pc, rp, iris, 10, 6)
    parts.append(pupil)
    hd = (look * 1.0 + upv * 0.55 + side * 0.35).normalized()
    parts.append(ball(prefix + "_hl", pc + hd * rp * 0.93, rp * 0.26, "eye_white", 6, 4))
    hd2 = (look * 1.0 - upv * 0.35 - side * 0.35).normalized()
    parts.append(ball(prefix + "_hl2", pc + hd2 * rp * 0.96, rp * 0.12, "eye_white", 5, 3))
    return parts


def arc(name, centre, radius, a0, a1, thick, material, axis_side=(1, 0, 0), axis_up=(0, 0, 1), n=8, segs=6):
    """Curved tube on an arc (smiles, eyebrows, handles). Angles in degrees; arc lies in the side/up plane."""
    c = Vector(centre)
    sx, uz = Vector(axis_side), Vector(axis_up)
    pts = []
    for i in range(n + 1):
        a = math.radians(a0 + (a1 - a0) * i / n)
        pts.append(c + sx * (radius * math.cos(a)) + uz * (radius * math.sin(a)))
    return tube(name, pts, thick, material, segs=segs, dome_start=thick, dome_end=thick, res=1, dome_rings=2,
                up=sx.cross(uz))


def shell_patch(name, body, blob, material, offset=0.006):
    """Decal-like coloured patch that follows `body`'s surface exactly: (body pushed out along its normals)
    intersected with `blob`. Gives crisp, curved patch outlines (cow patches, blazes, bellies)."""
    sh = body.copy()
    sh.data = body.data.copy()
    sh.modifiers.clear()
    T._link(sh)
    sh.name = name
    T.apply(sh)
    bm = bmesh.new()
    bm.from_mesh(sh.data)
    bm.normal_update()
    for v in bm.verts:
        v.co += v.normal * offset
    bm.to_mesh(sh.data)
    bm.free()
    _mats(sh, [material])
    _mats(blob, [material])
    T.apply(blob)
    T.boolean(sh, blob, 'INTERSECT')
    T.smooth(sh, 70)
    return sh


def blob(name, loc, radii, rot=(0, 0, 0), jitter=0.18, seed=0, subdiv=3):
    o = T.ico(name, 1.0, loc=loc, scale=radii, rot=rot, subdiv=subdiv, jitter=jitter, seed=seed)
    return o


def mirror(obj):
    """Mirrored copy across X = 0 of the mesh data AND transform (tt_common.mirror_x only mirrors the object
    location, which does nothing for meshes built in place)."""
    T.apply(obj)
    c = obj.copy()
    c.data = obj.data.copy()
    T._link(c)
    c.name = obj.name + "_m"
    c.data.transform(Matrix.Scale(-1, 4, (1, 0, 0)))
    c.data.flip_normals()
    c.data.update()
    return c


def pair(obj):
    return [obj, mirror(obj)]


def parent_keep(child, parent):
    mw = child.matrix_world.copy()
    child.parent = parent
    child.matrix_parent_inverse = parent.matrix_world.inverted()
    child.matrix_world = mw


def part(objs, name, pivot):
    """Joins objs into an animated part named `name` whose origin is the pivot."""
    o = T.join(objs, name)
    T.set_origin(o, pivot)
    return o


def meta(root, parts):
    objs = [root] + parts
    mn, mx = T._bounds(objs)
    rad = max(abs(mn.x), abs(mx.x), abs(mn.y), abs(mx.y))
    v, t = T.stats(objs)
    return {"height": round(mx.z, 3), "footprintRadius": round(rad, 3), "verts": v, "tris": t,
            "size": [round(mx.x - mn.x, 3), round(mx.y - mn.y, 3), round(mx.z - mn.z, 3)]}


def report(objs):
    """Debug: vertex count per source object (before joins)."""
    import collections
    acc = collections.Counter()
    for o in objs:
        dg = bpy.context.evaluated_depsgraph_get()
        acc[o.name.split(".")[0]] += len(o.evaluated_get(dg).data.vertices)
    print("[TT] parts:", dict(acc), "total", sum(acc.values()))
