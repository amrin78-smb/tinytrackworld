"""
Tiny Tracks World - original toy trains (5 locomotives + 2 wagons).

Run:  blender -b --factory-startup --python Tools/blender/models/build_trains.py -- [Loco_RedExpress ...]
Exports Assets/_Project/Art/Models/Trains/<Name>.fbx, previews to Logs/Blender/, manifest next to this script.

Vehicle conventions (match the wooden track): origin on the track bed top (z = 0) under the vehicle centre, length along
Y, front = -Y. Wheels Wheel_0.. are separate children (pivot = axle centre, axle = local X) at x = +/-0.30 with their
bottom at z = -0.02. Empties: BogieFront/BogieRear (track points under the front/rear axles), CouplerFront/CouplerRear
(vehicle ends incl. buffers), LampPoint (locos), SmokePoint (steam locos), CargoBed (cargo wagon bed floor centre),
DoorL/DoorR (passenger carriage boarding points).
Paint mask: every mesh has a second UV map "PaintMask" (Unity mesh.uv2 / UV channel 1): u = 1 on the vehicle's
repaintable signature colour (PAINT below, manifest "paintColor" = its sRGB before AO), 0 elsewhere; v = 0.
"""
import sys
import os
import json
import math

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import bpy
import bmesh
from mathutils import Vector, Euler
import tt_common as T
import trains_lib as L
from trains_lib import M, box, cyl_y, cyl_x, cyl_z, ball, lathe_m, lathe_y, HALF_PI, BUFFER_Z

HERE = os.path.dirname(os.path.abspath(__file__))


# ------------------------------------------------------------------------------------------------ shared pieces
def arc_roof(name, w, rise, thick, length, y, zbase, mat, n=16, bevel=0.008):
    """Curved cab / carriage roof: arched slab across X, extruded along Y."""
    outer, inner = [], []
    for k in range(n + 1):
        x = -w / 2 + w * k / n
        u = 2 * x / w
        z = zbase + rise * (1 - u * u)
        outer.append((x, z + thick))
        inner.append((x, z))
    prof = outer + inner[::-1]
    o = T.prism(name, prof, length, loc=(0, y, 0), material=M(mat), bevel=bevel, segments=1)
    T.smooth(o, 30)
    return o


def cowcatcher(name, y_back, y_top_front, y_tip, z_top, z_bot, half_w, mat, bar_mat):
    bm = bmesh.new()
    pts = [(-half_w, y_back, z_top), (half_w, y_back, z_top), (-half_w, y_back, z_bot), (half_w, y_back, z_bot),
           (-half_w, y_top_front, z_top), (half_w, y_top_front, z_top), (0, y_top_front - 0.05, z_top),
           (-half_w, y_tip + 0.12, z_bot), (half_w, y_tip + 0.12, z_bot), (0, y_tip, z_bot)]
    vs = [bm.verts.new(p) for p in pts]
    bmesh.ops.convex_hull(bm, input=vs)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    L.mats_on(o, [mat])
    mod = o.modifiers.new("bev", 'BEVEL')
    mod.width = 0.012
    mod.segments = 2
    mod.limit_method = 'ANGLE'
    parts = [o]
    # slats over the two sloped faces
    tl, tc = Vector((-half_w, y_top_front, z_top)), Vector((0, y_top_front - 0.05, z_top))
    bl, bc = Vector((-half_w, y_tip + 0.12, z_bot)), Vector((0, y_tip, z_bot))
    for sd in (1, -1):
        for k in range(5):
            u = 0.1 + 0.8 * k / 4
            a = tl.lerp(tc, u)
            b = bl.lerp(bc, u)
            a.x *= sd
            b.x *= sd
            nrm = (Vector((0, 0, 0)) + Vector((sd * 0.3, -1, 0.6))).normalized()
            a2, b2 = a + nrm * 0.012, b + nrm * 0.012
            parts.append(L.tube(f"{name}_bar{sd}{k}", [tuple(a2), tuple(b2)], 0.013, bar_mat, segs=6, up=(1, 0, 0)))
    parts.append(L.tube(f"{name}_top", [(-half_w, y_top_front - 0.01, z_top + 0.01), (0, y_top_front - 0.06, z_top + 0.01),
                                        (half_w, y_top_front - 0.01, z_top + 0.01)], 0.018, bar_mat, segs=6))
    return parts


def steam_cylinder(name, sd, y, z, r, length, body, band):
    x = sd * 0.40
    P = [cyl_y(name, r, length, y, z, x=x, mat=body, verts=20)]
    for e in (-1, 1):
        P.append(cyl_y(f"{name}_b{e}", r + 0.012, 0.022, y + e * (length / 2 - 0.012), z, x=x, mat=band, verts=18))
    P.append(cyl_y(f"{name}_cap", r * 0.55, 0.03, y - length / 2 - 0.012, z, x=x, mat=band, verts=14))
    return P


def coupling_rods(name, sd, ys, zc, mat="steel", x=0.385):
    x *= sd
    P = [box(f"{name}_rod", (0.022, ys[-1] - ys[0], 0.045), (x, (ys[0] + ys[-1]) / 2, zc), mat, bevel=0.01)]
    for i, y in enumerate(ys):
        P.append(cyl_x(f"{name}_pin{i}", 0.032, 0.03, x, y, zc, mat, verts=12))
    return P


def chassis(P, length, y0, footplate_mat, frame_mat="charcoal", fp_z=0.47, width=0.96, trim=None, frame_h=0.24):
    """Footplate + inner frames (between the wheels)."""
    P.append(box("frame", (0.44, length - 0.12, frame_h), (0, y0, fp_z - 0.03 - frame_h / 2 + 0.02), frame_mat,
                 bevel=0.02))
    P.append(box("footplate", (width, length, 0.06), (0, y0, fp_z), footplate_mat, bevel=0.015))
    if trim:
        for sd in (1, -1):
            P.append(box(f"fp_trim{sd}", (0.016, length - 0.02, 0.022), (sd * (width / 2 + 0.004), y0, fp_z - 0.008),
                         trim, bevel=0.006))


def buffer_beam(P, tag, y, direction, mat, trim=None, width=0.96, buffers=True, hook=True, rivets="brass",
                stock="charcoal", head="steel"):
    """Beam centred at y (depth 0.10). Returns the outermost y (coupler end)."""
    P.append(box(f"beam_{tag}", (width, 0.10, 0.20), (0, y, BUFFER_Z), mat, bevel=0.02))
    face = y + direction * 0.05
    tip = face
    if trim:
        P.append(L.frame_ring(f"beamtrim_{tag}", width - 0.06, 0.15, 0.02, 0.014, 0.012,
                              (0, face + direction * 0.004, BUFFER_Z), trim, facing="-Y" if direction < 0 else "+Y"))
    if rivets:
        for zz in (BUFFER_Z + 0.068, BUFFER_Z - 0.068):
            P += L.rivet_row(f"rv_{tag}{zz:.2f}", (-0.40, face + direction * 0.004, zz), (0.40, face + direction * 0.004, zz),
                             6, r=0.011, mat=rivets)
    if buffers:
        for sd in (1, -1):
            parts, t = L.buffer(f"buf_{tag}{sd}", sd * 0.30, face, BUFFER_Z, direction, stock=stock, head=head)
            P += parts
            tip = t
    if hook:
        parts, t = L.coupling_hook(f"hook_{tag}", face, BUFFER_Z, direction)
        P += parts
        tip = t if abs(t) > abs(tip) else tip
    return tip


