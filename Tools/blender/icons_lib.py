"""
Tiny Tracks World - helpers for the UI button icons (Tools/blender/icons/build_icons.py).

Icons are rendered with real glossy Principled materials (not the vertex-colour look of the game models), an
orthographic camera that frames every icon to the same fill ratio, a fixed 3-light studio rig, and a soft dark
outline added in post (so the symbol reads on any button colour). Output: straight-alpha RGBA PNG.
"""
import bpy
import bmesh
import math
import os
import sys
from mathutils import Vector, Matrix, Euler

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tt_common as T

ICON_DIR = os.path.join(T.REPO, "Assets", "_Project", "Art", "UI", "Icons")
OUTLINE_RGB = (0x1C / 255, 0x22 / 255, 0x3A / 255)


# ------------------------------------------------------------------------------------------------ materials
def gm(name, hexstr=None, rough=0.28, metal=0.0, coat=0.35, emit=0.0):
    """Glossy toy material. hexstr may be a palette name or '#RRGGBB'."""
    key = "icon_" + name
    m = bpy.data.materials.get(key)
    if m is not None:
        return m
    if hexstr is None:
        hexstr = name
    if not hexstr.startswith("#"):
        hexstr = T.PALETTE[hexstr][0]
    r, g, b = T.hex_rgb(hexstr)
    lin = (T.srgb_to_linear(r), T.srgb_to_linear(g), T.srgb_to_linear(b), 1.0)
    m = bpy.data.materials.new(key)
    m.diffuse_color = lin
    try:
        m.use_nodes = True
    except Exception:
        pass
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = lin
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    for nm in ("Coat Weight", "Coat"):
        if nm in bsdf.inputs:
            bsdf.inputs[nm].default_value = coat
            break
    if "Coat Roughness" in bsdf.inputs:
        bsdf.inputs["Coat Roughness"].default_value = 0.08
    if emit > 0:
        for nm in ("Emission Color", "Emission"):
            if nm in bsdf.inputs:
                bsdf.inputs[nm].default_value = lin
                break
        if "Emission Strength" in bsdf.inputs:
            bsdf.inputs["Emission Strength"].default_value = emit
    return m


def setm(obj, material):
    if isinstance(material, str):
        material = gm(material)
    obj.data.materials.clear()
    obj.data.materials.append(material)
    return obj


# ------------------------------------------------------------------------------------------------ 2D shapes
def _v2(p):
    return Vector((p[0], p[1]))


def round_poly(points, r, segs=6):
    """Rounds every corner of a closed polygon with a quadratic-bezier fillet of (approx.) radius r."""
    pts = [_v2(p) for p in points]
    n = len(pts)
    out = []
    for i in range(n):
        a, p, b = pts[i - 1], pts[i], pts[(i + 1) % n]
        ua, ub = (a - p), (b - p)
        la, lb = ua.length, ub.length
        if la < 1e-6 or lb < 1e-6:
            continue
        ua /= la
        ub /= lb
        cosang = max(-1.0, min(1.0, ua.dot(ub)))
        ang = math.acos(cosang)
        if ang > math.radians(175) or r <= 0:
            out.append(p)
            continue
        t = r / math.tan(ang / 2)
        t = min(t, la * 0.45, lb * 0.45)
        p0, p2 = p + ua * t, p + ub * t
        for k in range(segs + 1):
            s = k / segs
            q = (1 - s) ** 2 * p0 + 2 * (1 - s) * s * p + s * s * p2
            out.append(q)
    return [(q.x, q.y) for q in out]


def circle_pts(r, n=48, cx=0.0, cy=0.0, start=0.0):
    return [(cx + r * math.cos(start + 2 * math.pi * i / n), cy + r * math.sin(start + 2 * math.pi * i / n))
            for i in range(n)]


def arc_pts(cx, cy, r, a0_deg, a1_deg, n=24):
    return [(cx + r * math.cos(math.radians(a0_deg + (a1_deg - a0_deg) * i / n)),
             cy + r * math.sin(math.radians(a0_deg + (a1_deg - a0_deg) * i / n))) for i in range(n + 1)]


