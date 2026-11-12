"""
Tiny Tracks World - UI button icons (no text, toddler-readable glossy 3D toy symbols).

Run:  blender -b --factory-startup --python Tools/blender/icons/build_icons.py -- [icon names ...] [--sheet]
      (no names = all icons). Writes 256x256 RGBA PNGs to Assets/_Project/Art/UI/Icons/<name>.png and a contact
      sheet to Logs/Blender/Icons_Sheet.png.
Conventions: symbols are modelled facing the camera (-Y); 2D symbols are profiles in the XZ plane (x right, z up).
"""
import sys
import os
import math

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import bpy
from mathutils import Vector, Euler
import tt_common as T
import icons_lib as L

R = math.radians

# ------------------------------------------------------------------------------------------------ colours
GREEN = "#3DBA5A"
RED = "#F2474B"
YELLOW = "#FFCC2E"
ORANGE = "#FF8A2B"
BLUE = "#2E8BE6"
PURPLE = "#9B6BE0"
WHITE = "#FAFAF5"
CHAR = "#3E4150"
GOLD = "#F5C542"


def gm(name, hexstr=None, **kw):
    return L.gm(name, hexstr, **kw)


# ------------------------------------------------------------------------------------------------ primitive wrappers
def _fin(o, mat, ang=35):
    L.setm(o, mat)
    T.apply(o)
    T.smooth(o, ang)
    return o


def rb(name, size, loc, mat, bevel=0.12, rot=(0, 0, 0), segs=4):
    o = T.rbox(name, size, loc=loc, bevel=bevel, segments=segs, rot=rot)
    return _fin(o, mat)


def cy(name, r, depth, loc, mat, rot=(0, 0, 0), bevel=0.04, verts=40, r_top=None):
    o = T.cyl(name, r, depth, loc=loc, verts=verts, rot=rot, bevel=bevel, segments=3, radius_top=r_top)
    return _fin(o, mat, 50)


def sp(name, r, loc, mat, scale=(1, 1, 1), rot=(0, 0, 0)):
    o = T.sphere(name, r, loc=loc, scale=scale, segs=32, rings=20, rot=rot)
    return _fin(o, mat, 180)


def tor(name, major, minor, loc, mat, rot=(0, 0, 0)):
    o = T.torus(name, major, minor, loc=loc, rot=rot, major_segs=48, minor_segs=16)
    return _fin(o, mat, 180)


def cap(name, r, length, loc, mat, rot=(0, 0, 0)):
    o = T.capsule(name, r, length, loc=loc, rot=rot, segs=24)
    return _fin(o, mat, 180)


def lat(name, profile, loc, mat, rot=(0, 0, 0), segs=48):
    o = T.lathe(name, profile, loc=loc, segs=segs, rot=rot)
    return _fin(o, mat, 60)


def tube(name, path, r, mat, n=16):
    prof = [(r * math.cos(2 * math.pi * i / n), r * math.sin(2 * math.pi * i / n)) for i in range(n)]
    o = T.sweep(name, path, prof, up=(0, -1, 0))
    return _fin(o, mat, 180)


def slab(name, prof, depth, mat, bevel=0.12, y=0.0, rot=(0, 0, 0), loc=(0, 0, 0)):
    return L.slab(name, prof, depth, gm(mat) if isinstance(mat, str) and mat.startswith("#") else mat,
                  bevel=bevel, segs=4, y=y, rot=rot, loc=loc)


def M(hexstr, **kw):
    """Material from hex, cached by its parameters."""
    key = hexstr + "_" + "_".join(f"{k}{v}" for k, v in sorted(kw.items()))
    return gm(key, hexstr, **kw)


def eye(loc, r=0.13, look=(0, -1, 0.15)):
    """Cartoon eye (white + black pupil + tiny highlight) at loc, pupil pushed toward `look`."""
    d = Vector(look).normalized()
    p = Vector(loc)
    w = sp("eyeW", r, p, M("#FFFFFF", rough=0.2))
    b = sp("eyeB", r * 0.62, p + d * r * 0.55, M("#1E1E28", rough=0.15))
    h = sp("eyeH", r * 0.2, p + d * r * 0.95 + Vector((-r * 0.22, 0, r * 0.25)), M("#FFFFFF", rough=0.2, emit=0.6))
    return [w, b, h]


def plus_poly(arm=0.95, half=0.25):
    a, l = half, arm
    return [(a, a), (a, l), (-a, l), (-a, a), (-l, a), (-l, -a), (-a, -a), (-a, -l), (a, -l), (a, -a), (l, -a), (l, a)]


# ------------------------------------------------------------------------------------------------ icons
def ic_triangle(col):
    prof = L.round_poly([(-0.75, 1.0), (-0.75, -1.0), (1.05, 0.0)], 0.32, 8)
    return [slab("tri", prof, 0.55, M(col), bevel=0.16)]


def ic_go():
    return ic_triangle(GREEN)


def ic_play():
    return ic_triangle(YELLOW)


def ic_stop():
    outer = L.circle_pts(1.0, 8, start=math.pi / 8)
    inner = L.circle_pts(0.84, 8, start=math.pi / 8)
    o1 = slab("rim", L.round_poly(outer, 0.08, 4), 0.32, M(WHITE), bevel=0.08)
    o2 = slab("face", L.round_poly(inner, 0.06, 4), 0.32, M(RED), bevel=0.08, y=-0.07)
    bar = L.round_poly([(-0.55, -0.16), (0.55, -0.16), (0.55, 0.16), (-0.55, 0.16)], 0.13, 6)
    o3 = slab("bar", bar, 0.2, M(WHITE), bevel=0.07, y=-0.27)
    return [o1, o2, o3]


