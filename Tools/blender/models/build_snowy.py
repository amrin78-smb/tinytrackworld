"""
Tiny Tracks World - Snowy Valley asset set (nature, props, buildings, animals).

Run:  blender -b --factory-startup --python Tools/blender/models/build_snowy.py -- [Name ...] [--no-preview] [Group]
      (no names = build everything + the group shot; "Group" = only re-render the group shot from the FBX files)
Exports Assets/_Project/Art/Models/<Folder>/<Name>.fbx and Tools/blender/models/snowy_manifest.json.
Previews go to $TT_SNOWY_PREVIEWS (default Logs/Blender/Snowy).

Animated parts (child objects, origin = pivot): Canopy (trees), Head / Tail (animals), Head / ArmL / ArmR (snowman).
Cabin_Snowy has an empty `SmokePoint` at the chimney top. Front faces -Y, model's right = -X.
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402

import tt_common as T  # noqa: E402
import env_lib as E  # noqa: E402
import creatures_lib as C  # noqa: E402
import snowy_lib as S  # noqa: E402
from env_lib import box, cyl, prism, place, assemble, attach  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
MANIFEST = os.path.join(HERE, "snowy_manifest.json")
TAU = math.pi * 2

POST = []   # (object, gradient kwargs) applied after finalize


def rng(seed):
    return np.random.default_rng(seed)


def lathe(name, profile, material, segs=12, radial=None, smooth_deg=60, loc=(0, 0, 0)):
    return E.lathe(name, profile, loc, S.m(material), segs=segs, radial=radial, smooth_deg=smooth_deg)


def sbox(name, size, loc=(0, 0, 0), material="sv_snow", bevel=0.0, segments=1, rot=(0, 0, 0)):
    return box(name, size, loc, S.m(material), bevel=bevel, segments=segments, rot=rot)


def scyl(name, r, depth, loc=(0, 0, 0), material="sv_snow", verts=12, rot=(0, 0, 0), bevel=0.0, segments=1,
         r_top=None):
    return cyl(name, r, depth, loc, S.m(material), verts=verts, rot=rot, bevel=bevel, segments=segments, r_top=r_top)


def ssph(name, r, loc=(0, 0, 0), material="sv_snow", scale=(1, 1, 1), segs=10, rings=6, rot=(0, 0, 0)):
    return E.sph(name, r, loc, S.m(material), scale=scale, segs=segs, rings=rings, rot=rot)


# ================================================================================================ NATURE
def _trunk(height, r0, r1, flare=1.5, segs=10, mat="bark", branches=()):
    prof = [(r0 * flare, 0.0), (r0 * 1.15, 0.12), (r0, 0.35)]
    for i in range(1, 5):
        t = i / 4
        prof.append((r0 + (r1 - r0) * t, 0.35 + (height - 0.35) * t))
    prof.append((0.0, height + 0.02))
    wob = lambda i, a: 1.0 + (0.08 * math.sin(a * 3 + i) if i < 2 else 0.0)
    parts = [lathe("trunk", prof, mat, segs=segs, radial=wob)]
    for (z, yaw, tilt, length, rad) in branches:
        dv = Vector((math.sin(math.radians(tilt)) * math.cos(math.radians(yaw)),
                     math.sin(math.radians(tilt)) * math.sin(math.radians(yaw)), math.cos(math.radians(tilt))))
        b = scyl("branch", rad, length, Vector((0, 0, z)) + dv * (length / 2), mat, verts=6, r_top=rad * 0.55)
        b.rotation_euler = dv.to_track_quat('Z', 'Y').to_euler()
        parts.append(b)
    return parts


def _base_snow(r_out, r_in, h, seed, segs=16):
    """Low wobbly snow ring hugging a trunk base."""
    R = rng(seed)
    ph = R.uniform(0, TAU, 3)
    prof = [(r_out, -0.01), (r_out * 0.92, h * 0.45), (r_out * 0.7, h * 0.85), (r_in * 1.6, h),
            (r_in * 1.05, h * 0.9)]

    def fn(i, a):
        k = 1.0 + 0.12 * math.sin(3 * a + ph[0]) + 0.06 * math.sin(5 * a + ph[1])
        r, z = prof[i]
        if i == len(prof) - 1:
            return r, z
        return r * k, z * (1.0 + 0.25 * math.sin(4 * a + ph[2])) if i > 0 else z
    return S.revolve("basesnow", len(prof), segs, fn, "sv_snow", smooth_deg=180)


def _pine_tiers(specs, segs, seed, cap_frac=0.74):
    """Pine tiers (like Tree_Pine) with a drippy snow cap on every tier. Returns parts."""
    parts = []
    R0 = rng(seed)
    for i, (z0, R, h) in enumerate(specs):
        last = i == len(specs) - 1
        prof = [(R * 0.3, z0 + 0.14), (R * 0.78, z0 + 0.0), (R * 0.97, z0 + 0.03), (R, z0 + 0.1),
                (R * 0.86, z0 + 0.2), (R * 0.52, z0 + h * 0.52), (R * 0.2, z0 + h * 0.84)]
        prof += [(R * 0.07, z0 + h * 0.97), (0.0, z0 + h)] if last else [(0.0, z0 + h * 0.9)]
        sc = lambda ri, a, ph=i * 0.37: 1.0 + (0.035 * math.cos(9 * a + ph) if ri in (1, 2, 3, 4) else 0.0)
        mat = "sv_pine"
        parts.append(lathe(f"tier{i}", prof, mat, segs=segs, radial=sc, smooth_deg=80))
        # --- snow cap following the tier's upper surface
        up = prof[3:]            # (R, ..) -> apex, radius descending
        rs = [p[0] for p in up][::-1]
        zs = [p[1] for p in up][::-1]

        def zsurf(r, rs=rs, zs=zs):
            return float(np.interp(r, rs, zs))
        apex_z = up[-1][1]
        ph = R0.uniform(0, TAU)
        nd = int(R0.integers(5, 7)) if not last else 4
        off = 0.06 if not last else 0.05
        cf = cap_frac if not last else 0.95
        drop = 0.07 * (0.6 + R / 2.0)

        def drip(a):
            return max(0.0, math.sin(nd * a + ph)) ** 1.6

        def fn(k, a, R=R, cf=cf, off=off, zsurf=zsurf, drip=drip, drop=drop):
            dr = drip(a)
            re = R * (cf + 0.1 * dr)
            if k == 0:
                return re * 0.94, zsurf(re) - 0.035 - drop * dr
            if k == 1:
                return re + 0.03, zsurf(re) + 0.015 - drop * dr * 0.8
            if k == 2:
                rr = re * 0.9
                return rr, zsurf(rr) + off * 0.9 - drop * dr * 0.3
            fr = [0.62, 0.38, 0.17][k - 3]
            rr = R * fr
            return rr, zsurf(rr) + off
        parts.append(S.revolve(f"cap{i}", 6, segs, fn, "sv_snow", apex=apex_z + off * 0.8, smooth_deg=180))
    return parts


def build_tree_snowy_pine():
    trunk = assemble(_trunk(1.2, 0.17, 0.1, flare=1.6, segs=10) + [_base_snow(0.55, 0.17, 0.14, 3)],
                     "Tree_SnowyPine")
    specs = [(0.62, 1.38, 1.4), (1.42, 1.12, 1.25), (2.18, 0.86, 1.1), (2.88, 0.6, 0.95), (3.5, 0.36, 0.95)]
    can = assemble(_pine_tiers(specs, 20, 5), "Canopy")
    attach(can, trunk, (0, 0, 0.7))
    POST.append((can, dict(bottom=0.62, top=1.1, normal_mix=0.75, tint_top=(0.2, 0.55, 0.3), only_mat="sv_pine")))
    return trunk


def build_tree_snowy_pine_small():
    trunk = assemble(_trunk(0.8, 0.12, 0.07, flare=1.6, segs=8) + [_base_snow(0.42, 0.12, 0.11, 4, segs=14)],
                     "Tree_SnowyPineSmall")
    specs = [(0.42, 0.95, 1.0), (1.0, 0.72, 0.9), (1.55, 0.48, 0.85)]
    can = assemble(_pine_tiers(specs, 16, 9), "Canopy")
    attach(can, trunk, (0, 0, 0.45))
    POST.append((can, dict(bottom=0.62, top=1.1, normal_mix=0.75, tint_top=(0.2, 0.55, 0.3), only_mat="sv_pine")))
    return trunk


def _ring_clumps(n, ring_r, z, r, seed, z_jit=0.25, r_jit=0.08, sc=(1, 1, 0.9), phase=0.3):
    R = rng(seed)
    out = []
    for k in range(n):
        a = TAU * k / n + phase + R.uniform(-0.2, 0.2)
        rr = ring_r + R.uniform(-0.1, 0.1)
        out.append(((math.cos(a) * rr, math.sin(a) * rr, z + R.uniform(-z_jit * 0.4, z_jit)),
                    r + R.uniform(-r_jit, r_jit), sc))
    return out


def build_tree_snowy_round():
    top = 1.45
    trunk = assemble(_trunk(top + 0.6, 0.17, 0.1, segs=10,
                            branches=[(1.15, 30, 42, 0.85, 0.07), (1.3, 200, 45, 0.8, 0.06),
                                      (1.4, 115, 38, 0.7, 0.055)]) + [_base_snow(0.5, 0.17, 0.12, 7)],
                     "Tree_SnowyRound")
    cl = [((0, 0, 2.45), 0.98, (1.05, 1.05, 0.9))] + _ring_clumps(6, 0.9, 2.08, 0.6, 21) + \
         [((0.2, -0.1, 3.08), 0.66, (1, 1, 0.9)), ((-0.32, 0.28, 2.9), 0.56, (1, 1, 0.9))]
    blob = E.blob("crown", cl, S.m("sv_frost"), subdiv=4, smooth_iter=1, noise=0.012, seed=3, centre=(0, 0, 2.4))
    snow = S.snow_shell("crown_snow", blob, nz_min=0.5, thick=0.08, wobble=0.3, freq=3.4, seed=4, ramp=0.14,
                        lumps=0.4)
    can = assemble([blob, snow], "Canopy")
    attach(can, trunk, (0, 0, top))
    POST.append((can, dict(bottom=0.72, top=1.1, normal_mix=0.55, tint_top=None, only_mat="sv_frost")))
    return trunk


def build_bush_snowy():
    cl = [((0, 0, 0.4), 0.48, (1.15, 1, 0.85)), ((0.5, 0.1, 0.3), 0.36, (1, 1, 0.85)),
          ((-0.48, -0.05, 0.28), 0.38, (1, 1, 0.85)), ((0.1, -0.36, 0.27), 0.32, (1, 1, 0.85)),
          ((-0.1, 0.38, 0.3), 0.34, (1, 1, 0.85))]
    b = E.blob("bush", cl, S.m("sv_bush"), subdiv=4, smooth_iter=2, noise=0.015, seed=2, centre=(0, 0, 0.3),
               flat_bottom=0.02, bottom_squash=0.1)
    b.data.update()
    S.trim_bottom(b)
    snow = S.snow_shell("bush_snow", b, nz_min=0.64, thick=0.06, wobble=0.3, freq=4.5, seed=6, ramp=0.1,
                        lumps=0.4)
    parts = [b, snow]
    R = rng(8)
    vs = [v for v in b.data.vertices if -0.1 < v.normal.z < 0.35 and v.co.z > 0.18]
    for i, k in enumerate(R.choice(len(vs), 6, replace=False)):
        v = vs[int(k)]
        parts.append(ssph("berry", 0.045, Vector(v.co) + Vector(v.normal) * 0.025, "sv_berry", segs=6, rings=4))
    o = assemble(parts, "Bush_Snowy")
    POST.append((o, dict(bottom=0.72, top=1.12, normal_mix=0.55, tint_top=(0.42, 0.78, 0.3), only_mat="sv_bush")))
    return o


def build_rock_snowy():
    def rock(name, spheres, centre, seed, subdiv=4):
        return E.blob(name, spheres, S.m("sv_rock"), subdiv=subdiv, smooth_iter=1, noise=0.035, seed=seed,
                      centre=centre, flat_bottom=0.0, bottom_squash=0.05)
    a = rock("r0", [((0, 0, 0.32), 0.68, (1.3, 1.0, 0.85)), ((0.32, 0.15, 0.55), 0.45, (1, 1, 0.9)),
                    ((-0.36, -0.1, 0.4), 0.44, (1, 1, 0.85))], (0, 0, 0.28), 1)
    b = rock("r1", [((0.9, -0.42, 0.11), 0.34, (1.15, 1, 0.75)), ((1.05, -0.28, 0.1), 0.22, (1, 1, 0.8))],
             (0.95, -0.38, 0.07), 2, subdiv=3)
    S.trim_bottom(a)
    S.trim_bottom(b)
    sa = S.snow_shell("snow0", a, nz_min=0.45, thick=0.09, wobble=0.3, freq=3.0, seed=2, ramp=0.14, lumps=0.4)
    sb = S.snow_shell("snow1", b, nz_min=0.5, thick=0.055, wobble=0.2, freq=4.0, seed=3, ramp=0.08)
    o = assemble([a, b, sa, sb], "Rock_Snowy")
    POST.append((o, dict(bottom=0.8, top=1.08, normal_mix=0.7, only_mat="sv_rock")))
    return o


def build_snowdrift():
    cl = [((0, 0, 0.0), 0.62, (1.35, 1.0, 0.62)), ((0.62, 0.12, 0.0), 0.45, (1.2, 1, 0.6)),
          ((-0.6, -0.1, 0.0), 0.48, (1.1, 1, 0.55)), ((0.15, 0.4, 0.0), 0.36, (1.2, 1, 0.55)),
          ((-0.15, -0.38, 0.0), 0.3, (1.2, 1, 0.5))]
    o = E.blob("drift", cl, S.m("sv_snow"), subdiv=4, smooth_iter=3, noise=0.008, seed=5, centre=(0, 0, 0.0),
               flat_bottom=0.0, bottom_squash=0.0)
    S.trim_bottom(o, z=0.01)
    return assemble([o], "Snowdrift")


# ================================================================================================ PROPS
def _on(c, r, d, inset=0.0):
    """Point on a sphere (centre c, radius r) in direction d, pushed in by inset."""
    return Vector(c) + Vector(d).normalized() * (r - inset)


def _striped(obj, names, fn):
    """Recolours faces of obj: fn(face centre) -> slot index into names."""
    T.apply(obj)
    S.mats(obj, names)
    idx = [int(fn(p.center)) for p in obj.data.polygons]
    obj.data.polygons.foreach_set("material_index", idx)
    obj.data.update()
    return obj


def build_snowman():
    P = []
    base = S.ell("base", (0, 0, 0.37), (0.43, 0.43, 0.40), "sv_snowman", 14, 9)
    mid = S.ell("mid", (0, 0, 0.9), (0.3, 0.3, 0.29), "sv_snowman", 14, 8)
    S.cull_inside(mid, (0, 0, 0.37), (0.43, 0.43, 0.40), margin=0.03)
    S.cull_inside(base, (0, 0, 0.9), (0.3, 0.3, 0.29), margin=0.05)
    S.trim_bottom(base, z=0.02)
    P += [base, mid]
    # coal buttons on the middle ball
    for k, el in enumerate((0.3, -0.05, -0.42)):
        P.append(S.ball("button", _on((0, 0, 0.9), 0.29, (0, -1, el), 0.006), 0.03, "sv_coal", 6, 3))
    # striped scarf around the neck + a hanging end on the model's right (-X)
    sc = S.torus("scarf", 0.185, 0.062, (0, 0, 1.13), "sv_scarf", major_segs=14, minor_segs=5)
    _striped(sc, ["sv_scarf", "sv_scarf2"], lambda c: (int((math.atan2(c.y, c.x) + math.pi) / (TAU / 14))) % 2)
    P.append(sc)
    tail_keys = [((-0.11, -0.16, 1.1), 0.06, 0.022), ((-0.15, -0.23, 1.0), 0.062, 0.022),
                 ((-0.17, -0.27, 0.88), 0.064, 0.022), ((-0.175, -0.285, 0.8), 0.066, 0.022)]
    P.append(S.loft("scarf_end", tail_keys, segs=6, res=2, materials=("sv_scarf", "sv_scarf2"),
                    up=(0, -1, 0.3), exp=2.6, paint=lambda i, n, s_, c: 1 if (i // 2) % 2 == 1 else 0))
    # ---- head (pivot at the neck)
    H = []
    hc, hr = Vector((0, 0, 1.32)), 0.215
    head = S.ell("head", hc, (hr, hr, hr * 0.97), "sv_snowman", 14, 9)
    S.cull_inside(head, hc, (1, 1, 1), zmin=1.47)                      # under the hat
    S.cull_inside(head, (0, 0, 0.9), (0.3, 0.3, 0.29), margin=0.04)    # inside the middle ball
    H.append(head)
    for sx in (1, -1):
        H += S.eye(f"eye{sx}", _on(hc, hr, (sx * 0.36, -1, 0.17), 0.01), 0.03, (sx * 0.3, -1, 0.15), sclera=False,
                   iris="sv_coal", psegs=8, second_hl=False, prings=4, hl_segs=(5, 3))
        H.append(S.ell(f"cheek{sx}", _on(hc, hr, (sx * 0.62, -1, -0.2), 0.012), (0.04, 0.012, 0.026), "cheek",
                       6, 3, rot=(0, 0, sx * -0.55)))
    # carrot nose
    n0 = _on(hc, hr, (0, -1, 0.0), 0.02)
    H.append(S.tube("carrot", [n0, n0 + Vector((0, -0.09, -0.012)), n0 + Vector((0, -0.17, -0.03))], 0.04,
                    "sv_carrot", segs=8, radius_end=0.006, dome_end=0.008, res=1, dome_rings=2))
    # coal smile
    for k in range(5):
        a = math.radians(-50 + k * 25)
        H.append(S.ball("smile", _on(hc, hr, (math.sin(a) * 0.55, -1, -0.42 - math.cos(a) * 0.12), 0.006), 0.017,
                        "sv_coal", 6, 3))
    # knitted beanie with a pompom
    hat = [(0.17, 1.415), (0.212, 1.42), (0.226, 1.455), (0.212, 1.49), (0.186, 1.5),     # rolled band
           (0.185, 1.51), (0.172, 1.565), (0.128, 1.62), (0.064, 1.648)]
    H.append(S.revolve("hat", len(hat), 12, lambda i, a: hat[i], "sv_hat", apex=1.655, smooth_deg=70,
                       materials=["sv_scarf2", "sv_hat"], paint=lambda i, s_: 0 if i < 4 else 1))
    H.append(S.ball("pompom", (0, 0, 1.69), 0.06, "sv_scarf2", 8, 4))
    # ---- stick arms (pivot at the shoulder); model's right = -X
    arms = []
    for sx, nm in ((-1, "ArmR"), (1, "ArmL")):
        sh = Vector((sx * 0.25, 0.0, 1.0))
        el = Vector((sx * 0.48, -0.03, 1.12))
        hand = Vector((sx * 0.64, -0.05, 1.27))
        A = [S.tube("arm", [sh, el, hand], 0.024, "sv_twig", segs=6, radius_end=0.014, dome_end=0.012, res=1,
                    dome_rings=2)]
        A.append(S.tube("finger", [hand - (hand - el) * 0.15, hand + Vector((sx * 0.1, -0.01, 0.0))], 0.012,
                        "sv_twig", segs=5, radius_end=0.008, dome_end=0.008, res=1, dome_rings=2))
        A.append(S.tube("finger", [hand - (hand - el) * 0.1, hand + Vector((sx * 0.02, -0.01, 0.11))], 0.012,
                        "sv_twig", segs=5, radius_end=0.008, dome_end=0.008, res=1, dome_rings=2))
        if sx > 0:      # one little side twig (left arm only) - asymmetry reads more hand-made
            A.append(S.tube("twig", [el, el + Vector((sx * 0.03, -0.01, 0.1))], 0.011, "sv_twig", segs=5,
                            radius_end=0.007, dome_end=0.007, res=1, dome_rings=2))
        arms.append(C.part(A, nm, sh))
    root = T.join(P, "Snowman")
    hd = C.part(H, "Head", (0, 0, 1.13))
    return root, [hd] + arms


def build_sled():
    p = []
    prof = [(0.026 * math.cos(a), 0.018 * math.sin(a)) for a in [TAU * k / 8 for k in range(8)]]
    path = [(0, 0.47, 0.06), (0, 0.44, 0.025), (0, 0.3, 0.02), (0, -0.3, 0.02), (0, -0.42, 0.04),
            (0, -0.52, 0.1), (0, -0.565, 0.19), (0, -0.55, 0.28), (0, -0.5, 0.33), (0, -0.43, 0.33),
            (0, -0.4, 0.29)]
    for sx in (-1, 1):
        r = E.sweep_fix("runner", [(sx * 0.25, y, z) for (_, y, z) in path], prof, S.m("sv_runner"), side=(1, 0, 0))
        T.smooth(r, 60)
        p.append(r)
        for y in (-0.3, 0.02, 0.32):
            p.append(scyl("strut", 0.022, 0.2, (sx * 0.25, y, 0.13), "sv_runner", verts=8))
    # deck slats + battens
    for k in range(5):
        x = -0.24 + k * 0.12
        p.append(sbox("slat", (0.1, 0.86, 0.035), (x, 0.02, 0.255), "beech", bevel=0.014, segments=2))
    for y in (-0.3, 0.02, 0.32):
        p.append(sbox("batten", (0.6, 0.07, 0.04), (0, y, 0.222), "beech_dark", bevel=0.012))
    p.append(scyl("frontbar", 0.024, 0.56, (0, -0.44, 0.31), "sv_runner", verts=8, rot=(0, math.pi / 2, 0)))
    # pull rope
    rope = [(0.2, -0.45, 0.31), (0.17, -0.62, 0.2), (0.08, -0.76, 0.1), (0.0, -0.79, 0.08), (-0.08, -0.76, 0.1),
            (-0.17, -0.62, 0.2), (-0.2, -0.45, 0.31)]
    p.append(S.tube("rope", rope, 0.012, "sv_rope", segs=6, res=3))
    return assemble(p, "Sled")


def build_lamp_snowy():
    p = [lathe("post", [(0.17, 0.0), (0.17, 0.08), (0.13, 0.12), (0.12, 0.3), (0.07, 0.4), (0.06, 0.45),
                        (0.075, 0.5), (0.05, 0.56), (0.045, 2.12), (0.07, 2.18), (0.05, 2.22), (0.0, 2.24)],
               "sv_post", segs=12)]
    for z in (0.95, 1.6):
        p.append(S.torus("collar", 0.05, 0.015, (0, 0, z), "gold", major_segs=12, minor_segs=4))
    # snow on the base
    p.append(S.revolve("basesnow", 3, 12, lambda i, a: [(0.19, 0.075), (0.15, 0.13 + 0.015 * math.sin(3 * a)),
                                                         (0.07, 0.15 + 0.02 * math.sin(2 * a + 1))][i],
                       "sv_snow", smooth_deg=180))
    # red ribbon bow on the post (front)
    bz = 1.78
    p.append(S.torus("ribbon", 0.052, 0.014, (0, 0, bz), "sv_scarf", major_segs=12, minor_segs=4))
    for sx in (-1, 1):
        p.append(S.ell("bowloop", (sx * 0.075, -0.075, bz + 0.02), (0.07, 0.022, 0.045), "sv_scarf", 10, 6,
                       rot=(0, sx * 0.35, sx * 0.4)))
        p.append(S.loft("bowtail", [((sx * 0.02, -0.07, bz - 0.01), 0.022, 0.007),
                                    ((sx * 0.06, -0.08, bz - 0.12), 0.025, 0.007),
                                    ((sx * 0.08, -0.075, bz - 0.2), 0.028, 0.007)], segs=6, res=2,
                        materials=("sv_scarf",), up=(0, -1, 0)))
    p.append(S.ball("bowknot", (0, -0.07, bz + 0.005), 0.03, "sv_scarf", 8, 5))
    root = assemble(p, "Lamp_Snowy")
    h = [lathe("lantern_base", [(0.0, 2.2), (0.08, 2.22), (0.13, 2.28), (0.13, 2.31)], "charcoal", segs=6,
               smooth_deg=20),
         lathe("glass", [(0.0, 2.3), (0.12, 2.3), (0.17, 2.6), (0.0, 2.6)], "sv_glow", segs=6, smooth_deg=20),
         lathe("lantern_cap", [(0.0, 2.6), (0.21, 2.6), (0.21, 2.64), (0.1, 2.76), (0.04, 2.8), (0.0, 2.8)],
               "charcoal", segs=6, smooth_deg=20)]
    for k in range(6):
        a = TAU * k / 6
        b = sbox("bar", (0.025, 0.025, 0.32), (math.cos(a) * 0.145, math.sin(a) * 0.145, 2.45), "charcoal")
        b.rotation_euler = (0, math.atan2(0.05, 0.3), a)
        h.append(b)

    # snow cap with soft drips on the lantern roof
    def capfn(i, a):
        dr = max(0.0, math.sin(5 * a + 0.4)) ** 1.6
        return [(0.2 + 0.01 * dr, 2.635 - 0.045 * dr), (0.235 + 0.008 * dr, 2.665 - 0.03 * dr),
                (0.17, 2.74), (0.09, 2.81), (0.04, 2.845)][i]
    h.append(S.revolve("capsnow", 5, 14, capfn, "sv_snow", apex=2.86, smooth_deg=180))
    h.append(ssph("finial", 0.04, (0, 0, 2.89), "gold", segs=8, rings=5))
    head = assemble(h, "LampHead")
    attach(head, root, (0, 0, 2.48))
    return root


# ================================================================================================ BUILDINGS
def _log(name, length, r, centre, axis, mat, verts=9):
    S.m(mat)
    S.m("sv_log_end")
    rot = (0, math.pi / 2, 0) if axis == "X" else (math.pi / 2, 0, 0)
    o = scyl(name, r, length, centre, mat, verts=verts, rot=rot, bevel=0.035, segments=1)
    T.apply(o)
    ax = 0 if axis == "X" else 1
    E.tone_faces(o, "sv_log_end", lambda p: abs(p.normal[ax]) > 0.9)
    return o


def _snow_sill(w):
    return sbox("sillsnow", (w + 0.1, 0.12, 0.06), (0, -0.06, 0), "sv_snow", bevel=0.028, segments=2)


def build_cabin_snowy():
    w, d, r, dz = 3.2, 3.4, 0.13, 0.235
    S.m("sv_door"), S.m("sv_plank"), S.m("sv_window"), S.m("sv_roof"), S.m("sv_stone"), S.m("cream")
    p = [sbox("plinth", (w + 0.16, d + 0.16, 0.2), (0, 0, 0.1), "sv_stone2", bevel=0.05, segments=2)]
    z0 = 0.2 + r
    logm = ["sv_log", "sv_log2"]
    for k in range(8):
        for sy in (-1, 1):
            p.append(_log("flog", w + 0.5, r, (0, sy * d / 2, z0 + k * dz), "X", logm[k % 2]))
        for sx in (-1, 1):
            p.append(_log("slog", d + 0.5, r, (sx * w / 2, 0, z0 + dz / 2 + k * dz), "Y", logm[(k + 1) % 2]))
    Hr = z0 + dz / 2 + 7 * dz + r            # top of the side walls = roof base at the eaves
    run = w / 2 + r + 0.02
    pitch = math.radians(40)
    rise = run * math.tan(pitch)
    ridge = Hr + rise
    # gable ends: shortening logs + a plank backing
    for sy in (-1, 1):
        k = 8
        while True:
            z = z0 + k * dz
            if z > ridge - 0.32:
                break
            hw = run * (1 - (z - Hr) / rise)
            p.append(_log("glog", 2 * hw + 0.1, r * 0.95, (0, sy * d / 2, z), "X", logm[k % 2]))
            k += 1
        p.append(prism("gable", [(-run, Hr - 0.15), (run, Hr - 0.15), (0, ridge)], 0.1, (0, sy * (d / 2 - 0.04), 0),
                       S.m("sv_plank"), rot=(0, 0, 0)))
    # roof: red slab + thick rounded snow layer + ridge roll + drips + icicles
    L = d + 0.9
    eave = 0.38
    R = rng(31)
    for sgn in (-1, 1):
        dv = Vector((sgn * run, 0, -rise)).normalized()
        nv = Vector((sgn * rise, 0, run)).normalized()
        top = Vector((0, 0, ridge))
        slope = Vector((sgn * run, 0, -rise)).length
        beta = math.atan2(-dv.z, dv.x)
        ln = slope + eave + 0.08
        c = top + dv * (ln / 2 - 0.08) + nv * 0.065
        p.append(sbox("roofslab", (ln, L, 0.13), c, "sv_roof", bevel=0.03, segments=1, rot=(0, beta, 0)))
        sl = ln - 0.02
        c2 = top + dv * (sl / 2 - 0.08) + nv * (0.13 + 0.08)
        p.append(sbox("roofsnow", (sl, L + 0.06, 0.2), c2, "sv_snow", bevel=0.085, segments=3, rot=(0, beta, 0)))
        edge = top + dv * (ln - 0.1)
        ny = 9
        for i in range(ny):
            y = -L / 2 + 0.25 + (L - 0.5) * (i + R.uniform(-0.2, 0.2)) / (ny - 1)
            pt = edge + nv * 0.2 + Vector((0, y, -0.02))
            k = R.uniform(0.8, 1.15)
            p.append(S.ell("drip", pt, (0.13 * k, 0.17 * k, 0.11 * k * R.uniform(1.0, 1.4)), "sv_snow", 8, 5))
        for i in range(11):
            y = -L / 2 + 0.3 + (L - 0.6) * (i + R.uniform(-0.3, 0.3)) / 10
            pt = edge + Vector((0, y, -0.02)) - nv * 0.01
            p.append(S.icicle("icicle", (pt.x, pt.y, pt.z), R.uniform(0.16, 0.34), R.uniform(0.03, 0.042), segs=5))
    rz = ridge + 0.33 / math.cos(pitch) - 0.05
    p.append(scyl("ridgesnow", 0.17, L + 0.06, (0, 0, rz), "sv_snow", verts=14, rot=(math.pi / 2, 0, 0), bevel=0.08,
                  segments=2))
    # chimney: stacked stones, dark flue, little snow cap
    cx, cy = 0.9, 0.85
    zc = Hr + 0.1
    top_z = ridge + 0.55
    n = 7
    hstep = (top_z - zc) / n
    for i in range(n):
        jit = R.uniform(-0.02, 0.02)
        p.append(sbox("chim", (0.56 + jit, 0.56 - jit, hstep + 0.02), (cx, cy, zc + hstep * (i + 0.5)),
                      ["sv_stone", "sv_stone2"][i % 2], bevel=0.045, segments=2))
    p.append(sbox("chimcap", (0.68, 0.68, 0.1), (cx, cy, top_z + 0.04), "sv_stone2", bevel=0.035, segments=2))
    p.append(sbox("flue", (0.3, 0.3, 0.04), (cx, cy, top_z + 0.09), "sv_coal", bevel=0.01))
    for (ox, oy) in ((0.21, -0.2), (-0.22, 0.18), (0.2, 0.22)):
        p.append(S.ell("chimsnow", (cx + ox, cy + oy, top_z + 0.1), (0.13, 0.12, 0.06), "sv_snow", 10, 5))
    # door + wreath, windows with warm light and snowy sills
    dr = E.door(0.86, 1.62, "sv_door", "sv_plank", planks=4, handle="gold", step=None)
    wz = 0.2 + 1.12
    dr.append(S.torus("wreath", 0.16, 0.05, (0, -0.1, wz), "sv_wreath", rot=(math.pi / 2, 0, 0), major_segs=16,
                      minor_segs=6))
    for sx in (-1, 1):
        dr.append(S.ell("bow", (sx * 0.055, -0.16, wz - 0.15), (0.05, 0.02, 0.035), "sv_scarf", 8, 5,
                        rot=(0, sx * 0.4, 0)))
    dr.append(S.ball("bowknot", (0, -0.165, wz - 0.155), 0.025, "sv_scarf", 8, 5))
    for k in range(5):
        a = TAU * (k + 0.3) / 5
        dr.append(S.ball("wberry", (math.cos(a) * 0.16, -0.155, wz + math.sin(a) * 0.16), 0.022, "sv_berry", 6, 4))
    p += E.put(dr, "-y", w, d, 0, 0.2, out=r)
    p.append(sbox("step", (1.3, 0.5, 0.2), (0, -d / 2 - r - 0.27, 0.1), "sv_stone", bevel=0.05, segments=2))

    def win(wall, u, z, ww=0.66, hh=0.66, shutters="sv_roof"):
        wp = E.window(ww, hh, frame="cream", glass="sv_window", shutters=shutters, cross=True, sill=True)
        for o in [o for o in wp if o.name.startswith("shutter_in")]:     # inner panels: too small to matter
            wp.remove(o)
            bpy.data.objects.remove(o, do_unlink=True)
        wp.append(place([_snow_sill(ww)], (0, 0, -hh / 2 + 0.035))[0])
        return E.put(wp, wall, w, d, u, z, out=r)
    for u in (-1.0, 1.0):
        p += win("-y", u, 1.25)
    for wall in ("+x", "-x"):
        p += win(wall, 0.0, 1.25)
    p += win("+y", 0.0, 1.25, shutters=None)
    rw = E.round_window(0.21, frame="cream", glass="sv_window")
    p += E.put(rw, "-y", w, d, 0, Hr + 0.55, out=r)
    # little woodpile against the left (-X) wall with snow on top
    for i, (yy, zz) in enumerate([(-0.9, 0.08), (-0.75, 0.08), (-0.6, 0.08), (-0.45, 0.08), (-0.83, 0.21),
                                  (-0.68, 0.21), (-0.53, 0.21), (-0.75, 0.34), (-0.6, 0.34)]):
        p.append(_log("firewood", 0.55, 0.075, (-w / 2 - r - 0.36, yy, zz), "X", logm[i % 2], verts=7))
    p.append(S.ell("pilesnow", (-w / 2 - r - 0.36, -0.68, 0.42), (0.3, 0.22, 0.07), "sv_snow", 10, 6))
    root = assemble(p, "Cabin_Snowy")
    sp = bpy.data.objects.new("SmokePoint", None)
    T._link(sp)
    sp.empty_display_size = 0.2
    sp.location = (cx, cy, top_z + 0.12)
    sp.parent = root
    return root


def build_igloo():
    Rr, Hh = 1.4, 1.45
    rows, top_el, segs = 6, 76.0, 32
    rings = [(0, -4.0, 1.0)]
    for rw in range(rows):
        e0, e1 = top_el * rw / rows, top_el * (rw + 1) / rows
        de = e1 - e0
        rings += [(rw, e0 + 0.05 * de, 0.955), (rw, e0 + 0.2 * de, 1.0), (rw, e1 - 0.2 * de, 1.0),
                  (rw, e1 - 0.05 * de, 0.955)]
    rings += [(rows, 79.0, 0.99), (rows, 84.0, 1.0)]

    def fn(i, a):
        rw, e, k = rings[i]
        s_ = int(round(a / (TAU / segs)))
        if rw < rows and (s_ + rw % 2) % 2 == 0 and 0 < i:
            k *= 0.972                        # vertical joint between blocks
        er = math.radians(e)
        return Rr * math.cos(er) * k, Hh * math.sin(er) * k

    def paint(i, s_):
        rw = rings[i][0]
        if rw >= rows:
            return 0
        blk = (s_ + 1 - rw % 2) // 2
        return 1 if (blk * 5 + rw * 3) % 4 == 0 else 0
    dome = S.revolve("dome", len(rings), segs, fn, "sv_snow", apex=Hh * 1.0, smooth_deg=180,
                     materials=["sv_snow", "sv_snow2"], paint=paint)
    p = [dome]
    # entrance tunnel (half pipe along -Y) with a dark doorway
    import bmesh
    Ro, Ri, na = 0.8, 0.5, 14
    y_back, y_front = -Rr * 0.6, -(Rr + 0.62)
    ys = [y_back, y_front + 0.36, y_front + 0.32, y_front]
    bm = bmesh.new()
    th = [math.pi * k / na for k in range(na + 1)]
    outer = [[bm.verts.new((Ro * (0.985 if j == 2 else 1.0) * math.cos(t), y, Ro * (0.985 if j == 2 else 1.0) *
                            math.sin(t))) for t in th] for j, y in enumerate(ys)]
    inner = [bm.verts.new((Ri * math.cos(t), y_front, Ri * math.sin(t))) for t in th]
    inner_b = [bm.verts.new((Ri * math.cos(t), y_back, Ri * math.sin(t))) for t in th]
    faces = []
    for j in range(len(ys) - 1):
        for k in range(na):
            f = bm.faces.new((outer[j][k], outer[j][k + 1], outer[j + 1][k + 1], outer[j + 1][k]))
            f.material_index = 1 if (k // 2 + j) % 3 == 0 else 0
            faces.append((f, "out"))
    for k in range(na):
        f = bm.faces.new((outer[-1][k], outer[-1][k + 1], inner[k + 1], inner[k]))
        f.material_index = 1
        faces.append((f, "front"))
        f = bm.faces.new((inner[k], inner[k + 1], inner_b[k + 1], inner_b[k]))
        f.material_index = 2
        faces.append((f, "in"))
    cb = bm.verts.new((0, y_back, 0))
    for k in range(na):
        f = bm.faces.new((inner_b[k], inner_b[k + 1], cb))
        f.material_index = 2
        faces.append((f, "front"))
    bm.normal_update()
    for f, kind in faces:
        c = f.calc_center_median()
        want = {"out": Vector((c.x, 0, c.z)), "in": Vector((-c.x, 0, -c.z)), "front": Vector((0, -1, 0))}[kind]
        if f.normal.dot(want) < 0:
            f.normal_flip()
    tidx = [f.material_index for f in bm.faces]
    tun = T._new_obj("tunnel", bm)
    S.mats(tun, ["sv_snow", "sv_snow2", "sv_igloo_door"])
    tun.data.polygons.foreach_set("material_index", tidx)       # clearing the slots reset the indices
    tun.data.update()
    T.smooth(tun, 50)
    p.append(tun)
    # cut the doorway out of the dome wall so the dark tunnel interior is visible
    T.apply(dome)
    dbm = bmesh.new()
    dbm.from_mesh(dome.data)
    kill = [f for f in dbm.faces if any(v.co.y < 0 and v.co.x ** 2 + v.co.z ** 2 < (Ri + 0.03) ** 2 for v in f.verts)]
    bmesh.ops.delete(dbm, geom=kill, context='FACES')
    dbm.to_mesh(dome.data)
    dbm.free()
    # ice window, base snow, snowballs, a little pennant
    el, az = math.radians(28), math.radians(-35)
    pos = Vector((Rr * math.cos(el) * math.cos(az), Rr * math.cos(el) * math.sin(az), Hh * math.sin(el))) * 0.985
    p.append(sbox("icewin", (0.12, 0.56, 0.44), pos, "sv_ice", bevel=0.05, segments=2, rot=(0, -el, az)))
    Rb = rng(5)
    ph = Rb.uniform(0, TAU, 3)
    base = [(Rr + 0.28, -0.01), (Rr + 0.2, 0.08), (Rr + 0.05, 0.16), (Rr - 0.06, 0.17)]

    def bfn(i, a):
        k = 1.0 + 0.03 * math.sin(3 * a + ph[0]) + 0.02 * math.sin(7 * a + ph[1])
        r_, z = base[i]
        return r_ * k, z * (1 + 0.3 * math.sin(5 * a + ph[2]))
    p.append(S.revolve("basesnow", len(base), segs, bfn, "sv_snow", smooth_deg=180))
    for (x, y, z, rr) in ((1.05, -1.75, 0.13, 0.14), (1.31, -1.62, 0.12, 0.13), (1.16, -1.66, 0.33, 0.12)):
        p.append(S.ball("snowball", (x, y, z), rr, "sv_snowman", 12, 7))
    p.append(scyl("pole", 0.022, 0.6, (0, 0, Hh + 0.27), "sv_twig", verts=8))
    p.append(S.ball("polecap", (0, 0, Hh + 0.58), 0.035, "gold", 8, 5))
    p.append(prism("flag", [(0.0, 0.0), (0.34, -0.09), (0.0, -0.2)], 0.025, (0.02, 0, Hh + 0.55), S.m("sv_hat"),
                   bevel=0.008))
    return assemble(p, "Igloo")


# ================================================================================================ ANIMALS
def build_penguin():
    P = []
    bk = [((0, 0.0, 0.06), 0.12, 0.11), ((0, -0.005, 0.15), 0.158, 0.143), ((0, 0.0, 0.27), 0.148, 0.133),
          ((0, 0.005, 0.36), 0.112, 0.102)]
    body = S.loft("peng_body", bk, segs=18, res=3, materials=("sv_peng",), up=(0, -1, 0), dome_start=0.06,
                  dome_end=0.045)
    P.append(body)
    P.append(S.shell_patch("belly", body, C.blob("bb", (0, -0.13, 0.19), (0.115, 0.1, 0.17), jitter=0.0),
                           "sv_peng_belly", offset=0.004))
    for sx in (1, -1):
        P.append(S.ell("flipper", (sx * 0.162, 0.005, 0.235), (0.032, 0.07, 0.125), "sv_peng", 12, 8,
                       rot=(0.12, sx * 0.38, 0)))
        P.append(S.ell("foot", (sx * 0.062, -0.085, 0.022), (0.05, 0.078, 0.024), "sv_peng_feet", 12, 6,
                       rot=(0, 0, sx * -0.25)))
    # knitted scarf around the neck hides the head seam when it nods
    sc = S.torus("scarf", 0.098, 0.034, (0, 0.0, 0.372), "sv_collar", major_segs=18, minor_segs=6)
    _striped(sc, ["sv_collar", "sv_scarf2"], lambda c: (int((math.atan2(c.y, c.x) + math.pi) / (TAU / 12))) % 2)
    P.append(sc)
    P.append(S.loft("scarf_end", [((0.06, -0.08, 0.37), 0.035, 0.012), ((0.085, -0.115, 0.32), 0.036, 0.012),
                                  ((0.095, -0.13, 0.26), 0.038, 0.012)], segs=6, res=2,
                    materials=("sv_collar",), up=(0, -1, 0.2), exp=2.6))
    # ---- head
    H = []
    hc = Vector((0, -0.01, 0.47))
    head = S.ell("head", hc, (0.128, 0.122, 0.118), "sv_peng", 18, 12)
    H.append(head)
    H.append(S.shell_patch("face", head, C.blob("fb", (0, -0.1, 0.455), (0.105, 0.08, 0.078), jitter=0.0),
                           "sv_peng_belly", offset=0.003))
    for sx in (1, -1):
        H += S.eye(f"eye{sx}", (sx * 0.046, -0.112, 0.485), 0.026, (sx * 0.3, -1, 0.1), sclera=False)
        H.append(S.ell(f"cheek{sx}", (sx * 0.078, -0.098, 0.445), (0.022, 0.008, 0.015), "cheek", 8, 4,
                       rot=(0, 0, sx * -0.6)))
    H.append(S.tube("beak", [(0, -0.115, 0.455), (0, -0.15, 0.448), (0, -0.172, 0.442)], 0.026, "beak", segs=10,
                    radius_end=0.007, dome_end=0.007, res=2))
    H.append(S.ell("tuft", (0, -0.0, 0.585), (0.02, 0.035, 0.03), "sv_peng", 8, 5, rot=(-0.5, 0, 0)))
    tail = [S.ell("tail", (0, 0.135, 0.065), (0.055, 0.06, 0.025), "sv_peng", 10, 6, rot=(-0.6, 0, 0))]
    root = T.join(P, "Penguin")
    return root, [C.part(H, "Head", (0, 0, 0.37)), C.part(tail, "Tail", (0, 0.11, 0.085))]


def build_reindeer():
    """Chunky toy reindeer: short sturdy legs, big head, soft rounded antlers, red collar with a bell."""
    P = []
    bk = [((0, 0.32, 0.58), 0.15, 0.15), ((0, 0.19, 0.565), 0.175, 0.175), ((0, -0.01, 0.555), 0.178, 0.185),
          ((0, -0.19, 0.58), 0.165, 0.175), ((0, -0.28, 0.63), 0.135, 0.145)]
    body = S.loft("rd_body", bk, segs=18, res=3, materials=("sv_deer",), dome_start=0.11, dome_end=0.03, exp=2.2)
    P.append(body)
    P.append(S.shell_patch("belly", body, C.blob("bb", (0, 0.0, 0.4), (0.17, 0.32, 0.1), jitter=0.0),
                           "sv_deer_cream", offset=0.005))
    P.append(S.shell_patch("bib", body, C.blob("cb", (0, -0.31, 0.6), (0.1, 0.1, 0.1), jitter=0.0),
                           "sv_deer_cream", offset=0.005))
    P.append(S.loft("neck", [((0, -0.22, 0.64), 0.115, 0.125), ((0, -0.3, 0.74), 0.095, 0.098),
                             ((0, -0.34, 0.83), 0.085, 0.085)], segs=14, res=2, materials=("sv_deer",)))
    P += S.legs4("rd", 0.1, (-0.19, 0.21), 0.48, "sv_deer", "hoof", w_top=0.068, w_mid=0.056, w_low=0.052,
                 hoof_h=0.08, hoof_w=0.056, thigh=(0.035, 0.06), segs=10)
    P.append(S.torus("collar", 0.095, 0.022, (0, -0.305, 0.755), "sv_scarf", rot=(math.radians(50), 0, 0),
                     major_segs=18, minor_segs=6))
    P.append(S.ball("bell", (0, -0.39, 0.685), 0.042, "gold", 10, 7))
    P.append(S.ball("bellslot", (0, -0.425, 0.672), 0.013, "charcoal", 6, 4))
    # ---- head (big and round for a toddler-friendly face)
    H = []
    H.append(S.loft("rd_head", [((0, -0.31, 0.92), 0.118, 0.118), ((0, -0.41, 0.915), 0.124, 0.116),
                                ((0, -0.52, 0.865), 0.088, 0.082)], segs=16, res=2, materials=("sv_deer",),
                    dome_start=0.08, dome_end=0.055))
    H.append(S.ell("muzzle", (0, -0.55, 0.85), (0.085, 0.07, 0.064), "sv_deer_cream", 14, 8))
    H.append(S.ell("nose", (0, -0.613, 0.874), (0.042, 0.028, 0.031), "sv_deer_nose", 10, 6))
    H.append(S.ball("nose_hl", (0.012, -0.636, 0.889), 0.009, "grey_light", 5, 3))
    H.append(S.loft("smile", [((-0.03, -0.61, 0.83), 0.006, 0.006), ((0, -0.618, 0.821), 0.006, 0.006),
                              ((0.03, -0.61, 0.83), 0.006, 0.006)], segs=5, res=3, materials=("mouth",),
                    dome_start=0.005, dome_end=0.005, dome_rings=2))
    for sx in (1, -1):
        H += S.eye(f"eye{sx}", (sx * 0.068, -0.47, 0.955), 0.04, (sx * 0.4, -1, 0.15))
        H.append(S.ell(f"cheek{sx}", (sx * 0.088, -0.505, 0.89), (0.024, 0.012, 0.015), "cheek", 8, 4,
                       rot=(0, 0, sx * -0.7)))
        H.append(S.ell("ear", (sx * 0.145, -0.33, 0.985), (0.085, 0.024, 0.04), "sv_deer", 10, 6,
                       rot=(0.2, sx * -0.35, sx * 0.3)))
        H.append(S.ell("ear_in", (sx * 0.15, -0.344, 0.983), (0.062, 0.011, 0.025), "nose_pink", 8, 5,
                       rot=(0.2, sx * -0.35, sx * 0.3)))
        b0 = Vector((sx * 0.05, -0.33, 1.01))
        b1 = Vector((sx * 0.09, -0.32, 1.1))
        b2 = Vector((sx * 0.145, -0.3, 1.18))
        b3 = Vector((sx * 0.195, -0.27, 1.24))
        H.append(S.tube("antler", [b0, b1, b2, b3], 0.027, "sv_antler", segs=8, radius_end=0.019, dome_end=0.019,
                        res=2))
        H.append(S.tube("tine", [b1 + Vector((0, -0.005, 0.01)), b1 + Vector((-sx * 0.015, -0.05, 0.075))], 0.019,
                        "sv_antler", segs=7, radius_end=0.015, dome_end=0.015, res=1))
        H.append(S.tube("tine", [b2, b2 + Vector((-sx * 0.01, -0.04, 0.08))], 0.018, "sv_antler", segs=7,
                        radius_end=0.014, dome_end=0.014, res=1))
    H.append(S.ell("tuft", (0, -0.39, 1.02), (0.05, 0.045, 0.034), "sv_deer_dark", 8, 5))
    tail = [S.ell("tail", (0, 0.4, 0.65), (0.055, 0.05, 0.08), "sv_deer_cream", 10, 7, rot=(-0.5, 0, 0))]
    root = T.join(P, "Reindeer")
    return root, [C.part(H, "Head", (0, -0.34, 0.84)), C.part(tail, "Tail", (0, 0.37, 0.62))]


def build_husky():
    P = []
    bk = [((0, 0.22, 0.345), 0.1, 0.1), ((0, 0.08, 0.335), 0.12, 0.125), ((0, -0.08, 0.345), 0.125, 0.135),
          ((0, -0.18, 0.385), 0.106, 0.12), ((0, -0.24, 0.445), 0.086, 0.09)]
    body = S.loft("hk_body", bk, segs=16, res=3, materials=("sv_husky",), dome_start=0.075, dome_end=0.03)
    P.append(body)
    P.append(S.shell_patch("belly", body, C.blob("bb", (0, -0.02, 0.25), (0.13, 0.26, 0.085), jitter=0.0),
                           "fur_white", offset=0.004))
    P.append(S.shell_patch("chest", body, C.blob("cb", (0, -0.25, 0.37), (0.085, 0.09, 0.12), jitter=0.0),
                           "fur_white", offset=0.004))
    P += S.legs4("hk", 0.068, (-0.14, 0.18), 0.3, "sv_husky", "fur_white", w_top=0.05, w_mid=0.045, w_low=0.043,
                 hoof_h=0.1, hoof_w=0.048, thigh=(0.016, 0.034), segs=10)
    P.append(S.torus("collar", 0.088, 0.018, (0, -0.225, 0.425), "sv_collar", rot=(math.radians(55), 0, 0),
                     major_segs=18, minor_segs=6))
    P.append(S.ell("tag", (0, -0.3, 0.37), (0.024, 0.008, 0.024), "gold", 10, 6, rot=(0.6, 0, 0)))
    # ---- head
    H = []
    hk = [((0, -0.205, 0.565), 0.125, 0.12), ((0, -0.275, 0.565), 0.135, 0.126), ((0, -0.335, 0.545), 0.112,
                                                                                  0.11)]
    head = S.loft("hk_head", hk, segs=18, res=2, materials=("sv_husky",), dome_start=0.08, dome_end=0.06)
    H.append(head)
    H.append(S.shell_patch("mask", head, C.blob("mb", (0, -0.37, 0.535), (0.15, 0.11, 0.085), jitter=0.0),
                           "fur_white", offset=0.004))
    H.append(S.ell("muzzle", (0, -0.395, 0.51), (0.07, 0.068, 0.052), "fur_white", 14, 8))
    H.append(S.ell("nose", (0, -0.465, 0.535), (0.031, 0.02, 0.022), "eye_black", 10, 6))
    H.append(S.ball("nose_hl", (0.008, -0.482, 0.547), 0.006, "grey_light", 5, 3))
    H.append(S.loft("smile", [((-0.03, -0.462, 0.5), 0.005, 0.005), ((0, -0.47, 0.49), 0.005, 0.005),
                              ((0.03, -0.462, 0.5), 0.005, 0.005)], segs=5, res=3, materials=("eye_black",),
                    dome_start=0.004, dome_end=0.004, dome_rings=2))
    H.append(S.ell("tongue", (0, -0.46, 0.475), (0.02, 0.012, 0.022), "tongue", 8, 5, rot=(0.3, 0, 0)))
    for sx in (1, -1):
        H += S.eye(f"eye{sx}", (sx * 0.058, -0.368, 0.6), 0.031, (sx * 0.35, -1, 0.15), iris="sv_husky_eye",
                   pupil_scale=0.74)
        ear = S.loft("ear", [((sx * 0.072, -0.235, 0.655), 0.048, 0.022), ((sx * 0.092, -0.245, 0.775), 0.0, 0.0)],
                     segs=10, res=1, materials=("sv_husky_dark",), up=(0, -1, 0))
        inner = S.loft("ear_in", [((sx * 0.073, -0.258, 0.66), 0.03, 0.008), ((sx * 0.089, -0.258, 0.755), 0.0,
                                                                              0.0)],
                       segs=8, res=1, materials=("nose_pink",), up=(0, -1, 0))
        H += [ear, inner]
    tk = [((0, 0.26, 0.4), 0.035, 0.035), ((0, 0.33, 0.47), 0.046, 0.046), ((0, 0.33, 0.57), 0.052, 0.052),
          ((0, 0.27, 0.63), 0.046, 0.046), ((0, 0.2, 0.62), 0.03, 0.03)]
    tail = [S.loft("tail", tk, segs=10, res=3, materials=("sv_husky", "fur_white"), dome_end=0.03,
                   paint=lambda i, n, s_, c: 1 if i >= n - 4 else 0)]
    root = T.join(P, "Husky")
    return root, [C.part(H, "Head", (0, -0.22, 0.46)), C.part(tail, "Tail", (0, 0.26, 0.39))]


# ================================================================================================ DRIVER
REGISTRY = {}   # name -> dict(folder, fn, cat, kind, budget, fin)


def reg(name, folder, fn, cat, budget, kind=None, sound=None, pdist=1.0, **fin):
    fin.setdefault("ao_strength", 0.65 if cat == "building" else 0.8)
    REGISTRY[name] = dict(folder=folder, fn=fn, cat=cat, kind=kind, sound=sound, budget=budget, fin=fin,
                          pdist=pdist)


reg("Tree_SnowyPine", "Nature", build_tree_snowy_pine, "tree", 1500)
reg("Tree_SnowyPineSmall", "Nature", build_tree_snowy_pine_small, "tree", 1500)
reg("Tree_SnowyRound", "Nature", build_tree_snowy_round, "tree", 1500)
reg("Bush_Snowy", "Nature", build_bush_snowy, "plant", 1000)
reg("Rock_Snowy", "Nature", build_rock_snowy, "rock", 1500)
reg("Snowdrift", "Nature", build_snowdrift, "plant", 1000, ao_distance=0.5)

reg("Snowman", "Props", build_snowman, "prop", 1000, pdist=1.2, ao_distance=0.35)
reg("Sled", "Props", build_sled, "prop", 1000, ao_distance=0.25)
reg("Lamp_Snowy", "Props", build_lamp_snowy, "prop", 1000, pdist=1.3, ao_distance=0.3)

reg("Cabin_Snowy", "Buildings", build_cabin_snowy, "building", 6000)
reg("Igloo", "Buildings", build_igloo, "building", 6000, ao_distance=0.8)

ANIMAL = dict(ao_distance=0.35, ao_strength=0.7, pdist=1.0)
reg("Penguin", "Animals", build_penguin, "animal", 3500, kind="animal", sound="squeak", **ANIMAL)
reg("Reindeer", "Animals", build_reindeer, "animal", 3500, kind="animal", sound="snort", **ANIMAL)
reg("Husky", "Animals", build_husky, "animal", 3500, kind="animal", sound="bark", **ANIMAL)


def build_one(name, do_preview):
    info = REGISTRY[name]
    T.reset()
    POST.clear()
    res = info["fn"]()
    if isinstance(res, tuple):          # creature style: (root, parts) -> parts get parented after the bake
        root, parts = res
    else:
        root, parts = res, None
    root.name = name
    meshes = [root] + [c for c in root.children_recursive if c.type == 'MESH']
    if parts:
        meshes += [p for p in parts if p.type == 'MESH']
    keep = set(meshes) | set(root.children_recursive) | set(parts or [])
    for o in list(bpy.data.objects):
        if o not in keep:
            print("[SNOWY] removing stray object", o.name)
            bpy.data.objects.remove(o, do_unlink=True)
    fin = dict(info["fin"])
    T.finalize(meshes, **fin)
    for o, kw in POST:
        E.gradient(o, **kw)
    for o in meshes:
        S.snow_tint(o, fin.get("ao_strength", 0.85))
        S.glow(o)
    if parts:
        for p in parts:
            C.parent_keep(p, root)
    bpy.context.view_layer.update()
    rel = f"{info['folder']}/{name}"
    T.export_fbx(rel, [root])
    objs = [root] + list(root.children_recursive)
    v, t = T.stats(objs)
    mn, mx = T._bounds(objs)
    child_names = [c.name for c in root.children]
    if info["kind"]:
        rad = max(abs(mn.x), abs(mx.x), abs(mn.y), abs(mx.y))
        entry = {"name": name, "fbx": f"_Project/Art/Models/{rel}.fbx", "kind": info["kind"],
                 "sound": info["sound"], "footprintRadius": round(rad, 3), "height": round(mx.z, 3),
                 "parts": child_names, "verts": v}
    else:
        entry = {"name": name, "fbx": f"_Project/Art/Models/{rel}.fbx", "category": info["cat"],
                 "footprint": [round(mx.x - mn.x, 2), round(mx.y - mn.y, 2)], "height": round(mx.z, 2),
                 "parts": [c.name for c in root.children_recursive], "verts": v}
    flag = "" if v <= info["budget"] else f"  !!! OVER BUDGET ({info['budget']})"
    print(f"[SNOWY] {name}: verts={v} tris={t} size=({mx.x - mn.x:.2f}, {mx.y - mn.y:.2f}, {mx.z:.2f}){flag}")
    if do_preview:
        S.preview([root], name, dist=info["pdist"])
    return entry


def group_shot(names):
    """Imports the exported FBX files (what Unity gets) plus Tree_Pine and Cow for scale, renders them together."""
    T.reset()
    rows = [["Tree_Pine", "Tree_SnowyPine", "Tree_SnowyRound", "Tree_SnowyPineSmall", "Cabin_Snowy", "Igloo"],
            ["Cow", "Reindeer", "Husky", "Penguin", "Snowman", "Lamp_Snowy", "Sled", "Bush_Snowy", "Rock_Snowy",
             "Snowdrift"]]
    folders = {"Tree_Pine": "Nature", "Cow": "Animals"}
    for n, info in REGISTRY.items():
        folders[n] = info["folder"]
    roots = []
    y = 0.0
    for ri, row in enumerate(rows):
        x = 0.0
        row_objs = []
        depth = 0.0
        for n in row:
            p = os.path.join(T.MODELS, folders.get(n, "Nature"), n + ".fbx")
            if not os.path.exists(p):
                continue
            before = set(bpy.data.objects)
            bpy.ops.import_scene.fbx(filepath=p)
            new = [o for o in bpy.data.objects if o not in before]
            for o in new:
                if o.type == 'EMPTY' and o.parent is not None:
                    o.hide_render = True
            top = [o for o in new if o.parent is None]
            bpy.context.view_layer.update()
            mn, mx = T._bounds(new)
            for o in top:
                o.location.x += x - mn.x
                o.location.y += y - (mn.y + mx.y) / 2
            x += (mx.x - mn.x) + (0.6 if ri else 1.0)
            depth = max(depth, mx.y - mn.y)
            row_objs.append((top, x))
            roots += top
        # centre the row
        for top, _ in row_objs:
            for o in top:
                o.location.x -= x / 2
        y -= depth * 0.5 + 3.2
    bpy.context.view_layer.update()
    g = S.ground_disc(roots, pad=2.0, scale=0.7)
    T.render(roots, os.path.join(S.SCRATCH, "Snowy_Group.png"), size=(2000, 1100), yaw_deg=-12, pitch_deg=24,
             distance_scale=0.82, samples=40)
    bpy.data.objects.remove(g, do_unlink=True)


def main():
    argv = T.args()
    flags = [a for a in argv if a.startswith("--")]
    names = [a for a in argv if not a.startswith("--")]
    group_only = names == ["Group"]
    if group_only:
        names = []
    elif not names:
        names = list(REGISTRY)
    entries = {}
    if os.path.exists(MANIFEST):
        try:
            for e in json.load(open(MANIFEST)):
                entries[e["name"]] = e
        except Exception:
            pass
    for n in names:
        entries[n] = build_one(n, "--no-preview" not in flags)
    if names:
        order = [n for n in REGISTRY if n in entries]
        with open(MANIFEST, "w") as f:
            json.dump([entries[n] for n in order], f, indent=2)
        print("[SNOWY] manifest written", MANIFEST)
    if group_only or not T.args():
        group_shot(list(REGISTRY))


if __name__ == "__main__":
    main()
