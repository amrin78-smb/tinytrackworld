"""
Tiny Tracks World - environment models (nature, buildings, props) for Sunny Valley.

Run:  blender -b --factory-startup --python Tools/blender/models/build_env.py -- [Name ...] [--no-preview] [--no-lineup]
Exports Assets/_Project/Art/Models/<Folder>/<Name>.fbx, previews to Logs/Blender/<Name>.png (+ _High),
lineups Logs/Blender/Env_*_Lineup.png and the manifest Tools/blender/models/env_manifest.json.
"""
import sys
import os
import math
import json

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import bpy
import numpy as np
from mathutils import Vector, Matrix

import tt_common as T
import env_lib as E
from env_lib import box, cyl, sph, ico, prism, lathe, place, assemble, attach

HERE = os.path.dirname(os.path.abspath(__file__))
MANIFEST = os.path.join(HERE, "env_manifest.json")
TAU = math.pi * 2


def rng(seed):
    return np.random.default_rng(seed)


# ================================================================================================ NATURE
POST = []   # (object, gradient kwargs) applied after finalize (soft foliage shading baked into the vertex colours)

FOLIAGE = dict(bottom=0.72, top=1.12, normal_mix=0.55, tint_top=(0.42, 0.78, 0.12))


def foliage(obj, **kw):
    k = dict(FOLIAGE)
    k.update(kw)
    POST.append((obj, k))
    return obj


def _trunk(height, r0, r1, flare=1.5, segs=10, mat="bark", branches=(), with_trunk=True):
    parts = []
    if with_trunk:
        prof = [(r0 * flare, 0.0), (r0 * 1.15, 0.12), (r0, 0.35)]
        n = 4
        for i in range(1, n + 1):
            t = i / n
            prof.append((r0 + (r1 - r0) * t, 0.35 + (height - 0.35) * t))
        prof.append((0.0, height + 0.02))
        wob = lambda i, a: 1.0 + (0.08 * math.sin(a * 3 + i) if i < 2 else 0.0)
        parts.append(lathe("trunk", prof, material=mat, segs=segs, radial=wob))
    for (z, yaw, tilt, length, rad) in branches:
        dv = Vector((math.sin(math.radians(tilt)) * math.cos(math.radians(yaw)),
                     math.sin(math.radians(tilt)) * math.sin(math.radians(yaw)), math.cos(math.radians(tilt))))
        b = cyl("branch", rad, length, Vector((0, 0, z)) + dv * (length / 2), mat, verts=6, r_top=rad * 0.55)
        b.rotation_euler = dv.to_track_quat('Z', 'Y').to_euler()
        parts.append(b)
    return parts


def _ring_clumps(n, ring_r, z, r, seed, z_jit=0.25, r_jit=0.08, sc=(1, 1, 0.9), phase=0.3):
    R = rng(seed)
    out = []
    for k in range(n):
        a = TAU * k / n + phase + R.uniform(-0.2, 0.2)
        rr = ring_r + R.uniform(-0.1, 0.1)
        out.append(((math.cos(a) * rr, math.sin(a) * rr, z + R.uniform(-z_jit * 0.4, z_jit)),
                    r + R.uniform(-r_jit, r_jit), sc))
    return out


def build_tree_round():
    top = 1.5
    trunk = assemble(_trunk(top + 0.6, 0.18, 0.11, branches=[(1.2, 30, 42, 0.9, 0.075), (1.35, 200, 45, 0.8, 0.065),
                                                             (1.45, 115, 38, 0.7, 0.06)]), "Tree_Round")
    cl = [((0, 0, 2.55), 1.05, (1.05, 1.05, 0.92))] + _ring_clumps(7, 0.98, 2.15, 0.66, 11) + \
         [((0.25, -0.1, 3.25), 0.72, (1, 1, 0.9)), ((-0.35, 0.3, 3.05), 0.62, (1, 1, 0.9))]
    can = E.blob("Canopy", cl, "leaf", subdiv=4, smooth_iter=1, noise=0.012, seed=1, centre=(0, 0, 2.5))
    attach(can, trunk, (0, 0, top))
    foliage(can)
    return trunk


def build_tree_pine():
    top = 0.7
    trunk = assemble(_trunk(1.2, 0.17, 0.1, flare=1.6), "Tree_Pine")
    tiers = []
    specs = [(0.62, 1.38, 1.4), (1.42, 1.12, 1.25), (2.18, 0.86, 1.1), (2.88, 0.6, 0.95), (3.5, 0.36, 0.95)]
    for i, (z0, R, h) in enumerate(specs):
        prof = [(R * 0.3, z0 + 0.14), (R * 0.78, z0 + 0.0), (R * 0.97, z0 + 0.03), (R, z0 + 0.1),
                (R * 0.86, z0 + 0.2), (R * 0.52, z0 + h * 0.52), (R * 0.2, z0 + h * 0.84)]
        if i == len(specs) - 1:
            prof += [(R * 0.07, z0 + h * 0.97), (0.0, z0 + h)]
        else:
            prof += [(0.0, z0 + h * 0.9)]
        sc = lambda ri, a, ph=i * 0.37: 1.0 + (0.055 * math.cos(9 * a + ph) if ri in (1, 2, 3, 4) else 0.0)
        tiers.append(lathe(f"tier{i}", prof, material="pine", segs=24, radial=sc, smooth_deg=80))
    can = assemble(tiers, "Canopy")
    attach(can, trunk, (0, 0, top))
    foliage(can, bottom=0.62, top=1.12, normal_mix=0.75, tint_top=(0.25, 0.6, 0.12))
    return trunk


def build_tree_apple():
    top = 1.3
    trunk = assemble(_trunk(top + 0.4, 0.17, 0.11, branches=[(1.05, 0, 50, 0.8, 0.07), (1.15, 140, 50, 0.75, 0.065),
                                                             (1.1, 250, 45, 0.75, 0.065)]), "Tree_Apple")
    cl = [((0, 0, 2.2), 1.0, (1.12, 1.12, 0.82))] + _ring_clumps(6, 1.0, 1.95, 0.64, 5, sc=(1, 1, 0.85)) + \
         [((0.1, 0.1, 2.8), 0.7, (1, 1, 0.85))]
    can = E.blob("Canopy", cl, "leaf", subdiv=4, smooth_iter=1, noise=0.012, seed=4, centre=(0, 0, 2.15))
    can.data.update()
    R = rng(9)
    vs = [v for v in can.data.vertices if -0.45 < v.normal.z < 0.75]
    picks = R.choice(len(vs), 13, replace=False)
    parts = [can]
    for k in picks:
        v = vs[int(k)]
        p = Vector(v.co) + Vector(v.normal) * 0.07
        parts.append(sph("apple", 0.125, p, "red", segs=10, rings=7, scale=(1, 1, 0.92)))
        parts.append(box("astem", (0.02, 0.02, 0.07), p + Vector((0, 0, 0.125)), "walnut"))
    can = assemble(parts, "Canopy")
    attach(can, trunk, (0, 0, top))
    POST.append((can, dict(FOLIAGE, only_mat="leaf")))
    return trunk


