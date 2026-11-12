"""
Tiny Tracks World - helpers for the Snowy Valley asset set (build_snowy.py).
Builds on tt_common / env_lib / creatures_lib without changing them (same conventions: front = Blender -Y,
up = +Z, model's right = -X, metres, vertex colour "Col" with the detail code in alpha).

Main ideas:
  * `m()` resolves a material name from the snowy palette, then env_lib / creatures_lib extras, then tt_common.
  * creature primitives (loft, ell, tube, eye ...) are wrapped so they accept snowy palette names.
  * `revolve()` is a lathe whose profile may vary per angle (drippy snow caps on pine tiers).
  * `snow_shell()` lays a soft, rounded snow layer over the upward-facing part of any mesh: the edge sinks into
    the surface and the thickness ramps up away from it, so the cap reads as a fluffy blanket, never a sticker.
  * `snow_tint()` (after T.finalize) turns the grey AO on snow faces into a soft blue shade so snow stays
    clean white with blue-tinted creases instead of looking dirty grey.
"""
import math
import os

import bmesh
import bpy
import numpy as np
from mathutils import Vector, Euler, Matrix

import tt_common as T
import env_lib as E
import creatures_lib as C

# ------------------------------------------------------------------------------------------------ palette
SNOW_MATS = ("sv_snow", "sv_snow2", "sv_snowman")
EXTRA = {
    # snow / ice
    "sv_snow":       ("#EEF4FD", "noise", 0.14),
    "sv_snow2":      ("#DDE8F8", "noise", 0.14),
    "sv_snowman":    ("#F1F6FE", "noise", 0.10),
    "sv_ice":        ("#8ED3F2", "none", 0.0),
    "sv_icicle":     ("#D9F2FF", "none", 0.0),
    "sv_igloo_door": ("#22395C", "none", 0.0),
    # winter plants
    "sv_pine":       ("#2A8558", "noise", 0.6),
    "sv_pine_dark":  ("#1E6A46", "noise", 0.6),
    "sv_frost":      ("#5FAE7E", "noise", 0.5),
    "sv_bush":       ("#3A8F5E", "noise", 0.6),
    "sv_berry":      ("#E8323F", "none", 0.0),
    "sv_rock":       ("#A39C97", "noise", 0.8),
    # wood / building
    "sv_log":        ("#B0723F", "grain", 0.8),
    "sv_log2":       ("#9C6234", "grain", 0.8),
    "sv_log_end":    ("#E8BE84", "grain", 0.45),
    "sv_plank":      ("#8A5533", "grain", 0.7),
    "sv_window":     ("#FFD073", "none", 0.0),
    "sv_stone":      ("#BDBAC4", "noise", 0.8),
    "sv_stone2":     ("#9D9AA8", "noise", 0.8),
    "sv_roof":       ("#C8413A", "noise", 0.3),
    "sv_door":       ("#3E7E5A", "grain", 0.4),
    "sv_wreath":     ("#2F8A4E", "noise", 0.6),
    # props
    "sv_carrot":     ("#FF8424", "none", 0.0),
    "sv_coal":       ("#2A2A33", "none", 0.0),
    "sv_scarf":      ("#E8394A", "noise", 0.3),
    "sv_scarf2":     ("#FFF4E4", "noise", 0.3),
    "sv_hat":        ("#3C7FD9", "noise", 0.3),
    "sv_twig":       ("#76482A", "noise", 0.5),
    "sv_runner":     ("#E23B3B", "none", 0.0),
    "sv_rope":       ("#E4C28C", "noise", 0.5),
    "sv_post":       ("#2E5F63", "none", 0.0),
    "sv_glow":       ("#FFE7A0", "none", 0.0),
    # animals
    "sv_peng":       ("#2F3549", "noise", 0.2),
    "sv_peng_belly": ("#FBFAF5", "noise", 0.2),
    "sv_peng_feet":  ("#FF9A2E", "none", 0.0),
    "sv_deer":       ("#A86B42", "noise", 0.35),
    "sv_deer_dark":  ("#6E4329", "noise", 0.35),
    "sv_deer_cream": ("#F3E3C8", "noise", 0.35),
    "sv_antler":     ("#EAD3A6", "noise", 0.3),
    "sv_deer_nose":  ("#4A2A26", "none", 0.0),
    "sv_husky":      ("#717A8C", "noise", 0.35),
    "sv_husky_dark": ("#4D5466", "noise", 0.35),
    "sv_husky_eye":  ("#4FB0F0", "none", 0.0),
    "sv_collar":     ("#2E8BE6", "none", 0.0),
}