def _offsets(path, w):
    """Left/right offsets (miter) of an open 2D polyline."""
    P = [_v2(p) for p in path]
    left, right = [], []
    for i in range(len(P)):
        if i == 0:
            t = (P[1] - P[0]).normalized()
            nrm = Vector((-t.y, t.x))
            m = 1.0
        elif i == len(P) - 1:
            t = (P[-1] - P[-2]).normalized()
            nrm = Vector((-t.y, t.x))
            m = 1.0
        else:
            t0 = (P[i] - P[i - 1]).normalized()
            t1 = (P[i + 1] - P[i]).normalized()
            n0 = Vector((-t0.y, t0.x))
            n1 = Vector((-t1.y, t1.x))
            nrm = (n0 + n1).normalized()
            m = 1.0 / max(0.3, nrm.dot(n0))
        left.append(P[i] + nrm * w * m)
        right.append(P[i] - nrm * w * m)
    return left, right, P


def band_poly(path, width):
    left, right, _ = _offsets(path, width / 2)
    return [(p.x, p.y) for p in left + list(reversed(right))]


def arrow_poly(path, width, head_len, head_w, tail_round=True):
    """A thick arrow following an open polyline; the head sits at the last point (tip extends beyond it)."""
    left, right, P = _offsets(path, width / 2)
    t = (P[-1] - P[-2]).normalized()
    nrm = Vector((-t.y, t.x))
    base = P[-1]
    tip = base + t * head_len
    pts = list(left)
    pts += [base + nrm * head_w / 2, tip, base - nrm * head_w / 2]
    pts += list(reversed(right))
    if tail_round:
        t0 = (P[1] - P[0]).normalized()
        n0 = Vector((-t0.y, t0.x))
        c = P[0]
        for k in range(1, 8):
            a = math.pi * k / 8
            pts.append(c - n0 * math.cos(a) * width / 2 - t0 * math.sin(a) * width / 2)
    return [(p.x, p.y) for p in pts]


# ------------------------------------------------------------------------------------------------ 3D builders
def slab(name, profile, depth, material, bevel=0.08, segs=4, loc=(0, 0, 0), rot=(0, 0, 0), y=0.0):
    """Extrudes a 2D profile (x right, z up) along Y (depth, centred) with a soft rounded bevel; faces the camera."""
    bm = bmesh.new()
    front = [bm.verts.new((p[0], -depth / 2, p[1])) for p in profile]
    back = [bm.verts.new((p[0], depth / 2, p[1])) for p in profile]
    n = len(profile)
    bm.faces.new(list(reversed(front)))
    bm.faces.new(back)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((front[i], front[j], back[j], back[i]))
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    o.location = (loc[0], loc[1] + y, loc[2])
    o.rotation_euler = Euler(rot)
    setm(o, material)
    if bevel > 0:
        mod = o.modifiers.new("bevel", 'BEVEL')
        mod.width = min(bevel, depth * 0.48)
        mod.segments = segs
        mod.limit_method = 'ANGLE'
        mod.angle_limit = math.radians(30)
        mod.use_clamp_overlap = True
        T.apply(o)
    T.smooth(o, 38)
    return o


def m(obj, material):
    """Assigns a glossy material to a tt_common primitive (they take palette materials)."""
    return setm(obj, material)


def mesh_points_world(objs):
    dg = bpy.context.evaluated_depsgraph_get()
    pts = []
    for o in objs:
        if o.type != 'MESH':
            continue
        eo = o.evaluated_get(dg)
        me = eo.to_mesh()
        mw = eo.matrix_world
        co = np.zeros(len(me.vertices) * 3, dtype=np.float64)
        me.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3)
        M = np.array(mw)
        pts.append(co @ M[:3, :3].T + M[:3, 3])
        eo.to_mesh_clear()
    return np.concatenate(pts, axis=0)


# ------------------------------------------------------------------------------------------------ render
def _setup_render(res, samples):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = samples
    try:
        sc.cycles.use_denoising = True
    except Exception:
        pass
    try:
        sc.cycles.max_bounces = 6
        sc.cycles.transparent_max_bounces = 4
    except Exception:
        pass
    sc.render.resolution_x = sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = True
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGBA'
    sc.render.image_settings.color_depth = '8'
    sc.view_settings.view_transform = 'Standard'
    sc.view_settings.look = 'None'
    sc.view_settings.exposure = 0.0
    sc.render.filter_size = 1.2
    if sc.world is None:
        sc.world = bpy.data.worlds.new("World")
    w = sc.world
    try:
        w.use_nodes = True
    except Exception:
        pass
    bg = w.node_tree.nodes.get("Background")
    if bg:
        bg.inputs[0].default_value = (0.78, 0.84, 0.95, 1.0)
        bg.inputs[1].default_value = 0.45
    return sc


