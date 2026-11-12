"""
Tiny Tracks World - helpers for the passengers, cargo items and the cargo yard (build_passengers_cargo.py).
Builds on tt_common / creatures_lib / env_lib (same conventions: front = Blender -Y, up = +Z, model's right = -X,
metres, origin at the ground contact centre). Nothing here changes the behaviour of those modules: extra palette
colours are only ADDED to their lookup tables at runtime, under names they do not use.

Cargo pieces are built as plain part lists (not joined) so the yard can reuse smaller copies of them.
"""
import math

import bpy
import bmesh
import numpy as np
from mathutils import Vector, Matrix

import tt_common as T
import creatures_lib as C
import env_lib as E

# ------------------------------------------------------------------------------------------------ palette extras
PEOPLE_EXTRA = {
    "pc_skin_deep":  ("#8A5636", "none", 0.0),
    "pc_skin_olive": ("#D49A6A", "none", 0.0),
    "pc_skin_fair":  ("#FBDDC4", "none", 0.0),
    "pc_freckle":    ("#D98A5E", "none", 0.0),
    "pc_coral":      ("#FF6B5E", "noise", 0.15),
    "pc_purple":     ("#8E5BD9", "noise", 0.15),
    "pc_lime":       ("#8BD346", "noise", 0.15),
    "pc_mustard":    ("#E8A93A", "noise", 0.45),
    "pc_shirt":      ("#CFE8FF", "noise", 0.1),
    "pc_trouser":    ("#6F6A7E", "noise", 0.25),
    "pc_hat":        ("#3F6E57", "noise", 0.3),
    "pc_hatband":    ("#2B4A3A", "none", 0.0),
    "pc_whitehair":  ("#F1F1EE", "noise", 0.3),
    "pc_magenta":    ("#E8457F", "noise", 0.12),
    "pc_hair_auburn":("#8A3B22", "noise", 0.3),
    "pc_case":       ("#FF9A2E", "none", 0.0),
    "pc_case_dark":  ("#C9661A", "none", 0.0),
    "pc_stick":      ("#7A4E2D", "grain", 0.6),
    "pc_balloon":    ("#F2353F", "none", 0.0),
    "pc_string":     ("#FFFDF5", "none", 0.0),
    "pc_cap":        ("#2E7CE6", "none", 0.0),
    "pc_shoe_sole":  ("#FAFAF5", "none", 0.0),
    "pc_pack":       ("#2BB673", "noise", 0.2),
    "pc_pack_dark":  ("#1E8C57", "noise", 0.2),
}

CARGO_EXTRA = {
    "pc_crate":      ("#E2B47A", "grain", 0.75),
    "pc_crate_dark": ("#B98552", "grain", 0.8),
    "pc_crate_core": ("#7E5634", "grain", 0.4),
    "pc_stencil":    ("#E2463F", "none", 0.0),
    "pc_stencil_lf": ("#3F9E4A", "none", 0.0),
    "pc_bark":       ("#8A5A3B", "noise", 0.7),
    "pc_bark_dark":  ("#6B4229", "noise", 0.7),
    "pc_log_end":    ("#F2D29A", "grain", 0.35),
    "pc_log_ring":   ("#C9965A", "none", 0.0),
    "pc_strap":      ("#E8423F", "noise", 0.15),
    "pc_hay":        ("#F2C85B", "noise", 0.8),
    "pc_hay_dark":   ("#D6A63A", "noise", 0.8),
    "pc_churn":      ("#C9D0DA", "none", 0.0),
    "pc_churn_lid":  ("#A9B2BF", "none", 0.0),
    "pc_plank":      ("#E6BE86", "grain", 0.75),
    "pc_plank2":     ("#DDB17A", "grain", 0.75),
    "pc_crane":      ("#FFCC2E", "none", 0.0),
    "pc_crane_red":  ("#F2474B", "none", 0.0),
    "pc_sign":       ("#FFF1D6", "none", 0.0),
}

# register (runtime only) so C._mats / E.box etc. accept these names
for _k, _v in PEOPLE_EXTRA.items():
    C.EXTRA.setdefault(_k, _v)
    E.EXTRA.setdefault(_k, _v)
for _k, _v in CARGO_EXTRA.items():
    C.EXTRA.setdefault(_k, _v)
    E.EXTRA.setdefault(_k, _v)


def m(name):
    return E.m(name)