def boiler_handrails(P, zc, r, y0, y1, posts, mat="brass"):
    a = math.radians(48)
    rr = r + 0.045
    for sd in (1, -1):
        x, z = sd * rr * math.cos(a), zc + rr * math.sin(a)
        xs, zs = sd * (r - 0.01) * math.cos(a), zc + (r - 0.01) * math.sin(a)
        P += L.handrail(f"hr{sd}", [(x, y0, z), (x, y1, z)], mat, r=0.011,
                        post_to=[((x, py, z), (xs, py, zs)) for py in posts])


def cab_grabs(P, x_abs, y, z0, z1, mat="brass"):
    for sd in (1, -1):
        x = sd * x_abs
        P.append(L.tube(f"grab{sd}{y:.2f}", [(x, y, z0), (x, y, z1)], 0.011, mat, segs=6, up=(1, 0, 0)))
        for zz in (z0, z1):
            P.append(ball(f"grabk{sd}{y:.2f}{zz:.2f}", 0.017, (x - sd * 0.01, y, zz), mat, segs=6, rings=3))


def steps(P, x_abs, y, z, mat="charcoal"):
    for sd in (1, -1):
        x = sd * x_abs
        P.append(box(f"step{sd}{y:.2f}", (0.10, 0.17, 0.022), (x, y, z), mat, bevel=0.006))
        for e in (-1, 1):
            P.append(box(f"steph{sd}{y:.2f}{e}", (0.02, 0.02, 0.15), (x, y + e * 0.07, z + 0.07), mat, bevel=0.004))


def smokebox_face(P, prefix, y_front, zc, r, face_mat="face", ring="brass", **kw):
    """Domed smokebox door (face plate) on a smokebox whose front face is at y_front."""
    P.append(lathe_y(f"{prefix}_door", [(r, 0.0, 0), (r, 0.018, 0), (r - 0.015, 0.035, 0),
                                        (0.0, 0.046, 0)], [face_mat], 0, y_front, zc, segs=32,
                     smooth_angle=60))
    P.append(T.torus(f"{prefix}_ring", r + 0.006, 0.018, loc=(0, y_front - 0.012, zc), material=M(ring),
                     rot=(HALF_PI, 0, 0), major_segs=32, minor_segs=4))
    y0 = y_front - 0.046
    P += L.friendly_face(prefix, y0, zc - 0.01, r * 0.98, **kw)
    return y0


def dome_lathe(name, y, base_z, r, h, mat, segs=24):
    prof = [(r + 0.035, base_z - 0.03, 0), (r + 0.025, base_z + 0.03, 0), (r, base_z + 0.06, 0),
            (r, base_z + h * 0.45, 0)]
    for k in range(1, 6):
        a = HALF_PI * k / 5
        prof.append((r * math.cos(a) if k < 5 else 0.0, base_z + h * 0.45 + h * 0.55 * math.sin(a), 0))
    return lathe_m(name, prof, [mat], segs=segs, loc=(0, y, 0))


def safety_valve(name, y, base_z, mat="brass"):
    return lathe_m(name, [(0.065, base_z - 0.02, 0), (0.06, base_z + 0.05, 0), (0.045, base_z + 0.07, 0),
                          (0.03, base_z + 0.10, 0), (0.042, base_z + 0.115, 0), (0.03, base_z + 0.13, 0),
                          (0.0, base_z + 0.135, 0)], [mat], segs=16, loc=(0, y, 0))


def whistle(name, x, y, base_z, mat="brass"):
    return lathe_m(name, [(0.018, base_z - 0.02, 0), (0.018, base_z + 0.06, 0), (0.032, base_z + 0.07, 0),
                          (0.032, base_z + 0.13, 0), (0.02, base_z + 0.15, 0), (0.0, base_z + 0.16, 0)], [mat],
                   segs=12, loc=(x, y, 0))


# ------------------------------------------------------------------------------------------------ models
def build_red_express():
    P = []
    R, axles = 0.20, (-0.40, 0.05, 0.50)
    zc = 0.80
    chassis(P, 2.06, 0.0, "red", trim="brass")
    # boiler, smokebox, bands
    P.append(cyl_y("smokebox", 0.30, 0.30, -0.86, zc, mat="charcoal", verts=40))
    P.append(box("saddle", (0.42, 0.30, 0.14), (0, -0.86, 0.53), "charcoal", bevel=0.02))
    P.append(cyl_y("boiler", 0.27, 1.04, -0.19, zc, mat="red", verts=40))
    P.append(cyl_y("sbband", 0.305, 0.03, -0.715, zc, mat="brass", verts=40))
    for i, y in enumerate((-0.55, -0.20, 0.13)):
        P.append(cyl_y(f"band{i}", 0.281, 0.032, y, zc, mat="brass", verts=32))
    door_y0 = smokebox_face(P, "rxf", -1.01, zc, 0.265)
    # chimney (tapered, flared copper-capped top)
    P.append(lathe_m("chimney", [(0.135, 1.02, 0), (0.125, 1.10, 0), (0.095, 1.15, 0), (0.088, 1.27, 0),
                                 (0.095, 1.31, 1), (0.125, 1.355, 1), (0.13, 1.395, 1), (0.105, 1.405, 2),
                                 (0.085, 1.37, 2), (0.0, 1.35, 2)], ["charcoal", "brass", "coal"], segs=24,
                     loc=(0, -0.80, 0)))
    smoke = (0, -0.80, 1.41)
    P.append(dome_lathe("dome", -0.25, 1.03, 0.15, 0.22, "brass"))
    P.append(safety_valve("valve", 0.03, 1.05))
    P.append(whistle("whistle", 0.0, 0.25, 1.05))
    # bell on a little yoke
    P.append(box("bell_yoke", (0.10, 0.025, 0.08), (0, -0.53, 1.10), "charcoal", bevel=0.008))
    P.append(lathe_m("bell", [(0.07, 1.12, 0), (0.066, 1.135, 0), (0.05, 1.17, 0), (0.042, 1.21, 0), (0.03, 1.228, 0),
                              (0.0, 1.235, 0)], ["brass"], segs=16, loc=(0, -0.53, 0)))
    # headlamp on top of the smokebox
    parts, lamp_pt = L.lamp("lamp", 0, -0.975, 1.165, -1, body="charcoal", rim="brass", r=0.05)
    P += parts
    boiler_handrails(P, zc, 0.27, -0.66, 0.28, (-0.50, 0.20))
    # cylinders + motion
    for sd in (1, -1):
        P += steam_cylinder(f"cyl{sd}", sd, -0.78, 0.30, 0.10, 0.26, "red", "brass")
        P.append(L.tube(f"slide{sd}", [(sd * 0.40, -0.64, 0.30), (sd * 0.40, -0.46, 0.30)], 0.014, "steel", segs=6))
        P.append(box(f"xhead{sd}", (0.05, 0.06, 0.06), (sd * 0.40, -0.47, 0.30), "steel", bevel=0.01))
        P.append(L.tube(f"conrod{sd}", [(sd * 0.40, -0.47, 0.30), (sd * 0.395, -0.40, 0.18)], 0.014, "steel", segs=6,
                        up=(1, 0, 0)))
        P += coupling_rods(f"cr{sd}", sd, axles, R - 0.02)
    # cowcatcher + front coupler
    P.append(box("beam_front", (0.96, 0.10, 0.20), (0, -0.99, BUFFER_Z), "red", bevel=0.02))
    P.append(L.frame_ring("beamtrim_f", 0.90, 0.15, 0.02, 0.014, 0.012, (0, -1.044, BUFFER_Z), "brass"))
    P += cowcatcher("cowcatcher", -0.96, -1.05, -1.25, 0.25, 0.035, 0.44, "charcoal", "brass")
    parts, front_tip = L.coupling_hook("hook_f", -1.04, BUFFER_Z, -1)
    P += parts
    # cab
    P.append(box("cab", (0.92, 0.64, 0.80), (0, 0.62, 0.90), "red", bevel=0.03))
    P.append(arc_roof("roof", 1.04, 0.08, 0.045, 0.78, 0.62, 1.29, "charcoal"))
    P.append(box("roof_rim", (0.94, 0.66, 0.03), (0, 0.62, 1.29), "brass", bevel=0.01))
    for sd in (1, -1):
        P += L.round_window(f"spec{sd}", 0.085, (sd * 0.29, 0.30, 1.13), "-Y", "brass")
        P += L.round_window(f"rspec{sd}", 0.085, (sd * 0.25, 0.94, 1.13), "+Y", "brass")
        facing = "+X" if sd > 0 else "-X"
        P += L.window(f"sidew{sd}", 0.30, 0.30, 0.07, (sd * 0.46, 0.64, 1.07), facing, "brass")
        P.append(L.frame_ring(f"lining{sd}", 0.50, 0.30, 0.05, 0.016, 0.012, (sd * 0.462, 0.62, 0.71), "brass",
                              facing=facing))
        P.append(L.panel(f"plate{sd}", 0.18, 0.09, 0.04, 0.016, (sd * 0.466, 0.62, 0.71), "brass", facing=facing, n=3))
    cab_grabs(P, 0.475, 0.92, 0.62, 1.08)
    steps(P, 0.47, 0.70, 0.31)
    # small coal rails on top of the cab back + rear beam
    rear_tip = buffer_beam(P, "rear", 0.99, 1, "red", trim="brass")
    wheels = []
    for i, y in enumerate(axles):
        wheels += L.wheel_pair(i * 2, y, R, rim="steel", disc="red_deep", hub="brass", spokes=8, spoke_mat="red",
                               counterweight="red")
    return dict(parts=P, wheels=wheels, axles=axles, front=front_tip, rear=rear_tip, lamp=lamp_pt, smoke=smoke)