def _area(name, loc, target, energy, size, color=(1, 1, 1)):
    ld = bpy.data.lights.new(name, 'AREA')
    ld.energy = energy
    ld.size = size
    ld.color = color
    lo = bpy.data.objects.new(name, ld)
    bpy.context.scene.collection.objects.link(lo)
    lo.location = loc
    d = (Vector(target) - Vector(loc))
    lo.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    return lo


def render_icon(objs, name, yaw=-20.0, pitch=14.0, fill=0.80, res=512, out_size=256, samples=32,
                outline_px=7, out_dir=None, roll=0.0):
    """Frames `objs` with an orthographic camera so the larger projected extent fills `fill` of the frame
    (outline included on top of that), lights it with the shared rig and writes <out_dir>/<name>.png."""
    out_dir = out_dir or ICON_DIR
    os.makedirs(out_dir, exist_ok=True)
    sc = _setup_render(res, samples)
    pts = mesh_points_world(objs)
    yw, pt = math.radians(yaw), math.radians(pitch)
    fwd = -Vector((math.sin(yw) * math.cos(pt), -math.cos(yw) * math.cos(pt), math.sin(pt)))  # camera looks along
    rot_q = fwd.to_track_quat('-Z', 'Y')
    if roll:
        rot_q = rot_q @ Euler((0, 0, math.radians(roll))).to_quaternion()
    R = np.array(rot_q.to_matrix())
    right, up = R[:, 0], R[:, 1]
    pr, pu = pts @ right, pts @ up
    w, h = pr.max() - pr.min(), pu.max() - pu.min()
    cr, cu = (pr.max() + pr.min()) / 2, (pu.max() + pu.min()) / 2
    centre3 = Vector(right * cr + up * cu) + Vector(pts.mean(axis=0)).dot(fwd) * fwd
    extent = max(w, h)
    cd = bpy.data.cameras.new("__icam")
    cd.type = 'ORTHO'
    # leave room for the outline: fill applies to the whole symbol+outline
    o_frac = 2.0 * outline_px / res
    cd.ortho_scale = extent / max(0.2, fill - o_frac)
    cd.clip_start = 0.01
    cd.clip_end = 200
    cam = bpy.data.objects.new("__icam", cd)
    sc.collection.objects.link(cam)
    cam.location = centre3 - fwd * 30.0
    cam.rotation_euler = rot_q.to_euler()
    sc.camera = cam
    # light rig relative to the camera so every icon is lit the same way on screen
    def cam_space(x, y, z):
        return centre3 + Vector(right) * x + Vector(up) * y - fwd * z
    s = extent
    lights = [
        _area("__key", cam_space(-1.3 * s, 1.6 * s, 2.0 * s), centre3, 200.0 * s * s, 1.6 * s),
        _area("__fill", cam_space(1.8 * s, -0.4 * s, 1.6 * s), centre3, 70.0 * s * s, 2.0 * s, (0.92, 0.95, 1.0)),
        _area("__rim", cam_space(0.9 * s, 1.2 * s, -1.6 * s), centre3, 180.0 * s * s, 1.2 * s, (1.0, 0.97, 0.9)),
    ]
    tmp = os.path.join(T.PREVIEWS, "Icons", "_raw_" + name + ".png")
    os.makedirs(os.path.dirname(tmp), exist_ok=True)
    sc.render.filepath = tmp
    bpy.ops.render.render(write_still=True)
    for lo in lights + [cam]:
        bpy.data.objects.remove(lo, do_unlink=True)
    out = os.path.join(out_dir, name + ".png")
    post_outline(tmp, out, outline_px, out_size)
    print("[TT-ICON] wrote", out)
    return out