# ------------------------------------------------------------------------------------------------ small tools
def empty(name, loc, parent=None, size=0.15):
    """Named empty (marker for Unity) at the world point loc, optionally parented (keeping its world position)."""
    o = bpy.data.objects.new(name, None)
    o.empty_display_type = 'PLAIN_AXES'
    o.empty_display_size = size
    T._link(o)
    bpy.context.view_layer.update()          # parent's matrix_world must be current (fresh set_origin / attach)
    if parent is not None:
        o.parent = parent
    o.matrix_world = Matrix.Translation(Vector(loc))
    return o


def recolor(obj, material):
    obj.data.materials.clear()
    obj.data.materials.append(m(material))
    return obj


def hull2d(points):
    """Convex hull (monotone chain), counter-clockwise."""
    pts = sorted(set((round(p[0], 6), round(p[1], 6)) for p in points))
    if len(pts) <= 2:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, hi = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(hi) >= 2 and cross(hi[-2], hi[-1], p) <= 0:
            hi.pop()
        hi.append(p)
    return lo[:-1] + hi[:-1]


def flat_band(name, loop_pts, width, thick, material):
    """Closed flat strap (rectangular section: `width` across the loop plane, `thick` outwards) along a closed
    polyline lying in a plane."""
    pts = [Vector(p) for p in loop_pts]
    n = len(pts)
    centre = sum(pts, Vector()) / n
    nrm = Vector((0, 0, 0))
    for i in range(n):
        nrm += (pts[i] - centre).cross(pts[(i + 1) % n] - centre)
    nrm.normalize()
    bm = bmesh.new()
    rings = []
    prof = [(0, -width / 2), (thick, -width / 2), (thick, width / 2), (0, width / 2)]
    for i in range(n):
        t = (pts[(i + 1) % n] - pts[i - 1]).normalized()
        out = t.cross(nrm).normalized()
        if out.dot(pts[i] - centre) < 0:
            out = -out
        rings.append([bm.verts.new(pts[i] + out * a + nrm * b) for a, b in prof])
    for i in range(n):
        A, B = rings[i], rings[(i + 1) % n]
        for s in range(4):
            s2 = (s + 1) % 4
            bm.faces.new((A[s], A[s2], B[s2], B[s]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = T._new_obj(name, bm)
    T._assign(o, m(material))
    T.smooth(o, 50)
    return o


def bundle_loop(circles, pad, axis_y, n_per=14):
    """Closed loop hugging a bundle of circles [(x, z, r)] in the XZ plane at y = axis_y (strap around logs)."""
    pts = []
    for (x, z, r) in circles:
        for k in range(n_per * 2):
            a = 2 * math.pi * k / (n_per * 2)
            pts.append((x + (r + pad) * math.cos(a), z + (r + pad) * math.sin(a)))
    h = hull2d(pts)
    # resample evenly so the strap is smooth
    loop = [Vector((p[0], axis_y, p[1])) for p in h]
    L = [(loop[(i + 1) % len(loop)] - loop[i]).length for i in range(len(loop))]
    total = sum(L)
    nseg = 30
    out = []
    acc, i = 0.0, 0
    for k in range(nseg):
        target = total * k / nseg
        while acc + L[i] < target:
            acc += L[i]
            i += 1
        t = (target - acc) / max(L[i], 1e-9)
        out.append(loop[i].lerp(loop[(i + 1) % len(loop)], t))
    return out


# ------------------------------------------------------------------------------------------------ cargo parts
def apple_stencil(prefix, size=0.2):
    """Flat stencilled apple facing -Y at the origin (paint is ~6 mm proud): body, leaf, stem."""
    s = size
    p = []
    for sx in (-1, 1):
        # the two lobes sit at slightly different depths (coplanar overlapping caps would bake dark AO)
        p.append(E.cyl(prefix + "_ap", s * 0.29, 0.008, (sx * s * 0.13, -0.002 if sx > 0 else 0.0, -s * 0.02),
                       "pc_stencil", verts=14, rot=(math.pi / 2, 0, 0)))
    p.append(E.box(prefix + "_stem", (s * 0.06, 0.008, s * 0.2), (0.0, 0, s * 0.3), "pc_crate_core",
                   rot=(0, 0.25, 0)))
    leaf = E.sph(prefix + "_leaf", s * 0.16, (s * 0.15, 0.0, s * 0.33), "pc_stencil_lf", scale=(1.0, 0.04, 0.5),
                 segs=8, rings=4, rot=(0, -0.5, 0))
    p.append(leaf)
    return p


def crate_parts(prefix, size=(0.6, 0.6, 0.5), stencil_faces=("-y", "+y", "-x", "+x"), lid=True, slats=2,
                wood="pc_crate", dark="pc_crate_dark", core="pc_crate_core", stencil=True):
    """Chunky slatted wooden crate standing on z = 0, centred on the origin. Returns parts."""
    W, D, H = size
    p = [E.box(prefix + "_core", (W - 0.06, D - 0.06, H - 0.03), (0, 0, (H - 0.03) / 2 + 0.01), core)]
    gap = 0.025
    sh = (H - 0.06 - gap * (slats - 1)) / slats
    for wall, (nx, ny) in {"-y": (0, -1), "+y": (0, 1), "-x": (-1, 0), "+x": (1, 0)}.items():
        along = W if ny else D
        off = (D / 2 if ny else W / 2) - 0.02
        for j in range(slats):
            zc = 0.04 + sh / 2 + j * (sh + gap)
            if ny:
                p.append(E.box(prefix + "_slat", (along - 0.1, 0.04, sh), (0, ny * off, zc), wood, bevel=0.012))
            else:
                p.append(E.box(prefix + "_slat", (0.04, along - 0.1, sh), (nx * off, 0, zc), wood, bevel=0.012))
    for sx in (-1, 1):
        for sy in (-1, 1):
            p.append(E.box(prefix + "_post", (0.075, 0.075, H), (sx * (W / 2 - 0.035), sy * (D / 2 - 0.035), H / 2),
                           dark, bevel=0.018))
    if lid:
        n = 3
        pw = (W - 0.02) / n
        for k in range(n):
            p.append(E.box(prefix + "_lid", (pw - 0.018, D - 0.02, 0.04), (-W / 2 + 0.01 + pw * (k + 0.5), 0, H - 0.005),
                           wood, bevel=0.012))
        p.append(E.box(prefix + "_batten", (W - 0.04, 0.07, 0.03), (0, 0, H + 0.025), dark, bevel=0.01))
    if stencil:
        st = min(W, D, H) * 0.52
        for wall in stencil_faces:
            ap = apple_stencil(prefix + wall, st)
            out = (D / 2 if wall in ("-y", "+y") else W / 2) + 0.002
            yaw = {"-y": 0, "+y": 180, "-x": -90, "+x": 90}[wall]
            E.place(ap, (0, 0, 0), yaw, (0, -out, 0.04 + sh / 2 + (sh + gap) * 0.5 * (slats - 1)))
            p += ap
    return p


def log_parts(prefix, length, r, loc=(0, 0, 0), segs=12, seed=0, knot=False):
    """A log lying along Y centred at loc: bark body with light chamfered ends and a growth ring on each end."""
    x, y, z = loc
    L = length
    ch = min(0.02, r * 0.2)
    keys = [((x, y - L / 2, z), r * 0.84, r * 0.84), ((x, y - L / 2 + ch, z), r, r),
            ((x, y + L / 2 - ch, z), r, r), ((x, y + L / 2, z), r * 0.84, r * 0.84)]
    rng = np.random.default_rng(seed)

    def paint(i, n, s, c):
        return 1 if (i == 0 or i >= n - 1) else 0
    body = C.loft(prefix + "_log", keys, segs=segs, res=1, materials=("pc_bark", "pc_log_end"),
                  paint=paint, up=(0, 0, 1), smooth_angle=50)
    # flat end caps are painted with the last/first band's index (1 = log end)
    p = [body]
    for e in (-1, 1):
        rr = r * float(rng.uniform(0.45, 0.6))
        t = T.torus(prefix + "_ring", rr, 0.006, (x, y + e * (L / 2 + 0.001), z), m("pc_log_ring"),
                    rot=(math.pi / 2, 0, 0), major_segs=10, minor_segs=3)
        p.append(t)
    if knot:
        p.append(C.tube(prefix + "_knot", [(x + r * 0.6, y + L * 0.12, z + r * 0.6),
                                           (x + r * 1.05, y + L * 0.16, z + r * 1.0)], r * 0.22, "pc_bark",
                        segs=6, radius_end=r * 0.17, dome_end=r * 0.12, dome_rings=2))
    return p


def churn_parts(prefix, loc=(0, 0, 0), h=0.52, r=0.13, band="blue", segs=14, handles=True):
    """Classic milk churn standing at loc (bottom)."""
    x, y, z = loc
    prof = [(r * 0.92, 0.0), (r, 0.02), (r, h * 0.56), (r * 0.62, h * 0.74), (r * 0.5, h * 0.8),
            (r * 0.5, h * 0.86), (r * 0.62, h * 0.88), (r * 0.62, h * 0.93), (r * 0.42, h * 0.97), (0.0, h * 0.975)]
    p = [E.lathe(prefix + "_body", prof, (x, y, z), "pc_churn", segs=segs, smooth_deg=50)]
    p.append(T.torus(prefix + "_band", r * 1.005, 0.02, (x, y, z + h * 0.36), m(band), major_segs=segs, minor_segs=3))
    p.append(E.sph(prefix + "_knob", r * 0.18, (x, y, z + h * 0.99), "pc_churn_lid", scale=(1, 1, 0.7), segs=8,
                   rings=4))
    if handles:
        for sx in (-1, 1):
            p.append(T.torus(prefix + "_handle", 0.03, 0.01, (x + sx * r * 0.78, y, z + h * 0.78), m("pc_churn_lid"),
                             rot=(math.pi / 2, 0, 0), major_segs=10, minor_segs=3))
    return p


def barrel_parts(prefix, loc=(0, 0, 0), h=0.62, r=0.24, wood="oak", hoop="charcoal", segs=14, lid_mat="beech_dark"):
    x, y, z = loc
    prof = [(r * 0.84, 0.0), (r * 0.88, 0.0), (r * 0.97, h * 0.25), (r, h * 0.5), (r * 0.97, h * 0.75), (r * 0.88, h),
            (r * 0.8, h), (r * 0.8, h - 0.025), (0.0, h - 0.025)]
    p = [E.lathe(prefix + "_barrel", prof, (x, y, z), wood, segs=segs, smooth_deg=40)]
    for t in (0.12, 0.88):
        p.append(T.torus(prefix + "_hoop", r * (0.9 + 0.075 * math.sin(math.pi * t)) + 0.004, 0.014,
                         (x, y, z + h * t), m(hoop), major_segs=segs, minor_segs=3))
    return p


def hay_parts(prefix, radius=0.28, width=0.6, segs=18):
    """Round hay bale lying on its side, axis along X, resting on z = 0."""
    R, hw = radius, width / 2
    prof = [(0.0, -hw), (R * 0.55, -hw - 0.005), (R * 0.88, -hw + 0.005), (R * 0.97, -hw + 0.03),
            (R, -hw + 0.08), (R * 1.01, 0.0), (R, hw - 0.08), (R * 0.97, hw - 0.03), (R * 0.88, hw - 0.005),
            (R * 0.55, hw + 0.005), (0.0, hw)]
    wob = lambda i, a: 1.0 + 0.018 * math.sin(a * 7 + i * 1.7) + 0.01 * math.sin(a * 13 + i)
    p = [E.lathe(prefix + "_bale", prof, (0, 0, 0), "pc_hay", segs=segs, radial=wob, smooth_deg=70)]
    for zz in (-hw * 0.5, hw * 0.5):
        p.append(T.torus(prefix + "_twine", R * 1.012, 0.011, (0, 0, zz), m("pc_strap"), major_segs=segs, minor_segs=4))
    # spiral rolled-hay pattern on each end face
    for e in (-1, 1):
        pts = []
        turns, n = 2.3, 30
        for k in range(n + 1):
            t = k / n
            a = e * 2 * math.pi * turns * t
            rr = R * (0.12 + 0.72 * t)
            pts.append((rr * math.cos(a), rr * math.sin(a), e * (hw + 0.006 - 0.012 * t)))
        sp = C.tube(prefix + "_spiral", pts, 0.012, "pc_hay_dark", segs=4, res=1, dome_start=0.01, dome_end=0.01,
                    dome_rings=1)
        p.append(sp)
    # turn the bale so the axis runs along X and it rests on the ground
    for q in p:
        q.matrix_basis = Matrix.Translation((0, 0, R + 0.016)) @ Matrix.Rotation(math.pi / 2, 4, 'Y') @ q.matrix_basis
    return p


def crate_pictogram(prefix, s=0.42, wood="pc_crate", dark="walnut"):
    """Flat crate symbol facing -Y at the origin (for signs): a square with a frame and an X brace."""
    p = [E.box(prefix + "_pf", (s, 0.02, s), (0, 0, 0), wood, bevel=0.01)]
    b = 0.07 * s / 0.42
    for (w, h, x, z) in ((s, b, 0, s / 2 - b / 2), (s, b, 0, -s / 2 + b / 2), (b, s, s / 2 - b / 2, 0),
                         (b, s, -s / 2 + b / 2, 0)):
        p.append(E.box(prefix + "_pfr", (w, 0.03, h), (x, -0.01, z), dark, bevel=0.006))
    d = (s - 2 * b) * math.sqrt(2) * 0.98
    for a in (45, -45):
        p.append(E.box(prefix + "_px", (d, 0.025, b * 0.9), (0, -0.012, 0), dark, rot=(0, math.radians(a), 0)))
    return p
