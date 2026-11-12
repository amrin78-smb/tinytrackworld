"""
Tiny Tracks World - extra helpers for the scripted train models (locomotives + wagons).
Builds on tt_common (conventions: front = Blender -Y, up = +Z, model's right = -X, metres).
"""
import math
import bpy
import bmesh
from mathutils import Vector, Matrix, Euler

import tt_common as T

HALF_PI = math.pi / 2

# wheels: centre x = +/-WX, bottom of the wheel at z = WHEEL_BOTTOM (slightly inside the groove)
WX = 0.30
WHEEL_BOTTOM = -0.02
WHEEL_T = 0.07          # wheel thickness along the axle
BUFFER_Z = 0.35         # common buffer / coupler height for every vehicle

# extra materials (name: hex, detail, strength)
EXTRA = {
    "coal":      ("#26262C", "noise", 0.8),
    "lens":      ("#FFF4B8", "none", 0.0),
    "mouth":     ("#7A2633", "none", 0.0),
    "tongue":    ("#FF7F8E", "none", 0.0),
    "rubber":    ("#34353D", "none", 0.0),
    "brass":     ("#E8B33A", "none", 0.0),
    "steel":     ("#8E96A3", "none", 0.0),
    "face":      ("#FFF3DF", "none", 0.0),
    "eye_rim":   ("#3A3340", "none", 0.0),
    "red_deep":  ("#A8232F", "none", 0.0),
    "navy":      ("#173E7A", "none", 0.0),
    "teal":      ("#2FC1C9", "none", 0.0),
    "lime":      ("#9BE15D", "none", 0.0),
    "olive":     ("#1F6E3C", "none", 0.0),
    "sun":       ("#FFB21F", "none", 0.0),
    "orange_dk": ("#E06A12", "none", 0.0),
    "plank":     ("#C98D52", "grain", 0.8),
    "plank_dk":  ("#9C6537", "grain", 0.8),
    "log_end":   ("#EBC890", "grain", 0.5),
    "glass_hi":  ("#D9F3FF", "none", 0.0),
    "beacon":    ("#FF9A1F", "none", 0.0),
    "lemon":     ("#FFDA45", "none", 0.0),
    # Purple Starlight
    "violet":    ("#8E5CE6", "none", 0.0),
    "violet_dk": ("#6A3FC0", "none", 0.0),
    "midnight":  ("#232A63", "none", 0.0),
    "star":      ("#FFD23F", "none", 0.0),
}


def M(name):
    if name in EXTRA:
        h, k, s = EXTRA[name]
        return T.mat(name, h, k, s)
    return T.mat(name)


def mats_on(obj, names):
    obj.data.materials.clear()
    for n in names:
        obj.data.materials.append(M(n))


# ------------------------------------------------------------------------------------------------ primitives
def box(name, size, loc, mat, bevel=0.02, segments=None, rot=(0, 0, 0)):
    if segments is None:
        segments = 2 if min(size) >= 0.09 else 1
    if min(size) < 0.03:
        bevel = min(bevel, 0.004)
    o = T.rbox(name, size, loc=loc, material=M(mat), bevel=bevel, segments=segments, rot=rot)
    T.smooth(o, 35)
    return o


def cyl_y(name, r, length, y, z, x=0.0, mat="red", verts=24, bevel=0.0, r_top=None):
    """Cylinder whose axis runs along Y, centred at (x, y, z)."""
    return T.cyl(name, r, length, loc=(x, y, z), material=M(mat), verts=verts, rot=(HALF_PI, 0, 0),
                 bevel=bevel, radius_top=r_top)


def cyl_x(name, r, length, x, y, z, mat="red", verts=16, bevel=0.0):
    return T.cyl(name, r, length, loc=(x, y, z), material=M(mat), verts=verts, rot=(0, HALF_PI, 0), bevel=bevel)


def cyl_z(name, r, length, x, y, z, mat="red", verts=16, bevel=0.0, r_top=None):
    return T.cyl(name, r, length, loc=(x, y, z), material=M(mat), verts=verts, bevel=bevel, radius_top=r_top)