def build_blue_adventure():
    P = []
    axles = (-0.66, -0.10, 0.42)
    radii = (0.16, 0.21, 0.21)
    zc = 0.84
    sx = 1.15
    chassis(P, 1.98, 0.0, "navy", trim="white")
    for sd in (1, -1):
        P.append(box(f"skirt{sd}", (0.04, 1.92, 0.12), (sd * 0.462, 0.0, 0.42), "blue", bevel=0.015))
        P.append(box(f"skirt_ln{sd}", (0.012, 1.86, 0.024), (sd * 0.484, 0.0, 0.41), "white", bevel=0.005))
    # streamlined casing (elliptical section), flat nose with the face disc
    prof = [(0.0, -0.02, 0), (0.36, -0.02, 0), (0.36, 0.92, 0), (0.355, 1.00, 0), (0.34, 1.07, 0), (0.315, 1.12, 0),
            (0.285, 1.155, 0), (0.0, 1.165, 0)]
    P.append(lathe_y("casing", prof, ["blue"], 0, 0.30, zc, segs=44, scale_x=sx, smooth_angle=50))
    y_nose = 0.30 - 1.165
    P.append(lathe_y("face_disc", [(0.0, 0.0, 0), (0.262, 0.0, 0), (0.262, 0.012, 0), (0.25, 0.026, 0),
                                   (0.19, 0.034, 0), (0.0, 0.036, 0)], ["face"], 0, y_nose + 0.005, zc - 0.01, segs=40))
    P.append(T.torus("face_ring", 0.266, 0.016, loc=(0, y_nose - 0.006, zc - 0.01), material=M("steel"),
                     rot=(HALF_PI, 0, 0), major_segs=40, minor_segs=6))
    P += L.friendly_face("baf", y_nose + 0.005 - 0.036, zc - 0.02, 0.25, look=(0.0, 0.01))
    # white speed stripes along the casing + cab, brass wings on the nose
    th = math.radians(-6)
    for sd in (1, -1):
        nx, nz = math.cos(th) / sx, math.sin(th)
        n = Vector((sd * nx, 0, nz)).normalized()
        p = Vector((sd * 0.36 * sx * math.cos(th), 0, zc + 0.36 * math.sin(th)))
        prof2 = [(-0.028, -0.004), (0.028, -0.004), (0.028, 0.008), (-0.028, 0.008)]
        path = [(p.x, 0.30, p.z), (p.x, -0.58, p.z)]
        st = T.sweep(f"stripe{sd}", path, prof2, material=M("white"), up=tuple(n))
        P.append(st)
        P.append(T.sweep(f"stripe2{sd}", [(p.x + n.x * 0.0, 0.30, p.z + 0.075), (p.x, -0.45, p.z + 0.075)],
                         [(-0.012, -0.004), (0.012, -0.004), (0.012, 0.006), (-0.012, 0.006)], material=M("white"),
                         up=tuple(Vector((sd * math.cos(th + 0.2) / sx, 0, math.sin(th + 0.2))).normalized())))
        for e, (yy, ww) in enumerate(((-0.58, 0.028), (-0.45, 0.012))):
            pass
        # brass speed badge: disc + three trailing bars
        bx = sd * 0.393
        P.append(cyl_x(f"badge{sd}", 0.05, 0.02, bx, -0.66, zc + 0.12, "brass", verts=20))
        P.append(cyl_x(f"badgec{sd}", 0.032, 0.026, bx, -0.66, zc + 0.12, "red", verts=16))
        for k, (dz, ln) in enumerate(((0.035, 0.20), (0.0, 0.26), (-0.035, 0.20))):
            P.append(box(f"badgebar{sd}{k}", (0.016, ln, 0.018), (sd * 0.392, -0.66 + 0.03 + ln / 2, zc + 0.12 + dz),
                         "brass", bevel=0.004))
        P.append(box(f"cabstripe{sd}", (0.012, 0.64, 0.056), (sd * 0.462, 0.62, p.z), "white", bevel=0.004))
    # crest hump on top + chimney stub
    P.append(T.capsule("crest", 0.10, 0.80, loc=(0, -0.02, zc + 0.31), material=M("blue"),
                       rot=(HALF_PI, 0, 0), segs=20))
    P.append(lathe_m("chimney", [(0.085, 1.15, 0), (0.08, 1.245, 0), (0.09, 1.255, 1), (0.065, 1.26, 1),
                                 (0.0, 1.235, 2)], ["navy", "steel", "coal"], segs=20, loc=(0, -0.48, 0)))
    smoke = (0, -0.48, 1.26)
    parts, lamp_pt = L.lamp("lamp", 0, -0.70, 1.215, -1, body="navy", rim="steel", r=0.055)
    P += parts
    # chin with buffers
    P.append(box("chin", (0.96, 0.18, 0.26), (0, -0.92, 0.36), "navy", bevel=0.07, segments=3))
    for sd in (1, -1):
        parts, front_tip = L.buffer(f"buf_f{sd}", sd * 0.30, -1.01, BUFFER_Z, -1, stock="navy", head="steel")
        P += parts
    parts, _ = L.coupling_hook("hook_f", -1.01, BUFFER_Z, -1)
    P += parts
    P.append(L.tube("chin_bar", [(-0.40, -1.012, 0.43), (0.40, -1.012, 0.43)], 0.012, "steel", segs=6))
    # cab
    P.append(box("cab", (0.92, 0.66, 0.95), (0, 0.62, 0.975), "blue", bevel=0.09, segments=3))
    P.append(arc_roof("roof", 1.0, 0.06, 0.045, 0.76, 0.62, 1.41, "navy"))
    for sd in (1, -1):
        facing = "+X" if sd > 0 else "-X"
        P += L.window(f"fw{sd}", 0.26, 0.15, 0.05, (sd * 0.23, 0.29, 1.31), "-Y", "white")
        P += L.window(f"sw{sd}", 0.34, 0.25, 0.08, (sd * 0.46, 0.60, 1.17), facing, "white")
        P += L.window(f"rw{sd}", 0.24, 0.20, 0.06, (sd * 0.22, 0.95, 1.20), "+Y", "white")
    cab_grabs(P, 0.475, 0.93, 0.62, 1.05, mat="steel")
    steps(P, 0.47, 0.75, 0.31)
    rear_tip = buffer_beam(P, "rear", 0.98, 1, "navy", trim="white", rivets="steel", stock="navy")
    # running gear: front pony truck cylinders + rods
    for sd in (1, -1):
        P += steam_cylinder(f"cyl{sd}", sd, -0.40, 0.27, 0.085, 0.18, "navy", "steel")
        P.append(L.tube(f"slide{sd}", [(sd * 0.40, -0.31, 0.27), (sd * 0.40, -0.20, 0.27)], 0.013, "steel", segs=6))
        P.append(L.tube(f"conrod{sd}", [(sd * 0.40, -0.22, 0.27), (sd * 0.39, -0.10, 0.19)], 0.014, "steel", segs=6,
                        up=(1, 0, 0)))
        P += coupling_rods(f"cr{sd}", sd, axles[1:], 0.19)
    wheels = []
    for i, (y, r) in enumerate(zip(axles, radii)):
        cw = "red_deep" if r > 0.2 else None
        wheels += L.wheel_pair(i * 2, y, r, rim="steel", disc="red", hub="brass", counterweight=cw)
    return dict(parts=P, wheels=wheels, axles=(axles[0], axles[-1]), front=front_tip, rear=rear_tip, lamp=lamp_pt,
                smoke=smoke)


