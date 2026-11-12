"""
Tiny Tracks World - animals and people (premium collectible toy figures).

Run:  blender -b --factory-startup --python Tools/blender/models/build_creatures.py -- [Cow Sheep ... | Lineup]
      (no names = build everything + lineup; "Lineup" = only re-render the lineup from the exported FBX files)
Exports Assets/_Project/Art/Models/Animals/<Name>.fbx and .../People/<Name>.fbx, previews in Logs/Blender,
the lineup Logs/Blender/Creatures_Lineup.png and Tools/blender/models/creatures_manifest.json.

Animated parts (separate child objects, origin = pivot): Head (neck pivot), Tail (tail base),
WingL/WingR (bird shoulders), ArmL/ArmR (people shoulders). Root origin = ground contact centre.
Front faces -Y, model's right = -X (so ArmR / the right eye are on -X).
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import tt_common as T  # noqa: E402
import creatures_lib as C  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
MANIFEST = os.path.join(HERE, "creatures_manifest.json")


def legs4(prefix, xs, ys, top_z, mat_leg, mat_hoof, w_top=0.08, w_mid=0.065, w_low=0.058, hoof_h=0.09,
          hoof_w=0.07, thigh=None, segs=12):
    """Four straight toy legs with hooves/paws. thigh = (extra_w, extra_h) for chunky rear thighs."""
    out = []
    for (x, y, rear) in [(xs, ys[0], False), (xs, ys[1], True)]:
        keys = []
        if rear and thigh:
            keys.append(((x, y + 0.03, top_z + 0.02), w_top + thigh[0], w_top + thigh[1]))
            keys.append(((x, y + 0.01, top_z * 0.62), w_mid + 0.004, w_mid + 0.012))
        else:
            keys.append(((x, y, top_z), w_top, w_top * 1.05))
            keys.append(((x, y, top_z * 0.6), w_mid, w_mid * 1.05))
        keys.append(((x, y, hoof_h + 0.03), w_low, w_low * 1.05))
        keys.append(((x, y, hoof_h - 0.01), w_low * 1.02, w_low * 1.07))
        leg = C.loft(f"{prefix}_leg", keys, segs=segs, res=2, materials=(mat_leg,), up=(0, -1, 0))
        hoof = C.loft(f"{prefix}_hoof", [((x, y, hoof_h), hoof_w * 0.95, hoof_w), ((x, y, hoof_h * 0.5), hoof_w * 1.04,
                                                                                    hoof_w * 1.08),
                                         ((x, y, 0.0), hoof_w * 1.08, hoof_w * 1.12)],
                      segs=segs, res=1, materials=(mat_hoof,), up=(0, -1, 0), smooth_angle=50)
        out += [leg, hoof, C.mirror(leg), C.mirror(hoof)]
    return out


# ================================================================================================ COW
def build_cow():
    P = []
    # body: barrel with a soft belly, slightly higher at the shoulders and hips
    body_keys = [
        ((0, 0.42, 0.75), 0.215, 0.205),
        ((0, 0.30, 0.735), 0.25, 0.245),
        ((0, 0.05, 0.70), 0.265, 0.28),
        ((0, -0.20, 0.72), 0.25, 0.26),
        ((0, -0.34, 0.75), 0.21, 0.235),
        ((0, -0.44, 0.84), 0.15, 0.17),
        ((0, -0.51, 0.91), 0.115, 0.125),
    ]
    body = C.loft("cow_body", body_keys, segs=20, res=3, materials=("fur_white",), dome_start=0.12, dome_end=0.04,
                  dome_rings=4, exp=2.3)
    chest = C.ell("brisket", (0, -0.33, 0.66), (0.17, 0.12, 0.15), "fur_white", 14, 8)
    P += [body, chest]
    P += legs4("cow", 0.15, (-0.27, 0.27), 0.62, "fur_white", "hoof", w_top=0.085, w_mid=0.07, w_low=0.062,
               hoof_h=0.09, hoof_w=0.068, thigh=(0.035, 0.07))
    # udder (subtle)
    P.append(C.ell("udder", (0, 0.17, 0.42), (0.1, 0.09, 0.065), "cow_muzzle", 12, 8))
    for x in (-0.04, 0.04):
        for y in (0.13, 0.21):
            P.append(C.tube("teat", [(x, y, 0.40), (x, y, 0.345)], 0.016, "cow_muzzle", segs=5, dome_end=0.012))
    # patches (decals following the body surface)
    full = C.loft("cow_full_tmp", body_keys, segs=20, res=3, materials=("fur_white",), dome_start=0.12,
                  dome_end=0.04, dome_rings=4, exp=2.3)
    blobs = [
        C.blob("b1", (-0.22, 0.12, 0.80), (0.2, 0.2, 0.16), seed=3),
        C.blob("b2", (0.25, -0.12, 0.72), (0.2, 0.17, 0.2), seed=5),
        C.blob("b3", (0.08, 0.36, 0.95), (0.15, 0.13, 0.12), seed=8),
        C.blob("b4", (-0.2, -0.28, 0.60), (0.14, 0.12, 0.14), seed=11),
    ]
    for i, b in enumerate(blobs):
        P.append(C.shell_patch(f"patch{i}", full, b, "cow_patch", offset=0.006))
    bpy.data.objects.remove(full, do_unlink=True)

    # ---- head (pivot at the top of the neck)
    H = []
    head_keys = [((0, -0.50, 0.99), 0.12, 0.12), ((0, -0.60, 0.98), 0.145, 0.14),
                 ((0, -0.71, 0.89), 0.125, 0.11), ((0, -0.78, 0.82), 0.12, 0.095)]
    head = C.loft("cow_head", head_keys, segs=16, res=3, materials=("fur_white",), dome_start=0.07, dome_end=0.05)
    H.append(head)
    headc = C.loft("cow_head_tmp", head_keys, segs=16, res=3, materials=("fur_white",), dome_start=0.07, dome_end=0.05)
    H.append(C.shell_patch("head_patch", headc, C.blob("hb", (0.11, -0.66, 1.02), (0.09, 0.1, 0.08), seed=2),
                           "cow_patch", offset=0.004))
    bpy.data.objects.remove(headc, do_unlink=True)
    H.append(C.ell("muzzle", (0, -0.815, 0.80), (0.145, 0.10, 0.105), "cow_muzzle", segs=16, rings=10))
    for s in (1, -1):
        H.append(C.ell("nostril", (s * 0.055, -0.905, 0.825), (0.022, 0.012, 0.016), "mouth", 8, 5,
                       rot=(0, 0, s * 0.3)))
    H.append(C.arc("smile", (0, -0.86, 0.80), 0.06, 200, 340, 0.008, "mouth", axis_side=(1, 0, 0),
                   axis_up=(0, -0.45, 0.9), n=8))
    for s in (1, -1):
        H += C.eye(f"eye{s}", (s * 0.098, -0.70, 0.975), 0.05, (s * 0.55, -1, 0.25))
        ear = C.ell("ear", (s * 0.205, -0.525, 1.0), (0.095, 0.024, 0.042), "fur_white", 12, 6,
                    rot=(0.25, s * -0.45, s * 0.35))
        inner = C.ell("ear_in", (s * 0.21, -0.54, 0.997), (0.072, 0.012, 0.028), "cow_muzzle", 10, 5,
                      rot=(0.25, s * -0.45, s * 0.35))
        horn = C.tube("horn", [(s * 0.08, -0.55, 1.07), (s * 0.13, -0.55, 1.1), (s * 0.155, -0.56, 1.15)],
                      0.028, "horn", segs=8, radius_end=0.012, dome_end=0.012)
        H += [ear, inner, horn]
    # forelock tuft
    H.append(C.ell("tuft", (0, -0.565, 1.10), (0.06, 0.05, 0.04), "cow_patch", 10, 6))
    # ---- tail
    tail = [C.tube("tail", [(0, 0.52, 0.84), (0, 0.6, 0.80), (0, 0.635, 0.66), (0, 0.63, 0.50)], 0.022, "fur_white",
                   segs=8, radius_end=0.016),
            C.ell("tuft", (0, 0.63, 0.46), (0.04, 0.04, 0.07), "cow_patch", 10, 6)]
    C.report(P + H + tail)
    root = T.join(P, "Cow")
    hd = C.part(H, "Head", (0, -0.50, 0.92))
    tl = C.part(tail, "Tail", (0, 0.52, 0.84))
    return root, [hd, tl], {"kind": "animal", "sound": "moo", "folder": "Animals", "budget": 3500}


# ================================================================================================ SHEEP
def _fib_points(n, zmin=-1.0):
    pts = []
    ga = math.pi * (3 - math.sqrt(5))
    for i in range(n):
        z = 1 - 2 * (i + 0.5) / n
        r = math.sqrt(max(0.0, 1 - z * z))
        a = ga * i
        if z >= zmin:
            pts.append(Vector((r * math.cos(a), r * math.sin(a), z)))
    return pts


def build_sheep():
    P = []
    c = Vector((0, 0.03, 0.47))
    R = Vector((0.24, 0.33, 0.2))
    P.append(C.ell("core", c, (R.x * 1.02, R.y * 1.02, R.z * 1.02), "wool", 12, 7))
    for i, d in enumerate(_fib_points(23, zmin=-0.5)):
        p = c + Vector((d.x * R.x, d.y * R.y, d.z * R.z)) * 0.93
        r = 0.105 + 0.025 * ((i * 7) % 5) / 4
        P.append(C.ball(f"puff{i}", p, r * 1.05, "wool", 8, 6))
    P += legs4("sheep", 0.12, (-0.18, 0.2), 0.36, "sheep_face", "hoof", w_top=0.042, w_mid=0.036, w_low=0.033,
               hoof_h=0.06, hoof_w=0.038, segs=7)
    # head: dark long face with a wool fringe
    H = []
    hk = [((0, -0.27, 0.64), 0.085, 0.095), ((0, -0.37, 0.62), 0.09, 0.095), ((0, -0.46, 0.56), 0.065, 0.065)]
    H.append(C.loft("sheep_head", hk, segs=12, res=3, materials=("sheep_face",), dome_start=0.05, dome_end=0.045))
    H.append(C.ell("snout", (0, -0.49, 0.545), (0.055, 0.035, 0.04), "sheep_face", 8, 5))
    for s in (1, -1):
        H.append(C.ell("nostril", (s * 0.022, -0.52, 0.56), (0.01, 0.006, 0.007), "mouth", 6, 3))
    H.append(C.arc("smile", (0, -0.505, 0.54), 0.03, 205, 335, 0.006, "grey_light", axis_up=(0, -0.5, 0.85), n=5, segs=5))
    for i, (x, y, z, r) in enumerate([(0, -0.34, 0.725, 0.058), (0.055, -0.30, 0.71, 0.055),
                                      (-0.055, -0.30, 0.71, 0.055), (0, -0.27, 0.73, 0.06)]):
        H.append(C.ball(f"fringe{i}", (x, y, z), r, "wool", 8, 6))
    for s in (1, -1):
        H += C.eye(f"eye{s}", (s * 0.06, -0.415, 0.64), 0.034, (s * 0.5, -1, 0.15))
        ear = C.ell("ear", (s * 0.13, -0.31, 0.65), (0.075, 0.028, 0.03), "sheep_face", 8, 5, rot=(0, s * 0.35, s * -0.3))
        inner = C.ell("ear_in", (s * 0.135, -0.322, 0.648), (0.055, 0.012, 0.018), "nose_pink", 6, 4,
                      rot=(0, s * 0.35, s * -0.3))
        H += [ear, inner]
    tail = [C.ell("tail", (0, 0.39, 0.52), (0.06, 0.06, 0.075), "wool", 8, 5, rot=(-0.4, 0, 0))]
    C.report(P + H + tail)
    root = T.join(P, "Sheep")
    hd = C.part(H, "Head", (0, -0.26, 0.58))
    tl = C.part(tail, "Tail", (0, 0.35, 0.56))
    return root, [hd, tl], {"kind": "animal", "sound": "baa", "folder": "Animals", "budget": 2000}


# ================================================================================================ CHICKEN
def build_chicken():
    P = []
    bk = [((0, -0.11, 0.25), 0.075, 0.085), ((0, -0.05, 0.215), 0.11, 0.11), ((0, 0.05, 0.215), 0.105, 0.1),
          ((0, 0.12, 0.25), 0.065, 0.065)]
    body = C.loft("hen_body", bk, segs=16, res=3, materials=("hen", "hen_chest"), dome_start=0.05, dome_end=0.05,
                  paint=lambda i, n, s, ctr: 1 if (ctr.y < -0.06 and ctr.z < 0.26) else 0)
    neck = C.tube("neck", [(0, -0.09, 0.26), (0, -0.1, 0.31), (0, -0.1, 0.34)], 0.055, "hen", segs=12,
                  radius_end=0.045)
    P += [body, neck]
    for s in (1, -1):
        wing = C.loft("wing", [((s * 0.1, -0.06, 0.24), 0.05, 0.02), ((s * 0.108, 0.02, 0.235), 0.06, 0.022),
                               ((s * 0.095, 0.11, 0.25), 0.03, 0.012)], segs=10, res=2,
                      materials=("hen_dark",), up=(s, 0, 0), dome_start=0.03, dome_end=0.03)
        P.append(wing)
        leg = C.tube("leg", [(s * 0.045, 0.0, 0.16), (s * 0.045, -0.005, 0.07), (s * 0.045, -0.01, 0.02)], 0.013,
                     "hen_leg", segs=6, radius_end=0.01)
        P.append(leg)
        thigh = C.ell("thigh", (s * 0.05, 0.0, 0.15), (0.04, 0.045, 0.045), "hen", 10, 6)
        P.append(thigh)
        for a in (-0.5, 0, 0.5):
            d = Vector((math.sin(a), -math.cos(a), 0))
            p0 = Vector((s * 0.045, -0.01, 0.012))
            P.append(C.tube("toe", [p0, p0 + d * 0.05], 0.009, "hen_leg", segs=5, dome_end=0.008, res=1))
        P.append(C.tube("toe", [Vector((s * 0.045, -0.01, 0.012)), Vector((s * 0.045, 0.025, 0.012))], 0.008,
                        "hen_leg", segs=5, dome_end=0.007, res=1))
    H = []
    H.append(C.ell("head", (0, -0.115, 0.375), (0.06, 0.065, 0.062), "hen", 14, 9))
    for i, (y, z, r) in enumerate([(-0.15, 0.428, 0.024), (-0.12, 0.445, 0.029), (-0.088, 0.44, 0.026),
                                   (-0.062, 0.425, 0.02)]):
        H.append(C.ball(f"comb{i}", (0, y, z), r, "comb", 8, 6))
    H.append(C.loft("beak", [((0, -0.165, 0.372), 0.024, 0.02), ((0, -0.19, 0.366), 0.016, 0.012),
                             ((0, -0.21, 0.36), 0.004, 0.004)], segs=10, res=2, materials=("beak",),
                    dome_end=0.004, dome_rings=2))
    H.append(C.ell("wattle", (0, -0.165, 0.335), (0.016, 0.014, 0.026), "comb", 8, 6))
    for s in (1, -1):
        H += C.eye(f"eye{s}", (s * 0.04, -0.152, 0.39), 0.021, (s * 0.65, -1, 0.15))
        H.append(C.ell("cheek", (s * 0.052, -0.13, 0.36), (0.008, 0.014, 0.012), "comb", 6, 4))
    tail = []
    for i, (a, ln) in enumerate([(-0.45, 0.1), (0.0, 0.12), (0.45, 0.1)]):
        tail.append(C.loft(f"tailf{i}", [((0, 0.12, 0.27), 0.02, 0.035), ((math.sin(a) * 0.03, 0.17, 0.33), 0.03, 0.05),
                                         ((math.sin(a) * 0.05, 0.19, 0.27 + ln + 0.02), 0.015, 0.03)],
                           segs=10, res=2, materials=("hen_dark",), up=(0, 1, 0), dome_end=0.02, dome_start=0.01))
    C.report(P + H + tail)
    root = T.join(P, "Chicken")
    hd = C.part(H, "Head", (0, -0.10, 0.32))
    tl = C.part(tail, "Tail", (0, 0.12, 0.27))
    return root, [hd, tl], {"kind": "animal", "sound": "cluck", "folder": "Animals", "budget": 2000}


# ================================================================================================ DOG
def build_dog():
    P = []
    bk = [((0, 0.21, 0.31), 0.095, 0.095), ((0, 0.08, 0.30), 0.11, 0.115), ((0, -0.07, 0.31), 0.115, 0.125),
          ((0, -0.16, 0.34), 0.1, 0.115), ((0, -0.22, 0.40), 0.08, 0.085)]
    body = C.loft("dog_body", bk, segs=16, res=3, materials=("puppy", "fur_white"), dome_start=0.07, dome_end=0.03,
                  paint=lambda i, n, s, c: 1 if (c.y < -0.08 and c.z < 0.33 and abs(c.x) < 0.09) else 0)
    P.append(body)
    P += legs4("dog", 0.075, (-0.13, 0.17), 0.27, "puppy", "fur_white", w_top=0.05, w_mid=0.042, w_low=0.04,
               hoof_h=0.06, hoof_w=0.045, thigh=(0.02, 0.04), segs=10)
    P.append(C.torus("collar", 0.085, 0.017, loc=(0, -0.215, 0.405), material=None, rot=(math.radians(55), 0, 0),
                     major_segs=20, minor_segs=6))
    C._mats(P[-1], ["collar"])
    P.append(C.ell("tag", (0, -0.29, 0.355), (0.022, 0.008, 0.022), "gold", 10, 6, rot=(0.6, 0, 0)))
    H = []
    hk = [((0, -0.20, 0.53), 0.12, 0.12), ((0, -0.27, 0.53), 0.13, 0.125), ((0, -0.33, 0.51), 0.11, 0.11)]
    H.append(C.loft("dog_head", hk, segs=18, res=2, materials=("puppy",), dome_start=0.08, dome_end=0.06))
    H.append(C.ell("muzzle", (0, -0.385, 0.475), (0.072, 0.065, 0.055), "fur_white", 14, 8))
    H.append(C.ell("nose", (0, -0.445, 0.5), (0.03, 0.02, 0.022), "eye_black", 10, 6))
    H.append(C.ball("nose_hl", (0.008, -0.462, 0.512), 0.006, "grey_light", 5, 3))
    H.append(C.arc("smile", (0, -0.445, 0.47), 0.03, 200, 340, 0.006, "eye_black", axis_up=(0, -0.3, 0.95), n=6))
    H.append(C.ell("tongue", (0, -0.44, 0.44), (0.02, 0.012, 0.022), "tongue", 8, 5, rot=(0.3, 0, 0)))
    for s in (1, -1):
        H += C.eye(f"eye{s}", (s * 0.06, -0.366, 0.56), 0.034, (s * 0.35, -1, 0.15))
        ear = C.loft("ear", [((s * 0.095, -0.22, 0.63), 0.045, 0.014), ((s * 0.135, -0.24, 0.58), 0.055, 0.016),
                             ((s * 0.15, -0.25, 0.49), 0.045, 0.014)], segs=10, res=2, materials=("puppy_dark",),
                     up=(s, 0, 0), dome_start=0.01, dome_end=0.035)
        H.append(ear)
    tail = [C.tube("tail", [(0, 0.27, 0.35), (0, 0.32, 0.41), (0, 0.33, 0.48), (0, 0.31, 0.53)], 0.026, "puppy",
                   segs=8, radius_end=0.014, dome_end=0.015),
            C.ball("tailtip", (0, 0.31, 0.535), 0.018, "fur_white", 8, 5)]
    C.report(P + H + tail)
    root = T.join(P, "Dog")
    hd = C.part(H, "Head", (0, -0.21, 0.43))
    tl = C.part(tail, "Tail", (0, 0.27, 0.35))
    return root, [hd, tl], {"kind": "animal", "sound": "bark", "folder": "Animals", "budget": 2000}


# ================================================================================================ CAT
def _stripe(period, width, zmin):
    def f(i, n, s, c):
        return 1 if (i % period) < width and c.z > zmin else 0
    return f


def build_cat():
    P = []
    bk = [((0, 0.15, 0.21), 0.07, 0.072), ((0, 0.04, 0.2), 0.078, 0.082), ((0, -0.07, 0.21), 0.08, 0.085),
          ((0, -0.13, 0.235), 0.07, 0.075)]
    stripe = lambda i, n, s, c: 1 if (i % 4) < 2 and c.z > 0.21 and 3 < i < n - 3 else (
        2 if c.z < 0.165 and c.y < -0.0 else 0)
    P.append(C.loft("cat_body", bk, segs=16, res=5, materials=("ginger", "ginger_dark", "cream"), dome_start=0.06,
                    dome_end=0.05, paint=stripe))
    P += legs4("cat", 0.048, (-0.1, 0.12), 0.18, "ginger", "cream", w_top=0.034, w_mid=0.028, w_low=0.026,
               hoof_h=0.04, hoof_w=0.03, thigh=(0.015, 0.03), segs=8)
    H = []
    H.append(C.ell("head", (0, -0.2, 0.31), (0.1, 0.088, 0.085), "ginger", 18, 12))
    H.append(C.ell("cheeks", (0, -0.235, 0.28), (0.085, 0.06, 0.05), "ginger", 14, 8))
    H.append(C.ell("muzzle", (0, -0.282, 0.283), (0.045, 0.025, 0.03), "cream", 10, 6))
    H.append(C.ell("nose", (0, -0.302, 0.3), (0.014, 0.008, 0.009), "nose_pink", 8, 5))
    H.append(C.arc("smile", (0, -0.305, 0.282), 0.016, 200, 340, 0.004, "mouth", axis_up=(0, -0.3, 0.95), n=6))
    for i, x in enumerate((-0.03, 0.0, 0.03)):
        H.append(C.ell(f"fstripe{i}", (x, -0.235, 0.375), (0.009, 0.03, 0.006), "ginger_dark", 8, 4,
                       rot=(-0.9, 0, 0)))
    for s in (1, -1):
        H += C.eye(f"eye{s}", (s * 0.042, -0.262, 0.322), 0.026, (s * 0.35, -1, 0.1), iris="cat_eye",
                   pupil_scale=0.8)
        H.append(C.ell(f"pupil{s}", (s * 0.046, -0.29, 0.324), (0.006, 0.005, 0.014), "eye_black", 6, 4,
                       rot=(0, 0, s * 0.35)))
        ear = C.loft("ear", [((s * 0.055, -0.19, 0.36), 0.04, 0.018), ((s * 0.07, -0.19, 0.42), 0.0, 0.0)],
                     segs=10, res=1, materials=("ginger",), up=(0, -1, 0))
        inner = C.loft("ear_in", [((s * 0.056, -0.199, 0.365), 0.026, 0.008), ((s * 0.067, -0.199, 0.41), 0.0, 0.0)],
                       segs=8, res=1, materials=("nose_pink",), up=(0, -1, 0))
        H += [ear, inner]
        for k, a in enumerate((-8, 8)):
            d = Vector((s * math.cos(math.radians(a)), -0.25, math.sin(math.radians(a)))).normalized()
            p0 = Vector((s * 0.035, -0.285, 0.29))
            H.append(C.tube("whisker", [p0, p0 + d * 0.07], 0.0025, "white", segs=4, res=1))
    tk = [((0, 0.18, 0.23), 0.026, 0.026), ((0, 0.24, 0.30), 0.024, 0.024), ((0, 0.25, 0.40), 0.022, 0.022),
          ((0, 0.23, 0.48), 0.02, 0.02), ((0, 0.19, 0.52), 0.018, 0.018)]
    tail = [C.loft("tail", tk, segs=10, res=4, materials=("ginger", "ginger_dark"), dome_end=0.018,
                   paint=lambda i, n, s, c: 1 if (i % 3) == 0 and i > 2 else 0)]
    C.report(P + H + tail)
    root = T.join(P, "Cat")
    hd = C.part(H, "Head", (0, -0.15, 0.27))
    tl = C.part(tail, "Tail", (0, 0.18, 0.23))
    return root, [hd, tl], {"kind": "animal", "sound": "meow", "folder": "Animals", "budget": 2000}


# ================================================================================================ HORSE
def build_horse():
    P = []
    bk = [((0, 0.45, 0.94), 0.19, 0.19), ((0, 0.30, 0.93), 0.215, 0.225), ((0, 0.05, 0.90), 0.21, 0.235),
          ((0, -0.22, 0.92), 0.2, 0.235), ((0, -0.36, 1.00), 0.16, 0.2), ((0, -0.45, 1.14), 0.11, 0.14),
          ((0, -0.51, 1.28), 0.09, 0.11), ((0, -0.54, 1.37), 0.085, 0.1)]
    P.append(C.loft("horse_body", bk, segs=18, res=3, materials=("horse",), dome_start=0.12, dome_end=0.04,
                    exp=2.2))
    P.append(C.ell("chest", (0, -0.31, 0.85), (0.15, 0.11, 0.15), "horse", 12, 8))
    # legs: long, slimmer at the cannon, darker socks + hooves
    for (y, rear) in ((-0.29, False), (0.31, True)):
        x = 0.13
        if rear:
            keys = [((x, y + 0.03, 0.92), 0.105, 0.17), ((x, y + 0.04, 0.6), 0.075, 0.09), ((x, y, 0.42), 0.054, 0.064),
                    ((x, y, 0.2), 0.048, 0.054), ((x, y - 0.01, 0.1), 0.054, 0.06)]
        else:
            keys = [((x, y, 0.9), 0.09, 0.115), ((x, y, 0.6), 0.064, 0.075), ((x, y, 0.42), 0.05, 0.058),
                    ((x, y, 0.2), 0.047, 0.053), ((x, y - 0.01, 0.1), 0.054, 0.06)]
        leg = C.loft("leg", keys, segs=10, res=2, materials=("horse", "horse_dark"), up=(0, -1, 0),
                     paint=lambda i, n, s, c: 1 if c.z < 0.22 else 0)
        hoof = C.loft("hoof", [((x, y - 0.01, 0.1), 0.056, 0.062), ((x, y - 0.01, 0.0), 0.066, 0.072)], segs=10,
                      res=1, materials=("hoof",), up=(0, -1, 0), smooth_angle=50)
        P += [leg, hoof, C.mirror(leg), C.mirror(hoof)]
    # mane along the neck crest
    mk = [((0, -0.29, 1.15), 0.035, 0.05), ((0, -0.38, 1.28), 0.055, 0.08), ((0, -0.44, 1.39), 0.055, 0.08),
          ((0, -0.48, 1.47), 0.04, 0.05)]
    P.append(C.loft("mane", mk, segs=10, res=3, materials=("horse_dark",), dome_start=0.04, dome_end=0.03))
    for i, (y, z) in enumerate([(-0.31, 1.19), (-0.37, 1.28), (-0.42, 1.36), (-0.46, 1.44)]):
        P.append(C.ell(f"mane_lock{i}", (0, y + 0.03, z), (0.05, 0.065, 0.055), "horse_dark", 10, 6,
                       rot=(0.5, 0, 0)))
    H = []
    hk = [((0, -0.53, 1.47), 0.085, 0.09), ((0, -0.61, 1.44), 0.09, 0.095), ((0, -0.72, 1.33), 0.068, 0.072),
          ((0, -0.78, 1.26), 0.072, 0.068)]
    head = C.loft("horse_head", hk, segs=16, res=3, materials=("horse",), dome_start=0.07, dome_end=0.06)
    headc = C.loft("horse_head_tmp", hk, segs=16, res=3, materials=("horse",), dome_start=0.07, dome_end=0.06)
    H.append(head)
    H.append(C.shell_patch("blaze", headc, C.blob("bz", (0, -0.71, 1.38), (0.032, 0.19, 0.055), rot=(0.8, 0, 0),
                                                  jitter=0.06, seed=4), "white", offset=0.004))
    bpy.data.objects.remove(headc, do_unlink=True)
    H.append(C.ell("muzzle", (0, -0.81, 1.23), (0.078, 0.068, 0.064), "horse_dark", 12, 8))
    for s in (1, -1):
        H.append(C.ell("nostril", (s * 0.038, -0.87, 1.245), (0.016, 0.01, 0.014), "eye_black", 6, 4))
        H += C.eye(f"eye{s}", (s * 0.075, -0.605, 1.48), 0.045, (s * 0.7, -1, 0.15))
        ear = C.loft("ear", [((s * 0.045, -0.53, 1.53), 0.03, 0.018), ((s * 0.055, -0.53, 1.59), 0.025, 0.014),
                             ((s * 0.062, -0.54, 1.64), 0.0, 0.0)], segs=8, res=2, materials=("horse",),
                     up=(0, -1, 0))
        H.append(ear)
    H.append(C.arc("smile", (0, -0.855, 1.215), 0.04, 205, 335, 0.006, "eye_black", axis_up=(0, -0.4, 0.9), n=6))
    for i, (x, y, z) in enumerate([(0, -0.575, 1.565), (0.03, -0.59, 1.545), (-0.03, -0.59, 1.545)]):
        H.append(C.ell(f"forelock{i}", (x, y, z), (0.035, 0.035, 0.05), "horse_dark", 8, 6, rot=(0.6, 0, 0)))
    tk = [((0, 0.56, 1.02), 0.04, 0.045), ((0, 0.66, 0.98), 0.055, 0.06), ((0, 0.72, 0.82), 0.07, 0.065),
          ((0, 0.72, 0.6), 0.055, 0.05)]
    tail = [C.loft("tail", tk, segs=10, res=3, materials=("horse_dark",), dome_end=0.06, dome_start=0.02)]
    C.report(P + H + tail)
    root = T.join(P, "Horse")
    hd = C.part(H, "Head", (0, -0.53, 1.39))
    tl = C.part(tail, "Tail", (0, 0.56, 1.02))
    return root, [hd, tl], {"kind": "animal", "sound": "neigh", "folder": "Animals", "budget": 3500}


# ================================================================================================ BIRD
def build_bird():
    P = []
    bk = [((0, -0.07, 0.115), 0.05, 0.055), ((0, -0.01, 0.105), 0.065, 0.065), ((0, 0.06, 0.11), 0.05, 0.045),
          ((0, 0.11, 0.125), 0.025, 0.018)]
    P.append(C.loft("bird_body", bk, segs=14, res=3, materials=("bluebird", "robin_belly"), dome_start=0.04,
                    dome_end=0.02, paint=lambda i, n, s, c: 1 if c.z < 0.11 and c.y < 0.04 else 0))
    for s in (1, -1):
        P.append(C.tube("leg", [(s * 0.02, -0.01, 0.06), (s * 0.02, -0.015, 0.008)], 0.006, "charcoal", segs=5))
        for a in (-0.45, 0.0, 0.45):
            p0 = Vector((s * 0.02, -0.015, 0.006))
            d = Vector((math.sin(a), -math.cos(a), 0))
            P.append(C.tube("toe", [p0, p0 + d * 0.025], 0.005, "charcoal", segs=4, dome_end=0.004, res=1))
    H = []
    H.append(C.ell("head", (0, -0.085, 0.175), (0.052, 0.052, 0.05), "bluebird", 14, 9))
    H.append(C.loft("beak", [((0, -0.128, 0.172), 0.016, 0.012), ((0, -0.15, 0.168), 0.003, 0.003)], segs=8,
                    res=1, materials=("beak",)))
    for s in (1, -1):
        H += C.eye(f"eye{s}", (s * 0.03, -0.118, 0.185), 0.017, (s * 0.6, -1, 0.15))
    H.append(C.ell("crest", (0, -0.07, 0.225), (0.012, 0.03, 0.018), "bluebird_dk", 8, 5, rot=(-0.5, 0, 0)))
    wings = []
    for s, nm in ((1, "WingL"), (-1, "WingR")):
        wk = [((s * 0.035, -0.01, 0.13), 0.045, 0.014), ((s * 0.11, 0.0, 0.15), 0.06, 0.011),
              ((s * 0.19, 0.015, 0.16), 0.05, 0.008), ((s * 0.245, 0.03, 0.165), 0.025, 0.006)]
        w = C.loft(nm, wk, segs=12, res=3, materials=("bluebird", "bluebird_dk"), dome_end=0.02, dome_start=0.01,
                   up=(0, 0, 1), paint=lambda i, n, ss, c: 1 if abs(c.x) > 0.16 else 0)
        T.set_origin(w, (s * 0.035, -0.01, 0.13))
        wings.append(w)
    tail = [C.loft("tail", [((0, 0.09, 0.12), 0.02, 0.008), ((0, 0.15, 0.14), 0.04, 0.006),
                            ((0, 0.19, 0.155), 0.045, 0.005)], segs=10, res=2, materials=("bluebird_dk",),
                   dome_end=0.01)]
    C.report(P + H + wings + tail)
    root = T.join(P, "Bird")
    hd = C.part(H, "Head", (0, -0.07, 0.14))
    tl = C.part(tail, "Tail", (0, 0.09, 0.12))
    wl = C.part([wings[0]], "WingL", (0.035, -0.01, 0.13))
    wr = C.part([wings[1]], "WingR", (-0.035, -0.01, 0.13))
    return root, [hd, tl, wl, wr], {"kind": "bird", "sound": "tweet", "folder": "Animals", "budget": 2000}


# ================================================================================================ PEOPLE
def _face(H, hc, hr, skin, hair, brows=True, cheeks=True):
    """Big friendly toy face on a head centred at hc with radii hr=(rx, ry, rz)."""
    rx, ry, rz = hr
    cx, cy, cz = hc

    def surf(x, z):
        k = 1 - (x / rx) ** 2 - (z / rz) ** 2
        return cy - ry * math.sqrt(max(0.0, k))

    for s in (1, -1):
        ex, ez = s * rx * 0.36, rz * 0.05
        H += C.eye(f"eye{s}", (cx + ex, surf(ex, ez) + 0.012, cz + ez), rx * 0.19, (s * 0.15, -1, 0.05),
                   pupil_scale=0.78)
        if brows:
            bx, bz = s * rx * 0.37, rz * 0.33
            H.append(C.arc(f"brow{s}", (cx + bx, surf(bx, bz) - 0.002, cz + bz - 0.015), 0.03, 60, 120, 0.0055, hair,
                           axis_up=(0, -0.25, 1), n=4, segs=5))
        if cheeks:
            kx, kz = s * rx * 0.6, -rz * 0.28
            H.append(C.ell(f"cheek{s}", (cx + kx, surf(kx, kz) + 0.006, cz + kz), (0.03, 0.01, 0.02), "cheek", 8, 4,
                           rot=(0, 0, s * 0.62)))
        H.append(C.ball(f"ear{s}", (cx + s * rx * 0.98, cy + 0.01, cz - 0.01), rx * 0.2, skin, 8, 5))
    H.append(C.ball("nose", (cx, surf(0, -rz * 0.12) + 0.006, cz - rz * 0.12), rx * 0.11, skin, 8, 6))
    mz = -rz * 0.38
    H.append(C.arc("smile", (cx, surf(0, mz) - 0.003, cz + mz + 0.03), 0.042, 215, 325, 0.0075, "mouth",
                   axis_up=(0, -0.35, 1), n=7, segs=5))


def _person(D, outfit):
    """Chunky toy-figure person. D: dims. outfit: dict of materials / extras callbacks.
    Returns root, [Head, ArmL, ArmR]."""
    P, H, AL, AR = [], [], [], []
    hip, sh, lx, lr = D["hip"], D["sh"], D["leg_x"], D["leg_r"]
    # shoes
    for s in (1, -1):
        P.append(C.loft("shoe", segs=10, res=1, keys=[((s * lx, 0.045, 0.045), 0.055, 0.045), ((s * lx, -0.02, 0.045), 0.06, 0.05),
                                 ((s * lx, -0.07, 0.04), 0.052, 0.04)],
                        materials=(outfit["shoe"],), dome_start=0.035, dome_end=0.04, exp=2.4, dome_rings=3))
        # flatten sole to z=0 is handled by the shoe loft's ellipse bottom touching ~0
        leg_paint = outfit.get("leg_paint")
        P.append(C.loft("leg", [((s * lx, 0, 0.07), lr * 0.92, lr * 0.92), ((s * lx, 0, hip * 0.55), lr, lr),
                                ((s * lx, 0, hip + 0.02), lr * 1.12, lr * 1.12)], segs=12, res=2,
                        materials=outfit["leg_mats"], up=(0, -1, 0), dome_start=0.0,
                        paint=leg_paint))
    # torso (hips -> shoulders) with optional paint for clothing details
    tw, td = D["torso_w"], D["torso_d"]
    tk = [((0, 0, hip - 0.03), tw * 0.92, td * 0.95), ((0, 0, hip + (sh - hip) * 0.35), tw, td * 1.02),
          ((0, 0, hip + (sh - hip) * 0.75), tw * 1.02, td), ((0, 0, sh), tw * 0.92, td * 0.9)]
    P.append(C.loft("torso", tk, segs=16, res=3, materials=outfit["torso_mats"], up=(0, -1, 0), dome_start=0.03,
                    dome_end=0.06, paint=outfit.get("torso_paint")))
    P.append(C.tube("neck", [(0, 0, sh), (0, 0, D["neck"])], 0.05 * D["k"], outfit["skin"], segs=10))
    for f in outfit.get("body_extras", []):
        P += f(D)
    # head
    hc, hr = D["head_c"], D["head_r"]
    H.append(C.ell("head", hc, hr, outfit["skin"], 18, 12))
    _face(H, hc, hr, outfit["skin"], outfit["hair"])
    for f in outfit.get("head_extras", []):
        H += f(D)
    # arms (shoulder pivots); paint: sleeve material index 0, skin index 1 below `sleeve` fraction
    for s, lst in ((1, AL), (-1, AR)):
        path = outfit.get("arm_path", {}).get(s) or [
            (s * D["sh_x"], 0, sh - 0.04), (s * (D["sh_x"] + 0.035), -0.005, sh - 0.2 * D["k"]),
            (s * (D["sh_x"] + 0.05), -0.02, sh - 0.33 * D["k"])]
        keys = [(p, D["arm_r"] * (1.05 - 0.15 * i / (len(path) - 1)), D["arm_r"] * (1.05 - 0.15 * i / (len(path) - 1)))
                for i, p in enumerate(path)]
        sleeve = outfit.get("sleeve", 1.0)
        arm = C.loft("arm", keys, segs=10, res=3, dome_rings=3, materials=(outfit["sleeve_mat"], outfit["skin"]), dome_start=0.04,
                     paint=lambda i, n, ss, c, sl=sleeve: 0 if i < n * sl else 1)
        lst.append(arm)
        end = Vector(path[-1])
        dirv = (end - Vector(path[-2])).normalized()
        lst.append(C.ball("hand", end + dirv * D["arm_r"] * 0.6, D["arm_r"] * 1.15, outfit["skin"], 10, 6))
        for f in outfit.get("arm_extras", {}).get(s, []):
            lst += f(D, end + dirv * D["arm_r"] * 0.6)
    return P, H, AL, AR


def _dims(scale=1.0, head=1.0):
    k = scale
    return {
        "k": k, "hip": 0.40 * k, "sh": 0.77 * k, "neck": 0.84 * k, "leg_x": 0.075 * k, "leg_r": 0.06 * k,
        "torso_w": 0.165 * k, "torso_d": 0.115 * k, "sh_x": 0.175 * k, "arm_r": 0.047 * k,
        "head_c": (0, 0, 0.84 * k + 0.165 * head), "head_r": (0.175 * head, 0.163 * head, 0.178 * head),
    }


def _hair_shell(D, cutter_loc, cutter_r, hair, offset=0.012, seed=1, jitter=0.05):
    tmp = C.ell("head_tmp", D["head_c"], D["head_r"], "skin", 18, 12)
    sh = C.shell_patch("hair", tmp, C.blob("hc", cutter_loc, cutter_r, jitter=jitter, seed=seed), hair,
                       offset=offset)
    bpy.data.objects.remove(tmp, do_unlink=True)
    return sh


def _finish_person(name, P, H, AL, AR, D, info):
    C.report(P + H + AL + AR)
    root = T.join(P, name)
    hd = C.part(H, "Head", (0, 0, D["neck"] - 0.02))
    al = C.part(AL, "ArmL", (D["sh_x"], 0, D["sh"] - 0.04))
    ar = C.part(AR, "ArmR", (-D["sh_x"], 0, D["sh"] - 0.04))
    return root, [hd, al, ar], info


def build_conductor():
    D = _dims(1.0)
    sh = D["sh"]
    hc = Vector(D["head_c"])

    def buttons(D):
        out = []
        for i in range(3):
            z = D["hip"] + 0.08 + i * 0.1
            out.append(C.ell("button", (0, -D["torso_d"] - 0.003, z), (0.016, 0.008, 0.016), "gold", 6, 4))
        out.append(C.loft("tie", [((0, -D["torso_d"] - 0.006, sh - 0.02), 0.022, 0.006),
                                  ((0, -D["torso_d"] - 0.004, sh - 0.12), 0.026, 0.006)], segs=8, res=1,
                          materials=("red",), dome_end=0.02))
        out.append(C.ell("collar", (0, -0.03, sh + 0.005), (0.09, 0.07, 0.03), "white", 10, 5))
        out.append(C.ell("belt", (0, 0, D["hip"] + 0.02), (D["torso_w"] * 0.97, D["torso_d"] * 1.02, 0.025),
                         "navy_dark", 16, 5))
        for s in (1, -1):
            out.append(C.ell("epaulette", (s * 0.15, 0, sh - 0.01), (0.05, 0.06, 0.02), "gold", 8, 4))
        return out

    def cap(D):
        out = []
        out.append(C.lathe_solid("cap", [(0.168, 0.0), (0.17, 0.07), (0.195, 0.11), (0.19, 0.125), (0.0, 0.13)],
                                 (hc.x, hc.y + 0.01, hc.z + 0.085), "navy", rot=(math.radians(-6), 0, 0)))
        out.append(C.torus("band", 0.172, 0.014, loc=(hc.x, hc.y + 0.008, hc.z + 0.095), material=None,
                           rot=(math.radians(-6), 0, 0), major_segs=20, minor_segs=4))
        C._mats(out[-1], ["navy_dark"])
        out.append(C.ell("visor", (hc.x, hc.y - 0.15, hc.z + 0.085), (0.13, 0.085, 0.012), "eye_black", 14, 6,
                         rot=(math.radians(14), 0, 0)))
        out.append(C.ell("badge", (hc.x, hc.y - 0.172, hc.z + 0.135), (0.03, 0.01, 0.024), "gold", 10, 6,
                         rot=(math.radians(-8), 0, 0)))
        out.append(_hair_shell(D, (0, 0.13, hc.z + 0.03), (0.3, 0.2, 0.2), "hair_black", seed=2))
        return out

    def whistle(D, p):
        return [C.tube("whistle", [p + Vector((0.0, -0.02, 0.045)), p + Vector((0.0, -0.075, 0.06))], 0.014, "metal",
                       segs=8, dome_start=0.01),
                C.ball("whistle_ball", p + Vector((0.0, -0.03, 0.03)), 0.022, "metal", 8, 5)]

    outfit = {
        "skin": "skin_dark", "hair": "hair_black", "shoe": "shoe_black",
        "leg_mats": ("navy",), "torso_mats": ("navy",), "sleeve_mat": "navy",
        "body_extras": [buttons], "head_extras": [cap],
        # right arm (-X) bent up, whistle ready near the chin
        "arm_path": {-1: [(-0.175, 0, sh - 0.04), (-0.23, -0.06, sh - 0.2), (-0.15, -0.17, sh - 0.12),
                          (-0.09, -0.2, sh - 0.04)]},
        "arm_extras": {-1: [whistle]},
    }
    P, H, AL, AR = _person(D, outfit)
    for s in (1, -1):
        # gold cuff stripes
        pass
    return _finish_person("Person_Conductor", P, H, AL, AR, D,
                          {"kind": "person", "sound": "hello", "folder": "People", "budget": 2500})


def build_farmer():
    D = _dims(1.0)
    sh, hip = D["sh"], D["hip"]
    hc = Vector(D["head_c"])

    def overall_paint(i, n, s, c):
        if c.z < hip + 0.13:
            return 1
        if abs(c.x) < 0.1 and c.y < 0 and c.z < sh - 0.05:
            return 1
        return 0

    def extras(D):
        out = []
        for s in (1, -1):
            out.append(C.tube("strap", [(s * 0.08, -D["torso_d"] - 0.004, sh - 0.06), (s * 0.1, -0.06, sh + 0.035),
                                        (s * 0.1, 0.06, sh + 0.03), (s * 0.08, D["torso_d"] + 0.003, sh - 0.1),
                                        (s * 0.06, D["torso_d"] + 0.003, hip + 0.12)], 0.012, "denim", segs=6))
            out.append(C.ell("bib_button", (s * 0.075, -D["torso_d"] - 0.008, sh - 0.065), (0.014, 0.007, 0.014),
                             "gold", 8, 5))
        out.append(C.ell("pocket", (0, -D["torso_d"] - 0.004, sh - 0.15), (0.05, 0.006, 0.035), "blue_dark", 10, 5))
        return out

    def hat(D):
        out = []
        out.append(C.lathe_solid("hat", [(0.15, 0.0), (0.27, 0.005), (0.31, 0.022), (0.30, 0.03), (0.2, 0.022),
                                         (0.155, 0.03), (0.15, 0.12), (0.12, 0.155), (0.0, 0.16)],
                                 (hc.x, hc.y, hc.z + 0.09), "straw", rot=(math.radians(-13), 0, 0), segs=28))
        out.append(C.torus("hatband", 0.153, 0.02, loc=(hc.x, hc.y + 0.0125, hc.z + 0.1436), material=None,
                           rot=(math.radians(-13), 0, 0), major_segs=20, minor_segs=4))
        C._mats(out[-1], ["red"])
        out.append(_hair_shell(D, (0, 0.13, hc.z + 0.0), (0.3, 0.2, 0.17), "hair_brown", seed=4))
        for s in (1, -1):
            out.append(C.ell("moustache", (s * 0.03, hc.y - 0.158, hc.z - 0.055), (0.035, 0.016, 0.018),
                             "hair_brown", 10, 6, rot=(0, s * 0.35, 0)))
        return out

    outfit = {
        "skin": "skin", "hair": "hair_brown", "shoe": "boot",
        "leg_mats": ("denim",), "torso_mats": ("plaid_red", "denim"), "torso_paint": overall_paint,
        "sleeve_mat": "plaid_red", "sleeve": 0.8,
        "body_extras": [extras], "head_extras": [hat],
    }
    P, H, AL, AR = _person(D, outfit)
    return _finish_person("Person_Farmer", P, H, AL, AR, D,
                          {"kind": "person", "sound": "hello", "folder": "People", "budget": 2500})


def build_child():
    D = _dims(0.74, head=0.9)
    sh, hip = D["sh"], D["hip"]
    hc = Vector(D["head_c"])

    def shirt_paint(i, n, s, c):
        if c.z < hip + 0.06:
            return 2  # shorts
        if abs(c.z - (hip + (sh - hip) * 0.55)) < 0.025:
            return 1  # stripe
        return 0

    def leg_paint(i, n, s, c):
        if c.z > hip - 0.07:
            return 2
        if c.z < 0.1:
            return 1
        return 0

    def hair(D):
        out = [_hair_shell(D, (0, 0.1, hc.z + 0.06), (0.26, 0.2, 0.15), "hair_black", seed=7)]
        for s in (1, -1):
            out.append(C.ball("bun", (s * 0.15, 0.03, hc.z + 0.08), 0.06, "hair_black", 12, 8))
            out.append(C.ell("bobble", (s * 0.125, 0.025, hc.z + 0.06), (0.022, 0.022, 0.022), "child_pink", 8, 5))
        out.append(C.ell("fringe", (0, -0.1, hc.z + 0.1), (0.1, 0.04, 0.03), "hair_black", 12, 6, rot=(0.5, 0, 0)))
        return out

    outfit = {
        "skin": "skin_mid", "hair": "hair_black", "shoe": "child_pink",
        "leg_mats": ("skin_mid", "white", "red"), "leg_paint": leg_paint,
        "torso_mats": ("child_teal", "child_yellow", "red"), "torso_paint": shirt_paint,
        "sleeve_mat": "child_teal", "sleeve": 0.45,
        "head_extras": [hair],
    }
    P, H, AL, AR = _person(D, outfit)
    return _finish_person("Person_Child", P, H, AL, AR, D,
                          {"kind": "person", "sound": "hello", "folder": "People", "budget": 2500})


BUILDERS = {
    "Cow": build_cow,
    "Sheep": build_sheep,
    "Chicken": build_chicken,
    "Dog": build_dog,
    "Cat": build_cat,
    "Horse": build_horse,
    "Bird": build_bird,
    "Person_Conductor": build_conductor,
    "Person_Farmer": build_farmer,
    "Person_Child": build_child,
}


# ================================================================================================ pipeline
def build(name):
    T.reset()
    root, parts, info = BUILDERS[name]()
    T.finalize([root] + parts, ao_distance=0.35, ao_strength=0.7)
    for p in parts:
        C.parent_keep(p, root)
    bpy.context.view_layer.update()  # refresh bound boxes / world matrices (set_origin + parenting)
    m = C.meta(root, parts)
    rel = f"{info['folder']}/{name}"
    T.export_fbx(rel, [root])
    # tt_common.render fits the frame by the bounding-sphere radius against the horizontal FOV, which crops tall,
    # thin subjects (people) -> pull the camera back for them.
    ds = 1.35 if info["kind"] == "person" else 1.0
    T.render([root], T.preview_path(name), distance_scale=ds)
    T.render([root], T.preview_path(name + "_Top"), pitch_deg=50, yaw_deg=-25, distance_scale=ds)
    if m["verts"] > info["budget"]:
        print(f"[TT] WARNING {name} over budget: {m['verts']} > {info['budget']}")
    print(f"[TT] {name}: {m}")
    return {
        "name": name,
        "fbx": f"_Project/Art/Models/{rel}.fbx",
        "kind": info["kind"],
        "sound": info["sound"],
        "footprintRadius": m["footprintRadius"],
        "height": m["height"],
        "parts": [p.name for p in parts],
        "verts": m["verts"],
    }


def main():
    names = T.args() or list(BUILDERS.keys())
    lineup_only = names == ["Lineup"]
    if lineup_only:
        names = []
    entries = {}
    if os.path.exists(MANIFEST):
        try:
            for e in json.load(open(MANIFEST)):
                entries[e["name"]] = e
        except Exception:
            pass
    for n in names:
        entries[n] = build(n)
    order = [n for n in BUILDERS if n in entries]
    with open(MANIFEST, "w") as f:
        json.dump([entries[n] for n in order], f, indent=2)
    print("[TT] manifest written", MANIFEST)
    if not T.args() or lineup_only:
        lineup([entries[n] for n in order])


def lineup(entries):
    """Imports the exported FBX files (what Unity gets) and renders them side by side."""
    T.reset()
    x = 0.0
    roots = []
    for e in entries:
        before = set(bpy.data.objects)
        bpy.ops.import_scene.fbx(filepath=os.path.join(T.REPO, "Assets", e["fbx"]))
        new = [o for o in bpy.data.objects if o not in before]
        top = [o for o in new if o.parent is None]
        bpy.context.view_layer.update()
        mn, mx = T._bounds(new)
        w = mx.x - mn.x
        for o in top:
            o.location.x += x - mn.x
        x += w + 0.25
        roots += top
    bpy.context.view_layer.update()
    T.render(roots, os.path.join(T.PREVIEWS, "Creatures_Lineup.png"), size=(2000, 700), yaw_deg=0, pitch_deg=22,
             distance_scale=0.95, samples=32)


if __name__ == "__main__":
    main()