def ball(name, r, loc, mat, segs=10, rings=6, scale=(1, 1, 1)):
    return T.sphere(name, r, loc=loc, material=M(mat), segs=segs, rings=rings, scale=scale)


def lathe_m(name, profile, mats, segs=24, loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1), smooth_angle=55):
    """Multi-material lathe around local Z. profile: [(r, z, mat_index)], band i..i+1 uses point i's index.
    r == 0 makes a pole (no degenerate faces)."""
    bm = bmesh.new()
    rings = []
    for (r, z, _mi) in profile:
        if r < 1e-6:
            v = bm.verts.new((0, 0, z))
            rings.append([v] * segs)
        else:
            rings.append([bm.verts.new((r * math.cos(2 * math.pi * s / segs), r * math.sin(2 * math.pi * s / segs), z))
                          for s in range(segs)])
    for i in range(len(rings) - 1):
        mi = profile[i][2]
        for s in range(segs):
            s2 = (s + 1) % segs
            vs = [rings[i][s], rings[i][s2], rings[i + 1][s2], rings[i + 1][s]]
            uniq = []
            for v in vs:
                if v not in uniq:
                    uniq.append(v)
            if len(uniq) >= 3:
                f = bm.faces.new(uniq)
                f.material_index = mi
    if profile[0][0] > 1e-6:
        f = bm.faces.new(list(reversed(rings[0])))
        f.material_index = profile[0][2]
    if profile[-1][0] > 1e-6:
        f = bm.faces.new(rings[-1])
        f.material_index = profile[-2][2] if len(profile) > 1 else profile[-1][2]
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    for n in mats:  # materials first: clearing them later would reset the face material indices
        me.materials.append(M(n))
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = Euler(rot)
    o.scale = scale
    T.smooth(o, smooth_angle)
    return o


def lathe_y(name, profile, mats, x, y, z, segs=24, scale_z=1.0, scale_x=1.0, smooth_angle=55):
    """Lathe whose axis runs along Y; profile z = distance towards the FRONT (-Y) from y."""
    # rot X +90deg: local +Z -> world -Y, local +Y -> world +Z
    return lathe_m(name, profile, mats, segs=segs, loc=(x, y, z), rot=(HALF_PI, 0, 0),
                   scale=(scale_x, scale_z, 1.0), smooth_angle=smooth_angle)


def rr_points(w, h, r, n=4):
    """Rounded rectangle outline (CCW) centred at 0 in a 2D plane, as [(a, b)]."""
    r = min(r, w / 2, h / 2)
    pts = []
    corners = [(w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180),
               (w / 2 - r, -h / 2 + r, 270)]
    for (cx, cy, a0) in corners:
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n)
            p = (cx + r * math.cos(a), cy + r * math.sin(a))
            if not pts or (abs(pts[-1][0] - p[0]) > 1e-6 or abs(pts[-1][1] - p[1]) > 1e-6):
                pts.append(p)
    if abs(pts[0][0] - pts[-1][0]) < 1e-6 and abs(pts[0][1] - pts[-1][1]) < 1e-6:
        pts.pop()
    return pts


def _orient(o, facing):
    """Objects are built facing -Y; rotate for facing in {'-Y','+Y','+X','-X','+Z'}."""
    rz = {"-Y": 0.0, "+Y": math.pi, "+X": HALF_PI, "-X": -HALF_PI}.get(facing)
    if rz is not None:
        o.rotation_euler = Euler((0, 0, rz))
    elif facing == "+Z":
        o.rotation_euler = Euler((-HALF_PI, 0, 0))
    return o


def panel(name, w, h, r, depth, loc, mat, facing="-Y", n=3):
    """Flat rounded-rect slab (w across, h up) facing `facing`."""
    o = T.prism(name, rr_points(w, h, r, n), depth, loc=loc, material=M(mat))
    _orient(o, facing)
    T.smooth(o, 30)
    return o