def build_tree_birch():
    top = 2.0
    h = 2.7
    n = 10
    prof = [(0.17, 0.0), (0.13, 0.15)]
    for i in range(1, n + 1):
        t = i / n
        prof.append((0.12 - 0.055 * t, 0.15 + (h - 0.15) * t))
    tr = lathe("trunk", prof, material="birch", segs=10, smooth_deg=70)
    R = rng(3)
    marks = set()
    for ring in range(1, n + 1):
        s = int(R.integers(0, 10))
        for q in range(int(R.integers(1, 3))):
            marks.add((ring, (s + q) % 10))
        if R.uniform() < 0.5:
            marks.add((ring, (s + 5) % 10))
    nf = (len(prof) - 1) * 10
    E.tone_faces(tr, "charcoal", lambda p: p.index < nf and (p.index // 10, p.index % 10) in marks
                 and p.center.z > 0.25)
    br = _trunk(0, 0.05, 0.05, branches=[(1.7, 20, 40, 0.75, 0.045), (1.95, 210, 38, 0.65, 0.04)], with_trunk=False)
    trunk = assemble([tr] + br, "Tree_Birch")
    cl = [((0, 0, 3.05), 0.72, (1, 1, 1.3)), ((0.48, 0.2, 2.65), 0.52, (1, 1, 1.2)),
          ((-0.42, -0.3, 2.6), 0.52, (1, 1, 1.2)), ((-0.3, 0.48, 2.95), 0.48, (1, 1, 1.2)),
          ((0.32, -0.38, 3.35), 0.48, (1, 1, 1.2)), ((0.0, 0.05, 3.9), 0.45, (1, 1, 1.3))]
    can = E.blob("Canopy", cl, "leaf_birch", subdiv=4, smooth_iter=1, noise=0.015, seed=6, centre=(0, 0, 3.1))
    attach(can, trunk, (0, 0, top))
    foliage(can, tint_top=(0.6, 0.8, 0.15))
    return trunk


def build_bush():
    cl = [((0, 0, 0.42), 0.5, (1.15, 1, 0.85)), ((0.52, 0.1, 0.32), 0.38, (1, 1, 0.85)),
          ((-0.5, -0.05, 0.3), 0.4, (1, 1, 0.85)), ((0.1, -0.38, 0.28), 0.34, (1, 1, 0.85)),
          ((-0.1, 0.4, 0.32), 0.36, (1, 1, 0.85))]
    b = E.blob("bush", cl, "leaf", subdiv=4, smooth_iter=2, noise=0.015, seed=2, centre=(0, 0, 0.3),
               flat_bottom=0.02, bottom_squash=0.1)
    b.data.update()
    R = rng(8)
    vs = [v for v in b.data.vertices if v.normal.z > -0.1 and v.co.z > 0.2]
    parts = [b]
    for i, k in enumerate(R.choice(len(vs), 8, replace=False)):
        v = vs[int(k)]
        parts.append(sph("blossom", 0.06, Vector(v.co) + Vector(v.normal) * 0.03, ["pink", "petal_white"][i % 2],
                         segs=6, rings=4))
    o = assemble(parts, "Bush")
    POST.append((o, dict(FOLIAGE, only_mat="leaf")))
    return o


def _petal_head(r, petals, color, centre_col, loc, tilt=(0, 0), cup=0.25):
    """Flat flower head: lobed disc + domed centre."""
    prof = [(0.0, -0.012), (r, cup * r * 0.4 + 0.007), (r * 0.3, 0.022), (0.0, 0.026)]
    lob = lambda i, a: (0.62 + 0.38 * abs(math.cos(a * petals / 2)) ** 0.6) if i == 1 else 1.0
    head = lathe("head", prof, material=color, segs=petals * 4, radial=lob, smooth_deg=80)
    ctr = sph("centre", r * 0.32, (0, 0, 0.03), centre_col, segs=6, rings=4, scale=(1, 1, 0.6))
    for o in (head, ctr):
        o.location = Vector(o.location) + Vector(loc)
        o.rotation_euler = (tilt[0], tilt[1], 0)
    return [head, ctr]


def _stem(base, top, r=0.013):
    v = Vector(top) - Vector(base)
    s = cyl("stem", r, v.length, (Vector(base) + Vector(top)) / 2, "green_dark", verts=5)
    s.rotation_euler = v.to_track_quat('Z', 'Y').to_euler()
    return s


def _flower_cluster(name, kind, color, color2, seed):
    R = rng(seed)
    parts = []
    n = 7
    for i in range(n):
        a = TAU * i / n * 2.3 + R.uniform(-0.3, 0.3)
        d = 0.0 if i == 0 else 0.07 + 0.2 * math.sqrt(i / n)
        bx, by = math.cos(a) * d, math.sin(a) * d
        h = 0.5 if i == 0 else R.uniform(0.27, 0.44)
        lean = Vector((bx, by, 0)) * 0.3
        top = Vector((bx, by, 0)) + lean + Vector((0, 0, h))
        parts.append(_stem((bx, by, 0), top))
        col = color if i % 3 else color2
        if kind == "daisy":
            parts += _petal_head(R.uniform(0.075, 0.095), 8, col, "orange", top, tilt=(-lean.y * 1.5, lean.x * 1.5))
        elif kind == "tulip":
            prof = [(0.0, -0.01), (0.045, 0.0), (0.068, 0.05), (0.063, 0.1), (0.05, 0.135)]
            lob = lambda ri, aa: (1.0 + 0.16 * math.cos(3 * aa)) if ri >= 3 else 1.0
            t = lathe("tulip", prof, top, col, segs=12, radial=lob, smooth_deg=85)
            t.rotation_euler = (-lean.y * 1.2, lean.x * 1.2, R.uniform(0, 2))
            parts.append(t)
        else:   # lavender-like spike of buds
            for k in range(5):
                zz = top.z - k * 0.045
                rr = 0.028 + k * 0.006
                parts.append(sph("bud", rr, (top.x - lean.x * k * 0.06, top.y - lean.y * k * 0.06, zz),
                                 col if k % 2 else color2, segs=6, rings=4, scale=(1, 1, 0.85)))
    # leafy base: upright blades + a soft mound
    for k in range(8):
        a = TAU * k / 8 + R.uniform(-0.2, 0.2)
        dd = R.uniform(0.05, 0.2)
        base = (math.cos(a) * dd, math.sin(a) * dd, -0.01)
        hh = R.uniform(0.16, 0.26)
        parts.append(E.blade("leaf", base, hh, (math.cos(a) * hh * 0.5, math.sin(a) * hh * 0.5), 0.035,
                             ["green", "leaf"][k % 2], segs=3))
    parts.append(ico("mound", 0.17, (0, 0, -0.01), "grass_dark", scale=(1.7, 1.7, 0.35), subdiv=2, jitter=0.06,
                     seed=seed))
    return assemble(parts, name)


def build_flowers_red():
    return _flower_cluster("Flowers_Red", "tulip", "tulip_red", "red_dark", 101)


def build_flowers_yellow():
    return _flower_cluster("Flowers_Yellow", "daisy", "yellow", "petal_white", 102)


def build_flowers_purple():
    return _flower_cluster("Flowers_Purple", "spike", "lavender", "lavender2", 103)


def _rock(name, spheres, centre, seed, subdiv=4, moss=False, noise=0.035):
    o = E.blob(name, spheres, "rock", subdiv=subdiv, smooth_iter=1, noise=noise, seed=seed, centre=centre,
               flat_bottom=0.0, bottom_squash=0.05)
    if moss:
        E.tone_by_normal(o, "moss", nz_min=0.86)
    return o


def build_rock_large():
    a = _rock("r0", [((0, 0, 0.35), 0.75, (1.3, 1.0, 0.85)), ((0.35, 0.15, 0.6), 0.5, (1, 1, 0.9)),
                     ((-0.4, -0.1, 0.45), 0.48, (1, 1, 0.85))], (0, 0, 0.3), 1)
    b = _rock("r1", [((0.95, -0.45, 0.12), 0.38, (1.15, 1, 0.75)), ((1.12, -0.3, 0.1), 0.25, (1, 1, 0.8))],
              (1.0, -0.4, 0.08), 2, subdiv=3)
    o = assemble([a, b], "Rock_Large")
    POST.append((o, dict(bottom=0.8, top=1.08, normal_mix=0.7)))
    return o


def build_rock_small():
    a = _rock("r0", [((0, 0, 0.12), 0.26, (1.3, 1, 0.8)), ((0.1, 0.05, 0.2), 0.16, (1, 1, 1))], (0, 0, 0.1), 7,
              subdiv=4)
    b = _rock("r1", [((0.34, -0.14, 0.05), 0.13, (1.15, 1, 0.75))], (0.34, -0.14, 0.04), 8, subdiv=3)
    o = assemble([a, b], "Rock_Small")
    POST.append((o, dict(bottom=0.8, top=1.08, normal_mix=0.7)))
    return o


def build_grass_tuft():
    R = rng(12)
    parts = []
    for i in range(22):
        a = R.uniform(0, TAU)
        d = R.uniform(0, 0.14)
        base = (math.cos(a) * d, math.sin(a) * d, -0.01)
        h = R.uniform(0.22, 0.42) * (1.0 - d * 1.5)
        la = a + R.uniform(-0.5, 0.5)
        lean = (math.cos(la) * h * 0.5, math.sin(la) * h * 0.5)
        parts.append(E.blade("blade", base, h, lean, 0.03, ["grass", "grass_dark", "leaf_light"][i % 3], segs=4))
    o = assemble(parts, "Grass_Tuft")
    POST.append((o, dict(bottom=0.7, top=1.1, normal_mix=0.0)))
    return o


def _cloud(name, puffs, seed):
    """Overlapping smooth puffs (UV spheres) with gently flattened bottoms - reads as soft cotton from any angle."""
    parts = []
    for i, (c, r) in enumerate(puffs):
        o = sph(f"puff{i}", r, c, "cloud", segs=16, rings=10, scale=(1, 0.9, 0.86))
        T.apply(o)
        for v in o.data.vertices:
            if v.co.z < 0.25:
                v.co.z = 0.25 + (v.co.z - 0.25) * 0.15
        parts.append(o)
    return assemble(parts, name)


def build_cloud_a():
    p = [((0, 0, 1.25), 1.75), ((1.85, 0.15, 0.95), 1.35), ((-1.95, -0.1, 0.9), 1.3), ((0.9, -0.35, 2.05), 1.15),
         ((-0.8, 0.3, 2.1), 1.1), ((3.3, 0.0, 0.7), 0.85), ((-3.3, 0.15, 0.7), 0.8)]
    o = _cloud("Cloud_A", p, 200)
    POST.append((o, dict(bottom=0.84, top=1.0, normal_mix=0.85)))
    return o


def build_cloud_b():
    p = [((0, 0, 1.1), 1.5), ((1.6, 0.25, 0.85), 1.2), ((-1.5, -0.15, 0.8), 1.1), ((0.45, -0.3, 1.85), 0.95),
         ((2.75, -0.1, 0.6), 0.75), ((-2.65, 0.2, 0.6), 0.72)]
    o = _cloud("Cloud_B", p, 300)
    POST.append((o, dict(bottom=0.84, top=1.0, normal_mix=0.85)))
    return o


def _mushroom(s, loc, seed):
    stem = lathe("mstem", [(0.1 * s, 0), (0.105 * s, 0.03 * s), (0.08 * s, 0.2 * s), (0.085 * s, 0.3 * s),
                           (0.0, 0.31 * s)], loc, "cream", segs=14)
    cap = lathe("mcap", [(0.0, 0.25 * s), (0.2 * s, 0.25 * s), (0.255 * s, 0.28 * s), (0.25 * s, 0.33 * s),
                         (0.2 * s, 0.41 * s), (0.11 * s, 0.47 * s), (0.0, 0.49 * s)], loc, "red", segs=18,
                smooth_deg=80)
    E.tone_by_normal(cap, "cream", nz_max=-0.6)
    parts = [stem, cap]
    R = rng(seed)
    for k in range(7):
        a = TAU * k / 7 + R.uniform(-0.2, 0.2)
        el = math.radians(28 if k % 2 else 52)
        p = Vector(loc) + Vector((math.cos(a) * math.cos(el) * 0.245 * s, math.sin(a) * math.cos(el) * 0.245 * s,
                                  0.28 * s + math.sin(el) * 0.2 * s))
        d = sph("dot", 0.04 * s, p, "white", segs=8, rings=4, scale=(1, 1, 0.4))
        d.rotation_euler = (p - Vector(loc) - Vector((0, 0, 0.27 * s))).to_track_quat('Z', 'Y').to_euler()
        parts.append(d)
    parts.append(sph("dot", 0.045 * s, Vector(loc) + Vector((0, 0, 0.485 * s)), "white", segs=8, rings=4,
                     scale=(1, 1, 0.4)))
    return parts


def build_mushroom():
    parts = _mushroom(1.0, (0, 0, 0), 1) + _mushroom(0.6, (0.3, -0.14, 0), 2)
    for k in range(6):
        a = TAU * k / 6
        parts.append(E.blade("grass", (math.cos(a) * 0.15, math.sin(a) * 0.15, 0), 0.14,
                             (math.cos(a) * 0.07, math.sin(a) * 0.07), 0.025, "grass_dark", segs=3))
    return assemble(parts, "Mushroom")


# ================================================================================================ BUILDINGS
put = E.put


def win(wall, fw, fd, u, z, cx=0.0, cy=0.0, **kw):
    """Window on a wall of a fw x fd footprint (kw go to E.window: w, h, shutters, ...)."""
    return put(E.window(**kw), wall, fw, fd, u, z, cx, cy)


def build_farmhouse():
    w, d, H, pitch = 5.0, 3.6, 2.7, 40
    rise = d / 2 * math.tan(math.radians(pitch))
    p = [E.gable_body(w, d, H, rise, "wall_cream", ridge_axis="X"), E.plinth(w, d, 0.32, "stone")]
    roof, rz = E.gable_roof(w, d, H, pitch, overhang=0.3, eave=0.38, tiles=("roof_red", "roof_red2"))
    p += roof
    # half-timbered frame: two beams + studs on the long walls, corner posts
    for wall in ("-y", "+y"):
        for z in (1.6, H - 0.07):
            p += put([box("beam", (w + 0.04, 0.08, 0.13), (0, 0, z), "walnut", bevel=0.015)], wall, w, d, 0, 0,
                     out=0.02)
        for u in (-0.8, 0.8):
            p += put([box("stud", (0.11, 0.07, H - 1.7), (u, 0, (H + 1.6) / 2), "walnut", bevel=0.012)], wall, w,
                     d, 0, 0, out=0.02)
        for u in (-2.15, 2.15):
            for sgn in (-1, 1):
                p += put([box("brace", (0.09, 0.06, 0.95), (u + sgn * 0.0, 0, (H + 1.6) / 2), "walnut",
                              bevel=0.01, rot=(0, sgn * 0.62, 0))], wall, w, d, 0, 0, out=0.02)
    p += E.corner_trims(w, d, 0.3, H, "walnut", t=0.12)
    flowers = ["pink", "red", "yellow"]
    # front: porch door, two shuttered windows with flower boxes, three upper windows
    p += put(E.door(0.82, 1.42, "beech_dark", "white", planks=4, top_window=True), "-y", w, d, 0, 0.32)
    for u in (-1.55, 1.55):
        p += win("-y", w, d, u, 0.98, w=0.66, h=0.74, shutters="paint_green", flowerbox=flowers, seed=int(u * 10))
    for u in (-1.55, 0.0, 1.55):
        p += win("-y", w, d, u, 2.15, w=0.56, h=0.6)
    # porch: two posts + a little gable hood
    for sx in (-1, 1):
        p.append(box("porchpost", (0.11, 0.11, 1.6), (sx * 0.62, -d / 2 - 0.72, 0.32 + 0.8), "white", bevel=0.02))
    p.append(box("porchfloor", (1.5, 0.9, 0.12), (0, -d / 2 - 0.45, 0.3), "stone", bevel=0.03))
    hood, hz = E.gable_roof(0.82, 1.3, 1.92, 36, overhang=0.08, eave=0.14, ridge_axis="Y", centre=(0, -d / 2 - 0.4),
                            tiles=("roof_red", "roof_red2"), ridge_cap=True, rows=3)
    p += hood
    p.append(prism("porchgable", [(-0.65, 1.92), (0.65, 1.92), (0, 1.92 + 0.65 * math.tan(math.radians(36)))], 0.06,
                   (0, -d / 2 - 0.82, 0), "white"))
    # gable ends
    for wall in ("+x", "-x"):
        p += win(wall, w, d, 0, 0.98, w=0.66, h=0.74, shutters="paint_green")
        p += win(wall, w, d, 0, 2.2, w=0.56, h=0.6)
        p += put(E.round_window(0.22), wall, w, d, 0, 3.45)
    # back
    for u in (-1.3, 1.3):
        p += win("+y", w, d, u, 0.98, w=0.66, h=0.74)
        p += win("+y", w, d, u, 2.15, w=0.56, h=0.6)
    p += E.chimney(1.5, 0.55, rz - 0.6, 1.15)
    return assemble(p, "Farmhouse")


def build_barn():
    w, d, H = 4.6, 5.4, 2.4
    kx, kz, rzz = 1.55, 3.55, 4.35          # knee x/z, ridge z of the gambrel
    prof = [(-w / 2, 0), (w / 2, 0), (w / 2, H), (kx, kz), (0, rzz), (-kx, kz), (-w / 2, H)]
    p = [prism("body", prof, d, (0, 0, 0), "barn_red", bevel=0.03), E.plinth(w, d, 0.25, "stone")]
    tiles = ("roof_grey", "roof_grey2")
    roof = []
    L = d + 0.5
    for sgn in (-1, 1):
        roof += E.roof_plane((0, rzz), (sgn * kx, kz), L, tiles, "oak", rows=3, top_ext=0.0, barge="white")
        roof += E.roof_plane((sgn * kx, kz), (sgn * w / 2, H), L, tiles, "oak", rows=4, eave=0.35, barge="white")
        roof.append(cyl("knee", 0.07, L + 0.08, (0, sgn * (kx + 0.06), kz + 0.16), "roof_grey2", verts=8,
                        rot=(0, math.pi / 2, 0)))
    roof.append(cyl("ridge", 0.1, L + 0.12, (0, 0, rzz + 0.13), "roof_grey2", verts=10, rot=(0, math.pi / 2, 0)))
    place(roof, (0, 0, 0), 90)
    p += roof
    # board battens (vertical boards) on all walls, skipping the openings

    def roofline(x):
        x = abs(x)
        if x <= kx:
            return rzz + (kz - rzz) * x / kx
        return kz + (H - kz) * (x - kx) / (w / 2 - kx)
    for sx in (-1, 1):
        for i in range(17):
            y = -d / 2 + 0.3 + i * (d - 0.6) / 16
            if abs(y) < 0.45 or abs(abs(y) - 1.7) < 0.4:
                continue    # windows
            p.append(box("batten", (0.03, 0.07, H - 0.3), (sx * (w / 2 + 0.012), y, 0.25 + (H - 0.3) / 2),
                         "barn_red2"))
    for sy in (-1, 1):
        for i in range(15):
            x = -w / 2 + 0.25 + i * (w - 0.5) / 14
            top = roofline(x) - 0.1
            segs = [(0.25, top)]
            if sy < 0 and abs(x) < 1.25:
                segs = [(2.42, top)] if abs(x) > 0.55 else [(2.42, 2.55), (3.55, top)]
            if sy > 0 and abs(x) < 0.6:
                segs = [(1.85, top)]
            for z0, z1 in segs:
                if z1 - z0 > 0.1:
                    p.append(box("batten", (0.07, 0.03, z1 - z0), (x, sy * (d / 2 + 0.012), (z0 + z1) / 2),
                                 "barn_red2"))
    # white trim: corner boards, eave line
    p += E.corner_trims(w, d, 0.2, H, "white", t=0.13)
    for sx in (-1, 1):
        p.append(box("eavetrim", (0.06, d + 0.1, 0.12), (sx * (w / 2 + 0.03), 0, H - 0.04), "white"))
    # big double doors with X-bracing
    for sx in (-1, 1):
        cx = sx * 0.55
        leaf = [box("leaf", (1.06, 0.06, 2.12), (0, 0.0, 1.06), "barn_red2", bevel=0.015),
                E.ring_frame("dframe", 1.06, 2.12, 0.1, 0.08, (0, -0.03, 1.06), "white")]
        diag = math.atan2(1.92, 0.86)
        for s2 in (-1, 1):
            leaf.append(box("xbrace", (2.05, 0.06, 0.1), (0, -0.04, 1.06), "white", rot=(0, s2 * diag, 0)))
        p += put(leaf, "-y", w, d, cx, 0.22, out=0.02)
    p += put([box("doorheader", (2.5, 0.12, 0.14), (0, 0, 2.42), "white", bevel=0.02),
              box("doortrack", (2.9, 0.06, 0.05), (0, -0.06, 2.5), "charcoal")], "-y", w, d, 0, 0, out=0.02)
    # hay loft door + hoist beam
    loft = [box("loft", (0.9, 0.06, 0.95), (0, 0, 0), "barn_red2", bevel=0.01),
            E.ring_frame("lframe", 0.9, 0.95, 0.09, 0.08, (0, -0.03, 0), "white")]
    for s2 in (-1, 1):
        loft.append(box("lx", (1.15, 0.06, 0.08), (0, -0.04, 0), "white", rot=(0, s2 * math.atan2(0.77, 0.72), 0)))
    p += put(loft, "-y", w, d, 0, 3.05, out=0.02)
    p.append(box("hoist", (0.14, 0.9, 0.14), (0, -d / 2 - 0.3, 3.85), "walnut", bevel=0.02))
    p.append(cyl("pulley", 0.09, 0.06, (0, -d / 2 - 0.62, 3.68), "charcoal", verts=12, rot=(0, math.pi / 2, 0)))
    p.append(cyl("rope", 0.015, 0.9, (0.0, -d / 2 - 0.71, 3.2), "straw", verts=5))
    # side windows (white crossed)
    for wall in ("+x", "-x"):
        for u in (-1.7, 0, 1.7):
            p += win(wall, w, d, u, 1.45, w=0.62, h=0.62, border=0.08)
    # back: small door + window
    p += put(E.door(0.85, 1.5, "barn_red2", "white", planks=4, step=None), "+y", w, d, 0, 0.25)
    # cupola + weather vane on the ridge
    cz = rzz + 0.05
    p.append(box("cupola", (0.62, 0.62, 0.6), (0, 0, cz + 0.3), "white", bevel=0.03))
    for k in range(4):
        p += place([box("louvre", (0.36, 0.03, 0.05), (0, -0.315, cz + 0.18 + k * 0.1), "charcoal")], (0, 0, 0), k * 90)
    p.append(lathe("cuproof", [(0.0, cz + 0.58), (0.52, cz + 0.58), (0.52, cz + 0.64), (0.0, cz + 1.05)],
                   (0, 0, 0), "roof_grey2", segs=4, rot=(0, 0, math.pi / 4), smooth_deg=20))
    p.append(cyl("vanerod", 0.02, 0.6, (0, 0, cz + 1.3), "charcoal", verts=6))
    p.append(prism("vane", [(-0.32, -0.03), (0.2, -0.03), (0.2, -0.09), (0.34, 0.0), (0.2, 0.09), (0.2, 0.03),
                            (-0.32, 0.03)], 0.02, (0, 0, cz + 1.45), "gold", rot=(math.pi / 2, 0, 0)))
    p.append(sph("vaneball", 0.05, (0, 0, cz + 1.62), "gold", segs=8, rings=5))
    return assemble(p, "Barn")


def build_house_a():
    w, d, H, pitch = 3.4, 3.8, 2.4, 45
    rise = w / 2 * math.tan(math.radians(pitch))
    p = [E.gable_body(w, d, H, rise, "wall_mint", ridge_axis="Y"), E.plinth(w, d, 0.28, "stone")]
    roof, rz = E.gable_roof(d, w, H, pitch, overhang=0.3, eave=0.32, ridge_axis="Y", tiles=("roof_blue", "roof_blue2"))
    p += roof
    p += E.corner_trims(w, d, 0.28, H, "white", t=0.11)
    for wall in ("-y", "+y"):
        p += put([box("gablebeam", (w + 0.06, 0.08, 0.1), (0, 0, H), "white", bevel=0.015)], wall, w, d, 0, 0,
                 out=0.02)
    fl = ["pink", "yellow", "petal_white"]
    p += put(E.door(0.8, 1.45, "red", "white", planks=3, canopy="roof_blue2", top_window=True), "-y", w, d, 0, 0.28)
    for u in (-1.05, 1.05):
        p += win("-y", w, d, u, 1.05, w=0.6, h=0.74, shutters="paint_blue", flowerbox=fl, seed=int(u * 7))
    p += win("-y", w, d, 0, 2.95, w=0.58, h=0.66)
    p += put(E.round_window(0.18), "+y", w, d, 0, 3.0)
    for wall in ("+x", "-x"):
        for u in (-0.9, 0.9):
            p += win(wall, w, d, u, 1.05, w=0.6, h=0.74, shutters="paint_blue")
    p += win("+y", w, d, 0, 1.05, w=0.6, h=0.74)
    p += E.chimney(0.95, 0.9, rz - 0.9, 1.15, w=0.38, material="brick")
    return assemble(p, "House_A")


def build_house_b():
    w, d, H, pitch = 4.4, 3.4, 2.2, 42
    t = math.tan(math.radians(pitch))
    rise = d / 2 * t
    p = [E.gable_body(w, d, H, rise, "wall_yellow", ridge_axis="X"), E.plinth(w, d, 0.28, "stone_dark")]
    roof, rz = E.gable_roof(w, d, H, pitch, overhang=0.28, eave=0.32, tiles=("roof_green", "roof_green2"))
    p += roof
    p += E.corner_trims(w, d, 0.28, H, "white", t=0.11)
    # dormer on the front slope
    dz0, dh, dw = 2.85, 0.6, 1.0
    p.append(E.gable_body(dw, 1.0, dh, dw / 2 * math.tan(math.radians(40)), "wall_yellow", ridge_axis="Y",
                          loc=(0, -0.62, dz0)))
    dro, _ = E.gable_roof(1.0, dw, dz0 + dh, 40, overhang=0.08, eave=0.1, ridge_axis="Y", centre=(0, -0.58),
                          tiles=("roof_green", "roof_green2"), rows=2)
    p += dro
    p += place(E.window(0.46, 0.42, border=0.06), (0, -1.12, dz0 + 0.32))
    # front
    fl = ["red", "petal_white", "pink"]
    p += put(E.door(0.8, 1.4, "paint_blue", "white", planks=3, canopy="roof_green2", top_window=True), "-y", w, d,
             -1.25, 0.28)
    big = E.window(1.15, 0.8, cross=False, flowerbox=fl, seed=3)
    for u in (-0.19, 0.19):
        big.append(box("mul", (0.045, 0.05, 0.68), (u, -0.03, 0), "white"))
    big.append(box("mulh", (1.05, 0.05, 0.045), (0, -0.03, 0.18), "white"))
    p += put(big, "-y", w, d, 0.75, 1.05)
    # gable ends: external stone chimney on +x, windows on -x
    cx = w / 2 + 0.22
    p.append(box("chimbase", (0.44, 0.9, 1.3), (cx, 0, 0.65), "stone", bevel=0.04, segments=2))
    p.append(box("chimstep", (0.4, 0.75, 0.25), (cx - 0.02, 0, 1.38), "stone", bevel=0.05, segments=2,
                 rot=(0, -0.35, 0)))
    p.append(box("chimstack", (0.4, 0.58, rz + 0.9 - 1.3), (cx - 0.02, 0, (1.3 + rz + 0.9) / 2), "stone",
                 bevel=0.035, segments=2))
    p.append(box("chimcap", (0.52, 0.7, 0.1), (cx - 0.02, 0, rz + 0.92), "stone_dark", bevel=0.03))
    p.append(cyl("chimpot", 0.09, 0.22, (cx - 0.02, 0.0, rz + 1.06), "roof_red2", verts=10))
    p += win("+x", w, d, -1.05, 1.05, w=0.5, h=0.6)
    p += win("-x", w, d, 0, 1.05, w=0.62, h=0.74, flowerbox=fl, seed=5)
    p += win("-x", w, d, 0, 2.75, w=0.5, h=0.55)
    for u in (-1.2, 1.2):
        p += win("+y", w, d, u, 1.05, w=0.62, h=0.74, shutters="white")
    return assemble(p, "House_B")


def build_shop():
    w, d, H, pitch = 4.2, 3.4, 3.1, 38
    rise = d / 2 * math.tan(math.radians(pitch))
    p = [E.gable_body(w, d, H, rise, "wall_peach", ridge_axis="X"), E.plinth(w, d, 0.25, "stone")]
    roof, rz = E.gable_roof(w, d, H, pitch, overhang=0.28, eave=0.32, tiles=("roof_orange", "roof_orange2"))
    p += roof
    p += E.corner_trims(w, d, 0.25, H, "white", t=0.12)
    p += put([box("band", (w + 0.06, 0.09, 0.12), (0, 0, 2.18), "white", bevel=0.02)], "-y", w, d, 0, 0, out=0.02)
    # shop front: two display windows on a panelled base + door
    for u in (-1.3, 1.3):
        dw = E.window(1.25, 1.0, cross=False, sill=True, border=0.08)
        dw.append(box("dmul", (0.045, 0.05, 0.88), (0, -0.03, 0), "white"))
        dw.append(box("panel", (1.25, 0.08, 0.38), (0, -0.02, -0.75), "paint_blue", bevel=0.02))
        dw.append(box("panel_in", (1.0, 0.03, 0.22), (0, -0.07, -0.75), "sky", bevel=0.01))
        p += put(dw, "-y", w, d, u, 1.2)
    p += put(E.door(0.86, 1.62, "paint_blue", "white", planks=3, top_window=True), "-y", w, d, 0, 0.25)
    # striped awning with scalloped valance
    n = 12
    aw = 4.0 / n
    a_top, a_bot, depth = 2.12, 1.86, 0.85
    ang = math.atan2(a_top - a_bot, depth)
    slope_len = math.hypot(depth, a_top - a_bot)
    for i in range(n):
        x = -2.0 + aw * (i + 0.5)
        col = "red" if i % 2 == 0 else "white"
        p.append(box("awning", (aw, slope_len, 0.035), (x, -d / 2 - depth / 2, (a_top + a_bot) / 2), col,
                     rot=(ang, 0, 0)))
        bot, top = [], []
        for k in range(7):
            xx = x - aw / 2 + aw * k / 6
            sag = 0.12 * math.sin(math.pi * k / 6)
            bot.append((xx, a_bot - 0.1 - sag))
            top.append((xx, a_bot + 0.01))
        v = E.strip_mesh("valance", bot, top, 0.03, col)
        v.location = (0, -d / 2 - depth - 0.005, 0)
        p.append(v)
    for sx in (-1, 1):
        rod = cyl("awrod", 0.02, 0.92, (sx * 1.98, -d / 2 - 0.425, 1.68), "charcoal", verts=6)
        rod.rotation_euler = (math.radians(67), 0, 0)
        p.append(rod)
    # sign board with an apple emblem
    sb = [box("sign", (2.3, 0.08, 0.5), (0, -0.01, 0), "yellow", bevel=0.03),
          E.ring_frame("signframe", 2.3, 0.5, 0.06, 0.1, (0, -0.03, 0), "white"),
          sph("emblem", 0.15, (0, -0.07, 0), "red", segs=12, rings=8, scale=(1, 0.35, 0.95)),
          sph("emleaf", 0.07, (0.07, -0.1, 0.15), "green", segs=8, rings=5, scale=(1.2, 0.3, 0.6), rot=(0, 0.6, 0))]
    for u in (-0.7, 0.7):
        for k in range(3):
            sb.append(box("letter", (0.12, 0.03, 0.18), (u + (k - 1) * 0.17 * (1 if u > 0 else -1), -0.06, 0),
                          ["red", "paint_blue", "green"][k], bevel=0.02))
    p += put(sb, "-y", w, d, 0, 2.55, out=0.02)
    for u in (-1.5, 1.5):
        p += win("-y", w, d, u, 2.65, w=0.52, h=0.56)
    # fruit crates outside
    R = rng(21)
    for sx, fruit in ((-1, "red"), (1, "orange")):
        cx, cy = sx * 1.3, -d / 2 - 0.42
        p.append(box("fcrate", (0.7, 0.4, 0.3), (cx, cy, 0.15), "beech", bevel=0.02))
        p.append(box("fcrate_in", (0.62, 0.32, 0.05), (cx, cy, 0.28), "groove"))
        for k in range(8):
            p.append(sph("fruit", 0.075, (cx - 0.24 + (k % 4) * 0.16 + R.uniform(-0.02, 0.02),
                                         cy - 0.08 + (k // 4) * 0.16, 0.33 + R.uniform(0, 0.03)), fruit, segs=8,
                         rings=6))
    for wall in ("+x", "-x"):
        p += win(wall, w, d, 0, 1.15, w=0.6, h=0.74)
        p += win(wall, w, d, 0, 2.65, w=0.52, h=0.56)
    p += put(E.door(0.8, 1.5, "beech_dark", "white", planks=4), "+y", w, d, 0.9, 0.25)
    p += win("+y", w, d, -0.9, 1.15, w=0.6, h=0.74)
    p += E.chimney(-1.4, 0.5, rz - 0.6, 1.05)
    return assemble(p, "Shop")


def _bench_parts(length=1.4, frame="paint_green", wood="beech"):
    p = []
    for sx in (-1, 1):
        x = sx * (length / 2 - 0.12)
        prof = [(-0.045, -0.025), (0.045, -0.025), (0.045, 0.025), (-0.045, 0.025)]
        back = [(x, 0.17, 0.0), (x, 0.15, 0.2), (x, 0.13, 0.4), (x, 0.17, 0.62), (x, 0.23, 0.84)]
        front = [(x, -0.2, 0.0), (x, -0.18, 0.2), (x, -0.17, 0.4), (x, -0.2, 0.56), (x, -0.13, 0.62),
                 (x, 0.0, 0.62), (x, 0.15, 0.62)]
        p.append(E.sweep_fix("legb", back, prof, frame))
        p.append(E.sweep_fix("legf", front, prof, frame))
        p.append(box("seatrail", (0.06, 0.42, 0.06), (x, -0.01, 0.4), frame))
        p.append(box("foot", (0.1, 0.12, 0.04), (x, 0.17, 0.02), frame, bevel=0.01))
        p.append(box("foot", (0.1, 0.12, 0.04), (x, -0.2, 0.02), frame, bevel=0.01))
    for k in range(3):
        p.append(box("slat", (length, 0.11, 0.045), (0, -0.14 + k * 0.125, 0.455), wood, bevel=0.015))
    for k in range(2):
        z = 0.6 + k * 0.17
        y = 0.155 + (z - 0.6) * 0.33
        p.append(box("backslat", (length, 0.045, 0.12), (0, y, z), wood, bevel=0.015, rot=(-0.32, 0, 0)))
    return p


def build_station():
    p = []
    # platform: brick face, stone paving, white edge + yellow safety line (x 0.55 .. 4.5, top z = 0.35)
    x0, x1, L = 0.55, 4.5, 5.4
    p.append(box("platform", (x1 - x0, L, 0.3), ((x0 + x1) / 2, 0, 0.15), "brick", bevel=0.02))
    p.append(box("paving", (x1 - x0 + 0.04, L + 0.04, 0.06), ((x0 + x1) / 2 - 0.02, 0, 0.32), "stone", bevel=0.02))
    p.append(box("coping", (0.24, L + 0.06, 0.07), (x0 + 0.1, 0, 0.32), "white", bevel=0.02))
    p.append(box("safety", (0.07, L, 0.012), (x0 + 0.33, 0, 0.352), "yellow"))
    for k in range(9):
        p.append(box("joint", (x1 - x0 - 0.5, 0.025, 0.008), ((x0 + x1) / 2 + 0.25, -L / 2 + 0.3 + k * 0.6, 0.351),
                     "stone_dark"))
    for sy in (-1, 1):
        p.append(prism("ramp", [(0, 0), (0.6, 0), (0, 0.35)], 1.6, (x0 + 2.4, sy * (L / 2), 0), "stone",
                       rot=(0, 0, -sy * math.pi / 2)))
    # building
    bw, bd, H, zb = 2.4, 3.8, 2.9, 0.35
    cx = 3.2
    pitch = 35
    rise = bw / 2 * math.tan(math.radians(pitch))
    p.append(E.gable_body(bw, bd, H, rise, "wall_cream", ridge_axis="Y", loc=(cx, 0, zb)))
    p.append(box("dado", (bw + 0.08, bd + 0.08, 0.7), (cx, 0, zb + 0.35), "brick", bevel=0.03))
    p.append(box("dadocap", (bw + 0.14, bd + 0.14, 0.07), (cx, 0, zb + 0.72), "stone", bevel=0.02))
    roof, rz = E.gable_roof(bd, bw, zb + H, pitch, overhang=0.3, eave=0.3, ridge_axis="Y", centre=(cx, 0),
                            tiles=("roof_teal", "roof_teal2"))
    p += roof
    p += E.corner_trims(bw, bd, zb, zb + H, "white", t=0.11, cx=cx)
    # track-facing side (-x): double door, two windows, name board
    dd = E.door(0.62, 1.75, "paint_green", "white", planks=2, top_window=True, step=None) + \
        place(E.door(0.62, 1.75, "paint_green", "white", planks=2, top_window=True, step=None), (0, 0, 0), 0,
              (0.62, 0, 0))
    place(dd, (0, 0, 0), 0, (-0.31, 0, 0))
    p += put(dd, "-x", bw, bd, 0, zb, cx)
    for u in (-1.15, 1.15):
        p += win("-x", bw, bd, u, zb + 1.35, cx, w=0.62, h=0.95, border=0.08)
    nb = [box("nameboard", (2.2, 0.06, 0.28), (0, 0, 0), "white", bevel=0.02),
          E.ring_frame("nbframe", 2.2, 0.28, 0.05, 0.1, (0, -0.03, 0), "roof_teal2")]
    for k in range(7):
        nb.append(box("nbletter", (0.1, 0.03, 0.14), (-0.75 + k * 0.25, -0.05, 0), "roof_teal2", bevel=0.015))
    p += put(nb, "-x", bw, bd, 0, zb + 2.74, cx)
    # other walls
    for u in (-0.9, 0.9):
        p += win("+x", bw, bd, u, zb + 1.35, cx, w=0.62, h=0.95, border=0.08)
    for wall in ("-y", "+y"):
        p += win(wall, bw, bd, 0, zb + 1.35, cx, w=0.62, h=0.95, border=0.08)
        p += put(E.round_window(0.2), wall, bw, bd, 0, zb + H + 0.38, cx)
    p += E.chimney(cx + 0.55, 1.1, rz - 0.5, 0.95, w=0.36)
    # platform canopy: slab + tiles from the wall to the track edge, cast-iron posts, scalloped valance
    c_hi, c_lo, c_x0 = zb + 2.45, zb + 2.25, 0.62
    can = E.roof_plane((-(cx - bw / 2), c_hi), (-c_x0, c_lo), L + 0.0, ("roof_teal", "roof_teal2"), "white",
                       thick=0.08, rows=4, barge="white")
    place(can, (0, 0, 0), 90)      # canonical y -> world -x
    p += can
    for y in (-1.9, 1.9):
        p.append(lathe("post", [(0.1, zb), (0.1, zb + 0.12), (0.06, zb + 0.18), (0.05, zb + 1.9), (0.08, zb + 1.98),
                                (0.06, zb + 2.04), (0.06, c_lo + 0.06)], (0.95, y, 0), "paint_green", segs=10))
        br = E.strip_mesh("bracket", [(0.1, zb + 2.0), (0.4, c_lo + 0.02), (0.8, c_lo + 0.0)],
                          [(0.1, c_lo + 0.06), (0.4, c_lo + 0.06), (0.8, c_lo + 0.06)], 0.04, "paint_green")
        br.location = (0.85, y, 0)
        br2 = E.strip_mesh("bracket", [(-0.1, zb + 2.0), (-0.25, c_lo + 0.08)],
                           [(-0.1, c_lo + 0.12), (-0.25, c_lo + 0.12)], 0.04, "paint_green")
        br2.location = (0.95, y, 0)
        p += [br, br2]
    # valance along the track edge (runs along Y)
    nsc = 22
    ys = [-L / 2 + L * k / (nsc * 4) for k in range(nsc * 4 + 1)]
    bot = [(yy, c_lo - 0.08 - 0.1 * math.sin(math.pi * (k % 4) / 4.0)) for k, yy in enumerate(ys)]
    top = [(yy, c_lo + 0.06) for yy in ys]
    val = E.strip_mesh("valance", bot, top, 0.03, "white")
    val.rotation_euler = (0, 0, math.pi / 2)
    val.location = (c_x0 - 0.02, 0, 0)
    p.append(val)
    # hanging platform clock (faces the track and the building)
    ck = (1.45, 0.0, zb + 1.95)
    p.append(cyl("clockrod", 0.025, c_hi - 0.12 - ck[2] - 0.3, (ck[0], 0, (ck[2] + 0.3 + c_hi - 0.12) / 2),
                 "charcoal", verts=6))
    p.append(cyl("clockcase", 0.3, 0.16, ck, "red", verts=24, rot=(0, math.pi / 2, 0), bevel=0.03, segments=2))
    for sx in (-1, 1):
        fx = ck[0] + sx * 0.085
        p.append(cyl("clockface", 0.25, 0.02, (fx, 0, ck[2]), "white", verts=24, rot=(0, math.pi / 2, 0)))
        for k in range(12):
            a = TAU * k / 12
            p.append(box("tick", (0.012, 0.025 if k % 3 else 0.035, 0.05 if k % 3 else 0.07),
                         (fx + sx * 0.012, math.sin(a) * 0.2, ck[2] + math.cos(a) * 0.2), "black", rot=(-a, 0, 0)))
        for ln, ang, th in ((0.17, -math.radians(60), 0.03), (0.12, math.radians(60), 0.035)):
            a2 = ang
            p.append(box("hand", (0.012, th, ln), (fx + sx * 0.02, math.sin(a2) * ln / 2, ck[2] + math.cos(a2) * ln / 2),
                         "black", rot=(-a2, 0, 0)))
        p.append(cyl("hub", 0.022, 0.03, (fx + sx * 0.02, 0, ck[2]), "black", verts=8, rot=(0, math.pi / 2, 0)))
    p.append(sph("clocktop", 0.06, (ck[0], 0, ck[2] + 0.33), "gold", segs=8, rings=5))
    # bench + milk churns on the platform
    p += place(_bench_parts(1.3), (1.62, -1.0, zb), -90)
    for k, (yy, xx) in enumerate(((1.0, 1.55), (1.25, 1.75))):
        p.append(lathe("churn", [(0.13, zb), (0.14, zb + 0.04), (0.14, zb + 0.38), (0.09, zb + 0.5), (0.08, zb + 0.56),
                                 (0.09, zb + 0.58), (0.0, zb + 0.62)], (xx, yy, 0), "metal", segs=14))
        p.append(T.torus("churnband", 0.142, 0.012, (xx, yy, zb + 0.2), E.m("blue"), major_segs=14, minor_segs=4))
    return assemble(p, "Station")


def build_depot():
    p = []
    W, D, H, t = 2.8, 4.0, 2.4, 0.2
    pitch = 35
    tn = math.tan(math.radians(pitch))
    rz = H + W / 2 * tn
    ow, rect_h = 0.85, 1.8               # opening half width / straight jamb height (arch on top)
    gab = lambda x: H + (W / 2 - abs(x)) * tn
    # side walls
    for sx in (-1, 1):
        p.append(box("sidewall", (t, D - 0.06, H), (sx * (W / 2 - t / 2 - 0.004), 0, H / 2), "brick", bevel=0.02))
        p.append(box("sideplinth", (t + 0.08, D + 0.08, 0.25), (sx * (W / 2 - t / 2), 0, 0.125), "stone_dark",
                     bevel=0.03))
    # end walls with arched openings (both ends open so the track can run through)
    for sy in (-1, 1):
        y = sy * (D / 2 - t / 2)
        pieces = []
        for side in (-1, 1):
            xs = [side * ow, side * (W / 2 + 0.005)]
            if side < 0:
                xs = xs[::-1]
            bot = [(x, 0.0) for x in xs]
            top = [(x, gab(x)) for x in xs]
            pieces.append(E.strip_mesh("pier", bot, top, t, "brick"))
        bot, top = [], []
        n = 12
        for k in range(n + 1):
            a = math.pi * k / n
            x = -ow * math.cos(a)
            bot.append((x, rect_h + ow * math.sin(a)))
            top.append((x, gab(x)))
        pieces.append(E.strip_mesh("archwall", bot, top, t, "brick"))
        # stone voussoir ring + keystone + impost blocks
        vb, vt = [], []
        for k in range(n + 1):
            a = math.pi * k / n
            vb.append((-ow * math.cos(a), rect_h + ow * math.sin(a)))
            vt.append((-(ow + 0.16) * math.cos(a), rect_h + (ow + 0.16) * math.sin(a)))
        ring = E.strip_mesh("arch", vb, vt, t + 0.06, "stone")
        pieces.append(ring)
        pieces.append(box("keystone", (0.22, t + 0.1, 0.26), (0, 0, rect_h + ow + 0.08), "stone_dark", bevel=0.02))
        for side in (-1, 1):
            pieces.append(box("impost", (0.26, t + 0.1, 0.14), (side * (ow + 0.08), 0, rect_h), "stone_dark",
                              bevel=0.02))
            pieces.append(box("jambbase", (0.24, t + 0.08, 0.3), (side * (ow + 0.1), 0, 0.15), "stone_dark",
                              bevel=0.03))
        # round vent in the gable
        rv = E.round_window(0.2, frame="stone", glass="charcoal")
        place(rv, (0, -t / 2, rect_h + ow + 0.55))
        pieces += rv
        if sy > 0:
            place(pieces, (0, y, 0), 180)
        else:
            place(pieces, (0, y, 0), 0)
        # cut the plinth through the opening: plinth only under the piers
        p += pieces
        p += [box("endplinth", ((W / 2 - ow) + 0.04, t + 0.08, 0.25), (sx2 * (W / 2 + ow) / 2, y, 0.125), "stone_dark",
                  bevel=0.03) for sx2 in (-1, 1)]
    # pilasters
    for sx in (-1, 1):
        for y in (-D / 2 + 0.1, 0, D / 2 - 0.1):
            p.append(box("pilaster", (0.06, 0.26, H - 0.25), (sx * (W / 2 + 0.03), y, 0.25 + (H - 0.25) / 2),
                         "red_dark", bevel=0.015))
    # side windows (stone lintel + sill), each side
    for wall in ("+x", "-x"):
        for u in (-1.0, 1.0):
            wp = E.window(0.62, 0.8, frame="white", border=0.07)
            wp.append(box("lintel", (0.86, 0.12, 0.14), (0, -0.03, 0.48), "stone", bevel=0.02))
            p += put(wp, wall, W, D, u, 1.4)
    # roof + smoke vent lantern on the ridge
    roof, rz2 = E.gable_roof(D, W, H, pitch, overhang=0.15, eave=0.25, ridge_axis="Y",
                             tiles=("roof_grey", "roof_grey2"))
    p += roof
    for y in (-1.0, 1.0):     # smoke vents over the engine road
        p.append(box("smokevent", (0.36, 0.36, 0.5), (0, y, rz + 0.2), "red_dark", bevel=0.03))
        p.append(box("ventcap", (0.5, 0.5, 0.08), (0, y, rz + 0.5), "charcoal", bevel=0.025))
        p.append(lathe("venthood", [(0.0, rz + 0.52), (0.3, rz + 0.52), (0.0, rz + 0.72)], (0, y, 0), "charcoal",
                       segs=4, rot=(0, 0, math.pi / 4), smooth_deg=20))
    return assemble(p, "Depot")


def build_windmill():
    p = []
    rb, rt, zb, zt = 1.22, 0.84, 0.55, 3.7
    rad = lambda z: rb + (rt - rb) * (z - zb) / (zt - zb)
    p.append(lathe("base", [(1.42, 0), (1.42, 0.45), (1.32, 0.55), (0.0, 0.56)], (0, 0, 0), "stone", segs=24,
                   smooth_deg=40))
    prof = [(rb, zb - 0.02)]
    for k in range(1, 9):
        z = zb + (zt - zb) * k / 8
        prof.append((rad(z), z))
    prof.append((0.0, zt))
    p.append(lathe("tower", prof, (0, 0, 0), "wall_cream", segs=24))
    for z in (zb + 0.02, 2.0, zt - 0.02):
        p.append(T.torus("band", rad(z) + 0.01, 0.045, (0, 0, z), E.m("white" if z < 3 else "roof_red2"),
                         major_segs=24, minor_segs=5))
    # gallery (stage) with railing
    gz = 2.0
    p.append(lathe("stage", [(rad(gz) - 0.02, gz - 0.06), (1.62, gz - 0.06), (1.62, gz + 0.04), (rad(gz) - 0.02,
                                                                                               gz + 0.04)],
                   (0, 0, 0), "oak", segs=24, smooth_deg=30))
    for k in range(16):
        a = TAU * k / 16
        p.append(box("rail_post", (0.05, 0.05, 0.5), (math.cos(a) * 1.56, math.sin(a) * 1.56, gz + 0.28), "white"))
        if k % 2 == 0:
            p.append(box("strut", (0.05, 0.05, 0.62), (math.cos(a) * 1.3, math.sin(a) * 1.3, gz - 0.26), "oak",
                         rot=(0, math.radians(52), a)))
    p.append(T.torus("rail", 1.56, 0.03, (0, 0, gz + 0.53), E.m("white"), major_segs=32, minor_segs=5))
    # door with stone step at the front, windows on the sides/back
    dd = E.door(0.68, 1.3, "red", "white", planks=3, step="stone")
    p += place(dd, (0, -rad(0.6) + 0.03, 0.56))
    for yaw, z in ((90, 1.2), (-90, 1.2), (180, 1.3), (90, 2.9), (-90, 2.9), (180, 2.9)):
        wp = E.window(0.48, 0.6, shutters="paint_green" if z < 2 else None)
        p += place(wp, (0, 0, 0), yaw, (0, -rad(z) - 0.02, z))
    # cap
    cap = lathe("cap", [(0.0, zt - 0.02), (0.98, zt - 0.02), (1.02, zt + 0.08), (0.98, zt + 0.42), (0.78, zt + 0.82),
                        (0.48, zt + 1.08), (0.18, zt + 1.2), (0.0, zt + 1.22)], (0, 0, 0), "roof_red", segs=24,
                smooth_deg=70)
    p.append(cap)
    for z, r in ((zt + 0.42, 0.985), (zt + 0.82, 0.79)):
        p.append(T.torus("capring", r, 0.03, (0, 0, z), E.m("roof_red2"), major_segs=24, minor_segs=4))
    p.append(sph("finial", 0.12, (0, 0, zt + 1.32), "gold", segs=10, rings=7))
    hub_z, hub_y = zt + 0.45, -1.68
    p.append(box("capnose", (0.5, 0.5, 0.45), (0, -0.9, hub_z), "roof_red2", bevel=0.08, segments=2))
    root = assemble(p, "Windmill")
    # sails: windshaft + hub + 4 lattice sails in the XZ plane, rotating about Blender Y
    s = []
    shaft = cyl("shaft", 0.1, 0.65, (0, -1.35, hub_z), "walnut", verts=12, rot=(math.pi / 2, 0, 0))
    s.append(shaft)
    s.append(lathe("hub", [(0.0, -0.12), (0.2, -0.12), (0.24, 0.0), (0.2, 0.1), (0.1, 0.18), (0.0, 0.2)],
                   (0, hub_y, hub_z), "red", segs=16, rot=(math.pi / 2, 0, 0)))
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        arm = []
        L = 2.55
        arm.append(box("stock", (0.09, 0.08, L), (0, 0, L / 2 + 0.05), "walnut", bevel=0.015))
        for off in (0.14, 0.62):
            arm.append(box("rail", (0.04, 0.05, L - 0.5), (off, 0, 0.5 + (L - 0.5) / 2 + 0.05), "white"))
        for j in range(9):
            z = 0.55 + j * (L - 0.55) / 8
            arm.append(box("bar", (0.58, 0.04, 0.035), (0.36, 0.0, z), "white"))
        arm.append(box("cloth", (0.44, 0.02, L - 0.9), (0.38, 0.03, 0.55 + (L - 0.9) / 2 + 0.1), "cream",
                       bevel=0.01))
        for q in arm:
            q.matrix_basis = Matrix_rot_y(-a) @ q.matrix_basis
        place(arm, (0, hub_y - 0.06, hub_z))
        s += arm
    sails = assemble(s, "Sails")
    attach(sails, root, (0, hub_y, hub_z))
    return root


def Matrix_rot_y(a):
    return Matrix.Rotation(a, 4, 'Y')


def build_well():
    p = []
    # stone wall of staggered blocks around a round basin
    for course in range(2):
        n = 9
        for k in range(n):
            a = TAU * (k + 0.5 * course) / n
            r = 0.62
            p.append(box("block", (0.24, 0.43, 0.27), (math.cos(a) * r, math.sin(a) * r, 0.15 + course * 0.28),
                         "stone" if (k + course) % 3 else "stone_dark", bevel=0.04, segments=1, rot=(0, 0, a)))
    p.append(lathe("coping", [(0.46, 0.58), (0.8, 0.58), (0.84, 0.62), (0.8, 0.68), (0.46, 0.68), (0.44, 0.0)],
                   (0, 0, 0), "stone", segs=20, smooth_deg=40))
    p.append(cyl("water", 0.47, 0.04, (0, 0, 0.45), "water", verts=20))
    p.append(cyl("innerwall", 0.48, 0.45, (0, 0, 0.225), "stone_dark", verts=20))
    # posts + roof
    for sx in (-1, 1):
        p.append(box("post", (0.12, 0.12, 1.75), (sx * 0.72, 0, 0.6 + 1.75 / 2 - 0.05), "oak", bevel=0.02))
        p.append(box("brace", (0.07, 0.07, 0.42), (sx * 0.6, 0, 2.08), "oak", rot=(0, sx * 0.75, 0)))
    p.append(box("crossbeam", (1.62, 0.12, 0.12), (0, 0, 2.28), "oak", bevel=0.02))
    roof, rz = E.gable_roof(1.6, 1.25, 2.34, 40, overhang=0.08, eave=0.14, ridge_axis="X",
                            tiles=("roof_red", "roof_red2"), rows=3)
    p += roof
    p.append(prism("wgable", [(-0.62, 0), (0.62, 0), (0, 0.62 * math.tan(math.radians(40)))], 0.04, (0, 0, 2.34), "oak",
                   rot=(0, 0, math.pi / 2)))
    p[-1].location = (0.74, 0, 2.34)
    g2 = prism("wgable", [(-0.62, 0), (0.62, 0), (0, 0.62 * math.tan(math.radians(40)))], 0.04, (-0.74, 0, 2.34),
               "oak", rot=(0, 0, math.pi / 2))
    p.append(g2)
    # windlass, rope, bucket and crank
    p.append(cyl("windlass", 0.08, 1.44, (0, 0, 1.55), "beech", verts=12, rot=(0, math.pi / 2, 0)))
    p.append(cyl("ropecoil", 0.1, 0.5, (0, 0, 1.55), "straw", verts=12, rot=(0, math.pi / 2, 0)))
    p.append(cyl("rope", 0.015, 0.55, (0.0, -0.1, 1.25), "straw", verts=5))
    p.append(lathe("bucket", [(0.0, 0.82), (0.13, 0.82), (0.16, 1.02), (0.15, 1.04), (0.0, 1.04)], (0.0, -0.1, 0),
                   "oak", segs=14))
    for z in (0.86, 0.99):
        p.append(T.torus("hoop", 0.14 + (z - 0.82) * 0.15, 0.012, (0, -0.1, z), E.m("charcoal"), major_segs=14,
                         minor_segs=4))
    p.append(T.torus("handle", 0.15, 0.012, (0, -0.1, 1.05), E.m("charcoal"), rot=(0, math.pi / 2, 0),
                     major_segs=12, minor_segs=4))
    p.append(box("crankarm", (0.05, 0.05, 0.32), (0.84, 0, 1.43), "charcoal"))
    p.append(cyl("crankgrip", 0.03, 0.18, (0.92, 0, 1.3), "red", verts=8, rot=(0, math.pi / 2, 0)))
    return assemble(p, "Well")


# ================================================================================================ PROPS
def build_fence():
    p = []
    for x in (-0.94, 0.0, 0.94):
        p.append(box("post", (0.1, 0.1, 0.78), (x, 0, 0.39), "oak", bevel=0.02))
        p.append(lathe("postcap", [(0.0, 0.775), (0.085, 0.775), (0.085, 0.8), (0.0, 0.88)], (x, 0, 0), "oak", segs=4,
                       rot=(0, 0, math.pi / 4), smooth_deg=20))
    for z in (0.32, 0.62):
        p.append(box("rail", (2.0, 0.05, 0.11), (0, -0.07, z), "beech", bevel=0.018))
    for x0 in (-0.47, 0.47):
        p.append(box("diag", (0.045, 0.04, 0.42), (x0, -0.105, 0.47), "beech", bevel=0.01, rot=(0, 0.95, 0)))
    for x in (-0.94, 0.0, 0.94):
        for k in range(3):
            a = TAU * k / 3 + x
            p.append(E.blade("grass", (x + math.cos(a) * 0.07, math.sin(a) * 0.07, 0), 0.16,
                             (math.cos(a) * 0.07, math.sin(a) * 0.07), 0.025, "grass_dark", segs=3))
    return assemble(p, "Fence")


def build_sign_railway():
    p = [box("base", (0.34, 0.34, 0.12), (0, 0, 0.06), "grey_light", bevel=0.03, segments=2)]
    p.append(cyl("pole", 0.05, 2.0, (0, 0.02, 1.06), "grey_light", verts=12))
    for k in range(4):
        p.append(cyl("poleband", 0.052, 0.18, (0, 0.02, 0.25 + k * 0.36), "red", verts=12))
    # crossbuck
    for s in (-1, 1):
        p.append(box("buck", (0.95, 0.03, 0.15), (0, -0.05, 1.22), "white", bevel=0.02, rot=(0, s * 0.62, 0)))
        p.append(box("buckedge", (0.97, 0.025, 0.19), (0, -0.035, 1.22), "red", bevel=0.02, rot=(0, s * 0.62, 0)))
    # round sign with a little steam engine pictogram
    c = (0, -0.06, 1.78)
    p.append(cyl("disc", 0.36, 0.04, c, "white", verts=28, rot=(math.pi / 2, 0, 0)))
    p.append(T.torus("rim", 0.36, 0.045, c, E.m("red"), rot=(math.pi / 2, 0, 0), major_segs=28, minor_segs=6))
    p.append(cyl("discback", 0.36, 0.03, (0, -0.02, 1.78), "grey_light", verts=28, rot=(math.pi / 2, 0, 0)))
    zc, yf = 1.78, -0.09
    loco = [box("boiler", (0.26, 0.02, 0.1), (-0.04, yf, zc + 0.0), "black", bevel=0.01),
            box("cab", (0.11, 0.02, 0.18), (0.13, yf, zc + 0.04), "black", bevel=0.01),
            box("roof", (0.15, 0.02, 0.03), (0.13, yf, zc + 0.14), "black"),
            box("stack", (0.04, 0.02, 0.08), (-0.13, yf, zc + 0.08), "black"),
            box("dome", (0.05, 0.02, 0.04), (-0.03, yf, zc + 0.065), "black", bevel=0.01)]
    for x in (-0.12, -0.02, 0.11):
        loco.append(cyl("wheel", 0.045, 0.02, (x, yf, zc - 0.08), "black", verts=12, rot=(math.pi / 2, 0, 0)))
    loco.append(box("rail", (0.36, 0.02, 0.02), (0, yf, zc - 0.135), "black"))
    p += loco
    return assemble(p, "Sign_Railway")


def build_sign_arrow():
    p = [ico("mound", 0.2, (0, 0, 0), "grass_dark", scale=(1.3, 1.3, 0.35), subdiv=3, jitter=0.05)]
    p.append(box("post", (0.12, 0.12, 1.9), (0, 0, 0.95), "oak", bevel=0.02))
    p.append(lathe("cap", [(0.0, 1.89), (0.1, 1.89), (0.1, 1.93), (0.0, 2.05)], (0, 0, 0), "red", segs=4,
                   rot=(0, 0, math.pi / 4), smooth_deg=20))
    prof = [(-0.42, -0.1), (0.3, -0.1), (0.46, 0.0), (0.3, 0.1), (-0.42, 0.1)]
    for z, yaw, col, flip in ((1.65, 15, "yellow", 1), (1.38, -25, "sky", -1), (1.1, 60, "green", 1)):
        board = prism("arrow", [(x * flip, zz) for x, zz in prof][::flip], 0.04, (flip * 0.38, -0.08, 0), col,
                      bevel=0.012)
        stripe = box("stripe", (0.5, 0.012, 0.035), (flip * 0.3, -0.105, 0), "white")
        dots = [sph("dot", 0.03, (flip * (0.0 + k * 0.13), -0.1, 0), "white", segs=6, rings=4,
                    scale=(1, 0.3, 1)) for k in range(1)]
        grp = [board, stripe] + dots
        place(grp, (0, 0, z), yaw)
        p += grp
    return assemble(p, "Sign_Arrow")


def build_bench():
    return assemble(_bench_parts(1.4), "Bench")


def build_lamp():
    p = [lathe("post", [(0.17, 0.0), (0.17, 0.08), (0.13, 0.12), (0.12, 0.3), (0.07, 0.4), (0.06, 0.45),
                        (0.075, 0.5), (0.05, 0.56), (0.045, 2.1), (0.07, 2.16), (0.05, 2.22), (0.0, 2.24)], (0, 0, 0),
               "paint_green", segs=14)]
    for z in (0.95, 1.6):
        p.append(T.torus("collar", 0.05, 0.015, (0, 0, z), E.m("gold"), major_segs=12, minor_segs=4))
    p.append(box("ladderbar", (0.6, 0.04, 0.04), (0, 0, 1.95), "paint_green", bevel=0.01))
    for sx in (-1, 1):
        p.append(sph("barend", 0.035, (sx * 0.3, 0, 1.95), "gold", segs=8, rings=5))
    root = assemble(p, "Lamp")
    hz = 2.48
    h = [lathe("lantern_base", [(0.0, 2.2), (0.08, 2.22), (0.13, 2.28), (0.13, 2.31)], (0, 0, 0), "charcoal",
               segs=6, smooth_deg=20),
         lathe("glass", [(0.0, 2.3), (0.12, 2.3), (0.17, 2.6), (0.0, 2.6)], (0, 0, 0), "lamp_glow", segs=6,
               smooth_deg=20),
         lathe("lantern_cap", [(0.0, 2.6), (0.21, 2.6), (0.21, 2.64), (0.1, 2.76), (0.04, 2.8), (0.0, 2.8)],
               (0, 0, 0), "charcoal", segs=6, smooth_deg=20)]
    for k in range(6):
        a = TAU * k / 6
        b = box("bar", (0.025, 0.025, 0.32), (math.cos(a) * 0.145, math.sin(a) * 0.145, 2.45), "charcoal",
                rot=(0, 0, a))
        b.rotation_euler = (0, math.atan2(0.05, 0.3), a)
        h.append(b)
    h.append(sph("finial", 0.045, (0, 0, 2.84), "gold", segs=8, rings=5))
    head = assemble(h, "LampHead")
    attach(head, root, (0, 0, hz))
    return root


def build_haybale():
    prof = [(0.0, -0.5), (0.16, -0.5), (0.18, -0.52), (0.3, -0.5), (0.33, -0.48), (0.45, -0.5), (0.52, -0.47),
            (0.56, -0.4), (0.57, 0.0), (0.56, 0.4), (0.52, 0.47), (0.45, 0.5), (0.33, 0.48), (0.3, 0.5),
            (0.18, 0.52), (0.16, 0.5), (0.0, 0.5)]
    wob = lambda i, a: 1.0 + 0.015 * math.sin(a * 7 + i)
    b = lathe("bale", prof, (0, 0, 0), "straw", segs=24, radial=wob, smooth_deg=70)
    parts = [b]
    for z in (-0.25, 0.25):
        parts.append(T.torus("twine", 0.572, 0.012, (0, 0, z), E.m("red"), major_segs=24, minor_segs=4))
    place(parts, (0, 0, 0), 0)
    for q in parts:
        q.matrix_basis = Matrix_rot_y(math.pi / 2) @ q.matrix_basis
    place(parts, (0, 0, 0.56))
    return assemble(parts, "HayBale")


def _crate(c, size=0.62, yaw=0.0, fruit=None, seed=0):
    s = size
    x, y, z = c
    p = [box("core", (s - 0.06, s - 0.06, s - 0.04), (0, 0, s / 2), "groove")]
    for k in range(4):
        a = k * math.pi / 2
        for j in range(3):
            zz = 0.1 + j * (s - 0.16) / 2
            sl = box("slat", (s - 0.1, 0.04, 0.13), (0, -(s / 2 - 0.02), zz), "beech")
            place([sl], (0, 0, 0), math.degrees(a))
            p.append(sl)
    for sx in (-1, 1):
        for sy in (-1, 1):
            p.append(box("corner", (0.07, 0.07, s), (sx * (s / 2 - 0.03), sy * (s / 2 - 0.03), s / 2), "beech_dark",
                         bevel=0.012))
    if fruit:
        R = rng(seed)
        for k in range(9):
            p.append(sph("fruit", 0.085, ((k % 3 - 1) * 0.16 + R.uniform(-0.02, 0.02),
                                         (k // 3 - 1) * 0.16 + R.uniform(-0.02, 0.02), s - 0.06 + R.uniform(0, 0.03)),
                         fruit, segs=7, rings=5))
    place(p, (x, y, z), yaw)
    return p


def build_crate_stack():
    p = _crate((-0.34, 0, 0), yaw=3) + _crate((0.34, 0.03, 0), yaw=-4) + \
        _crate((0.0, 0.02, 0.62), yaw=12, fruit="red", seed=2)
    return assemble(p, "Crate_Stack")


def build_mailbox():
    p = [box("post", (0.1, 0.1, 1.0), (0, 0.05, 0.5), "oak", bevel=0.02),
         box("arm", (0.14, 0.4, 0.06), (0, 0.0, 0.98), "oak", bevel=0.015)]
    prof = [(-0.14, 0), (0.14, 0)] + [(0.14 * math.cos(math.pi * k / 8), 0.17 + 0.14 * math.sin(math.pi * k / 8))
                                      for k in range(9)]
    body = prism("box", prof, 0.48, (0, -0.02, 1.01), "paint_blue", bevel=0.02)
    p.append(body)
    p.append(prism("door", [(x * 1.03, z * 1.02) for x, z in prof], 0.03, (0, -0.27, 1.005), "blue_dark",
                   bevel=0.01))
    p.append(box("latch", (0.05, 0.03, 0.03), (0, -0.295, 1.12), "gold", bevel=0.008))
    # flag on the side (+X is the model's left)
    p.append(box("flagarm", (0.025, 0.025, 0.32), (0.16, 0.1, 1.2), "red_dark"))
    p.append(box("flag", (0.02, 0.15, 0.1), (0.16, 0.035, 1.31), "red", bevel=0.01))
    p.append(cyl("pivot", 0.025, 0.03, (0.155, 0.1, 1.08), "gold", verts=8, rot=(0, math.pi / 2, 0)))
    p.append(ico("mound", 0.2, (0, 0.05, 0), "grass_dark", scale=(1.2, 1.2, 0.3), subdiv=3, jitter=0.05))
    return assemble(p, "Mailbox")


def build_barrier_crossing():
    p = [box("base", (0.5, 0.5, 0.18), (0, 0, 0.09), "grey_light", bevel=0.03, segments=2)]
    p.append(cyl("post", 0.07, 1.0, (0, 0.06, 0.65), "white", verts=12))
    for k in range(2):
        p.append(cyl("postband", 0.072, 0.16, (0, 0.06, 0.3 + k * 0.32), "red", verts=12))
    p.append(box("housing", (0.3, 0.26, 0.36), (0, 0.06, 1.1), "yellow", bevel=0.04, segments=2))
    p.append(box("hood", (0.34, 0.3, 0.05), (0, 0.06, 1.3), "charcoal", bevel=0.02))
    for sx in (-1, 1):
        p.append(cyl("lamp", 0.06, 0.06, (sx * 0.09, -0.08, 1.45), "charcoal", verts=12, rot=(math.pi / 2, 0, 0)))
        p.append(sph("lens", 0.045, (sx * 0.09, -0.11, 1.45), "red", segs=10, rings=6, scale=(1, 0.5, 1)))
    p.append(box("lampbar", (0.3, 0.04, 0.04), (0, -0.05, 1.45), "charcoal"))
    p.append(box("lamppost", (0.04, 0.04, 0.14), (0, -0.0, 1.38), "charcoal"))
    root = assemble(p, "Barrier_Crossing")
    hinge = (0.0, -0.14, 1.05)
    a = [cyl("hinge", 0.06, 0.1, (0, -0.14, 1.05), "charcoal", verts=12, rot=(math.pi / 2, 0, 0))]
    n = 8
    L0, L1 = 0.12, 2.6
    seg = (L1 - L0) / n
    for k in range(n):
        x = L0 + seg * (k + 0.5)
        th = 0.11 - 0.03 * (k / n)
        a.append(box("armseg", (seg + 0.002, 0.07, th), (x, -0.16, 1.05), "red" if k % 2 == 0 else "white",
                     bevel=0.012))
    a.append(sph("tip", 0.045, (L1 + 0.01, -0.16, 1.05), "red", segs=8, rings=5))
    a.append(box("counter", (0.3, 0.1, 0.2), (-0.3, -0.16, 1.05), "charcoal", bevel=0.03, segments=2))
    a.append(box("counterarm", (0.3, 0.06, 0.06), (-0.12, -0.16, 1.05), "charcoal"))
    for k in range(3):
        a.append(box("reflector", (0.06, 0.02, 0.06), (0.5 + k * 0.8, -0.2, 1.05), "red_dark", bevel=0.01))
    arm = assemble(a, "Arm")
    attach(arm, root, hinge)
    return root


def build_pillar():
    p = [box("footing", (0.92, 0.92, 0.22), (0, 0, 0.11), "stone_dark", bevel=0.05, segments=2),
         box("plinth", (0.8, 0.8, 0.14), (0, 0, 0.29), "stone_dark", bevel=0.03, segments=2)]
    z0, z1 = 0.36, 1.66
    n = 5
    h = (z1 - z0) / n
    for k in range(n):
        z = z0 + h * (k + 0.5)
        mat = "stone" if k % 2 == 0 else "stone_dark"
        for j in (-1, 1):
            if k % 2 == 0:
                size, loc = (0.35, 0.7, h), (j * 0.175, 0, z)
            else:
                size, loc = (0.7, 0.35, h), (0, j * 0.175, z)
            p.append(box("block", size, loc, "stone" if (j + k) % 4 else "stone_dark", bevel=0.035, segments=1))
    p.append(box("capstone", (0.84, 0.84, 0.12), (0, 0, 1.72), "stone", bevel=0.03, segments=2))
    p.append(box("bearer", (0.76, 0.76, 0.06), (0, 0, 1.81), "oak", bevel=0.015))
    return assemble(p, "Pillar")


# ================================================================================================ DRIVER
REGISTRY = {}   # name -> (folder, builder, category, finalize kwargs)


def reg(name, folder, fn, cat, **fin):
    if cat == "building":
        fin.setdefault("ao_strength", 0.65)
    REGISTRY[name] = (folder, fn, cat, fin)


reg("Tree_Round", "Nature", build_tree_round, "tree")
reg("Tree_Pine", "Nature", build_tree_pine, "tree")
reg("Tree_Apple", "Nature", build_tree_apple, "tree")
reg("Tree_Birch", "Nature", build_tree_birch, "tree")
reg("Bush", "Nature", build_bush, "plant")
reg("Flowers_Red", "Nature", build_flowers_red, "plant", ao_distance=0.2)
reg("Flowers_Yellow", "Nature", build_flowers_yellow, "plant", ao_distance=0.2)
reg("Flowers_Purple", "Nature", build_flowers_purple, "plant", ao_distance=0.2)
reg("Rock_Large", "Nature", build_rock_large, "rock")
reg("Rock_Small", "Nature", build_rock_small, "rock", ao_distance=0.25)
reg("Grass_Tuft", "Nature", build_grass_tuft, "plant", ao_distance=0.15, ao_strength=0.5)
reg("Cloud_A", "Nature", build_cloud_a, "cloud", ground=False, ao_distance=1.2, ao_strength=0.25)
reg("Cloud_B", "Nature", build_cloud_b, "cloud", ground=False, ao_distance=1.2, ao_strength=0.25)
reg("Mushroom", "Nature", build_mushroom, "plant", ao_distance=0.2)

reg("Farmhouse", "Buildings", build_farmhouse, "building")
reg("Barn", "Buildings", build_barn, "building")
reg("House_A", "Buildings", build_house_a, "building")
reg("House_B", "Buildings", build_house_b, "building")
reg("Station", "Buildings", build_station, "building")
reg("Depot", "Buildings", build_depot, "building")
reg("Windmill", "Buildings", build_windmill, "building")
reg("Well", "Buildings", build_well, "building", ao_distance=0.4)
reg("Shop", "Buildings", build_shop, "building")

reg("Fence", "Props", build_fence, "prop", ao_distance=0.3)
reg("Sign_Railway", "Props", build_sign_railway, "prop", ao_distance=0.3)
reg("Sign_Arrow", "Props", build_sign_arrow, "prop", ao_distance=0.3)
reg("Bench", "Props", build_bench, "prop", ao_distance=0.3)
reg("Lamp", "Props", build_lamp, "prop", ao_distance=0.3)
reg("HayBale", "Props", build_haybale, "prop", ao_distance=0.3)
reg("Crate_Stack", "Props", build_crate_stack, "prop", ao_distance=0.3)
reg("Mailbox", "Props", build_mailbox, "prop", ao_distance=0.3)
reg("Barrier_Crossing", "Props", build_barrier_crossing, "prop", ao_distance=0.3)
reg("Pillar", "Props", build_pillar, "prop", ao_distance=0.4)

BUDGET = {"tree": 1800, "plant": 900, "rock": 900, "cloud": 1200, "building": 4500, "prop": 900}


def build_one(name, idx, do_preview):
    folder, fn, cat, fin = REGISTRY[name]
    bpy.ops.object.select_all(action='DESELECT')
    before = set(bpy.data.objects)
    POST.clear()
    root = fn()
    root.name = name
    root.location = (0, 0, 0)
    objs = [root] + list(root.children_recursive)
    for o in set(bpy.data.objects) - before - set(objs):     # stray helper objects: never export/bake them
        print("[ENV] removing stray object", o.name)
        bpy.data.objects.remove(o, do_unlink=True)
    T.finalize(objs, **fin)
    for o, kw in POST:
        E.gradient(o, **kw)
    T.export_fbx(f"{folder}/{name}", [root])
    v, t = T.stats(objs)
    mn, mx = T._bounds(objs)
    entry = {"name": name, "fbx": f"_Project/Art/Models/{folder}/{name}.fbx", "category": cat,
             "footprint": [round(mx.x - mn.x, 2), round(mx.y - mn.y, 2)], "height": round(mx.z, 2),
             "parts": [c.name for c in root.children_recursive], "verts": v}
    flag = "" if v <= BUDGET[cat] else "  !!! OVER BUDGET"
    print(f"[ENV] {name}: verts={v} tris={t} size={entry['footprint']} h={entry['height']}{flag}")
    if do_preview:
        E.preview([root], name)
    # park it far away so it neither shadows nor shows up in the next model's bake/renders
    root.location = (10000 + idx * 60, 0, 0)
    for c in root.children_recursive:
        c.name = f"{name}__{c.name}"          # free the child name ("Canopy", "Arm" ...) for the next model
    return root, entry


def lineup(roots, rows, out, spacing=1.0, size=(1600, 900)):
    """rows: list of lists of names. Lays them out left->right (Blender +X -> screen right with yaw 0)."""
    placed = []
    y = 0.0
    for row in rows:
        items = [roots[n] for n in row if n in roots]
        if not items:
            continue
        widths, depths = [], []
        for o in items:
            o.location = (0, 0, 0)
            bpy.context.view_layer.update()
            mn, mx = T._bounds([o] + list(o.children_recursive))
            widths.append((mn.x, mx.x))
            depths.append(mx.y - mn.y)
        total = sum(b - a for a, b in widths) + spacing * (len(items) - 1)
        x = -total / 2
        for o, (a, b) in zip(items, widths):
            o.location = (x - a, y, 0)
            x += (b - a) + spacing
            placed.append(o)
        y += max(depths) + spacing * 1.5
    bpy.context.view_layer.update()
    E.preview(placed, out, high=False, size=size, dist=1.05)
    for i, o in enumerate(placed):          # park again so the next lineup only shows its own models
        o.location = (20000 + i * 60, 0, 0)
    bpy.context.view_layer.update()


def main():
    argv = T.args()
    flags = [a for a in argv if a.startswith("--")]
    names = [a for a in argv if not a.startswith("--")] or list(REGISTRY)
    do_preview = "--no-preview" not in flags
    T.reset()
    manifest = {}
    if os.path.exists(MANIFEST):
        try:
            for e in json.load(open(MANIFEST)):
                manifest[e["name"]] = e
        except Exception:
            pass
    roots = {}
    for i, n in enumerate(names):
        root, entry = build_one(n, i, do_preview)
        roots[n] = root
        manifest[n] = entry
    order = [n for n in REGISTRY if n in manifest]
    with open(MANIFEST, "w") as f:
        json.dump([manifest[n] for n in order], f, indent=2)
    if "--no-lineup" not in flags:
        nature = [["Grass_Tuft", "Flowers_Red", "Flowers_Yellow", "Flowers_Purple", "Mushroom", "Rock_Small",
                   "Bush", "Rock_Large"],
                  ["Tree_Round", "Tree_Pine", "Tree_Apple", "Tree_Birch"], ["Cloud_A", "Cloud_B"]]
        if all(n in roots for r in nature for n in r):
            lineup(roots, nature, "Env_Nature_Lineup", spacing=0.6)
        bld = [["Well", "House_A", "House_B", "Shop", "Farmhouse"], ["Station", "Depot", "Barn", "Windmill"]]
        if all(n in roots for r in bld for n in r):
            lineup(roots, bld, "Env_Buildings_Lineup", spacing=1.2)
        props = [["Fence", "Bench", "Mailbox", "Crate_Stack", "HayBale", "Sign_Arrow", "Sign_Railway", "Lamp",
                  "Barrier_Crossing", "Pillar"]]
        if all(n in roots for r in props for n in r):
            lineup(roots, props, "Env_Props_Lineup", spacing=0.5, size=(1600, 600))


main()