def m(name):
    mt = bpy.data.materials.get(name)
    if mt is not None:
        return mt
    if name in EXTRA:
        h, k, s = EXTRA[name]
        return T.mat(name, h, k, s)
    if name in E.EXTRA:
        return E.m(name)
    if name in C.EXTRA:
        return C.mat(name)
    return T.mat(name)


def mats(obj, names):
    obj.data.materials.clear()
    for n in names:
        obj.data.materials.append(m(n))
    return obj


def _reslot(obj, names):
    for i, n in enumerate(names):
        obj.data.materials[i] = m(n)
    return obj


# ------------------------------------------------------------------------------------------------ creature wrappers
def loft(name, keys, materials=("sv_snow",), **kw):
    o = C.loft(name, keys, materials=["white"] * len(materials), **kw)
    return _reslot(o, materials)


def ell(name, loc, radii, material, segs=16, rings=10, rot=(0, 0, 0)):
    o = T.sphere(name, 1.0, loc=loc, material=None, scale=radii, segs=segs, rings=rings, rot=rot)
    return mats(o, [material])


def ball(name, loc, r, material, segs=12, rings=8):
    return ell(name, loc, (r, r, r), material, segs, rings)


def tube(name, path, radius, material, **kw):
    o = C.tube(name, path, radius, "white", **kw)
    return _reslot(o, [material])


def torus(name, major, minor, loc=(0, 0, 0), material="white", rot=(0, 0, 0), major_segs=24, minor_segs=8):
    o = T.torus(name, major, minor, loc=loc, material=None, rot=rot, major_segs=major_segs, minor_segs=minor_segs)
    return mats(o, [material])


def shell_patch(name, body, blob, material, offset=0.006):
    o = C.shell_patch(name, body, blob, "white", offset=offset)
    return _reslot(o, [material])