def frame_ring(name, w, h, r, border, depth, loc, mat, facing="-Y", n=3, bulge=0.0):
    """Rounded-rect picture frame (window frames, door outlines). Built in XZ, thickness along Y."""
    outer = rr_points(w, h, r, n)
    inner = rr_points(w - 2 * border, h - 2 * border, max(r - border, 0.004), n)
    assert len(outer) == len(inner), (len(outer), len(inner))
    bm = bmesh.new()
    d = depth / 2
    of = [bm.verts.new((a, -d - bulge, b)) for a, b in outer]
    ob = [bm.verts.new((a, d, b)) for a, b in outer]
    inf = [bm.verts.new((a, -d - bulge, b)) for a, b in inner]
    inb = [bm.verts.new((a, d, b)) for a, b in inner]
    k = len(outer)
    for i in range(k):
        j = (i + 1) % k
        bm.faces.new((of[i], of[j], inf[j], inf[i]))
        bm.faces.new((ob[j], ob[i], inb[i], inb[j]))
        bm.faces.new((of[j], of[i], ob[i], ob[j]))
        bm.faces.new((inf[i], inf[j], inb[j], inb[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    o.location = loc
    mats_on(o, [mat])
    _orient(o, facing)
    T.smooth(o, 30)
    return o


def window(name, w, h, r, loc, facing, frame_mat, glass="glass_dark", border=0.025, depth=0.03, n=3,
           highlight=True):
    """Glass pane + raised frame + a diagonal glint. loc = centre on the wall surface."""
    parts = []
    nrm = {"-Y": Vector((0, -1, 0)), "+Y": Vector((0, 1, 0)), "+X": Vector((1, 0, 0)), "-X": Vector((-1, 0, 0))}[facing]
    c = Vector(loc)
    parts.append(panel(name + "_g", w - border, h - border, max(r - border / 2, 0.004), 0.02, c + nrm * 0.002, glass,
                       facing, n))
    parts.append(frame_ring(name + "_f", w, h, r, border, depth, c + nrm * (depth / 2 - 0.004), frame_mat, facing, n))
    if highlight and w > 0.08:
        # small slanted glint strip on the glass (upper left)
        g = T.prism(name + "_hi", [(-0.012, -h * 0.22), (0.012, -h * 0.22), (0.012 + h * 0.12, h * 0.22),
                                    (-0.012 + h * 0.12, h * 0.22)], 0.012, material=M("glass_hi"))
        side = {"-Y": Vector((1, 0, 0)), "+Y": Vector((-1, 0, 0)), "+X": Vector((0, -1, 0)), "-X": Vector((0, 1, 0))}[facing]
        g.location = c + nrm * 0.012 - side * (w * 0.18) + Vector((0, 0, h * 0.05))
        _orient(g, facing)
        parts.append(g)
    return parts


def round_window(name, r, loc, facing, frame_mat, glass="glass_dark", border=0.022, depth=0.03, segs=18):
    """Porthole / spectacle window."""
    nrm = {"-Y": Vector((0, -1, 0)), "+Y": Vector((0, 1, 0)), "+X": Vector((1, 0, 0)), "-X": Vector((-1, 0, 0))}[facing]
    c = Vector(loc)
    rot = {"-Y": (HALF_PI, 0, 0), "+Y": (HALF_PI, 0, 0), "+X": (0, HALF_PI, 0), "-X": (0, HALF_PI, 0)}[facing]
    g = T.cyl(name + "_g", r - border * 0.5, 0.02, loc=c + nrm * 0.002, material=M(glass), verts=segs - 4, rot=rot)
    f = T.torus(name + "_f", r, border * 0.6, loc=c + nrm * 0.008, material=M(frame_mat), rot=rot,
                major_segs=segs, minor_segs=4)
    hi = T.cyl(name + "_hi", r * 0.22, 0.012, loc=c + nrm * 0.012 + Vector((0, 0, r * 0.35)) +
               (Vector((0, 0, 0))), material=M("glass_hi"), verts=8, rot=rot)
    side = {"-Y": Vector((1, 0, 0)), "+Y": Vector((-1, 0, 0)), "+X": Vector((0, -1, 0)), "-X": Vector((0, 1, 0))}[facing]
    hi.location += -side * r * 0.35
    return [g, f, hi]


def tube(name, path, r, mat, segs=8, up=(0, 0, 1), caps=True):
    prof = [(r * math.cos(2 * math.pi * k / segs), r * math.sin(2 * math.pi * k / segs)) for k in range(segs)]
    o = T.sweep(name, path, prof, material=M(mat), up=up)
    T.smooth(o, 70)
    return o


def arc_path(cx, cz, rx, rz, a0, a1, n, y):
    """Arc in the XZ plane at depth y; angles in degrees (0 = +X, 90 = up)."""
    pts = []
    for k in range(n + 1):
        a = math.radians(a0 + (a1 - a0) * k / n)
        pts.append((cx + rx * math.cos(a), y, cz + rz * math.sin(a)))
    return pts


def handrail(name, pts, mat="brass", r=0.012, post_to=None):
    """Tube along pts; post_to: list of (point_on_rail, point_on_body) for stanchions."""
    parts = [tube(name, pts, r, mat, up=(1, 0, 0) if abs(pts[1][2] - pts[0][2]) > abs(pts[1][1] - pts[0][1]) else (0, 0, 1))]
    for i, (a, b) in enumerate(post_to or []):
        parts.append(tube(f"{name}_p{i}", [a, b], r * 0.8, mat, segs=6,
                          up=(0, 0, 1) if abs(a[2] - b[2]) < 1e-3 else (1, 0, 0)))
        parts.append(ball(f"{name}_k{i}", r * 1.6, a, mat, segs=8, rings=4))
    return parts


def rivet_row(name, p0, p1, n, r=0.012, mat="brass"):
    out = []
    for i in range(n):
        t = i / (n - 1) if n > 1 else 0.5
        p = [p0[k] + (p1[k] - p0[k]) * t for k in range(3)]
        out.append(ball(f"{name}{i}", r, p, mat, segs=5, rings=3))
    return out


# ------------------------------------------------------------------------------------------------ running gear
def wheel(name, side, y, R, rim="rubber", disc="red", hub="brass", spokes=0, spoke_mat=None, segs=20,
          counterweight=None):
    """Wooden-toy wheel, axle along X, outer face pointing away from the centreline. side = +1 (x>0) / -1."""
    t = WHEEL_T / 2
    prof = [
        (0.0, -t, 0),
        (R, -t, 0),
        (R, t - 0.014, 0),
        (R - 0.014, t, 0),
        (R * 0.80, t, 0),
        (R * 0.77, t - 0.016, 1),
        (R * 0.30, t - 0.016, 2),
        (R * 0.27, t + 0.006, 2),
        (R * 0.17, t + 0.022, 2),
        (0.0, t + 0.026, 2),
    ]
    zc = R + WHEEL_BOTTOM
    w = lathe_m(name, prof, [rim, disc, hub], segs=segs, smooth_angle=50)
    parts = [w]
    if spokes:
        for k in range(spokes):
            a = 2 * math.pi * k / spokes
            rr = (R * 0.30 + R * 0.78) / 2
            ln = R * 0.50
            s = T.rbox(f"{name}_s{k}", (0.022, ln, 0.018), loc=(rr * math.cos(a), rr * math.sin(a), t - 0.010),
                       material=M(spoke_mat or disc), bevel=0.0, rot=(0, 0, a - HALF_PI))
            parts.append(s)
    if counterweight:
        # crescent balance weight between rim and hub
        pts = []
        for k in range(6):
            a = math.radians(-50 + 100 * k / 5)
            pts.append((R * 0.76 * math.cos(a), R * 0.76 * math.sin(a)))
        for k in range(5):
            a = math.radians(40 - 80 * k / 4)
            pts.append((R * 0.42 * math.cos(a), R * 0.42 * math.sin(a)))
        cw = T.prism(name + "_cw", pts, 0.02, material=M(counterweight))
        # prism profile is XZ extruded along Y -> rotate so it lies in XY at the outer face
        cw.rotation_euler = Euler((HALF_PI, 0, -HALF_PI))
        cw.location = (0, 0, t - 0.006)
        parts.append(cw)
    w = T.join(parts, name)
    # outer face (+Z) -> +X for the left wheel (side=+1), -X for the right wheel
    w.rotation_euler = Euler((0, HALF_PI * side, 0))
    w.location = (WX * side, y, zc)
    T.apply(w)
    T.set_origin(w, (WX * side, y, zc))
    return w


def wheel_pair(base_index, y, R, **kw):
    return [wheel(f"Wheel_{base_index}", 1, y, R, **kw), wheel(f"Wheel_{base_index + 1}", -1, y, R, **kw)]


def buffer(name, x, y_face, z, direction, stock="charcoal", head="steel"):
    """Sprung buffer on a beam face at y_face, pointing direction (-1 front / +1 rear). Returns parts, tip y."""
    # (segment counts kept low: buffers are small)
    rot = (HALF_PI, 0, 0) if direction < 0 else (-HALF_PI, 0, 0)
    s = lathe_m(name + "_st", [(0.0, 0.0, 0), (0.052, 0.0, 0), (0.052, 0.035, 0), (0.036, 0.04, 1),
                               (0.036, 0.08, 1), (0.0, 0.08, 1)], [stock, head], segs=12, loc=(x, y_face, z), rot=rot)
    h = lathe_m(name + "_hd", [(0.0, 0.0, 0), (0.074, 0.0, 0), (0.078, 0.012, 0), (0.072, 0.026, 0),
                               (0.04, 0.032, 0), (0.0, 0.033, 0)], [head], segs=16,
                loc=(x, y_face + direction * 0.078, z), rot=rot)
    return [s, h], y_face + direction * (0.078 + 0.033)


def coupling_hook(name, y_face, z, direction, mat="charcoal"):
    """Hook + link on the buffer beam centre. Returns parts and tip y."""
    plate = box(name + "_pl", (0.10, 0.02, 0.08), (0, y_face + direction * 0.01, z), mat, bevel=0.008)
    shank = box(name + "_sh", (0.035, 0.07, 0.03), (0, y_face + direction * 0.045, z), mat, bevel=0.008)
    tip = box(name + "_tp", (0.035, 0.025, 0.06), (0, y_face + direction * 0.075, z - 0.015), mat, bevel=0.01)
    return [plate, shank, tip], y_face + direction * 0.09


def lamp(name, x, y, z, direction=-1, body="charcoal", rim="brass", r=0.055):
    """Oil-lamp style headlamp facing direction (-1 = front). Returns parts and lens centre."""
    b = box(name + "_b", (r * 2.0, r * 1.6, r * 2.2), (x, y, z), body, bevel=r * 0.35)
    top = cyl_z(name + "_t", r * 0.55, r * 0.6, x, y, z + r * 1.3, body, verts=12, r_top=r * 0.35)
    rot = (HALF_PI, 0, 0)
    face_y = y + direction * r * 0.8
    ring = T.torus(name + "_r", r * 0.72, r * 0.16, loc=(x, face_y, z), material=M(rim), rot=rot,
                   major_segs=16, minor_segs=4)
    lens = T.cyl(name + "_l", r * 0.66, 0.02, loc=(x, face_y + direction * 0.004, z), material=M("lens"), verts=18,
                 rot=rot)
    return [b, top, ring, lens], (x, face_y + direction * 0.01, z)


# ------------------------------------------------------------------------------------------------ faces
def dome(name, rx, rz, depth, loc, mat, segs=24, rings=5, facing=-1):
    """Half-ellipsoid button on a plane facing -Y (facing=-1) or +Y."""
    prof = [(rx, -0.004, 0)]
    for k in range(1, rings + 1):
        a = HALF_PI * k / rings
        prof.append((rx * math.cos(a) if k < rings else 0.0, depth * math.sin(a), 0))
    o = lathe_m(name, prof, [mat], segs=segs, loc=loc, rot=(HALF_PI if facing < 0 else -HALF_PI, 0, 0),
                scale=(1, rz / rx, 1), smooth_angle=80)
    return o


def friendly_face(prefix, y0, zc, s, brow="eye_rim", cheek="cheek", look=(0.0, 0.0), x0=0.0, eye_sep=0.38,
                  mouth_w=0.26, mouth_d=0.23, eye_scale=1.15):
    """Big-eyed smiling face on a plane at y = y0 facing -Y, centred (x0, zc); s = face half size (m)."""
    P = []
    ex, ez = 0.27 * s * eye_scale, 0.32 * s * eye_scale
    ed = 0.10 * s
    for sd in (1, -1):
        cx = x0 + sd * eye_sep * s
        cz = zc + 0.20 * s
        P.append(dome(f"{prefix}_eyerim{sd}", ex + 0.035 * s, ez + 0.035 * s, ed * 0.35, (cx, y0, cz), "eye_rim", rings=2))
        P.append(dome(f"{prefix}_eye{sd}", ex, ez, ed, (cx, y0 - ed * 0.2, cz), "eye_white", rings=4))
        px = cx - sd * 0.035 * s + look[0] * s
        pz = cz - 0.03 * s + look[1] * s
        prx, prz = 0.155 * s * eye_scale, 0.19 * s * eye_scale
        P.append(dome(f"{prefix}_pup{sd}", prx, prz, ed * 0.45, (px, y0 - ed * 0.2 - ed * 0.78, pz), "eye_black",
                      segs=18, rings=3))
        P.append(dome(f"{prefix}_hl{sd}", 0.055 * s, 0.06 * s, ed * 0.15,
                      (px + 0.06 * s, y0 - ed * 0.2 - ed * 1.18, pz + 0.075 * s), "eye_white", segs=10, rings=2))
        P.append(dome(f"{prefix}_hs{sd}", 0.025 * s, 0.025 * s, ed * 0.1,
                      (px - 0.06 * s, y0 - ed * 0.2 - ed * 1.15, pz - 0.07 * s), "eye_white", segs=8, rings=2))
        # brows: gentle arcs
        bp = arc_path(cx, cz + ez + 0.06 * s, 0.17 * s, 0.07 * s, 30, 150, 8, y0 - 0.008)
        P.append(tube(f"{prefix}_brow{sd}", bp, 0.028 * s, brow, segs=6, up=(0, -1, 0)))
        # cheeks
        P.append(dome(f"{prefix}_ck{sd}", 0.12 * s, 0.09 * s, 0.03 * s, (x0 + sd * 0.64 * s, y0, zc - 0.25 * s), cheek,
                      segs=14, rings=2))
    # open smile (D shape), tongue and a soft lip line
    w = mouth_w * s
    top = zc - 0.22 * s
    lift = 0.06 * s
    d = mouth_d * s
    prof = []
    n = 10
    for k in range(n + 1):
        x = -w + 2 * w * k / n
        prof.append((x, top + lift * (x / w) ** 2))
    for k in range(1, n):
        a = math.pi * k / n
        prof.append((w * math.cos(a), top + lift - d * math.sin(a) - 0.0 * s))
    # profile must be CCW in the XZ plane seen from -Y; prism recalcs normals anyway
    m = T.prism(f"{prefix}_mouth", prof[::-1], 0.02, loc=(x0, y0 - 0.004, 0), material=M("mouth"))
    P.append(m)
    tw, th = 0.13 * s, 0.07 * s
    tc = top + lift - d * 0.62
    tprof = [(tw * math.cos(2 * math.pi * k / 16), tc + th * math.sin(2 * math.pi * k / 16)) for k in range(16)]
    # clip tongue to the mouth bottom so it never pokes out
    clipped = []
    for (x, z) in tprof:
        a = math.acos(max(-1.0, min(1.0, x / w)))
        zmin = top + lift - d * math.sin(a) + 0.012 * s
        clipped.append((x, max(z, zmin)))
    P.append(T.prism(f"{prefix}_tongue", clipped, 0.012, loc=(x0, y0 - 0.014, 0), material=M("tongue")))
    lip = [(x0 + p[0], y0 - 0.012, p[1]) for p in prof[:n + 1]]
    P.append(tube(f"{prefix}_lip", lip, 0.02 * s, "mouth", segs=5, up=(0, -1, 0)))
    for e in (lip[0], lip[-1]):
        P.append(ball(f"{prefix}_dimple{e[0]:.2f}", 0.035 * s, (e[0], y0 - 0.008, e[2]), "mouth", segs=6, rings=3))
    for p in P:
        if p.name.startswith(f"{prefix}_mouth") or p.name.startswith(f"{prefix}_tongue"):
            T.smooth(p, 30)
    return P


# ------------------------------------------------------------------------------------------------ assembly
def make_root(parts, name):
    import os, collections
    dbg = collections.Counter()
    for p in parts:
        T.apply(p)
        key = p.name.split("_")[0].rstrip("0123456789.-")[:10]
        dbg[key] += len(p.data.vertices)
        if p.type == 'MESH' and not p.data.uv_layers:
            T.cube_uv(p, 0.5)
    if os.environ.get("TT_VDEBUG"):
        print("[VDEBUG]", name, dbg.most_common(25))
    return T.join(parts, name)


def add_empty(root, name, loc, size=0.08):
    e = bpy.data.objects.new(name, None)
    e.empty_display_type = 'PLAIN_AXES'
    e.empty_display_size = size
    bpy.context.scene.collection.objects.link(e)
    e.location = loc
    e.parent = root
    e.matrix_parent_inverse = root.matrix_world.inverted()
    return e


def attach(root, child):
    mw = child.matrix_world.copy()
    child.parent = root
    child.matrix_parent_inverse = root.matrix_world.inverted()
    child.matrix_world = mw
    return child


# ------------------------------------------------------------------------------------------------ paint mask
PAINT_UV = "PaintMask"


def add_paint_mask(obj, paint_mats=()):
    """Adds a SECOND UV map "PaintMask" (after the primary "UVMap"): u = 1 on faces whose material is one of
    `paint_mats` (the vehicle's repaintable signature colour), else 0; v = 0. Unity imports it as mesh.uv2
    (UV channel 1). Call after the final join; wheels etc. get an all-zero mask (paint_mats empty)."""
    me = obj.data
    if not me.uv_layers:
        T.cube_uv(obj, 0.5)
    primary = me.uv_layers[0]
    if PAINT_UV in me.uv_layers:
        me.uv_layers.remove(me.uv_layers[PAINT_UV])
    lay = me.uv_layers.new(name=PAINT_UV)
    names = set(paint_mats)
    flags = [1.0 if (m is not None and m.name in names) else 0.0 for m in me.materials] or [0.0]
    import numpy as np
    uv = np.zeros((len(me.loops), 2), dtype=np.float32)
    for p in me.polygons:
        f = flags[min(p.material_index, len(flags) - 1)]
        if f:
            uv[p.loop_start:p.loop_start + p.loop_total, 0] = 1.0
    lay.data.foreach_set("uv", uv.ravel())
    # keep the primary map first + active for render/export
    me.uv_layers.active = primary
    primary.active_render = True
    return int(uv[:, 0].sum())


def star(name, r, loc, facing="-Y", mat="gold", depth=0.02, inner=0.46, points=5, spin=0.0):
    """Chunky five-point star slab (gold decals), built facing -Y then turned to `facing`."""
    prof = []
    for k in range(points * 2):
        a = math.pi / 2 + spin + math.pi * k / points
        rr = r if k % 2 == 0 else r * inner
        prof.append((rr * math.cos(a), rr * math.sin(a)))
    o = T.prism(name, prof, depth, loc=loc, material=M(mat), bevel=min(0.006, depth * 0.3), segments=1)
    _orient(o, facing)
    T.smooth(o, 30)
    return o