def ic_whistle():
    brass = M("#E9B23A", rough=0.22, metal=0.7, coat=0.3)
    prof = [(0.16, -1.0), (0.16, -0.62), (0.42, -0.6), (0.48, -0.52), (0.56, -0.48), (0.56, 0.4), (0.5, 0.56),
            (0.36, 0.68), (0.16, 0.74), (0.0, 0.75)]
    body = lat("body", prof, (0, 0, 0), brass)
    rings = [tor("ring%d" % i, 0.57, 0.05, (0, 0, z), M("#C98A1B", rough=0.25, metal=0.6))
             for i, z in enumerate((-0.25, 0.22))]
    mouth = rb("mouth", (0.6, 0.3, 0.2), (0, -0.48, -0.38), M("#4A2E0C", rough=0.5), bevel=0.08)
    knob = sp("knob", 0.15, (0, 0, 0.82), brass)
    base = cy("base", 0.3, 0.16, (0, 0, -1.0), M("#C98A1B", rough=0.25, metal=0.6), bevel=0.05)
    steam = M("#FFFFFF", rough=0.55, coat=0.0)
    puffs = [sp("puff%d" % i, r, (x, -0.1, z), steam) for i, (x, z, r) in
             enumerate([(0.55, 0.95, 0.3), (0.95, 1.15, 0.36), (0.62, 1.35, 0.28), (1.25, 1.45, 0.3),
                        (0.95, 1.55, 0.3)])]
    return [body, mouth, knob, base] + rings + puffs


def ic_bell():
    gold = M(GOLD, rough=0.2, metal=0.7, coat=0.3)
    prof = [(0.96, -0.6), (0.98, -0.5), (0.86, -0.38), (0.72, -0.12), (0.63, 0.2), (0.6, 0.45), (0.52, 0.62),
            (0.34, 0.74), (0.12, 0.79), (0.0, 0.8)]
    body = lat("bell", prof, (0, 0, 0), gold)
    lip = tor("lip", 0.95, 0.075, (0, 0, -0.56), gold)
    band = tor("band", 0.64, 0.04, (0, 0, 0.3), M("#E7A419", rough=0.25, metal=0.6))
    clap = sp("clapper", 0.2, (0, -0.05, -0.75), M("#C98A1B", rough=0.25, metal=0.6))
    loop = tor("loop", 0.2, 0.07, (0, 0, 0.98), gold, rot=(R(90), 0, 0))
    return [body, lip, band, clap, loop]


def ic_turtle():
    shell = sp("shell", 1.0, (0, 0, 0.3), M("#2E9E4A"), scale=(1.15, 0.95, 0.85))
    rim = sp("rim", 1.0, (0, 0, 0.18), M("#E9C46A"), scale=(1.28, 1.06, 0.22))
    skin = M("#8FD46A")
    head = sp("head", 0.5, (1.4, -0.05, 0.6), skin)
    legs = [sp("leg%d" % i, 0.25, (x, y, 0.0), skin, scale=(1.0, 1.0, 0.75)) for i, (x, y) in
            enumerate([(0.7, -0.62), (-0.7, -0.62), (0.7, 0.62), (-0.7, 0.62)])]
    tail = cy("tail", 0.12, 0.35, (-1.35, 0, 0.18), skin, rot=(0, R(-75), 0), r_top=0.02)
    spot = M("#7FD35A")
    spots = [sp("spot%d" % i, 0.26, loc, spot, scale=(1, 1, 0.35), rot=rot) for i, (loc, rot) in enumerate([
        ((0.0, -0.18, 1.0), (R(-15), 0, 0)), ((-0.62, -0.32, 0.78), (R(-28), R(-35), 0)),
        ((0.62, -0.32, 0.78), (R(-28), R(35), 0)), ((0.0, -0.72, 0.62), (R(-62), 0, 0)),
        ((-0.66, -0.75, 0.38), (R(-60), R(-30), 0)), ((0.66, -0.75, 0.38), (R(-60), R(30), 0))])]
    eyes = eye((1.65, -0.34, 0.78), 0.16, look=(0.6, -1, 0.2))
    eyes2 = eye((1.74, 0.1, 0.8), 0.13, look=(0.9, -0.4, 0.2))
    smile = tor("smile", 0.13, 0.03, (1.84, -0.24, 0.5), M("#2B5A2B"), rot=(R(80), R(15), R(-50)))
    cheek = sp("cheek", 0.08, (1.66, -0.47, 0.55), M("#FF9AA8"), scale=(1, 0.5, 0.7))
    return [shell, rim, head, tail, cheek] + legs + spots + eyes + eyes2


def ic_speed_slow():
    return ic_turtle()


def ic_speed_fast():
    fur = M("#F7F2EA", rough=0.45, coat=0.1)
    pink = M("#FF9AB8")
    body = sp("body", 0.7, (0, 0, 0), fur, scale=(1.25, 0.9, 0.9))
    head = sp("head", 0.5, (0.85, 0, 0.55), fur)
    ears = []
    for i, (yo, tilt) in enumerate([(-0.14, -18), (0.16, -30)]):
        ears.append(cap("ear%d" % i, 0.15, 1.05, (0.6 - (0.05 if i else 0), yo, 1.3), fur,
                        rot=(0, R(tilt), 0)))
    inner = cap("earIn", 0.08, 0.8, (0.6, -0.27, 1.3), pink, rot=(0, R(-18), 0))
    tail = sp("tail", 0.26, (-0.92, 0, 0.2), fur)
    foot = cap("foot", 0.16, 0.75, (-0.15, -0.42, -0.62), fur, rot=(0, R(90), 0))
    paw = cap("paw", 0.12, 0.42, (0.62, -0.3, -0.5), fur, rot=(0, R(70), 0))
    nose = sp("nose", 0.08, (1.33, -0.08, 0.6), pink)
    cheek = sp("cheek", 0.09, (1.08, -0.4, 0.42), M("#FFB3C3"), scale=(1, 0.5, 0.7))
    eyes = eye((1.07, -0.33, 0.7), 0.12, look=(0.5, -1, 0.1))
    lines = [cap("line%d" % i, 0.08, ln, (-1.55 - ln / 2 + 0.6, -0.1, z), M("#8FD3FF", rough=0.3), rot=(0, R(90), 0))
             for i, (z, ln) in enumerate([(0.45, 0.9), (0.0, 1.2), (-0.45, 0.8)])]
    return [body, head, inner, tail, foot, paw, nose, cheek] + ears + eyes + lines