def eye(prefix, loc, r, look, sclera=True, iris="eye_black", pupil_scale=0.72, up=(0, 0, 1), segs=12, psegs=10,
        second_hl=True, prings=None, hl_segs=(6, 4)):
    """Glossy toy eye (same construction as creatures_lib.eye, but accepts snowy palette names)."""
    loc = Vector(loc)
    look = Vector(look).normalized()
    upv = Vector(up)
    side = look.cross(upv).normalized()
    upv = side.cross(look).normalized()
    parts = []
    if sclera:
        parts.append(ball(prefix + "_white", loc, r, "eye_white", segs, max(5, segs // 2 + 1)))
        rp = r * pupil_scale
        pc = loc + look * (r * 0.42)
    else:
        rp = r
        pc = loc
    parts.append(ball(prefix + "_pupil", pc, rp, iris, psegs, prings or max(4, psegs // 2 + 1)))
    if iris != "eye_black":
        parts.append(ball(prefix + "_dot", pc + look * rp * 0.62, rp * 0.5, "eye_black", 8, 5))
    hd = (look * 1.0 + upv * 0.55 + side * 0.35).normalized()
    parts.append(ball(prefix + "_hl", pc + hd * rp * 0.93, rp * 0.26, "eye_white", *hl_segs))
    if second_hl:
        hd2 = (look * 1.0 - upv * 0.35 - side * 0.35).normalized()
        parts.append(ball(prefix + "_hl2", pc + hd2 * rp * 0.96, rp * 0.12, "eye_white", 5, 3))
    return parts


def legs4(prefix, xs, ys, top_z, mat_leg, mat_hoof, w_top=0.08, w_mid=0.065, w_low=0.058, hoof_h=0.09,
          hoof_w=0.07, thigh=None, segs=12, hoof_segs=None):
    """Four straight toy legs with hooves / paws (same recipe as the farm animals)."""
    out = []
    hs = hoof_segs or segs
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
        leg = loft(f"{prefix}_leg", keys, segs=segs, res=2, materials=(mat_leg,), up=(0, -1, 0))
        hoof = loft(f"{prefix}_hoof", [((x, y, hoof_h), hoof_w * 0.95, hoof_w),
                                       ((x, y, hoof_h * 0.5), hoof_w * 1.04, hoof_w * 1.08),
                                       ((x, y, 0.0), hoof_w * 1.08, hoof_w * 1.12)],
                    segs=hs, res=1, materials=(mat_hoof,), up=(0, -1, 0), smooth_angle=50)
        out += [leg, hoof, C.mirror(leg), C.mirror(hoof)]
    return out


# ------------------------------------------------------------------------------------------------ geometry
def revolve(name, rings, segs, fn, material, apex=None, bottom_cap=False, smooth_deg=70, paint=None,
            materials=None):
    """Lathe whose profile may depend on the angle. fn(ring_index, angle) -> (radius, z).
    apex: z of a single closing vertex on the axis above the last ring (None = open / flat top).
    paint(ring_index, seg_index) -> material slot (into `materials`)."""
    bm = bmesh.new()
    vr = []
    for i in range(rings):
        ring = []
        for s in range(segs):
            a = 2 * math.pi * s / segs
            r, z = fn(i, a)
            ring.append(bm.verts.new((r * math.cos(a), r * math.sin(a), z)))
        vr.append(ring)
    idx = []
    for i in range(rings - 1):
        for s in range(segs):
            s2 = (s + 1) % segs
            bm.faces.new((vr[i][s], vr[i][s2], vr[i + 1][s2], vr[i + 1][s]))
            idx.append(paint(i, s) if paint else 0)
    if apex is not None:
        top = bm.verts.new((0, 0, apex))
        for s in range(segs):
            bm.faces.new((vr[-1][s], vr[-1][(s + 1) % segs], top))
            idx.append(paint(rings - 1, s) if paint else 0)
    if bottom_cap:
        bm.faces.new(list(reversed(vr[0])))
        idx.append(paint(0, 0) if paint else 0)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = T._new_obj(name, bm)
    mats(o, materials or [material])
    o.data.polygons.foreach_set("material_index", idx)
    o.data.update()
    T.smooth(o, smooth_deg)
    return o


def _vnoise(p, freq, ph):
    x, y, z = p
    return (math.sin(freq * x + ph[0]) * math.cos(freq * y + ph[1]) +
            0.5 * math.sin(2.3 * freq * (x - y) + ph[2]) + 0.35 * math.sin(1.7 * freq * z + ph[3]))


def snow_shell(name, src, nz_min=0.35, thick=0.07, wobble=0.18, freq=4.0, seed=0, ramp=0.12, sink=0.012,
               material="sv_snow", z_min=None, up_bias=0.35, lumps=0.0):
    """Soft snow blanket over the up-facing part of `src` (any mesh object; it is not modified).
    The kept region is where normal.z (+ noise wobble) >= nz_min; it is cut along that smooth iso-contour (edges are
    split at the zero crossing), so the rim is a clean wavy line. Vertices are pushed out along the normal (slightly
    biased up) by up to `thick`, ramping from -sink at the rim over `ramp` metres so the edge tucks into the surface.
    lumps adds a little low-frequency thickness variation (fluffy, uneven snow)."""
    sh = src.copy()
    sh.data = src.data.copy()
    sh.modifiers.clear()
    sh.parent = None
    T._link(sh)
    sh.matrix_world = src.matrix_world.copy()
    T.apply(sh)
    sh.name = name
    bm = bmesh.new()
    bm.from_mesh(sh.data)
    bm.normal_update()
    R = np.random.default_rng(seed)
    ph = R.uniform(0, 2 * math.pi, 4)
    ph2 = R.uniform(0, 2 * math.pi, 4)
    nrm = {v: v.normal.copy() for v in bm.verts}
    f = {}
    for v in bm.verts:
        sc = nrm[v].z + wobble * _vnoise(v.co, freq, ph) / 1.85 - nz_min
        if z_min is not None:
            sc = min(sc, (v.co.z - z_min) * 4.0)
        f[v] = sc if abs(sc) > 1e-4 else 1e-4
    # split every edge that crosses the contour at the zero crossing
    cross = [e for e in bm.edges if (f[e.verts[0]] < 0) != (f[e.verts[1]] < 0)]
    newv = []
    for e in cross:
        a, b = e.verts
        t = f[a] / (f[a] - f[b])
        pa, pb = a.co.copy(), b.co.copy()
        na, nb = nrm[a], nrm[b]
        ne, nv = bmesh.utils.edge_split(e, a, t)
        nv.co = pa.lerp(pb, t)
        nrm[nv] = na.lerp(nb, t).normalized()
        f[nv] = 0.0
        newv.append(nv)
    if newv:
        bmesh.ops.connect_verts(bm, verts=newv)
    kill = [v for v in bm.verts if f[v] < 0]
    bmesh.ops.delete(bm, geom=kill, context='VERTS')
    lone = [v for v in bm.verts if not v.link_faces]
    if lone:
        bmesh.ops.delete(bm, geom=lone, context='VERTS')
    # merge near-duplicate rim vertices (crossings right next to an original vertex make slivers)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=0.006)
    # euclidean distance to the rim -> thickness ramp
    bverts = [v for v in bm.verts if v.is_boundary]
    bco = np.array([v.co[:] for v in bverts]) if bverts else np.zeros((0, 3))
    for v in bm.verts:
        if len(bco):
            dd = float(np.sqrt(((bco - np.array(v.co[:])) ** 2).sum(1)).min())
        else:
            dd = ramp
        t = min(1.0, dd / ramp)
        s = t * t * (3 - 2 * t)
        n = nrm.get(v, Vector((0, 0, 1)))
        th = thick * (1.0 + lumps * _vnoise(v.co, freq * 0.8, ph2) / 1.85)
        dirv = (n + Vector((0, 0, up_bias))).normalized()
        v.co += dirv * (-sink + (th + sink) * s)
    bm.to_mesh(sh.data)
    bm.free()
    mats(sh, [material])
    for p in sh.data.polygons:
        p.use_smooth = True
    return sh


def cull_inside(obj, centre, radii, margin=0.01, zmin=None):
    """Deletes faces of obj that lie completely inside an ellipsoid (hidden overlap) - or above zmin if given."""
    T.apply(obj)
    c = Vector(centre)
    bm = bmesh.new()
    bm.from_mesh(obj.data)

    def inside(v):
        if zmin is not None:
            return v.co.z > zmin
        d = v.co - c
        return (d.x / radii[0]) ** 2 + (d.y / radii[1]) ** 2 + (d.z / radii[2]) ** 2 < (1 - margin) ** 2
    kill = [f for f in bm.faces if all(inside(v) for v in f.verts)]
    bmesh.ops.delete(bm, geom=kill, context='FACES')
    lone = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=lone, context='VERTS')
    bm.to_mesh(obj.data)
    bm.free()
    return obj


def trim_bottom(obj, z=0.025, nz=-0.6):
    """Deletes the hidden, flattened underside of a ground-sitting blob (saves vertices)."""
    T.apply(obj)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.normal_update()
    kill = [f for f in bm.faces if f.calc_center_median().z < z and f.normal.z < nz]
    bmesh.ops.delete(bm, geom=kill, context='FACES')
    lone = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=lone, context='VERTS')
    bm.to_mesh(obj.data)
    bm.free()
    for p in obj.data.polygons:
        p.use_smooth = True
    return obj


def drips(prefix, pts, r, material="sv_snow", seed=0, segs=10, rings=6):
    """Rounded snow lumps hanging over an edge: pts = [(x, y, z), ...]; random size / sag."""
    R = np.random.default_rng(seed)
    out = []
    for i, p in enumerate(pts):
        k = R.uniform(0.75, 1.2)
        out.append(ell(f"{prefix}{i}", p, (r * k * 1.15, r * k, r * k * R.uniform(1.0, 1.5)), material, segs, rings))
    return out


def icicle(name, top, length, r, material="sv_icicle", segs=6):
    """Small rounded icicle hanging from `top`."""
    x, y, z = top
    prof = [(r, z), (r * 0.9, z - length * 0.25), (r * 0.45, z - length * 0.7), (r * 0.12, z - length * 0.95),
            (0.0, z - length)]
    o = E.lathe(name, prof, (0, 0, 0), m(material), segs=segs, smooth_deg=80)
    o.location = (x, y, 0)
    return o


# ------------------------------------------------------------------------------------------------ colour post
def _lin(hexstr):
    r, g, b = T.hex_rgb(hexstr)
    return np.array([T.srgb_to_linear(r), T.srgb_to_linear(g), T.srgb_to_linear(b)], dtype=np.float32)


def snow_tint(obj, ao_strength, shadow="#9AB6E6", gamma=0.85, names=SNOW_MATS, sky=0.04, side=0.66):
    """After T.finalize(..., ao_strength): on faces using snow materials, replace the grey AO darkening with a
    blend toward a soft blue shadow colour, plus a gentle top-to-bottom gradient by normal (snow facing down or
    sideways picks up a little blue; `side` = brightness factor of vertical snow, 1 = off)."""
    me = obj.data
    if "Col" not in me.color_attributes:
        return
    mnames = [mm.name if mm else "" for mm in me.materials]
    if not any(n in names for n in mnames):
        return
    n = len(me.loops)
    c = np.zeros(n * 4, dtype=np.float32)
    me.color_attributes["Col"].data.foreach_get("color", c)
    c = c.reshape(n, 4)
    sh = _lin(shadow)
    li = np.zeros(n, dtype=np.int32)
    me.loops.foreach_get("vertex_index", li)
    nz = np.zeros(len(me.vertices) * 3, dtype=np.float32)
    me.vertices.foreach_get("normal", nz)
    nz = nz.reshape(-1, 3)[:, 2][li]
    for p in me.polygons:
        nm = mnames[p.material_index] if p.material_index < len(mnames) else ""
        if nm not in names:
            continue
        hexstr = EXTRA[nm][0]
        base = _lin(hexstr)
        sl = slice(p.loop_start, p.loop_start + p.loop_total)
        occ = c[sl, 1] / max(base[1], 1e-4)
        ao = np.clip((occ - (1 - ao_strength)) / max(ao_strength, 1e-4), 0, 1) ** gamma
        u = np.clip(nz[sl] * 0.6 + 0.5, 0, 1)
        u = u * u * (3 - 2 * u)
        dirk = (2 * side - 1) + (2 - 2 * side) * u     # nz=-1 -> 2*side-1, nz=0 -> side, nz=1 -> 1
        col = sh[None, :] + (base - sh)[None, :] * (ao * np.clip(dirk, 0, 1))[:, None]
        col *= (1.0 + sky * np.clip(nz[sl], 0, 1))[:, None]
        c[sl, :3] = np.clip(col, 0, 1)
    me.color_attributes["Col"].data.foreach_set("color", c.ravel())


GLOW_MATS = ("sv_glow", "sv_window")


def glow(obj, names=GLOW_MATS, keep=0.15):
    """After T.finalize: faces using 'lit' materials (lantern glass, warm windows) get their flat colour back with
    only `keep` of the baked AO, so they read as glowing rather than shaded."""
    me = obj.data
    if "Col" not in me.color_attributes:
        return
    mnames = [mm.name if mm else "" for mm in me.materials]
    if not any(n in names for n in mnames):
        return
    n = len(me.loops)
    c = np.zeros(n * 4, dtype=np.float32)
    me.color_attributes["Col"].data.foreach_get("color", c)
    c = c.reshape(n, 4)
    for p in me.polygons:
        nm = mnames[p.material_index] if p.material_index < len(mnames) else ""
        if nm not in names:
            continue
        base = _lin(EXTRA[nm][0])
        sl = slice(p.loop_start, p.loop_start + p.loop_total)
        occ = np.clip(c[sl, 1] / max(base[1], 1e-4), 0, 1)
        c[sl, :3] = base[None, :] * (1 - keep * (1 - occ))[:, None]
    me.color_attributes["Col"].data.foreach_set("color", c.ravel())


# ------------------------------------------------------------------------------------------------ preview
SCRATCH = os.environ.get("TT_SNOWY_PREVIEWS", os.path.join(T.PREVIEWS, "Snowy"))


def ground_disc(objs, colour=(0.50, 0.60, 0.74), pad=1.0, scale=1.0):
    mn, mx = T._bounds([x for o in objs for x in [o] + list(o.children_recursive)])
    r = max(mx.x - mn.x, mx.y - mn.y) * scale + pad
    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=r, depth=0.02,
                                        location=((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, -0.012))
    g = bpy.context.active_object
    g.name = "__preview_ground"
    gm = bpy.data.materials.new("__ground_snow")
    try:
        bsdf = gm.node_tree.nodes["Principled BSDF"]
        bsdf.inputs["Base Color"].default_value = (*colour, 1)
        bsdf.inputs["Roughness"].default_value = 0.9
    except Exception:
        gm.diffuse_color = (*colour, 1)
    g.data.materials.append(gm)
    return g


def preview(objs, name, size=(640, 480), high=True, dist=1.0, ground=(0.50, 0.60, 0.74)):
    g = ground_disc(objs, ground) if ground else None
    out = [T.render(objs, os.path.join(SCRATCH, name + ".png"), size=size, distance_scale=dist)]
    if high:
        out.append(T.render(objs, os.path.join(SCRATCH, name + "_High.png"), size=size, pitch_deg=50, yaw_deg=-25,
                            distance_scale=dist))
    if g is not None:
        bpy.data.objects.remove(g, do_unlink=True)
    return out