def build_green_explorer():
    P = []
    R, axles = 0.18, (-0.45, 0.0, 0.45)
    chassis(P, 2.0, 0.0, "olive", trim="yellow")
    # long hood
    hy0, hy1 = -0.955, 0.24
    P.append(box("hood", (0.72, hy1 - hy0, 0.60), (0, (hy0 + hy1) / 2, 0.80), "green", bevel=0.08, segments=3))
    P.append(box("hood_cap", (0.60, hy1 - hy0 - 0.1, 0.04), (0, (hy0 + hy1) / 2 + 0.05, 1.10), "green_dark",
                 bevel=0.018))
    P += L.friendly_face("gef", hy0, 0.79, 0.30, look=(0.0, 0.0))
    for sd in (1, -1):
        parts, _ = L.lamp(f"hl{sd}", sd * 0.27, hy0 + 0.02, 0.60, -1, body="green_dark", rim="steel", r=0.04)
        P += parts
        facing = "+X" if sd > 0 else "-X"
        # radiator grilles and hood doors
        for gi, gy in enumerate((-0.70, -0.22)):
            P.append(L.frame_ring(f"grf{sd}{gi}", 0.34, 0.30, 0.03, 0.02, 0.014, (sd * 0.36, gy, 0.86), "green_dark",
                                  facing=facing))
            P.append(L.panel(f"grb{sd}{gi}", 0.31, 0.27, 0.02, 0.01, (sd * 0.358, gy, 0.86), "charcoal", facing=facing))
            for k in range(5):
                P.append(box(f"slat{sd}{gi}{k}", (0.016, 0.30, 0.018), (sd * 0.366, gy, 0.76 + 0.05 * k), "green",
                             bevel=0.0))
        P.append(box(f"hstripe{sd}", (0.012, hy1 - hy0 - 0.16, 0.05), (sd * 0.361, (hy0 + hy1) / 2, 0.60), "yellow",
                     bevel=0.005))
        P.append(ball(f"hhandle{sd}", 0.018, (sd * 0.362, 0.05, 0.86), "brass", segs=8, rings=4))
        # walkway railings
        rail = [(sd * 0.455, -0.93, 0.80), (sd * 0.455, 0.20, 0.80)]
        P += L.handrail(f"rail{sd}", rail, "yellow", r=0.013,
                        post_to=[((sd * 0.455, py, 0.80), (sd * 0.455, py, 0.50)) for py in (-0.93, -0.55, -0.17, 0.20)])
        P.append(L.tube(f"rail_lo{sd}", [(sd * 0.455, -0.93, 0.66), (sd * 0.455, 0.20, 0.66)], 0.009, "yellow", segs=6))
    # hood top: fan + exhaust + lamp
    P.append(cyl_z("fan", 0.13, 0.02, 0, -0.66, 1.12, "charcoal", verts=28))
    P.append(T.torus("fan_ring", 0.135, 0.014, loc=(0, -0.66, 1.125), material=M("green_dark"), major_segs=28,
                     minor_segs=6))
    for k in range(4):
        P.append(box(f"fanbar{k}", (0.24, 0.016, 0.012), (0, -0.66, 1.132), "steel", bevel=0.0,
                     rot=(0, 0, math.pi * k / 4)))
    P.append(lathe_m("exhaust", [(0.06, 1.08, 0), (0.05, 1.20, 0), (0.055, 1.24, 1), (0.04, 1.245, 1), (0.0, 1.23, 2)],
                     ["charcoal", "steel", "coal"], segs=16, loc=(0, -0.25, 0)))
    parts, lamp_pt = L.lamp("lamp", 0, -0.88, 1.17, -1, body="green_dark", rim="brass", r=0.05)
    P += parts
    # cab
    P.append(box("cab", (0.94, 0.72, 0.92), (0, 0.58, 0.96), "green", bevel=0.04))
    P.append(arc_roof("roof", 1.02, 0.07, 0.045, 0.84, 0.58, 1.42, "cream"))
    P.append(lathe_m("beacon", [(0.06, 1.52, 0), (0.06, 1.55, 1), (0.05, 1.585, 1), (0.0, 1.598, 1)],
                     ["steel", "beacon"], segs=16, loc=(0, 0.70, 0)))
    for sd in (1, -1):
        facing = "+X" if sd > 0 else "-X"
        P += L.window(f"fw{sd}", 0.30, 0.22, 0.05, (sd * 0.23, 0.22, 1.26), "-Y", "cream")
        P += L.window(f"sw{sd}", 0.40, 0.28, 0.06, (sd * 0.47, 0.56, 1.18), facing, "cream")
        P += L.window(f"rw{sd}", 0.30, 0.22, 0.05, (sd * 0.23, 0.94, 1.22), "+Y", "cream")
        P.append(box(f"cstripe{sd}", (0.012, 0.64, 0.05), (sd * 0.471, 0.58, 0.60), "yellow", bevel=0.005))
        # horns
        P.append(lathe_m(f"horn{sd}", [(0.0, 0.0, 0), (0.018, 0.0, 0), (0.018, 0.08, 0), (0.04, 0.12, 0),
                                        (0.04, 0.125, 0), (0.0, 0.11, 0)], ["brass"], segs=12,
                         loc=(sd * 0.12, 0.34, 1.555), rot=(HALF_PI, 0, 0)))
    P.append(box("horn_base", (0.30, 0.06, 0.04), (0, 0.37, 1.535), "charcoal", bevel=0.01))
    cab_grabs(P, 0.485, 0.30, 0.62, 1.05, mat="yellow")
    cab_grabs(P, 0.485, 0.88, 0.62, 1.05, mat="yellow")
    steps(P, 0.47, 0.58, 0.31, mat="yellow")
    # sandboxes / fuel tank between frames
    P.append(box("tank", (0.44, 0.40, 0.14), (0, 0.22, 0.28), "charcoal", bevel=0.04))
    # beams with chevrons
    front_tip = buffer_beam(P, "front", -1.0, -1, "yellow", rivets=None)
    rear_tip = buffer_beam(P, "rear", 1.0, 1, "yellow", rivets=None)
    for (y, d) in ((-1.0, -1), (1.0, 1)):
        face = y + d * 0.054
        for sd in (1, -1):
            for x0 in (0.04, 0.17, 0.33):
                w, sl, zb, zt = 0.05, 0.08, BUFFER_Z - 0.085, BUFFER_Z + 0.085
                prof = [(x0, zb), (x0 + w, zb), (x0 + w + sl, zt), (x0 + sl, zt)]
                if x0 + w + sl > 0.46:
                    continue
                prof = [(sd * px, pz) for px, pz in prof]
                P.append(T.prism(f"chev{y}{sd}{x0}", prof, 0.01, loc=(0, face, 0), material=M("black")))
    for sd in (1, -1):
        P += coupling_rods(f"cr{sd}", sd, axles, R - 0.02, mat="steel")
    wheels = []
    for i, y in enumerate(axles):
        wheels += L.wheel_pair(i * 2, y, R, rim="steel", disc="charcoal", hub="yellow", spokes=0,
                               counterweight="green_dark")
    return dict(parts=P, wheels=wheels, axles=(axles[0], axles[-1]), front=front_tip, rear=rear_tip, lamp=lamp_pt,
                smoke=None)