def ic_camera_follow():
    body = rb("body", (2.0, 0.9, 1.3), (0, 0, 0), M(BLUE), bevel=0.22)
    top = rb("top", (0.7, 0.7, 0.4), (-0.45, 0, 0.7), M(BLUE), bevel=0.12)
    grip = rb("grip", (0.5, 0.2, 1.12), (-0.72, -0.42, 0), M("#1E5FAF"), bevel=0.08)
    barrel = cy("barrel", 0.55, 0.5, (0.12, -0.55, -0.02), M("#9DA3AE", metal=0.5, rough=0.25), rot=(R(90), 0, 0),
                bevel=0.06)
    ring = tor("ring", 0.5, 0.06, (0.12, -0.82, -0.02), M("#3E4150"), rot=(R(90), 0, 0))
    glass = sp("glass", 0.42, (0.12, -0.78, -0.02), M("#24406E", rough=0.05, coat=0.8), scale=(1, 0.35, 1))
    hl = sp("hl", 0.11, (-0.02, -0.92, 0.12), M("#FFFFFF", emit=1.0), scale=(1, 0.4, 1))
    btn = cy("btn", 0.15, 0.2, (0.6, 0, 0.7), M(YELLOW), bevel=0.05)
    flash = rb("flash", (0.32, 0.12, 0.22), (0.68, -0.46, 0.38), M("#FFFFFF", rough=0.2), bevel=0.05)
    return [body, top, grip, barrel, ring, glass, hl, btn, flash]


def ic_camera_reset():
    red = M(RED)
    ring = tor("ring", 0.72, 0.15, (0, 0, 0), red, rot=(R(90), 0, 0))
    inner = tor("ring2", 0.36, 0.09, (0, 0, 0), M(WHITE), rot=(R(90), 0, 0))
    dot = sp("dot", 0.19, (0, -0.02, 0), red, scale=(1, 0.8, 1))
    ticks = []
    for i, (x, z) in enumerate([(0, 1), (0, -1), (1, 0), (-1, 0)]):
        rot = (0, 0, 0) if x == 0 else (0, R(90), 0)
        ticks.append(cap("tick%d" % i, 0.11, 0.62, (x * 0.83, 0, z * 0.83), red, rot=rot))
    return [ring, inner, dot] + ticks


def _undo_path(sign=1):
    path = [(-0.25, -0.5)] + L.arc_pts(0.25, 0.05, 0.55, -90, 90, 28) + [(-0.3, 0.6)]
    return [(sign * x, z) for x, z in path] if sign < 0 else path


def ic_undo(sign=1):
    path = _undo_path(1)
    prof = L.arrow_poly(path, 0.38, 0.55, 1.0)
    prof = L.round_poly(prof, 0.08, 4)
    if sign < 0:
        prof = [(-x, z) for x, z in reversed(prof)]
    return [slab("arrow", prof, 0.5, M(YELLOW), bevel=0.14)]


def ic_redo():
    return ic_undo(-1)


def ic_delete():
    body_m = M("#9DA3AE", metal=0.35, rough=0.3)
    prof = [(0.0, -0.95), (0.62, -0.95), (0.68, -0.9), (0.8, 0.55), (0.0, 0.55)]
    body = lat("bin", prof, (0, 0, 0), body_m)
    ribs = []
    for i in range(7):
        a = R(-90 + (i - 3) * 22)
        x, y = math.cos(a), math.sin(a)
        ribs.append(cap("rib%d" % i, 0.05, 1.32, (x * 0.73, y * 0.73, -0.22), M("#7F8191", metal=0.35),
                        rot=(-y * R(5), x * R(5), 0)))
    rim = tor("rim", 0.82, 0.06, (0, 0, 0.56), body_m)
    lid = lat("lid", [(0.0, 0.62), (0.95, 0.62), (0.97, 0.7), (0.9, 0.78), (0.6, 0.88), (0.0, 0.92)], (0, 0, 0),
              M(RED))
    handle = rb("handle", (0.55, 0.22, 0.2), (0, 0, 1.0), M("#C42F3A"), bevel=0.08)
    return [body, rim, lid, handle] + ribs


def ic_rotate():
    col = M(ORANGE)
    a1 = L.arrow_poly(L.arc_pts(0, 0, 0.75, 170, 48, 24), 0.32, 0.45, 0.82)
    a2 = L.arrow_poly(L.arc_pts(0, 0, 0.75, -10, -132, 24), 0.32, 0.45, 0.82)
    return [slab("a1", L.round_poly(a1, 0.06, 4), 0.45, col, bevel=0.13),
            slab("a2", L.round_poly(a2, 0.06, 4), 0.45, col, bevel=0.13)]


def ic_confirm():
    prof = L.band_poly([(-0.9, 0.05), (-0.3, -0.58), (0.95, 0.78)], 0.46)
    prof = L.round_poly(prof, 0.16, 6)
    return [slab("check", prof, 0.5, M(GREEN), bevel=0.15)]


