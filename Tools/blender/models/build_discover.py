"""
Tiny Tracks World - discovery animals (extra toy figures found around the world): Duck, Rabbit.

Run:  blender -b --factory-startup --python Tools/blender/models/build_discover.py -- [Duck Rabbit]
Exports Assets/_Project/Art/Models/Animals/<Name>.fbx, previews in Logs/Blender/<Name>.png (+ _Top) and
Tools/blender/models/discover_manifest.json (same fields as creatures_manifest.json).

Same conventions as build_creatures.py: front faces -Y, model's right = -X, root origin = ground contact centre
(feet on z = 0). Animated parts are child objects whose origin is the pivot: Head (neck), Tail (tail base).
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
MANIFEST = os.path.join(HERE, "discover_manifest.json")

# extra colours (registered into creatures_lib's palette extras so C.mat / C.loft can use them)
C.EXTRA.setdefault("duck_white", ("#FFFDF6", "noise", 0.25))
C.EXTRA.setdefault("duck_wing", ("#EFEADF", "noise", 0.3))
C.EXTRA.setdefault("duck_bill", ("#FF9A1F", "none", 0.0))
C.EXTRA.setdefault("duck_feet", ("#FF8A1A", "none", 0.0))
C.EXTRA.setdefault("bunny", ("#C9A58A", "noise", 0.35))
C.EXTRA.setdefault("bunny_dark", ("#A9805F", "noise", 0.35))
C.EXTRA.setdefault("bunny_belly", ("#FBF4EA", "noise", 0.3))
C.EXTRA.setdefault("bunny_ear", ("#FFB3C4", "none", 0.0))


# ================================================================================================ DUCK
def build_duck():
    P = []
    bk = [((0, -0.10, 0.205), 0.10, 0.105), ((0, -0.01, 0.19), 0.13, 0.115), ((0, 0.09, 0.195), 0.12, 0.10),
          ((0, 0.16, 0.22), 0.075, 0.07)]
    P.append(C.loft("duck_body", bk, segs=18, res=3, materials=("duck_white",), dome_start=0.07, dome_end=0.05,
                    exp=2.1))
    P.append(C.tube("neck", [(0, -0.085, 0.26), (0, -0.10, 0.31), (0, -0.105, 0.35)], 0.06, "duck_white",
                    segs=14, radius_end=0.05))
    for s in (1, -1):
        # folded wings: plump teardrops along the flanks, tips lifted towards the tail
        P.append(C.loft("wing", [((s * 0.118, -0.06, 0.215), 0.03, 0.05), ((s * 0.128, 0.02, 0.22), 0.035, 0.062),
                                 ((s * 0.11, 0.11, 0.245), 0.022, 0.035)], segs=12, res=2,
                        materials=("duck_wing",), up=(s, 0, 0), dome_start=0.035, dome_end=0.045, roll=0.0))
        # stubby orange legs + webbed feet (three rounded toes)
        P.append(C.tube("leg", [(s * 0.05, 0.0, 0.11), (s * 0.05, -0.005, 0.05), (s * 0.05, -0.01, 0.02)], 0.016,
                        "duck_feet", segs=8, radius_end=0.013))
        P.append(C.ell("foot", (s * 0.05, -0.045, 0.013), (0.042, 0.055, 0.013), "duck_feet", 12, 6))
        for a in (-0.45, 0.0, 0.45):
            d = Vector((math.sin(a), -math.cos(a), 0))
            P.append(C.ball("toe", Vector((s * 0.05, -0.045, 0.014)) + d * 0.05, 0.016, "duck_feet", 8, 5))
    # ---- head (pivot at the neck top)
    H = [C.ell("head", (0, -0.115, 0.40), (0.078, 0.08, 0.076), "duck_white", 18, 12)]
    H.append(C.ell("tuft", (0, -0.10, 0.475), (0.02, 0.035, 0.025), "duck_white", 8, 6, rot=(0.5, 0, 0)))
    # broad, rounded toy bill (upper + a slimmer lower half: a happy open beak)
    H.append(C.loft("bill", [((0, -0.165, 0.378), 0.045, 0.024), ((0, -0.21, 0.372), 0.056, 0.019),
                             ((0, -0.24, 0.37), 0.052, 0.016)], segs=16, res=2, materials=("duck_bill",),
                    dome_end=0.03, up=(0, 0, 1), exp=2.6))
    H.append(C.loft("bill_lo", [((0, -0.165, 0.352), 0.034, 0.012), ((0, -0.205, 0.35), 0.038, 0.01)],
                    segs=12, res=1, materials=("duck_bill",), dome_end=0.02, up=(0, 0, 1)))
    H.append(C.ell("mouth", (0, -0.19, 0.361), (0.034, 0.03, 0.007), "mouth", 10, 4))
    for s in (1, -1):
        H += C.eye(f"eye{s}", (s * 0.045, -0.172, 0.425), 0.025, (s * 0.45, -1, 0.15))
        H.append(C.ell("cheek", (s * 0.06, -0.165, 0.39), (0.012, 0.016, 0.012), "cheek", 6, 4))
    # ---- tail: perky upturned feather tuft
    tail = [C.loft("tail", [((0, 0.17, 0.235), 0.055, 0.035), ((0, 0.215, 0.265), 0.04, 0.022),
                            ((0, 0.235, 0.305), 0.012, 0.01)], segs=12, res=2, materials=("duck_white",),
                   up=(0, 1, 0), dome_start=0.02, dome_end=0.012)]
    C.report(P + H + tail)
    root = T.join(P, "Duck")
    hd = C.part(H, "Head", (0, -0.10, 0.33))
    tl = C.part(tail, "Tail", (0, 0.17, 0.235))
    return root, [hd, tl], {"kind": "animal", "sound": "quack", "folder": "Animals", "budget": 2500}


# ================================================================================================ RABBIT
def build_rabbit():
    P = []
    # sitting bunny: pear-shaped body, big haunches, long hind feet, little front paws
    P.append(C.loft("bun_body", [((0, 0.07, 0.10), 0.13, 0.11), ((0, 0.02, 0.18), 0.125, 0.12),
                                 ((0, -0.04, 0.26), 0.095, 0.09)], segs=18, res=3, materials=("bunny",),
                    up=(0, -1, 0), dome_start=0.09, dome_end=0.05))
    P.append(C.ell("belly", (0, -0.06, 0.17), (0.08, 0.06, 0.1), "bunny_belly", 14, 9, rot=(-0.25, 0, 0)))
    for s in (1, -1):
        P.append(C.ell("haunch", (s * 0.095, 0.07, 0.10), (0.06, 0.1, 0.085), "bunny", 14, 9))
        P.append(C.ell("hfoot", (s * 0.09, 0.0, 0.025), (0.042, 0.11, 0.026), "bunny", 12, 7))
        P.append(C.tube("arm", [(s * 0.052, -0.07, 0.17), (s * 0.052, -0.095, 0.09), (s * 0.05, -0.11, 0.035)],
                        0.032, "bunny", segs=10, radius_end=0.027))
        P.append(C.ell("paw", (s * 0.048, -0.12, 0.025), (0.028, 0.035, 0.024), "bunny_belly", 10, 6))
    # ---- head (pivot at the neck)
    H = [C.ell("head", (0, -0.07, 0.365), (0.118, 0.105, 0.102), "bunny", 18, 12)]
    H.append(C.ell("muzzle", (0, -0.157, 0.33), (0.055, 0.035, 0.04), "bunny_belly", 12, 8))
    for s in (1, -1):
        H.append(C.ell("puff", (s * 0.03, -0.17, 0.322), (0.032, 0.026, 0.027), "bunny_belly", 10, 6))
    H.append(C.ell("nose", (0, -0.194, 0.347), (0.017, 0.01, 0.012), "nose_pink", 8, 5))
    H.append(C.arc("smile", (0, -0.19, 0.318), 0.016, 205, 335, 0.0045, "mouth", axis_up=(0, -0.35, 0.94), n=6))
    H.append(C.ell("teeth", (0, -0.188, 0.303), (0.012, 0.005, 0.009), "white", 6, 4))
    for s in (1, -1):
        H += C.eye(f"eye{s}", (s * 0.056, -0.147, 0.392), 0.032, (s * 0.5, -1, 0.12))
        H.append(C.ell("cheek", (s * 0.078, -0.14, 0.338), (0.016, 0.01, 0.012), "cheek", 6, 4))
        # tall ears, slightly splayed
        flop = 0.0
        ek = [((s * 0.04, -0.06, 0.43), 0.032, 0.016), ((s * 0.06, -0.055, 0.52), 0.04, 0.018),
              ((s * (0.075 + flop), -0.05 + flop * 0.3, 0.60 - flop), 0.03, 0.014)]
        H.append(C.loft("ear", ek, segs=10, res=3, materials=("bunny",), up=(0, -1, 0), dome_end=0.03))
        ik = [((s * 0.04, -0.075, 0.44), 0.019, 0.006), ((s * 0.06, -0.071, 0.52), 0.025, 0.007),
              ((s * (0.075 + flop), -0.066 + flop * 0.3, 0.595 - flop), 0.017, 0.005)]
        H.append(C.loft("ear_in", ik, segs=8, res=3, materials=("bunny_ear",), up=(0, -1, 0), dome_end=0.02))
    # ---- tail: cotton puff
    tail = [C.ball("tail", (0, 0.19, 0.09), 0.05, "bunny_belly", 12, 8)]
    for i, (x, z) in enumerate(((0.025, 0.11), (-0.025, 0.105), (0.0, 0.065))):
        tail.append(C.ball(f"tuft{i}", (x, 0.205, z), 0.03, "bunny_belly", 8, 5))
    C.report(P + H + tail)
    root = T.join(P, "Rabbit")
    hd = C.part(H, "Head", (0, -0.04, 0.28))
    tl = C.part(tail, "Tail", (0, 0.17, 0.09))
    return root, [hd, tl], {"kind": "animal", "sound": "squeak", "folder": "Animals", "budget": 2500}


BUILDERS = {
    "Duck": build_duck,
    "Rabbit": build_rabbit,
}


# ================================================================================================ pipeline
def build(name):
    T.reset()
    root, parts, info = BUILDERS[name]()
    T.finalize([root] + parts, ao_distance=0.35, ao_strength=0.7)
    for p in parts:
        C.parent_keep(p, root)
    bpy.context.view_layer.update()
    m = C.meta(root, parts)
    rel = f"{info['folder']}/{name}"
    T.export_fbx(rel, [root])
    T.render([root], T.preview_path(name))
    T.render([root], T.preview_path(name + "_Top"), pitch_deg=50, yaw_deg=-25)
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
    names = [n for n in T.args() if n in BUILDERS] or list(BUILDERS.keys())
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


if __name__ == "__main__":
    main()