def build_yellow_sunshine():
    P = []
    R, axles = 0.22, (-0.36, 0.40)
    zc = 0.84
    chassis(P, 1.92, -0.01, "red", trim="brass", fp_z=0.49)
    P.append(cyl_y("smokebox", 0.31, 0.24, -0.80, zc, mat="orange", verts=40, bevel=0.015))
    P.append(box("saddle", (0.42, 0.24, 0.12), (0, -0.80, 0.56), "charcoal", bevel=0.02))
    P.append(cyl_y("boiler", 0.30, 0.80, -0.29, zc, mat="lemon", verts=40))
    P.append(cyl_y("sbband", 0.315, 0.03, -0.685, zc, mat="brass", verts=40))
    for i, y in enumerate((-0.52, -0.06)):
        P.append(cyl_y(f"band{i}", 0.311, 0.035, y, zc, mat="orange_dk", verts=40))
    smokebox_face(P, "ysf", -0.92, zc, 0.275, look=(0.0, 0.01))
    # balloon stack + big dome
    P.append(lathe_m("chimney", [(0.12, 1.08, 0), (0.095, 1.15, 0), (0.075, 1.22, 0), (0.09, 1.28, 0),
                                 (0.15, 1.35, 0), (0.175, 1.41, 0), (0.17, 1.46, 1), (0.15, 1.49, 1),
                                 (0.13, 1.495, 2), (0.0, 1.47, 2)], ["charcoal", "brass", "coal"], segs=30,
                     loc=(0, -0.78, 0)))
    smoke = (0, -0.78, 1.50)
    P.append(dome_lathe("dome", -0.33, 1.08, 0.20, 0.26, "red", segs=32))
    P.append(T.torus("dome_ring", 0.222, 0.016, loc=(0, -0.33, 1.15), material=M("brass"), major_segs=32,
                     minor_segs=4))
    P.append(safety_valve("valve", -0.02, 1.10))
    parts, lamp_pt = L.lamp("lamp", 0, -0.95, 1.2, -1, body="red", rim="brass", r=0.05)
    P += parts
    P.append(box("lamp_bracket", (0.06, 0.08, 0.06), (0, -0.92, 1.13), "charcoal", bevel=0.01))
    boiler_handrails(P, zc, 0.30, -0.64, 0.05, (-0.55, -0.15))
    for sd in (1, -1):
        P += steam_cylinder(f"cyl{sd}", sd, -0.75, 0.32, 0.09, 0.22, "yellow", "brass")
        P.append(L.tube(f"slide{sd}", [(sd * 0.40, -0.64, 0.32), (sd * 0.40, -0.48, 0.32)], 0.013, "steel", segs=6))
        P.append(L.tube(f"conrod{sd}", [(sd * 0.40, -0.48, 0.32), (sd * 0.395, -0.36, 0.20)], 0.014, "steel", segs=6,
                        up=(1, 0, 0)))
        P += coupling_rods(f"cr{sd}", sd, axles, R - 0.02)
    # barrel cab with portholes and a sun emblem
    P.append(box("cab", (0.90, 0.62, 0.90), (0, 0.39, 0.97), "lemon", bevel=0.17, segments=4))
    P.append(arc_roof("roof", 1.02, 0.10, 0.05, 0.78, 0.39, 1.33, "red"))
    for sd in (1, -1):
        facing = "+X" if sd > 0 else "-X"
        P += L.round_window(f"fport{sd}", 0.085, (sd * 0.26, 0.08, 1.16), "-Y", "brass")
        P += L.round_window(f"rport{sd}", 0.08, (sd * 0.24, 0.70, 1.12), "+Y", "brass")
        P += L.window(f"sw{sd}", 0.36, 0.26, 0.11, (sd * 0.45, 0.39, 1.12), facing, "brass")
        # sun emblem
        sx = sd * 0.452
        P.append(T.cyl(f"sun{sd}", 0.085, 0.02, loc=(sx, 0.39, 0.80), material=M("sun"), verts=24, rot=(0, HALF_PI, 0)))
        P.append(T.cyl(f"sunc{sd}", 0.058, 0.026, loc=(sx, 0.39, 0.80), material=M("orange"), verts=20,
                       rot=(0, HALF_PI, 0)))
        for k in range(10):
            a = 2 * math.pi * k / 10
            ray = T.prism(f"ray{sd}{k}", [(-0.026, 0.0), (0.026, 0.0), (0.0, 0.075)], 0.014, material=M("sun"))
            # build in XZ (facing -Y) at radius, then turn to face the side
            ray.location = (0, 0, 0)
            ray.rotation_euler = Euler((0, -a, 0))
            T.apply(ray)
            ray.data.transform(__import__("mathutils").Matrix.Translation((0.098 * math.sin(a), 0, 0.098 * math.cos(a))))
            ray.rotation_euler = Euler((0, 0, HALF_PI if sd > 0 else -HALF_PI))
            ray.location = (sx, 0.39, 0.80)
            P.append(ray)
    P.append(whistle("whistle", 0.0, 0.0, 1.12))
    cab_grabs(P, 0.465, 0.12, 0.66, 1.0)
    # bunker with coal
    P.append(box("bunker", (0.84, 0.18, 0.30), (0, 0.79, 0.66), "yellow", bevel=0.03))
    P.append(box("bunker_rim", (0.86, 0.20, 0.03), (0, 0.79, 0.81), "brass", bevel=0.01))
    for k, (cx, cy) in enumerate(((-0.2, 0.78), (0.0, 0.80), (0.2, 0.78))):
        P.append(T.ico(f"coal{k}", 0.09, loc=(cx, cy, 0.82), material=M("coal"), subdiv=1, jitter=0.15, seed=k,
                       scale=(1.2, 0.8, 0.6)))
    steps(P, 0.47, 0.30, 0.33)
    front_tip = buffer_beam(P, "front", -0.93, -1, "red", trim="brass", rivets=None)
    rear_tip = buffer_beam(P, "rear", 0.91, 1, "red", trim="brass", rivets=None)
    wheels = []
    for i, y in enumerate(axles):
        wheels += L.wheel_pair(i * 2, y, R, rim="steel", disc="navy", hub="brass", spokes=8, spoke_mat="blue",
                               counterweight="blue")
    return dict(parts=P, wheels=wheels, axles=axles, front=front_tip, rear=rear_tip, lamp=lamp_pt, smoke=smoke)