def ic_cancel():
    prof = L.round_poly(plus_poly(1.0, 0.24), 0.12, 6)
    return [slab("x", prof, 0.5, M(RED), bevel=0.15, rot=(0, R(45), 0))]


def ic_plus():
    return [slab("plus", L.round_poly(plus_poly(0.95, 0.26), 0.12, 6), 0.5, M(GREEN), bevel=0.15)]


def ic_minus():
    prof = L.round_poly([(-0.95, -0.26), (0.95, -0.26), (0.95, 0.26), (-0.95, 0.26)], 0.16, 6)
    return [slab("minus", prof, 0.5, M(RED), bevel=0.15)]


def _track(length=2.2, n=4, y0=0.0):
    sleeper = M("#C9965A", rough=0.45, coat=0.15)
    rail = M("#B8BEC8", metal=0.6, rough=0.25)
    objs = []
    for i in range(n):
        x = -length / 2 + length * (i + 0.5) / n
        objs.append(rb("sl%d" % i, (0.32, 1.25, 0.14), (x, y0, 0.07), sleeper, bevel=0.05))
    for s in (-1, 1):
        objs.append(rb("rail", (length + 0.1, 0.13, 0.16), (0, y0 + s * 0.38, 0.22), rail, bevel=0.04))
    return objs


def ic_build():
    objs = _track(2.0, 4, 0.2)
    handle = cy("handle", 0.13, 1.5, (0, 0, 0.75), M("#E39B4A", rough=0.4), bevel=0.05)
    head = rb("head", (1.15, 0.5, 0.5), (0.0, 0, 1.55), M("#5C6377", metal=0.5, rough=0.25), bevel=0.1)
    face = cy("face", 0.27, 0.14, (0.6, 0, 1.55), M("#8E95A6", metal=0.6, rough=0.2), rot=(0, R(90), 0))
    grip = cy("grip", 0.17, 0.6, (0, 0, 0.32), M(RED), bevel=0.06)
    hammer = [handle, head, face, grip]
    for o in hammer:
        T.apply(o)
    h = T.join(hammer, "hammer")
    h.rotation_euler = (0, R(30), 0)
    h.location = (-0.05, -0.75, 0.15)
    return objs + [h]


def ic_train():
    red = M(RED)
    blue = M(BLUE)
    dark = M(CHAR, rough=0.35)
    yel = M(YELLOW)
    boiler = cy("boiler", 0.55, 1.4, (0, -0.3, 0.95), red, rot=(R(90), 0, 0), bevel=0.05)
    front = cy("smokebox", 0.58, 0.16, (0, -1.0, 0.95), dark, rot=(R(90), 0, 0), bevel=0.05)
    face = cy("face", 0.48, 0.06, (0, -1.08, 0.95), M("#FFF1D6"), rot=(R(90), 0, 0), bevel=0.02)
    eyes = eye((-0.19, -1.12, 1.08), 0.11) + eye((0.19, -1.12, 1.08), 0.11)
    mouth = [sp("m%d" % i, 0.045, (0.17 * math.sin(a), -1.12, 0.82 - 0.12 * math.cos(a)), M("#C42F3A"))
             for i, a in enumerate([R(x) for x in (-60, -30, 0, 30, 60)])]
    cheeks = [sp("ck%d" % i, 0.07, (s * 0.32, -1.11, 0.85), M("#FF9AA8"), scale=(1, 0.4, 0.7)) for i, s in
              enumerate((-1, 1))]
    chim = cy("chim", 0.17, 0.5, (0, -0.72, 1.65), dark, bevel=0.03)
    chim_top = cy("chimtop", 0.25, 0.16, (0, -0.72, 1.92), dark, bevel=0.05)
    dome = sp("dome", 0.22, (0, -0.15, 1.45), M(GOLD, metal=0.6, rough=0.22))
    cab = rb("cab", (1.3, 0.9, 1.4), (0, 0.75, 1.05), blue, bevel=0.1)
    win = rb("win", (0.8, 0.1, 0.45), (0, 0.28, 1.35), M("#9BDCF5", rough=0.08, coat=0.6), bevel=0.05)
    roof = rb("roof", (1.55, 1.15, 0.16), (0, 0.75, 1.82), dark, bevel=0.06)
    base = rb("base", (1.3, 2.3, 0.3), (0, 0.0, 0.42), dark, bevel=0.06)
    wheels = []
    for i, (x, y) in enumerate([(s, yy) for s in (-1, 1) for yy in (-0.6, 0.15, 0.85)]):
        wheels.append(cy("wh%d" % i, 0.33, 0.16, (x * 0.7, y, 0.33), yel, rot=(0, R(90), 0), bevel=0.05))
        wheels.append(cy("hub%d" % i, 0.11, 0.2, (x * 0.72, y, 0.33), red, rot=(0, R(90), 0), bevel=0.04))
    buf = [cy("buf%d" % i, 0.1, 0.25, (s * 0.45, -1.2, 0.45), dark, rot=(R(90), 0, 0)) for i, s in
           enumerate((-1, 1))]
    cow = L.slab("cow", [(-0.6, 0.0), (0.6, 0.0), (0.4, 0.3), (-0.4, 0.3)], 0.25, yel, bevel=0.05, loc=(0, -1.15, 0.0))
    cow.rotation_euler = (R(-25), 0, 0)
    return [boiler, front, face, chim, chim_top, dome, cab, win, roof, base, cow] + eyes + mouth + cheeks + wheels + buf


