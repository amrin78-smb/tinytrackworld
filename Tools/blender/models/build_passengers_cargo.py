"""
Tiny Tracks World - station passengers, wagon cargo and the cargo yard.

Run:  blender -b --factory-startup --python Tools/blender/models/build_passengers_cargo.py -- [Name ...] [--preview DIR]
      (no names = build everything)
Exports Assets/_Project/Art/Models/People/Passenger_*.fbx, Props/Cargo_*.fbx, Buildings/CargoYard.fbx and the
manifest Tools/blender/models/passengers_cargo_manifest.json. Previews go to --preview DIR (default Logs/Blender).

PEOPLE (same build as Person_* in build_creatures.py, which is imported, not changed): root origin = feet centre,
front = -Y. Animated children (origin = pivot): Head (neck), ArmL / ArmR (shoulders), LegL / LegR (hips).
Held props travel with their arm (suitcase, walking stick: ArmR; balloon: ArmL).

CARGO: origin = bottom centre, front = -Y, every item fits the Car_Cargo open bed (interior 0.80 x 1.50 m,
floor 0.56 m above the vehicle origin) with >= 4 cm margin and stays <= 0.6 m tall.

CARGO YARD: same convention as Buildings/Station. Origin = track centre line at the middle of the 6 m station piece,
ground level (z = 0, the bed top is z = 0.16); the track runs along Blender Y; the yard stands on Blender +X
(Unity -X, the same side as the Station). Unity accessory offset (0, 0, 3), yaw 0 - identical to the Station.
Children: Crane (pivot = top of the pedestal; the jib points Blender -Y = Unity +Z at rest, so LookRotation swivels
it; hook position in the manifest); LoadPoint (empty) on the deck at the platform edge.
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
import bpy  # noqa: E402
from mathutils import Vector, Matrix  # noqa: E402

import tt_common as T  # noqa: E402
import creatures_lib as C  # noqa: E402
import env_lib as E  # noqa: E402
import passengers_lib as PL  # noqa: E402
import build_creatures as B  # noqa: E402  (module import only: its main() is guarded)

MANIFEST = os.path.join(HERE, "passengers_cargo_manifest.json")
PREVIEW_DIR = T.PREVIEWS


# ================================================================================================ PEOPLE
def _surf(D):
    rx, ry, rz = D["head_r"]
    cx, cy, cz = D["head_c"]

    def surf(x, z):
        k = 1 - (x / rx) ** 2 - (z / rz) ** 2
        return cy - ry * math.sqrt(max(0.0, k))
    return surf


def _skirt(D, top, bottom, flare, material, hem=None):
    tw, td, hip = D["torso_w"], D["torso_d"], D["hip"]
    keys = [((0, 0, top), tw * 1.03, td * 1.08), ((0, 0, (top + bottom) / 2), tw * (1 + flare * 0.45), td * (1 + flare * 0.4)),
            ((0, 0, bottom), tw * (1 + flare), td * (1 + flare * 0.85))]
    mats = (material,) if hem is None else (material, hem)
    paint = None if hem is None else (lambda i, n, s, c: 1 if c.z < bottom + 0.025 else 0)
    return C.loft("skirt", keys, segs=16, res=2, materials=mats, up=(0, -1, 0), paint=paint)


def _finish(name, P, H, AL, AR, D):
    """Like build_creatures._finish_person, plus separate legs (LegL / LegR, hip pivots) for walking."""
    legL, legR = P[0:2], P[2:4]
    rest = P[4:]
    C.report(P + H + AL + AR)
    root = T.join(rest, name)
    hd = C.part(H, "Head", (0, 0, D["neck"] - 0.02))
    al = C.part(AL, "ArmL", (D["sh_x"], 0, D["sh"] - 0.04))
    ar = C.part(AR, "ArmR", (-D["sh_x"], 0, D["sh"] - 0.04))
    ll = C.part(legL, "LegL", (D["leg_x"], 0, D["hip"]))
    lr = C.part(legR, "LegR", (-D["leg_x"], 0, D["hip"]))
    return root, [hd, al, ar, ll, lr]


def build_girl():
    D = B._dims(0.72, head=0.95)
    sh, hip, td = D["sh"], D["hip"], D["torso_d"]
    hc = Vector(D["head_c"])
    rx, ry, rz = D["head_r"]

    def backpack(D):
        zc = hip + (sh - hip) * 0.52
        out = [T.rbox("pack", (0.2, 0.11, 0.23), (0, td + 0.06, zc), C.mat("pc_pack"), bevel=0.045, segments=2),
               T.rbox("pocket", (0.15, 0.05, 0.09), (0, td + 0.12, zc - 0.05), C.mat("yellow"), bevel=0.022,
                      segments=2),
               C.ell("flap", (0, td + 0.07, zc + 0.1), (0.1, 0.065, 0.035), "pc_pack_dark", 10, 5)]
        for s in (1, -1):
            out.append(C.tube("strap", [(s * 0.055, td + 0.03, sh - 0.02), (s * 0.07, 0.0, sh + 0.03),
                                        (s * 0.07, -td - 0.0, sh - 0.05), (s * 0.065, -td - 0.004, hip + 0.1)],
                              0.012, "pc_pack_dark", segs=6))
        return out

    def hair(D):
        out = [B._hair_shell(D, (0, 0.1, hc.z + 0.06), (0.26, 0.2, 0.15), "hair_black", seed=11)]
        out.append(C.ell("fringe", (0, hc.y - ry * 0.62, hc.z + rz * 0.62), (0.1, 0.045, 0.035), "hair_black", 10, 5,
                         rot=(0.55, 0, 0)))
        for s in (1, -1):
            tie = (s * rx * 0.93, 0.03, hc.z + 0.04)
            out.append(C.tube("pigtail", [tie, (s * (rx + 0.06), 0.05, hc.z + 0.0), (s * (rx + 0.085), 0.06, hc.z - 0.08),
                                          (s * (rx + 0.07), 0.05, hc.z - 0.15)], 0.042, "hair_black", segs=10,
                              radius_end=0.024, dome_end=0.03, dome_rings=2))
            out.append(C.ball("bobble", tie, 0.03, "yellow", 8, 5))
        return out

    outfit = {
        "skin": "pc_skin_deep", "hair": "hair_black", "shoe": "pc_purple",
        "leg_mats": ("pc_skin_deep", "white"), "leg_paint": lambda i, n, s, c: 1 if c.z < 0.11 else 0,
        "torso_mats": ("pc_coral", "pc_purple"), "torso_paint": lambda i, n, s, c: 1 if c.z < hip + 0.05 else 0,
        "sleeve_mat": "pc_coral", "sleeve": 0.42,
        "body_extras": [backpack, lambda D: [_skirt(D, hip + 0.06, hip - 0.12, 0.55, "pc_purple", "white")]],
        "head_extras": [hair],
    }
    P, H, AL, AR = B._person(D, outfit)
    return _finish("Passenger_Girl", P, H, AL, AR, D)


def build_grandpa():
    D = B._dims(1.0)
    sh, hip, td = D["sh"], D["hip"], D["torso_d"]
    hc = Vector(D["head_c"])
    rx, ry, rz = D["head_r"]
    surf = _surf(D)

    def torso_paint(i, n, s, c):
        if c.z < hip + 0.03:
            return 2
        if c.y < 0 and c.z > hip + 0.06 and abs(c.x) < 0.035:
            return 1
        return 0

    def cardigan(D):
        out = []
        for k in range(3):
            out.append(C.ell("button", (-0.045, -td - 0.002, hip + 0.11 + k * 0.09), (0.014, 0.007, 0.014), "walnut",
                             6, 4))
        for s in (1, -1):
            out.append(C.ell("bowtie", (s * 0.03, -td - 0.0, sh - 0.025), (0.032, 0.014, 0.022), "red", 8, 4,
                             rot=(0, s * 0.25, 0)))
        out.append(C.ball("bowknot", (0, -td - 0.008, sh - 0.025), 0.014, "red_dark", 6, 4))
        return out

    def head(D):
        out = []
        out.append(C.lathe_solid("hat", [(0.165, 0.0), (0.255, 0.003), (0.272, 0.02), (0.262, 0.032), (0.17, 0.03),
                                         (0.16, 0.045), (0.152, 0.13), (0.115, 0.155), (0.04, 0.142), (0.0, 0.14)],
                                 (hc.x, hc.y + 0.01, hc.z + 0.095), "pc_hat", rot=(math.radians(-8), 0, 0), segs=18))
        out.append(C.torus("hatband", 0.158, 0.02, loc=(hc.x, hc.y + 0.014, hc.z + 0.15), material=None,
                           rot=(math.radians(-8), 0, 0), major_segs=18, minor_segs=3))
        C._mats(out[-1], ["yellow"])
        out.append(B._hair_shell(D, (0, 0.11, hc.z - 0.01), (0.3, 0.2, 0.11), "pc_whitehair", seed=5))
        for s in (1, -1):
            out.append(C.ell("tash", (s * 0.033, hc.y - 0.158, hc.z - 0.05), (0.042, 0.02, 0.022), "pc_whitehair", 8,
                             5, rot=(0, s * 0.3, 0)))
            ex, ez = s * rx * 0.36, rz * 0.05
            out.append(C.torus("glasses", 0.044, 0.006, loc=(hc.x + ex, surf(ex, ez) - 0.012, hc.z + ez), material=None,
                               rot=(math.pi / 2, 0, s * 0.15), major_segs=12, minor_segs=3))
            C._mats(out[-1], ["charcoal"])
            out.append(C.tube("temple", [(s * (rx * 0.36 + 0.044), surf(rx * 0.36, ez) - 0.005, hc.z + ez),
                                         (s * rx * 0.97, hc.y - 0.02, hc.z + ez + 0.01)], 0.005, "charcoal", segs=4,
                              res=1))
        out.append(C.arc("bridge", (0, surf(0, ez) - 0.022, hc.z + ez - 0.005), 0.02, 30, 150, 0.005, "charcoal",
                         axis_up=(0, 0, 1), n=4, segs=4))
        return out

    def stick(D, p):
        x, y, z = p.x, p.y, p.z
        path = [(x, y - 0.07, z + 0.02), (x, y - 0.065, z + 0.075), (x, y - 0.02, z + 0.1), (x, y + 0.012, z + 0.07),
                (x, y + 0.01, z + 0.0), (x, y - 0.01, z * 0.5), (x, y - 0.03, 0.035)]
        return [C.tube("stick", path, 0.016, "pc_stick", segs=7, res=2, dome_start=0.012, dome_rings=2),
                C.ball("ferrule", (x, y - 0.03, 0.03), 0.022, "eye_black", 8, 5)]

    outfit = {
        "skin": "skin", "hair": "pc_whitehair", "shoe": "boot",
        "leg_mats": ("pc_trouser",),
        "torso_mats": ("pc_mustard", "pc_shirt", "pc_trouser"), "torso_paint": torso_paint,
        "sleeve_mat": "pc_mustard", "sleeve": 0.86,
        "body_extras": [cardigan], "head_extras": [head],
        "arm_path": {-1: [(-0.175, 0, sh - 0.04), (-0.225, -0.04, sh - 0.19), (-0.245, -0.12, sh - 0.31)]},
        "arm_extras": {-1: [stick]},
    }
    P, H, AL, AR = B._person(D, outfit)
    return _finish("Passenger_Grandpa", P, H, AL, AR, D)


def build_mum():
    D = B._dims(1.0, head=0.98)
    sh, hip, td = D["sh"], D["hip"], D["torso_d"]
    hc = Vector(D["head_c"])
    rx, ry, rz = D["head_r"]

    def dress(D):
        out = [_skirt(D, hip + 0.1, hip - 0.2, 0.42, "pc_magenta")]
        out.append(C.ell("collar", (0, -0.03, sh + 0.005), (0.09, 0.07, 0.03), "white", 10, 5))
        for k, (x, z) in enumerate(((-0.1, hip - 0.12), (0.06, hip - 0.05), (0.13, hip - 0.15), (-0.03, hip - 0.17),
                                    (-0.15, hip - 0.03))):
            # white polka dots on the skirt front
            t = (hip + 0.1 - z) / 0.3
            yy = -(td * (1.08 + 0.36 * t)) * math.sqrt(max(0.0, 1 - (x / (D["torso_w"] * (1.03 + 0.42 * t) + 0.01)) ** 2))
            out.append(C.ell("dot", (x, yy - 0.002, z), (0.018, 0.006, 0.018), "white", 6, 3,
                             rot=(0, 0, -math.atan2(x, 0.25))))
        return out

    def hair(D):
        out = [B._hair_shell(D, (0, 0.12, hc.z + 0.03), (0.3, 0.22, 0.19), "pc_hair_auburn", seed=9)]
        out.append(C.ell("fringe", (0.035, hc.y - ry * 0.55, hc.z + rz * 0.72), (0.1, 0.04, 0.035), "pc_hair_auburn", 10,
                         5, rot=(0.75, 0, -0.2)))
        tie = (0, hc.y + ry * 0.8, hc.z + 0.11)
        out.append(C.tube("ponytail", [tie, (0, hc.y + ry + 0.06, hc.z + 0.07), (0, hc.y + ry + 0.08, hc.z - 0.04),
                                       (0, hc.y + ry + 0.05, hc.z - 0.15)], 0.055, "pc_hair_auburn", segs=10,
                          radius_end=0.03, dome_start=0.02, dome_end=0.035, dome_rings=2))
        out.append(C.torus("scrunchie", 0.045, 0.02, loc=tie, material=None, rot=(math.radians(-60), 0, 0),
                           major_segs=12, minor_segs=5))
        C._mats(out[-1], ["yellow"])
        for s in (1, -1):
            out.append(C.ball("earring", (s * rx * 0.98, hc.y - 0.0, hc.z - 0.075), 0.016, "gold", 6, 4))
        return out

    def suitcase(D, p):
        x, y, z = p.x - 0.01, p.y, p.z
        top = z - 0.065
        h, w, t = 0.29, 0.4, 0.11
        out = [T.rbox("case", (t, w, h), (x, y, top - h / 2), C.mat("pc_case"), bevel=0.035, segments=2)]
        for sy in (-1, 1):
            out.append(T.rbox("casestrap", (t + 0.012, 0.035, h + 0.012), (x, y + sy * 0.1, top - h / 2),
                              C.mat("pc_case_dark"), bevel=0.008, segments=1))
        out.append(C.tube("casehandle", [(x, y - 0.06, top - 0.005), (x, y - 0.045, top + 0.045),
                                         (x, y + 0.045, top + 0.045), (x, y + 0.06, top - 0.005)], 0.013, "charcoal",
                          segs=6, res=2))
        out.append(C.ell("sticker", (x - t / 2 - 0.003, y + 0.0, top - h * 0.45), (0.006, 0.05, 0.05), "sky", 10, 4))
        out.append(C.ell("sticker2", (x - t / 2 - 0.006, y + 0.0, top - h * 0.45), (0.005, 0.022, 0.022), "yellow",
                         8, 4))
        return out

    outfit = {
        "skin": "pc_skin_olive", "hair": "pc_hair_auburn", "shoe": "blue_dark",
        "leg_mats": ("pc_skin_olive",),
        "torso_mats": ("pc_magenta", "yellow"),
        "torso_paint": lambda i, n, s, c: 1 if abs(c.z - (hip + 0.11)) < 0.022 else 0,
        "sleeve_mat": "pc_magenta", "sleeve": 0.45,
        "body_extras": [dress], "head_extras": [hair],
        "arm_path": {-1: [(-0.175, 0, sh - 0.04), (-0.235, 0, sh - 0.2), (-0.29, 0.0, sh - 0.33)]},
        "arm_extras": {-1: [suitcase]},
    }
    P, H, AL, AR = B._person(D, outfit)
    return _finish("Passenger_Mum", P, H, AL, AR, D)


def build_boy():
    D = B._dims(0.76, head=0.92)
    sh, hip, td, shx = D["sh"], D["hip"], D["torso_d"], D["sh_x"]
    hc = Vector(D["head_c"])
    rx, ry, rz = D["head_r"]
    surf = _surf(D)

    def shirt(D):
        return [C.ell("star", (0.0, -td * 1.02 - 0.002, hip + (sh - hip) * 0.6), (0.035, 0.006, 0.035), "yellow", 10, 4)]

    def head(D):
        out = []
        cap_c = (hc.x, hc.y + 0.015, hc.z + 0.08)
        out.append(C.lathe_solid("cap", [(rx * 1.04, 0.0), (rx * 1.03, 0.04), (rx * 0.9, 0.095), (rx * 0.6, 0.135),
                                         (0.0, 0.148)], cap_c, "pc_cap", rot=(math.radians(-10), 0, 0), segs=20))
        out.append(C.ell("visor", (hc.x, hc.y - ry * 0.98, hc.z + 0.108), (rx * 0.68, 0.062, 0.011), "pc_cap", 14, 6,
                         rot=(math.radians(-12), 0, 0)))
        out.append(C.ball("capbutton", (hc.x, hc.y + 0.02, hc.z + 0.226), 0.017, "white", 8, 5))
        out.append(B._hair_shell(D, (0, 0.11, hc.z - 0.0), (0.27, 0.2, 0.12), "hair_ginger", seed=13))
        for s in (1, -1):
            out.append(C.ell("tuft", (s * rx * 0.82, hc.y - ry * 0.45, hc.z + 0.03), (0.035, 0.03, 0.025), "hair_ginger",
                             8, 5, rot=(0, s * 0.6, 0)))
            for k, (dx, dz) in enumerate(((0.0, 0.0), (0.024, 0.012), (0.012, -0.02))):
                fx, fz = s * (rx * 0.5 + dx), -rz * 0.2 + dz
                out.append(C.ball("freckle", (hc.x + fx, surf(fx, fz) + 0.004, hc.z + fz), 0.0065, "pc_freckle", 5, 3))
        return out

    def balloon(D, p):
        x, y, z = p.x, p.y, p.z
        knot = Vector((x + 0.04, y + 0.03, z + 0.46))
        string = C.tube("string", [(x, y, z + 0.02), (x + 0.025, y + 0.01, z + 0.15), (x + 0.02, y + 0.02, z + 0.3),
                                   tuple(knot)], 0.0055, "pc_string", segs=4, res=2)
        bc = knot + Vector((0, 0, 0.155))
        return [string,
                C.ell("balloon", tuple(bc), (0.125, 0.125, 0.155), "pc_balloon", 16, 10),
                C.loft("knot", [(tuple(knot + Vector((0, 0, -0.012))), 0.016, 0.016), (tuple(knot + Vector((0, 0, 0.02))), 0.006, 0.006)],
                       segs=6, res=1, materials=("pc_balloon",)),
                C.ell("shine", tuple(bc + Vector((-0.05, -0.09, 0.05))), (0.025, 0.012, 0.04), "white", 8, 4,
                      rot=(0, 0.4, -0.5))]

    outfit = {
        "skin": "pc_skin_fair", "hair": "hair_ginger", "shoe": "red",
        "leg_mats": ("pc_skin_fair", "white", "denim"),
        "leg_paint": lambda i, n, s, c: 2 if c.z > hip - 0.07 else (1 if c.z < 0.1 else 0),
        "torso_mats": ("orange", "denim"), "torso_paint": lambda i, n, s, c: 1 if c.z < hip + 0.06 else 0,
        "sleeve_mat": "orange", "sleeve": 0.45,
        "body_extras": [shirt], "head_extras": [head],
        "arm_path": {1: [(shx, 0, sh - 0.03), (shx + 0.065, -0.02, sh + 0.05), (shx + 0.085, -0.04, sh + 0.17)]},
        "arm_extras": {1: [balloon]},
    }
    P, H, AL, AR = B._person(D, outfit)
    return _finish("Passenger_Boy", P, H, AL, AR, D)


# ================================================================================================ CARGO
def build_cargo_crate():
    return PL.crate_parts("cr", (0.62, 0.62, 0.5))


def build_cargo_logs():
    p = []
    logs = [(-0.215, 0.11, 1.1, 0.0), (0.0, 0.11, 1.14, 0.03), (0.215, 0.105, 1.06, -0.02)]
    circles = []
    for k, (x, r, L, dy) in enumerate(logs):
        p += PL.log_parts(f"lg{k}", L, r, (x, dy, r), segs=16, seed=k, knot=(k == 2))
        circles.append((x, r, r))
    rt = 0.1
    xt = -0.1075
    zt = 0.11 + math.sqrt((0.11 + rt) ** 2 - (0.1075) ** 2)
    p += PL.log_parts("lg3", 1.0, rt, (xt, 0.01, zt), segs=16, seed=3)
    circles.append((xt, zt, rt))
    for yy in (-0.3, 0.3):
        loop = PL.bundle_loop(circles, 0.002, yy)
        p.append(PL.flat_band("strap", loop, 0.055, 0.014, "pc_strap"))
    top = max(z + r for (_, z, r) in circles)
    # buckle on the strap where it crosses the top log's crown
    p.append(E.box("buckle", (0.07, 0.075, 0.02), (xt, -0.3, top + 0.016), "gold", bevel=0.006))
    lift = 0.002 + 0.014                     # strap pad + thickness under the bottom logs
    E.place(p, (0, 0, lift))
    return p


def build_cargo_milk():
    p = []
    for k, (x, y, band) in enumerate(((-0.15, -0.08, "blue"), (0.15, -0.08, "pc_strap"), (0.0, 0.16, "blue"))):
        p += PL.churn_parts(f"ch{k}", (x, y, 0), h=0.54, r=0.13, band=band, segs=14)
    return p


def build_cargo_hay():
    return PL.hay_parts("hay", radius=0.285, width=0.62, segs=24)


# ================================================================================================ CARGO YARD
YARD = {
    "edge_x": 0.62,        # platform edge (track side); deck top z = 0.36
    "back_x": 4.3,
    "half_len": 2.7,
    "deck_z": 0.36,
    "crane_pivot": (1.45, 2.25, 1.0),
    "jib_reach": 1.8,
    "load_point": (1.05, 0.45, 0.36),
}


def _crane(pivot):
    """Crane turret + jib built around the pivot at the origin, jib towards -Y. Returns (parts, hook_local)."""
    c = []
    c.append(E.cyl("turntable", 0.36, 0.08, (0, 0, 0.04), "charcoal", verts=20, bevel=0.025, segments=2))
    c.append(E.box("cab", (0.58, 0.6, 0.52), (0, 0.06, 0.34), "pc_crane", bevel=0.08, segments=2))
    c.append(E.box("cabroof", (0.68, 0.74, 0.08), (0, 0.06, 0.64), "pc_crane_red", bevel=0.03, segments=2))
    c.append(E.cyl("roofknob", 0.07, 0.07, (0, 0.06, 0.7), "pc_crane_red", verts=10, bevel=0.02))
    for sx in (-1, 1):
        c.append(E.cyl("cabwin", 0.12, 0.03, (sx * 0.29, 0.06, 0.4), "glass", verts=16, rot=(0, math.pi / 2, 0)))
        c.append(T.torus("cabwinrim", 0.125, 0.022, (sx * 0.295, 0.06, 0.4), E.m("white"), rot=(0, math.pi / 2, 0),
                         major_segs=16, minor_segs=4))
    c.append(E.box("frontwin", (0.36, 0.03, 0.18), (0, -0.245, 0.43), "glass", bevel=0.01))
    c.append(E.box("counterweight", (0.52, 0.22, 0.3), (0, 0.48, 0.24), "charcoal", bevel=0.06, segments=2))
    for k in range(2):
        c.append(E.box("cwstripe", (0.53, 0.225, 0.05), (0, 0.48, 0.17 + k * 0.13), "pc_crane", bevel=0.02))
    # jib: two rails + rungs (a chunky toy ladder), from the cab front up to the tip
    reach = YARD["jib_reach"]
    a0 = Vector((0, -0.18, 0.42))
    tip = Vector((0, -reach, 1.72))
    d = tip - a0
    L = d.length
    ang = math.atan2(d.z, -d.y)
    for sx in (-1, 1):
        c.append(E.box("jibrail", (0.055, L + 0.1, 0.13), tuple((a0 + tip) / 2 + Vector((sx * 0.1, 0, 0))),
                       "pc_crane_red", bevel=0.025, segments=2, rot=(-ang, 0, 0)))
    n = 6
    for k in range(n):
        q = a0 + d * ((k + 0.7) / (n + 0.4))
        c.append(E.cyl("jibrung", 0.022, 0.2, tuple(q), "pc_crane", verts=8, rot=(0, math.pi / 2, 0)))
    c.append(E.cyl("jibhinge", 0.06, 0.3, tuple(a0), "charcoal", verts=12, rot=(0, math.pi / 2, 0)))
    c.append(E.cyl("pulley", 0.1, 0.07, tuple(tip), "pc_crane", verts=16, rot=(0, math.pi / 2, 0), bevel=0.02))
    c.append(E.cyl("pulleyaxle", 0.03, 0.27, tuple(tip), "charcoal", verts=8, rot=(0, math.pi / 2, 0)))
    # rope, hook block and hook
    hb = tip.z - 0.65
    c.append(E.cyl("rope", 0.014, tip.z - 0.02 - hb, (0, tip.y - 0.1, (tip.z - 0.02 + hb) / 2), "cream", verts=6))
    c.append(E.box("hookblock", (0.13, 0.15, 0.13), (0, tip.y - 0.1, hb), "pc_crane_red", bevel=0.035, segments=2))
    c.append(E.cyl("shank", 0.016, 0.07, (0, tip.y - 0.1, hb - 0.09), "charcoal", verts=6))
    hook = C.arc("hook", (0, tip.y - 0.1, hb - 0.17), 0.045, 95, 375, 0.016, "charcoal", axis_side=(0, 1, 0),
                 axis_up=(0, 0, 1), n=10, segs=6)
    c.append(hook)
    hook_local = Vector((0, tip.y - 0.1, hb - 0.17 - 0.06))
    E.place(c, pivot)
    return c, Vector(pivot) + hook_local


def build_cargo_yard():
    p = []
    x0, x1, H, zt = YARD["edge_x"], YARD["back_x"], YARD["half_len"], YARD["deck_z"]
    L = 2 * H
    # --- timber platform: dark core, posts, beams, cross planks, painted safety edge
    p.append(E.box("core", (x1 - x0 - 0.12, L - 0.12, 0.28), ((x0 + x1) / 2, 0, 0.14), "walnut"))
    ny = 7
    for k in range(ny):
        y = -H + 0.08 + (L - 0.16) * k / (ny - 1)
        for x in (x0 + 0.08, x1 - 0.08):
            p.append(E.box("post", (0.15, 0.15, 0.3), (x, y, 0.15), "oak", bevel=0.025, segments=1))
    for x in (x0 + 0.07, x1 - 0.07):
        p.append(E.box("beam", (0.13, L, 0.11), (x, 0, 0.255), "oak", bevel=0.02, segments=1))
    for y in (-H + 0.07, H - 0.07):
        p.append(E.box("beam", (x1 - x0, 0.13, 0.11), ((x0 + x1) / 2, y, 0.255), "oak", bevel=0.02, segments=1))
        p.append(E.box("post", (0.15, 0.15, 0.3), ((x0 + x1) / 2, y, 0.15), "oak", bevel=0.025, segments=1))
    for k in range(ny - 1):     # bolts on the track-side beam
        y = -H + 0.08 + (L - 0.16) * (k + 0.5) / (ny - 1)
        p.append(E.sph("bolt", 0.025, (x0 + 0.002, y, 0.255), "charcoal", scale=(0.5, 1, 1), segs=8, rings=4))
    edge_w = 0.16
    p.append(E.box("edge", (edge_w, L + 0.02, 0.06), (x0 + edge_w / 2, 0, zt - 0.03), "yellow", bevel=0.02,
                   segments=2))
    n = 18
    pw = L / n
    for k in range(n):
        y = -H + pw * (k + 0.5)
        p.append(E.box("plank", (x1 - x0 - edge_w - 0.01, pw - 0.018, 0.05), ((x0 + edge_w + x1) / 2 + 0.005, y,
                                                                             zt - 0.025),
                       "pc_plank" if k % 2 == 0 else "pc_plank2", bevel=0.012, segments=1))
    # ramp down at the back for the hand carts
    p.append(E.prism("ramp", [(x1 - 0.02, 0.0), (x1 + 0.85, 0.0), (x1 + 0.85, 0.03), (x1 - 0.02, zt)], 1.3,
                     (0, 1.5, 0), "oak", bevel=0.015))
    for sy in (-1, 1):
        p.append(E.prism("ramprail", [(x1 - 0.02, 0.0), (x1 + 0.85, 0.0), (x1 + 0.85, 0.06), (x1 - 0.02, zt + 0.03)],
                         0.08, (0, 1.5 + sy * 0.65, 0), "walnut", bevel=0.012))

    # --- goods shed at the back (-Y end), door facing the track
    sw, sd, sH = 1.15, 1.95, 1.5
    scx, scy = x1 - 0.05 - sw / 2, -H + 0.12 + sd / 2
    pitch = 32
    rise = sw / 2 * math.tan(math.radians(pitch))
    p.append(E.gable_body(sw, sd, sH, rise, "barn_red", ridge_axis="Y", loc=(scx, scy, zt)))
    roof, rz = E.gable_roof(sd, sw, zt + sH, pitch, overhang=0.18, eave=0.22, ridge_axis="Y", centre=(scx, scy),
                            tiles=("roof_green", "roof_green2"), rows=3)
    p += roof
    p += E.corner_trims(sw, sd, zt, zt + sH, "white", t=0.08, cx=scx, cy=scy)
    dr = E.door(0.78, 1.12, "barn_red2", "white", planks=3, step=None, handle="gold")
    p += E.put(dr, "-x", sw, sd, 0.1, zt, scx, scy)
    for u in (-0.75, 0.75):
        p.append(E.box("batten", (0.03, 0.05, sH - 0.1), (scx - sw / 2 - 0.012, scy + u, zt + sH / 2), "barn_red2"))
    for u in (-0.3, 0.3):
        p.append(E.box("batten", (0.05, 0.03, sH - 0.1), (scx + u, scy - sd / 2 - 0.012, zt + sH / 2), "barn_red2"))
    p += E.put(E.round_window(0.2), "-y", sw, sd, 0, zt + sH + 0.12, scx, scy)
    p += E.put(PL.crate_pictogram("shedpic", 0.36), "-y", sw, sd, 0, zt + 0.85, scx, scy, out=0.01)

    # --- crane pedestal (fixed); the turret + jib are the swivelling child "Crane"
    px, py, pz = YARD["crane_pivot"]
    p.append(E.box("cranefoot", (0.74, 0.74, 0.08), (px, py, zt + 0.04), "charcoal", bevel=0.03, segments=2))
    for sx in (-1, 1):
        for sy in (-1, 1):
            p.append(E.sph("footbolt", 0.03, (px + sx * 0.28, py + sy * 0.28, zt + 0.085), "metal", segs=8, rings=4))
    p.append(E.lathe("pedestal", [(0.3, zt + 0.08), (0.3, zt + 0.12), (0.24, zt + 0.2), (0.21, pz - 0.12),
                                  (0.26, pz - 0.06), (0.26, pz), (0.0, pz)], (px, py, 0), "blue", segs=20))
    # --- stacked crates + barrels along the back edge, clear of the cargo pile strip (x 1.85 .. 2.95)
    cx0 = x1 - 0.55
    p += E.place(PL.crate_parts("ya", (0.6, 0.6, 0.5), stencil_faces=("-x",), slats=2), (cx0, 0.25, zt), 4)
    p += E.place(PL.crate_parts("yb", (0.6, 0.6, 0.5), stencil_faces=("-x", "-y"), slats=2), (cx0, 0.95, zt), -3)
    p += E.place(PL.crate_parts("yc", (0.5, 0.5, 0.42), stencil_faces=("-x",), slats=2, lid=False,
                                wood="pc_plank2"), (cx0 + 0.02, 0.55, zt + 0.55), 10)
    p += PL.barrel_parts("bb1", (x1 - 0.42, 1.75, zt), h=0.62, r=0.22)
    p += PL.barrel_parts("bb2", (x1 - 0.38, 2.3, zt), h=0.62, r=0.22, wood="beech_dark")

    # --- sign with a crate pictogram at the -Y end, facing the oncoming train
    sx_, sy_ = 1.3, -H + 0.25
    for dx in (-0.36, 0.36):
        p.append(E.box("signpost", (0.08, 0.08, 1.55), (sx_ + dx, sy_, zt + 0.775), "walnut", bevel=0.02))
        p.append(E.sph("signcap", 0.055, (sx_ + dx, sy_, zt + 1.57), "pc_crane_red", segs=8, rings=5))
    p.append(E.box("signboard", (0.9, 0.06, 0.66), (sx_, sy_, zt + 1.18), "pc_sign", bevel=0.03, segments=2))
    p.append(E.ring_frame("signframe", 0.9, 0.66, 0.06, 0.09, (sx_, sy_, zt + 1.18), "pc_crane_red"))
    for face in (-1, 1):
        pic = PL.crate_pictogram("signpic", 0.5, dark="beech_dark")
        E.place(pic, (sx_, sy_ + face * 0.035, zt + 1.18), 0 if face < 0 else 180)
        p += pic

    root = E.assemble(p, "CargoYard")
    cparts, hook = _crane((px, py, pz))
    crane = E.assemble(cparts, "Crane")
    E.attach(crane, root, (px, py, pz))
    # NOTE: no CraneHook empty: an empty nested under a child mesh does not survive the FBX export with
    # bake_space_transform (its transform comes back axis-swapped). The hook's Crane-local position is recorded in
    # the manifest instead ("craneHookLocalBlender" / "craneHookLocalUnity").
    YARD["hook_local"] = tuple(round(v, 3) for v in (hook - Vector((px, py, pz))))
    PL.empty("LoadPoint", YARD["load_point"], parent=root)
    return root


# ================================================================================================ pipeline
def _ground_disc(objs, pad=1.0):
    mn, mx = T._bounds([x for o in objs for x in [o] + list(o.children_recursive)])
    r = max(mx.x - mn.x, mx.y - mn.y) * 0.75 + pad
    bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=r, depth=0.02,
                                        location=((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, -0.012))
    g = bpy.context.active_object
    g.name = "__preview_ground"
    gm = bpy.data.materials.new("__ground")
    gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.30, 0.60, 0.18, 1)
    gm.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.9
    g.data.materials.append(gm)
    return g


def previews(root, name, kind):
    out = os.path.join(PREVIEW_DIR, name)
    if kind == "person":
        T.render([root], out + ".png", distance_scale=1.35)
        T.render([root], out + "_Back.png", yaw_deg=150, distance_scale=1.35)
    else:
        g = _ground_disc([root], 0.6 if kind == "cargo" else 1.0)
        T.render([root], out + ".png", distance_scale=1.15)
        T.render([root], out + "_High.png", pitch_deg=50, yaw_deg=-25, distance_scale=1.15)
        if kind == "building":
            T.render([root], out + "_Back.png", pitch_deg=35, yaw_deg=150, distance_scale=1.1)
        bpy.data.objects.remove(g, do_unlink=True)


REGISTRY = {
    # name: (folder, builder, kind, finalize kwargs, budget)
    "Passenger_Girl": ("People", build_girl, "person", dict(ao_distance=0.35, ao_strength=0.7), 2500),
    "Passenger_Grandpa": ("People", build_grandpa, "person", dict(ao_distance=0.35, ao_strength=0.7), 2500),
    "Passenger_Mum": ("People", build_mum, "person", dict(ao_distance=0.35, ao_strength=0.7), 2500),
    "Passenger_Boy": ("People", build_boy, "person", dict(ao_distance=0.35, ao_strength=0.7), 2500),
    "Cargo_Crate": ("Props", build_cargo_crate, "cargo", dict(ao_distance=0.3), 800),
    "Cargo_Logs": ("Props", build_cargo_logs, "cargo", dict(ao_distance=0.3), 800),
    "Cargo_Milk": ("Props", build_cargo_milk, "cargo", dict(ao_distance=0.3), 800),
    "Cargo_Hay": ("Props", build_cargo_hay, "cargo", dict(ao_distance=0.3), 800),
    "CargoYard": ("Buildings", build_cargo_yard, "building", dict(ao_strength=0.65), 6000),
}

# Car_Cargo open bed interior (from build_trains.build_cargo): planks at x = +/-0.425, ends at y = +/-0.776,
# plank thickness 0.048 -> inner 0.802 x 1.504; floor 0.56 above the vehicle origin, walls 0.40 high.
WAGON_BED = (0.80, 1.50)


def build_one(name, do_preview=True):
    folder, fn, kind, fin, budget = REGISTRY[name]
    T.reset()
    res = fn()
    if kind == "person":
        root, parts = res
        meshes = [root] + parts
        T.finalize(meshes, **fin)
        for q in parts:
            C.parent_keep(q, root)
    elif kind == "cargo":
        root = E.assemble(res, name)
        meshes = [root]
        T.finalize(meshes, **fin)
    else:
        root = res
        meshes = [root] + [c for c in root.children_recursive if c.type == 'MESH']
        T.finalize(meshes, **fin)
    root.location = (0, 0, 0)
    bpy.context.view_layer.update()
    T.export_fbx(f"{folder}/{name}", [root])
    v, t = T.stats(meshes)
    mn, mx = T._bounds(meshes)
    size = [round(mx.x - mn.x, 3), round(mx.y - mn.y, 3), round(mx.z - mn.z, 3)]
    entry = {"name": name, "fbx": f"_Project/Art/Models/{folder}/{name}.fbx"}
    if kind == "person":
        rad = max(abs(mn.x), abs(mx.x), abs(mn.y), abs(mx.y))
        entry.update({"kind": "person", "sound": "hello", "footprintRadius": round(rad, 3), "height": round(mx.z, 3)})
    else:
        entry.update({"category": "cargo" if kind == "cargo" else "building",
                      "footprint": [round(mx.x - mn.x, 2), round(mx.y - mn.y, 2)], "height": round(mx.z, 2)})
    entry["parts"] = [c.name for c in root.children_recursive]
    entry["verts"] = v
    entry["size"] = size
    entry["bounds"] = [[round(mn.x, 3), round(mn.y, 3), round(mn.z, 3)], [round(mx.x, 3), round(mx.y, 3), round(mx.z, 3)]]
    if kind == "cargo":
        fits = size[0] <= WAGON_BED[0] - 0.08 and size[1] <= WAGON_BED[1] - 0.08 and size[2] <= 0.6
        entry["fitsCargoWagon"] = bool(fits)
        if not fits:
            print(f"[PC] WARNING {name} does not fit the wagon bed: {size}")
    if kind == "building":
        pts = {}
        for c in root.children_recursive:
            pts[c.name] = [round(x, 3) for x in c.matrix_world.translation]
        entry["points"] = pts
        hl = YARD.get("hook_local")
        if hl:
            entry["craneHookLocalBlender"] = list(hl)
            entry["craneHookLocalUnity"] = [round(-hl[0], 3), round(hl[2], 3), round(-hl[1], 3)]
    flag = "" if v <= budget else f"  !!! OVER BUDGET ({budget})"
    print(f"[PC] {name}: verts={v} tris={t} size={size} bounds={entry['bounds']}{flag}")
    if do_preview:
        previews(root, name, kind)
    return entry


def main():
    global PREVIEW_DIR
    argv = T.args()
    if "--preview" in argv:
        i = argv.index("--preview")
        PREVIEW_DIR = argv[i + 1]
        argv = argv[:i] + argv[i + 2:]
    flags = [a for a in argv if a.startswith("--")]
    names = [a for a in argv if not a.startswith("--")] or list(REGISTRY)
    manifest = {}
    if os.path.exists(MANIFEST):
        try:
            for e in json.load(open(MANIFEST)):
                manifest[e["name"]] = e
        except Exception:
            pass
    for n in names:
        manifest[n] = build_one(n, "--no-preview" not in flags)
    order = [n for n in REGISTRY if n in manifest]
    with open(MANIFEST, "w") as f:
        json.dump([manifest[n] for n in order], f, indent=2)
    print("[PC] manifest written", MANIFEST)


if __name__ == "__main__":
    main()
