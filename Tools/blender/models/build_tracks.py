"""
Track pieces for Tiny Tracks World, generated from Tools/blender/track_shapes.json (exported by Unity from
TrackShapeLibrary, the single source of track geometry), so every bed follows the exact path the trains drive.

Wooden toy railway look: a beech bed with rounded edges and two grooves (x = +/-0.25), bed top 0.16 m above the
path (trains ride at path + 0.16). Usage: blender -b --factory-startup --python build_tracks.py -- [Type ...]
Output: Assets/_Project/Art/Models/Tracks/<Type>.fbx (origin = piece origin = entry connector).
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import tt_common as T  # noqa: E402
from mathutils import Vector  # noqa: E402
import numpy as np  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SHAPES = json.load(open(os.path.join(HERE, "..", "track_shapes.json")))["shapes"]

BED_W = 1.0
BED_H = 0.16
GROOVE_X = 0.25
GROOVE_W = 0.11
GROOVE_D = 0.055


def B(p):
    """Unity local (x, y, z) -> Blender (-x, -z, y)."""
    return Vector((-p[0], -p[2], p[1]))


def simplify(points, max_angle=4.0, max_len=1.0):
    """Keeps samples where the direction (incl. slope) turned more than max_angle, or every max_len metres."""
    pts = [B(p) for p in points]
    out = [pts[0]]
    last_dir = (pts[1] - pts[0]).normalized()
    acc = 0.0
    for i in range(1, len(pts) - 1):
        d = (pts[i + 1] - pts[i]).normalized()
        acc += (pts[i] - pts[i - 1]).length
        ang = math.degrees(last_dir.angle(d)) if d.length > 0 and last_dir.length > 0 else 0.0
        if ang > max_angle or acc >= max_len:
            out.append(pts[i])
            last_dir = (pts[i] - out[-2]).normalized() if len(out) > 1 else d
            acc = 0.0
    out.append(pts[-1])
    return out


def extend(path, amount):
    """Lengthens a polyline at both ends (so boolean cutters fully open the groove ends)."""
    a = path[0] - (path[1] - path[0]).normalized() * amount
    b = path[-1] + (path[-1] - path[-2]).normalized() * amount
    return [a] + path + [b]


def rounded_rect(w, h, r, seg=3, bottom=0.0):
    """Profile (across, up) of the bed: flat bottom, rounded top corners. Counter-clockwise."""
    pts = [(-w / 2, bottom), (w / 2, bottom)]
    cx, cy = w / 2 - r, bottom + h - r
    for i in range(seg + 1):
        a = 0 + (math.pi / 2) * i / seg
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    cx = -w / 2 + r
    for i in range(seg + 1):
        a = math.pi / 2 + (math.pi / 2) * i / seg
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def bed(name, path, material="beech", width=BED_W, height=BED_H, bottom=0.0):
    prof = rounded_rect(width, height, 0.045, 3, bottom)
    o = T.sweep(name, path, prof, material=material, uv_scale=0.5)
    T.smooth(o, 35)
    return o


def grooves(path, tag):
    cutters = []
    for gx in (-GROOVE_X, GROOVE_X):
        prof = [(gx - GROOVE_W / 2, BED_H - GROOVE_D), (gx + GROOVE_W / 2, BED_H - GROOVE_D),
                (gx + GROOVE_W / 2, BED_H + 0.2), (gx - GROOVE_W / 2, BED_H + 0.2)]
        c = T.sweep(f"cut_{tag}_{gx}", extend(path, 0.05), prof, material="groove", uv_scale=0.5)
        cutters.append(c)
    return cutters


def track_bed(paths, name, material="beech"):
    """Bed(s) for all paths unioned, then both grooves cut along every path."""
    beds = [bed(f"{name}_bed{i}", p, material) for i, p in enumerate(paths)]
    root = beds[0]
    for other in beds[1:]:
        T.boolean(root, other, 'UNION')
    for i, p in enumerate(paths):
        for c in grooves(p, f"{name}{i}"):
            T.boolean(root, c, 'DIFFERENCE')
    root.name = name
    return root


def slice_off(obj, point, normal):
    """Cuts the mesh with a plane and removes everything on the normal side, filling the cut flat."""
    import bmesh
    T.apply(obj)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    res = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=Vector(point), plane_no=Vector(normal), clear_outer=True)
    cut_edges = [e for e in res["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
    if cut_edges:
        bmesh.ops.holes_fill(bm, edges=cut_edges, sides=0)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(obj.data)
    bm.free()


def offset_path(path, side, up=0.0):
    """Polyline offset sideways (Blender coords) by `side` metres, raised by `up`."""
    out = []
    for i, p in enumerate(path):
        t = (path[min(i + 1, len(path) - 1)] - path[max(i - 1, 0)])
        t.z = 0
        t.normalize()
        s = t.cross(Vector((0, 0, 1))).normalized()
        out.append(p + s * side + Vector((0, 0, up)))
    return out


def point_at(path, frac):
    total = sum((path[i + 1] - path[i]).length for i in range(len(path) - 1))
    target = total * frac
    acc = 0.0
    for i in range(len(path) - 1):
        seg = (path[i + 1] - path[i]).length
        if acc + seg >= target:
            t = (target - acc) / seg if seg > 0 else 0
            return path[i].lerp(path[i + 1], t), (path[i + 1] - path[i]).normalized()
        acc += seg
    return path[-1], (path[-1] - path[-2]).normalized()


def stream(length_across, width, along_offset=0.0, centre=(0, -4, 0)):
    """A little blue stream crossing under a bridge (flat, just above ground) with sandy banks."""
    parts = []
    cx, cy, _ = centre
    parts.append(T.rbox("bank", (length_across, width + 0.8, 0.03), (cx, cy, 0.012), "sand", bevel=0.01, segments=1))
    parts.append(T.rbox("water", (length_across, width, 0.03), (cx, cy, 0.03), "water", bevel=0.01, segments=1))
    return parts


# ------------------------------------------------------------------------------------------------ per type
def build(type_name):
    T.reset()
    shape = SHAPES[type_name]
    paths = [simplify(p["points"]) for p in shape["paths"]]
    extras = []
    root = None

    if type_name in ("EndPiece", "Depot"):
        root = track_bed(paths, type_name)
        end, d = paths[0][-1], (paths[0][-1] - paths[0][-2]).normalized()
        yaw = math.atan2(d.y, d.x) - math.pi / 2
        c = end - d * 0.32
        extras.append(T.rbox("buffer_block", (0.86, 0.3, 0.36), (c.x, c.y, BED_H + 0.18), "red", bevel=0.06,
                             rot=(0, 0, yaw)))
        extras.append(T.rbox("buffer_beam", (1.05, 0.12, 0.16), (c.x - d.x * 0.17, c.y - d.y * 0.17, BED_H + 0.28),
                             "yellow", bevel=0.04, rot=(0, 0, yaw)))
        for sx in (-0.3, 0.3):
            side = Vector((math.cos(yaw), math.sin(yaw), 0)) * sx
            p = c - d * 0.26 + side
            extras.append(T.cyl("pad", 0.08, 0.12, (p.x, p.y, BED_H + 0.28), "black", verts=14,
                                rot=(math.pi / 2, 0, yaw)))

    elif type_name == "WoodenBridge":
        root = track_bed(paths, type_name, "beech")
        p = paths[0]
        # Underside beam following the arch, and railings.
        extras.append(T.sweep("underbeam", p, [(-0.42, -0.12), (0.42, -0.12), (0.42, 0.0), (-0.42, 0.0)], "beech_dark"))
        for side in (-0.58, 0.58):
            rail_path = offset_path(p, side, 0.55)
            extras.append(T.sweep(f"rail{side}", rail_path, [(-0.05, -0.04), (0.05, -0.04), (0.05, 0.04), (-0.05, 0.04)],
                                  "oak"))
            for k in range(9):
                pt, _ = point_at(offset_path(p, side, 0.0), k / 8.0)
                extras.append(T.cyl(f"post{side}{k}", 0.055, 0.6, (pt.x, pt.y, pt.z + 0.3), "oak", verts=10))
        # Trestle legs at the quarter points.
        for frac in (0.3, 0.7):
            pt, d = point_at(p, frac)
            yaw = math.atan2(d.y, d.x)
            for side in (-0.4, 0.4):
                s = Vector((-math.sin(yaw), math.cos(yaw), 0)) * side
                q = pt + s
                h = max(0.05, pt.z - 0.1)
                extras.append(T.rbox("leg", (0.14, 0.14, h), (q.x, q.y, h / 2), "beech_dark", bevel=0.03))
        mid, d = point_at(p, 0.5)
        yaw = math.atan2(d.y, d.x)
        extras += stream_cross(mid, yaw, 1.6)

    elif type_name == "StoneBridge":
        root = track_bed(paths, type_name, "beech")
        p = paths[0]
        for side in (-0.62, 0.62):
            # Parapet wall following the hump, from below the bed to 0.35 above it.
            wall = T.sweep(f"wall{side}", offset_path(p, side, 0.0),
                           [(-0.12, -0.55), (0.12, -0.55), (0.12, 0.3), (0.09, 0.34), (-0.09, 0.34), (-0.12, 0.3)], "stone")
            T.smooth(wall, 35)
            extras.append(wall)
        # Arched spandrel: a solid stone body under the bed with an arch cut out.
        body = T.sweep("spandrel", p, [(-0.62, -0.55), (0.62, -0.55), (0.62, 0.0), (-0.62, 0.0)], "stone_dark")
        mid, d = point_at(p, 0.5)
        # Fill to the ground at the ends: a box spanning the whole length up to the low ends of the arch.
        yaw = math.atan2(d.y, d.x)
        arch = T.cyl("arch", 1.0, 3.0, (mid.x, mid.y, -0.25), None, verts=28, rot=(0, math.pi / 2, yaw + math.pi / 2))
        T.boolean(body, arch, 'DIFFERENCE')
        extras.append(body)
        extras += stream_cross(mid, yaw, 1.6)

    elif type_name == "Tunnel":
        root = track_bed(paths, type_name)
        extras += tunnel_parts(paths[0])

    elif type_name == "Ramp":
        root = track_bed(paths, type_name)
        p = paths[0]
        extras.append(T.sweep("underbeam", p, [(-0.42, -0.14), (0.42, -0.14), (0.42, 0.0), (-0.42, 0.0)], "beech_dark"))
        for frac in (0.55, 0.85):
            pt, _ = point_at(p, frac)
            h = pt.z - 0.14
            if h > 0.2:
                extras.append(T.rbox("pier", (0.62, 0.5, h), (pt.x, pt.y, h / 2), "stone", bevel=0.06))
        for side in (-0.56, 0.56):
            extras.append(T.sweep(f"guard{side}", offset_path(p, side, 0.0),
                                  [(-0.05, 0.1), (0.05, 0.1), (0.05, 0.36), (-0.05, 0.36)], "red"))

    elif type_name == "ElevatedStraight":
        root = track_bed(paths, type_name)
        p = paths[0]
        extras.append(T.sweep("underbeam", p, [(-0.42, -0.16), (0.42, -0.16), (0.42, 0.0), (-0.42, 0.0)], "beech_dark"))
        for side in (-0.56, 0.56):
            extras.append(T.sweep(f"guard{side}", offset_path(p, side, 0.0),
                                  [(-0.05, 0.1), (0.05, 0.1), (0.05, 0.36), (-0.05, 0.36)], "red"))

    elif type_name == "Crossing":
        root = track_bed(paths, type_name)
        p = paths[0]
        mid, d = point_at(p, 0.5)
        yaw = math.atan2(d.y, d.x)
        s = Vector((-math.sin(yaw), math.cos(yaw), 0))
        for side in (-1, 1):
            c = mid + s * side * 2.05
            extras.append(T.rbox("road", (2.4, 3.1, 0.12), (c.x, c.y, 0.06), "charcoal", bevel=0.03,
                                 rot=(0, 0, yaw)))
            for k in (-1, 0, 1):
                q = c + s * k * 0.9
                extras.append(T.rbox("dash", (0.14, 0.45, 0.02), (q.x, q.y, 0.125), "white", bevel=0.005,
                                     rot=(0, 0, yaw + math.pi / 2)))
        # Rubber crossing panels between the grooves (sit just above the bed top).
        extras.append(T.rbox("panel", (2.3, 0.36, 0.02), (mid.x, mid.y, BED_H + 0.003), "charcoal", bevel=0.005,
                             rot=(0, 0, yaw)))
        for side in (-1, 1):
            q = mid + s * side * 0.43
            extras.append(T.rbox("panel_o", (2.3, 0.12, 0.02), (q.x, q.y, BED_H + 0.003), "charcoal", bevel=0.005,
                                 rot=(0, 0, yaw)))

    else:
        # Straight, curves, S-curves, junctions, cross, station (platform/building are composed in Unity).
        root = track_bed(paths, type_name)

    parts = [root] + extras
    obj = T.join(parts, type_name)
    T.finalize([obj], ao_samples=32, ao_distance=0.5, ao_strength=0.75)
    T.export_fbx("Tracks/" + type_name, [obj])
    return obj


# ------------------------------------------------------------------------------------------------ tunnel
# Bore (clearance) kept from the first version: 1.6 m wide, straight walls to 1.4 m, round roof to 2.2 m.
BORE_HALF_W = 0.8
BORE_SPRING = 1.4


def _spow(c, e):
    return math.copysign(abs(c) ** e, c)


def tunnel_parts(p):
    """Rounded toy hill over a straight tunnel with a stone voussoir arch at both portals, and a few smooth
    bushes, rocks and flowers on top. All in the piece's own frame (s along the track, x across, z up)."""
    import bmesh
    from mathutils.bvhtree import BVHTree

    total = sum((p[i + 1] - p[i]).length for i in range(len(p) - 1))
    half = total / 2
    mid, d = point_at(p, 0.5)
    yaw = math.atan2(d.y, d.x)
    side = Vector((-math.sin(yaw), math.cos(yaw), 0))

    def W(s, x, z):
        return Vector((mid.x, mid.y, 0.0)) + d * s + side * x + Vector((0, 0, z))

    parts = []

    # --- hill: a loaf of dome-shaped cross-sections along the track. Each section is a full-shouldered arch with a
    # softly flared foot; sections shrink towards both ends with a superellipse (full for most of the length so the
    # hill wraps the portal arches, then rounding down). The ends close to a point at track level, inside the bore.
    A, WD, H = 2.9, 2.45, 2.8           # half-length, half-width, height
    P_ALONG = 4.0                       # along-track roundness (2 = ellipse, higher = fuller)
    E_DOME = 0.8                        # cross-section exponent (< 1 = fuller shoulders)
    FLARE = 0.14                        # extra spread at the foot
    NS, NP = 10, 22                     # stations per half, profile points over the arch
    prof = []
    for i in range(NP + 1):
        th = math.pi * i / NP
        z = _spow(math.sin(th), E_DOME)
        prof.append((_spow(math.cos(th), E_DOME) * (1 + FLARE * (1 - z) ** 3), z))
    bm = bmesh.new()
    stations = []
    for k in range(-NS + 1, NS):
        sk = A * math.sin(0.5 * math.pi * k / NS)
        f = (1 - abs(sk / A) ** P_ALONG) ** (1 / P_ALONG)
        crown = 1.0 + 0.05 * math.cos(math.pi * sk / A)
        stations.append([bm.verts.new(W(sk, WD * f * px, H * f * crown * pz)) for (px, pz) in prof])
    tip0 = bm.verts.new(W(-A, 0, 0))
    tip1 = bm.verts.new(W(A, 0, 0))
    n = len(prof)
    for k in range(len(stations) - 1):
        r0, r1 = stations[k], stations[k + 1]
        for i in range(n):
            i2 = (i + 1) % n
            bm.faces.new((r0[i], r0[i2], r1[i2], r1[i]))
    for i in range(n):
        i2 = (i + 1) % n
        bm.faces.new((tip0, stations[0][i2], stations[0][i]))
        bm.faces.new((tip1, stations[-1][i], stations[-1][i2]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bvh = BVHTree.FromBMesh(bm)
    hill = T._new_obj("hill", bm)
    T._assign(hill, "grass_dark")

    def bore_cutter(lenx, s_c, material=None, half_w=BORE_HALF_W):
        c = W(s_c, 0, 0)
        bore = T.rbox("bore", (lenx, 2 * half_w, BORE_SPRING + 0.1), (c.x, c.y, (BORE_SPRING - 0.1) / 2),
                      material, bevel=0.0, rot=(0, 0, yaw))
        roof = T.cyl("roof", half_w, lenx, (c.x, c.y, BORE_SPRING), material, verts=32,
                     rot=(0, math.pi / 2, yaw))
        T.boolean(bore, roof, 'UNION')
        return bore

    # (inside the hill the bore is 6 cm wider than the arch opening, so no faces coincide with the stones)
    T.boolean(hill, bore_cutter(total + 2, 0.0, "stone_dark", BORE_HALF_W + 0.06), 'DIFFERENCE')
    T.smooth(hill, 50)
    parts.append(hill)

    # --- portals: stone voussoir arches (separate rounded blocks, keystone on top).
    RI, RO, DEPTH, GAP = BORE_HALF_W, BORE_HALF_W + 0.36, 0.5, 0.035
    prism_rot = (0, 0, yaw - math.pi / 2)    # prism local X -> across, local Y -> along the track

    def block(name, profile, s_c, material, depth=DEPTH):
        c = W(s_c, 0, 0)
        o = T.prism(name, profile, depth, (c.x, c.y, 0.0), material, rot=prism_rot, bevel=0.045, segments=1)
        T.smooth(o, 40)
        return o

    for sign in (1, -1):
        s_c = sign * (half - 0.04 - DEPTH / 2)
        # legs: two blocks on each side
        for xs in (-1, 1):
            for z0, z1 in ((0.0, 0.72), (0.72, BORE_SPRING)):
                x0, x1 = xs * RI, xs * RO
                prof = [(min(x0, x1), z0 + GAP / 2), (max(x0, x1), z0 + GAP / 2),
                        (max(x0, x1), z1 - GAP / 2), (min(x0, x1), z1 - GAP / 2)]
                parts.append(block("leg", prof, s_c, "stone" if z0 == 0 else "stone_dark"))
        # arch: 7 wedges over the half circle, the middle one is the bigger keystone
        n = 5
        for k in range(n):
            a0 = math.pi * k / n + GAP / RO
            a1 = math.pi * (k + 1) / n - GAP / RO
            ro = RO + (0.12 if k == n // 2 else 0.0)
            arc = 3
            outer = [(ro * math.cos(a0 + (a1 - a0) * t / arc), BORE_SPRING + ro * math.sin(a0 + (a1 - a0) * t / arc))
                     for t in range(arc + 1)]
            inner = [(RI * math.cos(a1 - (a1 - a0) * t / arc), BORE_SPRING + RI * math.sin(a1 - (a1 - a0) * t / arc))
                     for t in range(arc + 1)]
            mat = "stone_dark" if k == n // 2 else ("stone" if k % 2 == 0 else "stone_dark")
            depth = DEPTH + (0.08 if k == n // 2 else 0.0)
            parts.append(block("arch", outer + inner, s_c + sign * (0.04 if k == n // 2 else 0.0), mat, depth))

    # --- decorations, dropped onto the hill surface.
    def ground(s, x):
        hit = bvh.ray_cast(W(s, x, H + 2.0), Vector((0, 0, -1)))
        return hit[0] if hit[0] is not None else W(s, x, 0.0)

    def bush(tag, s, x, r, material, seed):
        rng = np.random.default_rng(seed)
        g = ground(s, x)
        for k, (ds, dx, rr) in enumerate(((0.0, 0.0, 1.0), (0.55, 0.35, 0.72), (-0.45, 0.42, 0.66))):
            q = ground(s + ds * r, x + dx * r)
            q = Vector((q.x, q.y, max(q.z, g.z - 0.25)))
            sc = r * rr
            parts.append(T.sphere(f"bush{tag}{k}", sc, (q.x, q.y, q.z + sc * 0.45), material,
                                  scale=(1.0, 1.0, 0.86 + 0.1 * float(rng.random())), segs=12, rings=7))

    def rock(tag, s, x, r, seed, material="rock", subdiv=3):
        q = ground(s, x)
        o = T.ico(f"rock{tag}", r, (q.x, q.y, q.z + r * 0.2), material, scale=(1.25, 1.0, 0.72), subdiv=subdiv,
                  jitter=0.05, seed=seed, rot=(0, 0, seed * 0.9))
        parts.append(o)

    def flower(tag, s, x, petal, centre="yellow", r=0.17):
        q = ground(s, x)
        fb = bmesh.new()
        n = 20
        top = fb.verts.new((0, 0, 0.035))
        bot = fb.verts.new((0, 0, 0.0))
        outline_t, outline_b = [], []
        for i in range(n):
            a = 2 * math.pi * i / n
            rr = r * (0.62 + 0.38 * abs(math.cos(2.5 * a)))
            outline_t.append(fb.verts.new((rr * math.cos(a), rr * math.sin(a), 0.035)))
            outline_b.append(fb.verts.new((rr * math.cos(a), rr * math.sin(a), 0.0)))
        for i in range(n):
            i2 = (i + 1) % n
            fb.faces.new((top, outline_t[i], outline_t[i2]))
            fb.faces.new((bot, outline_b[i2], outline_b[i]))
            fb.faces.new((outline_b[i], outline_b[i2], outline_t[i2], outline_t[i]))
        bmesh.ops.recalc_face_normals(fb, faces=fb.faces)
        o = T._new_obj(f"flower{tag}", fb)
        o.location = (q.x, q.y, q.z + 0.01)
        o.rotation_euler = (0, 0, float(ord(tag[0]) % 7))
        T._assign(o, petal)
        T.smooth(o, 40)
        parts.append(o)
        parts.append(T.sphere(f"fc{tag}", r * 0.34, (q.x, q.y, q.z + 0.05), centre, scale=(1, 1, 0.6),
                              segs=6, rings=4))

    bush("a", 0.6, -0.85, 0.5, "leaf", 4)
    bush("b", -1.3, 0.95, 0.4, "leaf_light", 5)
    rock("a", 0.95, 0.75, 0.3, 3)
    rock("b", -0.35, 1.55, 0.2, 8, "rock_dark", subdiv=2)
    flower("a", -0.5, -0.35, "white")
    flower("b", -1.1, -1.25, "pink")
    flower("c", 1.55, -0.15, "yellow", "orange")
    flower("d", 0.15, 0.55, "white")
    return parts


def stream_cross(mid, yaw, width):
    """Stream running across the track under a bridge (perpendicular to the track)."""
    s = Vector((-math.sin(yaw), math.cos(yaw), 0))
    parts = []
    bank = T.rbox("bank", (width + 0.9, 7.0, 0.03), (mid.x, mid.y, 0.012), "sand", bevel=0.01, segments=1,
                  rot=(0, 0, yaw))
    water = T.rbox("water", (width, 7.2, 0.035), (mid.x, mid.y, 0.03), "water", bevel=0.012, segments=1,
                   rot=(0, 0, yaw))
    parts += [bank, water]
    for k, off in enumerate((-2.6, -1.8, 1.9, 2.7)):
        q = mid + s * off + Vector((math.cos(yaw), math.sin(yaw), 0)) * (0.9 if k % 2 else -0.95)
        parts.append(T.ico(f"pebble{k}", 0.16, (q.x, q.y, 0.05), "rock", scale=(1.3, 1, 0.6), subdiv=1, jitter=0.2,
                           seed=k))
    return parts


if __name__ == "__main__":
    names = T.args() or list(SHAPES.keys())
    for n in names:
        o = build(n)
        if os.environ.get("TT_PREVIEW"):
            T.render([o], T.preview_path("Track_" + n), yaw_deg=-30, pitch_deg=45)