def ic_decorate():
    trunk = cy("trunk", 0.16, 0.9, (-0.5, 0.2, 0.45), M("#8A5A3B", rough=0.5), r_top=0.12)
    can = sp("canopy", 0.75, (-0.5, 0.2, 1.35), M("#3FAE4A"), scale=(1, 1, 1.05))
    can2 = sp("canopy2", 0.45, (-0.82, -0.05, 1.05), M("#4FB548"))
    can3 = sp("canopy3", 0.42, (-0.15, -0.1, 1.0), M("#4FB548"))
    apples = [sp("ap%d" % i, 0.09, loc, M(RED)) for i, loc in
              enumerate([(-0.75, -0.48, 1.25), (-0.25, -0.5, 1.55), (-0.38, -0.45, 1.0)])]
    stem = tube("stem", [(0.55, -0.45, 0.0), (0.58, -0.45, 0.4), (0.62, -0.45, 0.85)], 0.06, M("#2F8F45"))
    leaf = sp("leaf", 0.22, (0.75, -0.45, 0.35), M("#5FB043"), scale=(1.2, 0.3, 0.55), rot=(0, R(-30), 0))
    petal = M("#FF8FB8")
    petals = [sp("pt%d" % i, 0.21, (0.62 + 0.25 * math.cos(a), -0.5, 0.95 + 0.25 * math.sin(a)), petal,
                 scale=(1, 0.5, 1)) for i, a in enumerate([2 * math.pi * k / 6 + 0.3 for k in range(6)])]
    center = sp("center", 0.16, (0.62, -0.62, 0.95), M(YELLOW), scale=(1, 0.6, 1))
    return [trunk, can, can2, can3, stem, leaf, center] + petals + apples


def ic_explore():
    ring = tor("ring", 0.62, 0.15, (-0.25, 0, 0.3), M(ORANGE), rot=(R(90), 0, 0))
    glass = sp("glass", 0.6, (-0.25, 0, 0.3), M("#BDE9FF", rough=0.05, coat=0.6), scale=(1, 0.18, 1))
    hl = cap("hl", 0.07, 0.42, (-0.47, -0.12, 0.5), M("#FFFFFF", emit=0.8), rot=(0, R(-45), 0))
    hl2 = sp("hl2", 0.06, (-0.6, -0.12, 0.25), M("#FFFFFF", emit=0.8))
    a = R(-45)
    d = Vector((math.cos(a), 0, math.sin(a)))
    c0 = Vector((-0.25, 0, 0.3)) + d * 0.75
    neck = cy("neck", 0.15, 0.25, tuple(c0 + d * 0.1), M("#9DA3AE", metal=0.5), rot=(0, R(135), 0))
    handle = cap("handle", 0.19, 0.95, tuple(c0 + d * 0.65), M("#C42F3A"), rot=(0, R(135), 0))
    return [ring, glass, hl, hl2, neck, handle]


def ic_home():
    wall = M("#FFF1D6", rough=0.4)
    walls = rb("walls", (1.6, 1.3, 1.1), (0, 0, 0.55), wall, bevel=0.06)
    gable = L.slab("gable", [(-0.8, 1.08), (0.8, 1.08), (0.0, 1.72)], 1.3, wall, bevel=0.04)
    gable.rotation_euler = (0, 0, 0)
    roof_prof = L.band_poly([(-1.08, 0.92), (0.0, 1.86), (1.08, 0.92)], 0.24)
    roof = L.slab("roof", roof_prof, 1.6, M("#D9483B"), bevel=0.06)
    chim = rb("chim", (0.26, 0.26, 0.55), (0.48, 0.25, 1.62), M("#D2694B"), bevel=0.04)
    door = rb("door", (0.42, 0.1, 0.68), (0.25, -0.66, 0.36), M(BLUE), bevel=0.06)
    knob = sp("knob", 0.045, (0.37, -0.72, 0.35), M(GOLD, metal=0.6))
    fr = rb("winfr", (0.48, 0.08, 0.46), (-0.38, -0.64, 0.62), M(WHITE), bevel=0.04)
    win = rb("win", (0.36, 0.1, 0.34), (-0.38, -0.67, 0.62), M("#9BDCF5", rough=0.08, coat=0.6), bevel=0.04)
    gw = cy("gwin", 0.15, 0.1, (0, -0.66, 1.32), M("#9BDCF5", rough=0.08, coat=0.6), rot=(R(90), 0, 0))
    return [walls, gable, roof, chim, door, knob, win, fr, gw]


def ic_settings():
    pts = []
    n = 8
    for i in range(n):
        a0 = 2 * math.pi * i / n
        for (da, r) in [(-0.2, 0.74), (-0.12, 1.0), (0.12, 1.0), (0.2, 0.74)]:
            pts.append((r * math.cos(a0 + da * 2 * math.pi / n * 2.1), r * math.sin(a0 + da * 2 * math.pi / n * 2.1)))
    # fill the gaps between teeth with root circle points
    full = []
    for i in range(n):
        tooth = pts[i * 4:i * 4 + 4]
        full += tooth
        a_end = math.atan2(tooth[-1][1], tooth[-1][0])
        a_next = math.atan2(pts[((i + 1) % n) * 4][1], pts[((i + 1) % n) * 4][0])
        if a_next < a_end:
            a_next += 2 * math.pi
        for k in range(1, 4):
            a = a_end + (a_next - a_end) * k / 4
            full.append((0.74 * math.cos(a), 0.74 * math.sin(a)))
    prof = L.round_poly(full, 0.05, 3)
    gear = slab("gear", prof, 0.45, M("#A9B3C6", metal=0.45, rough=0.25), bevel=0.1)
    hole = cy("hole", 0.3, 2.0, (0, 0, 0), None, rot=(R(90), 0, 0), bevel=0)
    T.boolean(gear, hole)
    T.smooth(gear, 38)
    hub = tor("hubring", 0.3, 0.07, (0, -0.22, 0), M("#7F8BA3", metal=0.5, rough=0.25), rot=(R(90), 0, 0))
    return [gear, hub]