# ------------------------------------------------------------------------------------------------ image io + post
def read_png(path):
    img = bpy.data.images.load(path, check_existing=False)
    w, h = img.size
    a = np.zeros(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(a)
    bpy.data.images.remove(img)
    return a.reshape(h, w, 4)  # rows bottom->top, sRGB values, straight alpha


def write_png(path, arr):
    h, w, _ = arr.shape
    img = bpy.data.images.new("__out", w, h, alpha=True)
    img.pixels.foreach_set(np.ascontiguousarray(arr, dtype=np.float32).ravel())
    img.filepath_raw = path
    img.file_format = 'PNG'
    img.save()
    bpy.data.images.remove(img)


def _dilate(alpha, r):
    out = alpha.copy()
    h, w = alpha.shape
    pad = np.pad(alpha, r)
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            d2 = dx * dx + dy * dy
            if d2 > r * r:
                continue
            wgt = 1.0 if d2 <= (r - 1) ** 2 else (r - math.sqrt(d2)) + 1.0
            wgt = max(0.0, min(1.0, wgt))
            out = np.maximum(out, pad[r + dy:r + dy + h, r + dx:r + dx + w] * wgt)
    return out


def _blur(a, k=1):
    h, w = a.shape
    pad = np.pad(a, k, mode='edge')
    acc = np.zeros_like(a)
    for dy in range(-k, k + 1):
        for dx in range(-k, k + 1):
            acc += pad[k + dy:k + dy + h, k + dx:k + dx + w]
    return acc / (2 * k + 1) ** 2


def post_outline(src, dst, r, out_size):
    a = read_png(src)
    rgb, al = a[..., :3], a[..., 3]
    ol = _blur(_dilate(np.clip(al * 1.6, 0, 1), r), 1) * 0.92
    # drop a slightly offset shadow-ish lower outline for depth
    sh = np.zeros_like(ol)
    off = max(1, r // 2)
    sh[:-off, :] = ol[off:, :]  # rows are bottom->top, so this shifts down
    ol = np.maximum(ol, sh * 0.9)
    out_a = al + ol * (1 - al)
    oc = np.array(OUTLINE_RGB, dtype=np.float32)
    prem = rgb * al[..., None] + oc * (ol * (1 - al))[..., None]
    # downsample (box) in premultiplied space
    f = a.shape[0] // out_size
    if f > 1:
        H = out_size
        prem = prem.reshape(H, f, H, f, 3).mean(axis=(1, 3))
        out_a = out_a.reshape(H, f, H, f).mean(axis=(1, 3))
    col = np.where(out_a[..., None] > 1e-4, prem / np.maximum(out_a[..., None], 1e-4), 0)
    res = np.concatenate([np.clip(col, 0, 1), np.clip(out_a, 0, 1)[..., None]], axis=-1)
    write_png(dst, res)


def contact_sheet(names, src_dir, dst, cols=6, cell=256, small=96, bg=(0.30, 0.52, 0.86)):
    """Sheet: each icon at full size on a blue rounded-square cell plus a 96px copy, to judge readability."""
    rows = math.ceil(len(names) / cols)
    pad = 16
    cw = cell + pad
    chh = cell + small + pad * 2
    W, H = cols * cw + pad, rows * chh + pad
    sheet = np.zeros((H, W, 4), dtype=np.float32)
    sheet[..., :3] = (0.93, 0.94, 0.97)
    sheet[..., 3] = 1
    bgc = np.array(bg, dtype=np.float32)
    alt = [np.array(c, dtype=np.float32) for c in [(0.30, 0.52, 0.86), (0.98, 0.62, 0.20), (0.36, 0.74, 0.40)]]
    for i, n in enumerate(names):
        p = os.path.join(src_dir, n + ".png")
        if not os.path.exists(p):
            continue
        img = read_png(p)[::-1]  # top->bottom
        r, c = divmod(i, cols)
        y0, x0 = pad + r * chh, pad + c * cw
        sheet[y0:y0 + cell, x0:x0 + cell, :3] = bgc
        a = img[..., 3:4]
        sheet[y0:y0 + cell, x0:x0 + cell, :3] = img[..., :3] * a + bgc * (1 - a)
        # small version (box filter) on a rotating button colour
        f = cell / small
        idx = (np.arange(small) * f).astype(int)
        sm = np.zeros((small, small, 4), dtype=np.float32)
        k = int(round(f))
        for dy in range(k):
            for dx in range(k):
                yy = np.clip(idx + dy, 0, cell - 1)
                xx = np.clip(idx + dx, 0, cell - 1)
                blk = img[yy][:, xx]
                sm[..., :3] += blk[..., :3] * blk[..., 3:4]
                sm[..., 3] += blk[..., 3]
        sm /= k * k
        col = alt[i % len(alt)]
        ys, xs = y0 + cell + pad // 2, x0 + (cell - small) // 2
        circle = np.zeros((small, small), dtype=np.float32)
        yy, xx = np.mgrid[0:small, 0:small]
        rr = np.sqrt((yy - small / 2 + 0.5) ** 2 + (xx - small / 2 + 0.5) ** 2)
        circle = np.clip(small / 2 - rr, 0, 1)
        base = sheet[ys:ys + small, xs:xs + small, :3]
        base = base * (1 - circle[..., None]) + col * circle[..., None]
        base = sm[..., :3] + base * (1 - sm[..., 3:4])
        sheet[ys:ys + small, xs:xs + small, :3] = base
    write_png(dst, sheet[::-1])
    print("[TT-ICON] sheet", dst)