def wagon_underframe(P, R, axles, body_len, frame_mat="charcoal"):
    for sd in (1, -1):
        P.append(box(f"solebar{sd}", (0.06, body_len, 0.09), (sd * 0.40, 0.0, 0.465), frame_mat, bevel=0.012))
        for i, y in enumerate(axles):
            zc = R + L.WHEEL_BOTTOM
            # W-iron, axlebox and leaf spring
            P.append(box(f"axlebox{sd}{i}", (0.05, 0.11, 0.11), (sd * 0.392, y, zc + 0.02), frame_mat, bevel=0.015))
            for k in range(2):
                ln = 0.36 - 0.10 * k
                P.append(box(f"leaf{sd}{i}{k}", (0.045, ln, 0.016), (sd * 0.395, y, 0.405 - 0.017 * k), "steel",
                             bevel=0.004))
            for e in (-1, 1):
                P.append(box(f"wiron{sd}{i}{e}", (0.03, 0.025, 0.20), (sd * 0.392, y + e * 0.075, zc + 0.12), frame_mat,
                             bevel=0.006, rot=(e * 0.35, 0, 0)))
    P.append(box("headstock_mid", (0.44, body_len - 0.1, 0.06), (0, 0, 0.45), frame_mat, bevel=0.01))


def build_passenger():
    P = []
    R, axles = 0.17, (-0.55, 0.55)
    wagon_underframe(P, R, axles, 1.66)
    P.append(box("floor", (0.90, 1.62, 0.05), (0, 0, 0.52), "charcoal", bevel=0.01))
    P.append(box("body_lo", (0.88, 1.60, 0.36), (0, 0, 0.72), "red_deep", bevel=0.03))
    P.append(box("body_hi", (0.88, 1.60, 0.34), (0, 0, 1.04), "cream", bevel=0.03))
    P.append(box("beading", (0.896, 1.616, 0.024), (0, 0, 0.885), "brass", bevel=0.008))
    P.append(arc_roof("roof", 0.98, 0.10, 0.04, 1.72, 0.0, 1.20, "grey"))
    P.append(box("cornice", (0.90, 1.63, 0.035), (0, 0, 1.205), "red_deep", bevel=0.01))
    for k, y in enumerate((-0.45, 0.0, 0.45)):
        P.append(lathe_m(f"vent{k}", [(0.0, 1.29, 0), (0.05, 1.29, 0), (0.05, 1.33, 0), (0.06, 1.345, 1), (0.06, 1.36, 1),
                                      (0.0, 1.37, 1)], ["charcoal", "grey_light"], segs=12, loc=(0, y, 0)))
    for sd in (1, -1):
        facing = "+X" if sd > 0 else "-X"
        x = sd * 0.44
        for k, y in enumerate((-0.33, -0.11, 0.11, 0.33)):
            P += L.window(f"w{sd}{k}", 0.18, 0.21, 0.05, (x, y, 1.04), facing, "red_deep", glass="glass", n=2)
        P.append(L.frame_ring(f"wl{sd}", 0.92, 0.22, 0.04, 0.014, 0.01, (x, 0.0, 0.72), "brass", facing=facing))
        for e in (-1, 1):
            y = e * 0.62
            P.append(L.frame_ring(f"door{sd}{e}", 0.22, 0.60, 0.04, 0.016, 0.012, (x, y, 0.84), "brass", facing=facing))
            P.append(L.panel(f"dw{sd}{e}", 0.13, 0.16, 0.04, 0.02, (x, y, 1.04), "glass", facing=facing, n=2))
            P.append(ball(f"dh{sd}{e}", 0.018, (x + sd * 0.012, y + e * 0.07, 0.86), "brass", segs=8, rings=4))
            P.append(L.tube(f"dg{sd}{e}", [(x + sd * 0.02, y - e * 0.13, 0.66), (x + sd * 0.02, y - e * 0.13, 0.98)],
                            0.009, "brass", segs=6, up=(1, 0, 0)))
            P.append(box(f"step{sd}{e}", (0.08, 0.24, 0.022), (sd * 0.47, y, 0.40), "charcoal", bevel=0.006))
            P.append(box(f"stepb{sd}{e}", (0.02, 0.02, 0.10), (sd * 0.47, y, 0.45), "charcoal", bevel=0.004))
    for (y, d) in ((-0.80, -1), (0.80, 1)):
        facing = "-Y" if d < 0 else "+Y"
        for sd in (1, -1):
            P += L.window(f"ew{y}{sd}", 0.20, 0.20, 0.05, (sd * 0.2, y, 1.04), facing, "red_deep", glass="glass", n=2)
        P.append(L.tube(f"ehr{y}", [(-0.30, y + d * 0.02, 0.62), (-0.30, y + d * 0.02, 0.98)], 0.01, "brass", segs=6,
                        up=(1, 0, 0)))
        P.append(L.tube(f"ehr2{y}", [(0.30, y + d * 0.02, 0.62), (0.30, y + d * 0.02, 0.98)], 0.01, "brass", segs=6,
                        up=(1, 0, 0)))
    front_tip = buffer_beam(P, "front", -0.84, -1, "charcoal", rivets=None)
    rear_tip = buffer_beam(P, "rear", 0.84, 1, "charcoal", rivets=None)
    wheels = []
    for i, y in enumerate(axles):
        wheels += L.wheel_pair(i * 2, y, R, rim="steel", disc="charcoal", hub="brass")
    # DoorL / DoorR: boarding points at carriage-floor height (top of "floor", z = 0.545) just outside the front
    # door of each side (doors sit at y = +/-0.62; the model's left is +X)
    door_y, floor_top = -0.62, 0.545
    return dict(parts=P, wheels=wheels, axles=axles, front=front_tip, rear=rear_tip, lamp=None, smoke=None,
                extras=[("DoorL", (0.55, door_y, floor_top)), ("DoorR", (-0.55, door_y, floor_top))])