def ic_new_world():
    soil = sp("soil", 0.8, (0, 0, 0), M("#8A5A3B", rough=0.55), scale=(1.35, 1.1, 0.45))
    crumbs = [sp("cr%d" % i, 0.12, loc, M("#6E4529", rough=0.6)) for i, loc in
              enumerate([(-0.7, -0.55, 0.12), (0.62, -0.58, 0.1), (0.2, -0.75, 0.05)])]
    stem = tube("stem", [(0, -0.2, 0.25), (0.02, -0.2, 0.6), (0.0, -0.2, 0.95), (-0.04, -0.2, 1.15)], 0.08,
                M("#3DA548"))
    leafL = sp("leafL", 0.5, (-0.45, -0.2, 1.25), M("#4FC24F"), scale=(1.0, 0.25, 0.48), rot=(0, R(-25), 0))
    leafR = sp("leafR", 0.42, (0.38, -0.2, 1.38), M("#7FD35A"), scale=(1.0, 0.25, 0.48), rot=(0, R(35), 0))
    veinL = cap("veinL", 0.025, 0.7, (-0.45, -0.33, 1.25), M("#2F8F45"), rot=(0, R(90 - 25), 0))
    veinR = cap("veinR", 0.025, 0.6, (0.38, -0.31, 1.38), M("#4FB548"), rot=(0, R(90 + 35), 0))
    return [soil, stem, leafL, leafR, veinL, veinR] + crumbs


def ic_clear_all():
    straw = M("#F2C14E", rough=0.45)
    handle = cy("handle", 0.12, 1.3, (0, 0, 1.05), M("#B07A45", rough=0.4))
    knob = sp("knob", 0.16, (0, 0, 1.72), M(RED))
    brush = lat("brush", [(0.17, 0.42), (0.26, 0.3), (0.62, -0.1), (0.85, -0.5), (0.87, -0.56)], (0, 0, 0), straw)
    brush.scale = (1, 0.4, 1)
    T.apply(brush)
    T.smooth(brush, 60)
    band = cy("band", 0.28, 0.2, (0, 0, 0.4), M(RED), bevel=0.06)
    band.scale = (1, 0.65, 1)
    lines = [cap("ln%d" % i, 0.03, 0.62, (x, -0.24, -0.18), M("#D49A2A"), rot=(0, R(x * 35), 0)) for i, x in
             enumerate((-0.5, -0.25, 0.0, 0.25, 0.5))]
    broom = [handle, knob, brush, band] + lines
    for o in broom:
        T.apply(o)
    b = T.join(broom, "broom")
    b.rotation_euler = (0, R(25), 0)
    b.location = (0.3, 0, 0.3)
    dust = M("#E6E2DA", rough=0.6, coat=0.0)
    puffs = [sp("dust%d" % i, r, (x, -0.2, z), dust) for i, (x, z, r) in
             enumerate([(-0.75, -0.5, 0.24), (-1.1, -0.38, 0.18), (-0.9, -0.12, 0.14)])]
    return [b] + puffs


def _wheels(xs, y, r=0.24, z=0.22):
    out = []
    for i, x in enumerate(xs):
        out.append(cy("w%d" % i, r, 0.14, (x, y, z), M(YELLOW), rot=(R(90), 0, 0), bevel=0.04))
        out.append(cy("h%d" % i, 0.08, 0.18, (x, y - 0.02, z), M(CHAR), rot=(R(90), 0, 0), bevel=0.03))
    return out


def ic_carriage_passenger():
    body = rb("body", (2.3, 0.95, 0.95), (0, 0, 0.82), M(GREEN), bevel=0.1)
    roof = rb("roof", (2.5, 1.12, 0.2), (0, 0, 1.38), M("#C42F3A"), bevel=0.08)
    band = rb("band", (2.32, 0.97, 0.1), (0, 0, 0.42), M("#24894A"), bevel=0.04)
    wins = [rb("win%d" % i, (0.46, 0.1, 0.4), (x, -0.46, 0.9), M("#9BDCF5", rough=0.08, coat=0.6), bevel=0.06)
            for i, x in enumerate((-0.72, 0.0, 0.72))]
    chassis = rb("chassis", (2.0, 0.8, 0.2), (0, 0, 0.3), M(CHAR), bevel=0.05)
    cpl = [cy("cpl%d" % i, 0.07, 0.3, (s * 1.25, 0, 0.42), M(CHAR), rot=(0, R(90), 0)) for i, s in enumerate((-1, 1))]
    return [body, roof, band, chassis] + wins + cpl + _wheels((-0.65, 0.65), -0.45)


def ic_carriage_cargo():
    wag = M("#D2694B", rough=0.35)
    floor = rb("floor", (2.2, 1.0, 0.18), (0, 0, 0.42), wag, bevel=0.05)
    walls = [rb("wf", (2.2, 0.1, 0.5), (0, -0.46, 0.68), wag, bevel=0.04),
             rb("wb", (2.2, 0.1, 0.5), (0, 0.46, 0.68), wag, bevel=0.04),
             rb("wl", (0.1, 1.0, 0.5), (-1.06, 0, 0.68), wag, bevel=0.04),
             rb("wr", (0.1, 1.0, 0.5), (1.06, 0, 0.68), wag, bevel=0.04)]
    trim = rb("trim", (2.26, 0.14, 0.1), (0, -0.48, 0.95), M("#B2513A"), bevel=0.03)
    crate_m = M("#E9C48C", rough=0.45, coat=0.15)
    plank = M("#C9965A", rough=0.45)
    crates = []
    for i, (x, z, s, rz) in enumerate([(-0.5, 1.05, 0.7, 6), (0.35, 0.98, 0.6, -8), (-0.1, 1.5, 0.5, 12)]):
        c = rb("crate%d" % i, (s, s, s), (x, 0, z), crate_m, bevel=0.05, rot=(0, 0, R(rz)))
        crates.append(c)
        for k, dz in enumerate((-0.3, 0.3)):
            p = rb("pl%d%d" % (i, k), (s * 1.02, s * 1.02, 0.07), (x, 0, z + dz * s), plank, bevel=0.02,
                   rot=(0, 0, R(rz)))
            crates.append(p)
        crates.append(rb("x%d" % i, (0.08, s * 1.02, s * 0.8), (x, 0, z), plank, bevel=0.02, rot=(0, R(45), R(rz))))
    chassis = rb("chassis", (1.9, 0.8, 0.2), (0, 0, 0.28), M(CHAR), bevel=0.05)
    return [floor, trim, chassis] + walls + crates + _wheels((-0.6, 0.6), -0.45)


def ic_music():
    col = M(PURPLE)
    heads = [sp("hd%d" % i, 0.34, (x, 0, z), col, scale=(1.25, 0.75, 0.88), rot=(0, R(-22), 0)) for i, (x, z) in
             enumerate([(-0.55, -0.68), (0.6, -0.42)])]
    st = [rb("st%d" % i, (0.15, 0.22, h), (x, 0, z), col, bevel=0.05) for i, (x, z, h) in
          enumerate([(-0.18, 0.1, 1.55), (0.97, 0.36, 1.55)])]
    beam = L.slab("beam", L.round_poly([(-0.26, 0.6), (1.05, 0.88), (1.05, 1.22), (-0.26, 0.94)], 0.06, 3), 0.26,
                  col, bevel=0.07)
    return heads + st + [beam]


def ic_sound():
    body_pts = [(-0.95, -0.32), (-0.45, -0.32), (0.1, -0.8), (0.1, 0.8), (-0.45, 0.32), (-0.95, 0.32)]
    spk = slab("spk", L.round_poly(body_pts, 0.1, 5), 0.6, M(ORANGE), bevel=0.14)
    cone = cy("cone", 0.32, 0.2, (-0.1, -0.33, 0), M("#C46A1E"), rot=(R(90), 0, 0), r_top=0.12)
    waves = []
    for i, r in enumerate((0.48, 0.88)):
        pts = L.band_poly(L.arc_pts(0.25, 0, r, -48, 48, 24), 0.2)
        waves.append(slab("wave%d" % i, L.round_poly(pts, 0.06, 4), 0.35, M(YELLOW), bevel=0.08))
    return [spk, cone] + waves


def ic_switch():
    col = M(YELLOW)
    left = L.arrow_poly([(0, -1.0), (0, -0.25), (-0.5, 0.35)], 0.36, 0.45, 0.9)
    right = L.arrow_poly([(0, -0.25), (0.5, 0.35)], 0.36, 0.45, 0.9, tail_round=False)
    l = slab("left", L.round_poly(left, 0.06, 4), 0.46, col, bevel=0.13)
    r = slab("right", L.round_poly(right, 0.06, 4), 0.46, M(ORANGE), bevel=0.13, y=0.02)
    return [l, r]


def ic_hand():
    skin = M("#F6C9A0", rough=0.4, coat=0.15)
    palm = rb("palm", (0.95, 0.6, 0.85), (0, 0, 0), skin, bevel=0.28)
    index = cap("index", 0.17, 1.05, (-0.27, -0.02, 0.8), skin)
    nail = sp("nail", 0.1, (-0.27, -0.13, 1.15), M("#FFDCD0"), scale=(0.9, 0.4, 1.1))
    fingers = [cap("f%d" % i, 0.16, 0.66, (0.15, -0.26, z), skin, rot=(0, R(90), 0)) for i, z in
               enumerate((0.3, 0.04, -0.22))]
    thumb = cap("thumb", 0.16, 0.62, (-0.48, -0.25, 0.02), skin, rot=(0, R(55), 0))
    cuff = cy("cuff", 0.5, 0.36, (0, 0, -0.58), M(BLUE), bevel=0.1)
    cuff.scale = (1.05, 0.72, 1)
    hand = [palm, index, nail, thumb, cuff] + fingers
    for o in hand:
        T.apply(o)
    h = T.join(hand, "hand")
    h.rotation_euler = (0, R(-18), 0)
    return [h]