def build_cargo():
    P = []
    R, axles = 0.17, (-0.55, 0.55)
    wagon_underframe(P, R, axles, 1.66)
    P.append(box("floor", (0.90, 1.60, 0.06), (0, 0, 0.53), "plank_dk", bevel=0.01))
    ph, gap = 0.125, 0.012
    z0 = 0.56
    for k in range(3):
        zc = z0 + ph / 2 + k * (ph + gap)
        prof = [(-0.024, -ph / 2), (0.024, -ph / 2), (0.024, ph / 2), (-0.024, ph / 2)]
        for sd in (1, -1):
            o = T.sweep(f"plank{sd}{k}", [(sd * 0.425, -0.80, zc), (sd * 0.425, 0.80, zc)], prof,
                        material=M("plank"), up=(0, 0, 1), uv_scale=1.2)
            o.modifiers.new("b", 'BEVEL').width = 0.006
            P.append(o)
        for e in (-1, 1):
            o = T.sweep(f"eplank{e}{k}", [(-0.40, e * 0.776, zc), (0.40, e * 0.776, zc)], prof,
                        material=M("plank"), up=(0, 0, 1), uv_scale=1.2)
            o.modifiers.new("b", 'BEVEL').width = 0.006
            P.append(o)
    top = z0 + 3 * ph + 2 * gap
    for sd in (1, -1):
        for y in (-0.78, -0.27, 0.27, 0.78):
            P.append(box(f"strap{sd}{y}", (0.02, 0.05, top - z0 + 0.04), (sd * 0.452, y, (z0 + top) / 2), "charcoal",
                         bevel=0.006))
            for zz in (z0 + 0.06, top - 0.04):
                P.append(ball(f"bolt{sd}{y}{zz:.2f}", 0.011, (sd * 0.462, y, zz), "steel", segs=6, rings=3))
        P.append(box(f"toprail{sd}", (0.06, 1.62, 0.03), (sd * 0.425, 0, top + 0.012), "charcoal", bevel=0.008))
        # diagonal braces
        for e in (-1, 1):
            br = box(f"brace{sd}{e}", (0.016, 0.42, 0.035), (sd * 0.452, e * 0.52, (z0 + top) / 2), "charcoal",
                     bevel=0.005, rot=(e * 0.62, 0, 0))
            P.append(br)
    for e in (-1, 1):
        P.append(box(f"etop{e}", (0.90, 0.06, 0.03), (0, e * 0.776, top + 0.012), "charcoal", bevel=0.008))
    # the bed is left empty: the game loads separate cargo items at the CargoBed empty
    floor_z = 0.56
    front_tip = buffer_beam(P, "front", -0.84, -1, "red_deep", rivets=None)
    rear_tip = buffer_beam(P, "rear", 0.84, 1, "red_deep", rivets=None)
    wheels = []
    for i, y in enumerate(axles):
        wheels += L.wheel_pair(i * 2, y, R, rim="steel", disc="red_deep", hub="brass")
    # CargoBed: centre of the bed floor's top surface; usable interior = inside faces of the side / end planks
    bed_w = round(2 * (0.425 - 0.024), 3)
    bed_l = round(2 * (0.776 - 0.024), 3)
    return dict(parts=P, wheels=wheels, axles=axles, front=front_tip, rear=rear_tip, lamp=None, smoke=None,
                extras=[("CargoBed", (0.0, 0.0, floor_z))], manifest={"cargoBedSize": [bed_w, bed_l]})


def build_purple_starlight():
    """Unlockable night-sky tank engine: violet boiler, side tanks and cab, midnight-blue frame and roof, gold stars,
    a star finial on the dome and a little lantern on the smokebox."""
    P = []
    R, axles = 0.19, (-0.42, 0.04, 0.50)
    zc = 0.80
    chassis(P, 2.04, 0.0, "midnight", trim="gold")
    # smokebox, boiler, bands
    P.append(cyl_y("smokebox", 0.30, 0.28, -0.85, zc, mat="midnight", verts=40))
    P.append(box("saddle", (0.42, 0.28, 0.14), (0, -0.85, 0.53), "midnight", bevel=0.02))
    P.append(cyl_y("boiler", 0.275, 1.00, -0.21, zc, mat="violet", verts=40))
    P.append(cyl_y("sbband", 0.305, 0.03, -0.71, zc, mat="gold", verts=40))
    for i, y in enumerate((-0.50, 0.12)):
        P.append(cyl_y(f"band{i}", 0.287, 0.032, y, zc, mat="gold", verts=32))
    smokebox_face(P, "psf", -0.99, zc, 0.268, ring="gold", look=(0.0, 0.015))
    # chimney with a gold crown rim
    P.append(lathe_m("chimney", [(0.13, 1.02, 0), (0.115, 1.10, 0), (0.09, 1.15, 0), (0.085, 1.25, 0),
                                 (0.10, 1.285, 1), (0.135, 1.33, 1), (0.14, 1.37, 1), (0.112, 1.38, 2),
                                 (0.09, 1.35, 2), (0.0, 1.33, 2)], ["midnight", "gold", "coal"], segs=24,
                     loc=(0, -0.79, 0)))
    smoke = (0, -0.79, 1.385)
    for k in range(6):  # little crown points around the chimney rim
        a = 2 * math.pi * k / 6
        P.append(ball(f"crown{k}", 0.026, (0.135 * math.cos(a), -0.79 + 0.135 * math.sin(a), 1.385), "gold",
                      segs=8, rings=4))
    # dome with a standing gold star
    P.append(dome_lathe("dome", -0.28, 1.03, 0.15, 0.21, "violet"))
    P.append(T.torus("dome_ring", 0.172, 0.016, loc=(0, -0.28, 1.09), material=M("gold"), major_segs=28,
                     minor_segs=4))
    P.append(cyl_z("finial", 0.018, 0.08, 0, -0.28, 1.27, "gold", verts=8))
    P.append(L.star("dome_star", 0.085, (0, -0.28, 1.36), "-Y", mat="star", depth=0.035))
    P.append(safety_valve("valve", 0.02, 1.05, mat="gold"))
    # little lantern on top of the smokebox
    parts, lamp_pt = L.lamp("lamp", 0, -0.97, 1.16, -1, body="midnight", rim="gold", r=0.05)
    P += parts
    P.append(ball("lamp_knob", 0.022, (0, -0.97, 1.255), "gold", segs=8, rings=4))
    boiler_handrails(P, zc, 0.275, -0.66, 0.24, (-0.48, 0.12), mat="gold")
    # side tanks with big stars
    for sd in (1, -1):
        facing = "+X" if sd > 0 else "-X"
        P.append(box(f"tank{sd}", (0.17, 0.80, 0.38), (sd * 0.385, -0.24, 0.69), "violet", bevel=0.05, segments=3))
        P.append(box(f"tank_top{sd}", (0.19, 0.82, 0.03), (sd * 0.385, -0.24, 0.885), "midnight", bevel=0.01))
        P.append(L.frame_ring(f"tank_line{sd}", 0.70, 0.28, 0.06, 0.016, 0.012, (sd * 0.47, -0.24, 0.69), "gold",
                              facing=facing))
        P.append(L.star(f"tstar{sd}", 0.10, (sd * 0.476, -0.24, 0.69), facing, mat="star", depth=0.02))
        for k, (dy, dz, r) in enumerate(((-0.25, 0.10, 0.035), (0.25, -0.08, 0.03), (0.22, 0.10, 0.022))):
            P.append(L.star(f"tstar{sd}{k}", r, (sd * 0.476, -0.24 + dy, 0.69 + dz), facing, mat="star",
                            depth=0.016, spin=0.3 * k))
    # cylinders + motion
    for sd in (1, -1):
        P += steam_cylinder(f"cyl{sd}", sd, -0.78, 0.30, 0.095, 0.24, "midnight", "gold")
        P.append(L.tube(f"slide{sd}", [(sd * 0.40, -0.65, 0.30), (sd * 0.40, -0.48, 0.30)], 0.014, "steel", segs=6))
        P.append(box(f"xhead{sd}", (0.05, 0.06, 0.06), (sd * 0.40, -0.49, 0.30), "steel", bevel=0.01))
        P.append(L.tube(f"conrod{sd}", [(sd * 0.40, -0.49, 0.30), (sd * 0.395, -0.42, 0.17)], 0.014, "steel", segs=6,
                        up=(1, 0, 0)))
        P += coupling_rods(f"cr{sd}", sd, axles, R - 0.02)
    # cab
    P.append(box("cab", (0.92, 0.66, 0.82), (0, 0.63, 0.91), "violet", bevel=0.05, segments=3))
    P.append(arc_roof("roof", 1.04, 0.09, 0.045, 0.80, 0.63, 1.31, "midnight"))
    P.append(box("roof_rim", (0.94, 0.68, 0.03), (0, 0.63, 1.31), "gold", bevel=0.01))
    # crescent moon on the roof
    moon = []
    for k in range(13):  # outer arc 60 -> 300 deg (left bulge)
        a = math.radians(60 + 240 * k / 12)
        moon.append((0.09 * math.cos(a), 0.09 * math.sin(a)))
    for k in range(1, 10):  # inner arc back up (circle centred right), endpoints shared with the outer arc
        a = math.radians(270 - 180 * k / 10)
        moon.append((0.045 + 0.078 * math.cos(a), 0.078 * math.sin(a)))
    mo = T.prism("moon", moon, 0.03, loc=(0, 0.63, 1.50), material=M("star"), bevel=0.006, segments=1)
    mo.rotation_euler = Euler((0, 0, 0))
    T.smooth(mo, 30)
    P.append(mo)
    P.append(cyl_z("moon_post", 0.014, 0.08, 0.0, 0.63, 1.42, "gold", verts=8))
    for sd in (1, -1):
        facing = "+X" if sd > 0 else "-X"
        P += L.round_window(f"spec{sd}", 0.085, (sd * 0.29, 0.30, 1.12), "-Y", "gold")
        P += L.round_window(f"rspec{sd}", 0.085, (sd * 0.25, 0.96, 1.12), "+Y", "gold")
        P += L.window(f"sidew{sd}", 0.30, 0.28, 0.07, (sd * 0.46, 0.66, 1.07), facing, "gold")
        # star cluster on the cab side
        for k, (dy, dz, r) in enumerate(((0.0, 0.0, 0.07), (-0.17, 0.08, 0.035), (0.17, -0.06, 0.03))):
            P.append(L.star(f"cstar{sd}{k}", r, (sd * 0.466, 0.63 + dy, 0.72 + dz), facing, mat="star", depth=0.02,
                            spin=0.25 * k))
    cab_grabs(P, 0.475, 0.94, 0.62, 1.06, mat="gold")
    steps(P, 0.47, 0.72, 0.31)
    front_tip = buffer_beam(P, "front", -1.00, -1, "midnight", trim="gold", rivets="gold")
    rear_tip = buffer_beam(P, "rear", 1.00, 1, "midnight", trim="gold", rivets="gold")
    wheels = []
    for i, y in enumerate(axles):
        wheels += L.wheel_pair(i * 2, y, R, rim="steel", disc="midnight", hub="gold", spokes=8, spoke_mat="violet_dk",
                               counterweight="violet_dk")
    return dict(parts=P, wheels=wheels, axles=axles, front=front_tip, rear=rear_tip, lamp=lamp_pt, smoke=smoke)


MODELS = {
    "Loco_RedExpress": ("loco", "Classic Red Express", build_red_express),
    "Loco_BlueAdventure": ("loco", "Blue Adventure", build_blue_adventure),
    "Loco_GreenExplorer": ("loco", "Green Explorer", build_green_explorer),
    "Loco_YellowSunshine": ("loco", "Yellow Sunshine", build_yellow_sunshine),
    "Car_Passenger": ("car", "Passenger Carriage", build_passenger),
    "Car_Cargo": ("car", "Cargo Wagon", build_cargo),
    "Loco_PurpleStarlight": ("loco", "Purple Starlight", build_purple_starlight),
}

# Repaintable signature colour of each vehicle (material names -> PaintMask u = 1). The first one is "paintColor".
PAINT = {
    "Loco_RedExpress": ["red"],
    "Loco_BlueAdventure": ["blue"],
    "Loco_GreenExplorer": ["green"],
    "Loco_YellowSunshine": ["lemon"],
    "Car_Passenger": ["red_deep"],
    "Car_Cargo": ["plank"],
    "Loco_PurpleStarlight": ["violet"],
}

# Built in a scene of their own (and removed afterwards) so their object names carry no ".00N" suffix and the
# older models keep exactly the names they always had.
ISOLATED = {"Loco_PurpleStarlight"}


def build(name):
    kind, display, fn = MODELS[name]
    d = fn()
    root = L.make_root(d["parts"], name)
    wheels = d["wheels"]
    fast = bool(os.environ.get("TT_FAST"))
    T.finalize([root] + wheels, ao=not fast, ao_distance=0.35, ao_strength=0.7)
    paint = PAINT.get(name, [])
    painted = L.add_paint_mask(root, paint)
    for w in wheels:
        L.add_paint_mask(w, ())
    print(f"[TRAIN] {name}: PaintMask {painted}/{len(root.data.loops)} loops painted ({paint})")
    for w in wheels:
        L.attach(root, w)
    yf, yr = d["axles"][0], d["axles"][-1]
    L.add_empty(root, "BogieFront", (0, yf, 0))
    L.add_empty(root, "BogieRear", (0, yr, 0))
    L.add_empty(root, "CouplerFront", (0, d["front"], BUFFER_Z))
    L.add_empty(root, "CouplerRear", (0, d["rear"], BUFFER_Z))
    if d.get("lamp"):
        L.add_empty(root, "LampPoint", tuple(d["lamp"]))
    if d.get("smoke"):
        L.add_empty(root, "SmokePoint", tuple(d["smoke"]))
    for en, loc in d.get("extras", []):
        L.add_empty(root, en, loc)
    T.export_fbx(f"Trains/{name}", [root])
    verts, tris = T.stats([root] + wheels)
    print(f"[TRAIN] body={T.stats([root])[0]} wheels={[len(w.data.vertices) for w in wheels]}")
    mn, mx = T._bounds([root] + wheels)
    print(f"[TRAIN] {name}: verts={verts} tris={tris} size=({mx.x - mn.x:.2f}, {mx.y - mn.y:.2f}, {mx.z - mn.z:.2f}) "
          f"zmin={mn.z:.3f} ymin={mn.y:.3f} ymax={mx.y:.3f}")
    if not fast:
        T.render([root], T.preview_path(name))
        T.render([root], T.preview_path(name + "_Side"), yaw_deg=-90, pitch_deg=8)
        T.render([root], T.preview_path(name + "_Front"), yaw_deg=-15, pitch_deg=10, distance_scale=1.15)
    entry = dict(name=name, fbx=f"Assets/_Project/Art/Models/Trains/{name}.fbx", kind=kind, displayName=display,
                 length=round(d["rear"] - d["front"], 3), bogieSpacing=round(yr - yf, 3),
                 wheelNames=[w.name for w in wheels], verts=verts)
    if paint:
        entry["paintColor"] = [round(c, 4) for c in M(paint[0])["tt_srgb"]]
    entry.update(d.get("manifest", {}))
    return root, entry


def main():
    names = [a for a in T.args() if a in MODELS] or list(MODELS)
    isolated = [n for n in names if n in ISOLATED]
    names = [n for n in names if n not in ISOLATED]
    T.reset()
    built = []
    for i, n in enumerate(names):
        root, entry = build(n)
        built.append((root, entry))
        root.location.z = -1000  # park it so it does not shadow the next model's AO bake
        bpy.context.view_layer.update()
    entries = [e for _r, e in built]
    if len(built) > 1 and not os.environ.get("TT_FAST"):
        x = 0.0
        roots = []
        for r, _e in built:
            r.location = (x, 0, 0)
            roots.append(r)
            x -= 1.35
        bpy.context.view_layer.update()
        T.render(roots, os.path.join(T.PREVIEWS, "Trains_Lineup.png"), size=(1800, 720), yaw_deg=-28, pitch_deg=18,
                 distance_scale=0.95)
    for n in isolated:  # after the others (their names / bakes stay exactly as before), each in a fresh scene
        T.reset()
        _root, entry = build(n)
        entries.append(entry)
    # manifest (merge with an existing one when building a subset)
    mpath = os.path.join(HERE, "trains_manifest.json")
    old = {}
    if os.path.exists(mpath):
        try:
            old = {e["name"]: e for e in json.load(open(mpath))}
        except Exception:
            old = {}
    for e in entries:
        old[e["name"]] = e
    ordered = [old[n] for n in MODELS if n in old]
    with open(mpath, "w") as f:
        json.dump(ordered, f, indent=2)
    print("[TT] manifest", mpath)


main()