def ic_narrator():
    """Friendly train conductor (head + shoulders, blue cap) with a little speech bubble: 'listen again'."""
    skin = M("#F6C9A0", rough=0.4, coat=0.15)
    navy = M("#1E5FAF")
    blue = M(BLUE)
    gold = M(GOLD, metal=0.6, rough=0.22)
    white = M(WHITE, rough=0.3)
    # shoulders / jacket
    body = sp("body", 1.0, (0, 0.15, -1.22), navy, scale=(1.08, 0.7, 0.55))
    collar = [sp("collar%d" % i, 0.26, (s * 0.2, -0.42, -0.74), white, scale=(1.0, 0.45, 0.65),
                 rot=(0, R(s * 35), 0)) for i, s in enumerate((-1, 1))]
    buttons = [sp("btn%d" % i, 0.075, (0, -0.52, z), gold, scale=(1, 0.6, 1)) for i, z in enumerate((-1.0, -1.25))]
    # head
    head = sp("head", 0.74, (0, 0, 0.0), skin, scale=(1.0, 0.9, 0.95))
    ears = [sp("ear%d" % i, 0.17, (s * 0.73, 0.04, -0.02), skin, scale=(0.6, 0.8, 1.0)) for i, s in enumerate((-1, 1))]
    hair = [sp("hair%d" % i, 0.22, (s * 0.6, 0.1, 0.34), M("#7A4E2D", rough=0.5), scale=(0.8, 1.0, 0.9))
            for i, s in enumerate((-1, 1))]
    eyes = eye((-0.25, -0.6, 0.08), 0.14) + eye((0.25, -0.6, 0.08), 0.14)
    nose = sp("nose", 0.09, (0, -0.68, -0.06), M("#F2A97E", rough=0.4), scale=(1.1, 0.8, 0.9))
    cheeks = [sp("ck%d" % i, 0.11, (s * 0.44, -0.53, -0.16), M("#FF9AA8"), scale=(1, 0.4, 0.7)) for i, s in
              enumerate((-1, 1))]
    smile_pts = L.band_poly(L.arc_pts(0, 0, 0.24, 200, 340, 16), 0.08)
    smile = slab("smile", L.round_poly(smile_pts, 0.03, 3), 0.12, M("#C42F3A", rough=0.35), bevel=0.03,
                 loc=(0, -0.6, -0.1))
    # conductor cap: crown, band, visor, badge
    tilt = (R(-8), 0, 0)
    crown = cy("crown", 0.66, 0.42, (0, 0.04, 0.72), blue, bevel=0.08, r_top=0.74)
    band = cy("band", 0.69, 0.14, (0, 0.03, 0.56), navy, bevel=0.04)
    for o in (crown, band):
        o.rotation_euler = tilt
    visor = sp("visor", 0.52, (0, -0.52, 0.5), M(CHAR, rough=0.3), scale=(1.05, 0.62, 0.15), rot=(R(-12), 0, 0))
    badge = sp("badge", 0.14, (0, -0.66, 0.74), gold, scale=(1, 0.4, 1))
    # speech bubble (top right) with three dots
    bub_prof = [(x * 1.25, z) for x, z in L.circle_pts(0.5, 32)]
    bx, bz = 1.15, 1.05
    bubble = slab("bubble", bub_prof, 0.26, white, bevel=0.09, loc=(bx, -0.15, bz))
    tail = slab("tail", L.round_poly([(-0.3, 0.12), (0.05, 0.1), (-0.45, -0.34)], 0.05, 3), 0.2, white,
                bevel=0.06, loc=(bx, -0.15, bz - 0.33))
    dots = [sp("dot%d" % i, 0.1, (bx + dx, -0.3, bz), M(BLUE), scale=(1, 0.6, 1)) for i, dx in
            enumerate((-0.27, 0.0, 0.27))]
    return ([body, head, nose, smile, crown, band, visor, badge, bubble, tail] + collar + buttons + ears + hair
            + eyes + cheeks + dots)

ICONS = {
    "go": (ic_go, dict(yaw=-18, pitch=12)),
    "stop": (ic_stop, dict(yaw=-15, pitch=10)),
    "whistle": (ic_whistle, dict(yaw=-20, pitch=12)),
    "bell": (ic_bell, dict(yaw=-15, pitch=14)),
    "speed_slow": (ic_speed_slow, dict(yaw=22, pitch=20)),
    "speed_fast": (ic_speed_fast, dict(yaw=18, pitch=10)),
    "camera_follow": (ic_camera_follow, dict(yaw=-25, pitch=16)),
    "camera_reset": (ic_camera_reset, dict(yaw=-15, pitch=12)),
    "undo": (ic_undo, dict(yaw=-15, pitch=12)),
    "redo": (ic_redo, dict(yaw=-15, pitch=12)),
    "delete": (ic_delete, dict(yaw=-15, pitch=18)),
    "rotate": (ic_rotate, dict(yaw=-15, pitch=12)),
    "confirm": (ic_confirm, dict(yaw=-15, pitch=12)),
    "cancel": (ic_cancel, dict(yaw=-15, pitch=12)),
    "build": (ic_build, dict(yaw=-25, pitch=30)),
    "train": (ic_train, dict(yaw=-30, pitch=12)),
    "decorate": (ic_decorate, dict(yaw=-15, pitch=12)),
    "explore": (ic_explore, dict(yaw=-15, pitch=12)),
    "home": (ic_home, dict(yaw=-28, pitch=14)),
    "settings": (ic_settings, dict(yaw=-15, pitch=12)),
    "play": (ic_play, dict(yaw=-18, pitch=12)),
    "new_world": (ic_new_world, dict(yaw=-15, pitch=16)),
    "clear_all": (ic_clear_all, dict(yaw=-12, pitch=10)),
    "carriage_passenger": (ic_carriage_passenger, dict(yaw=-25, pitch=14)),
    "carriage_cargo": (ic_carriage_cargo, dict(yaw=-25, pitch=18)),
    "music": (ic_music, dict(yaw=-15, pitch=10)),
    "sound": (ic_sound, dict(yaw=-15, pitch=10)),
    "switch": (ic_switch, dict(yaw=-15, pitch=12)),
    "hand": (ic_hand, dict(yaw=-15, pitch=10)),
    "plus": (ic_plus, dict(yaw=-15, pitch=12)),
    "minus": (ic_minus, dict(yaw=-15, pitch=12)),
    "narrator": (ic_narrator, dict(yaw=-15, pitch=8)),
}


def main():
    a = T.args()
    sheet = "--sheet" in a or not [x for x in a if not x.startswith("--")]
    names = [x for x in a if not x.startswith("--")] or list(ICONS.keys())
    if names == ["none"]:
        names = []
    for n in names:
        fn, view = ICONS[n]
        T.reset()
        objs = fn()
        L.render_icon(objs, n, **view)
    if sheet:
        T.reset()
        L.contact_sheet(list(ICONS.keys()), L.ICON_DIR, os.path.join(T.PREVIEWS, "Icons_Sheet.png"))


main()
