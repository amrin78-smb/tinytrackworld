"""
Renders the game's branding with Blender (Cycles):

* Logo.png: "Tiny Tracks World" in chunky 3D word-art. The letters are rainbow-coloured with a white outline and
  a navy shadow, and the red locomotive rides a rail under "World". The background is transparent. It is used for
  the Unity splash screen and the main-menu title.
* AppIcon.png (1024, full square), AppIcon_Round.png (circle), AppIcon_Fg.png / AppIcon_Bg.png (Android adaptive
  layers, 432 px). The icon shows the red locomotive in 3/4 view on the rails, on a green hill, under a sky.

Usage: blender -b --factory-startup --python Tools/blender/branding/build_branding.py -- [logo] [icon]
Output: Assets/_Project/Art/UI/Branding/
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402
import tt_common as T  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(HERE, "Fredoka-SemiBold.ttf")
OUT = os.path.join(T.REPO, "Assets", "_Project", "Art", "UI", "Branding")
TMP = os.path.join(T.REPO, "Temp", "branding")
TRAIN = os.path.join(T.MODELS, "Trains", "Loco_RedExpress.fbx")
RAIL = os.path.join(T.MODELS, "Tracks", "Straight.fbx")

RAINBOW = ["#FF4D4D", "#FF9A1F", "#FFD21F", "#4CC94C", "#2EA8FF", "#9B5CFF"]
OUTLINE = "#FFFFFF"
SHADOW = "#1F3A75"


# ------------------------------------------------------------------------------------------------ helpers
def lin(hexstr):
    r, g, b = T.hex_rgb(hexstr)
    return (T.srgb_to_linear(r), T.srgb_to_linear(g), T.srgb_to_linear(b), 1.0)


def glossy(name, hexstr, rough=0.32, emission=0.0):
    m = bpy.data.materials.new(name)
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = lin(hexstr)
    bsdf.inputs["Roughness"].default_value = rough
    if emission > 0:
        bsdf.inputs["Emission Color"].default_value = lin(hexstr)
        bsdf.inputs["Emission Strength"].default_value = emission
    return m


def vcol_material():
    m = bpy.data.materials.new("__vcol")
    nt = m.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    attr = nt.nodes.new("ShaderNodeVertexColor")
    attr.layer_name = "Col"
    nt.links.new(attr.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.55
    return m


def import_fbx(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=path)
    objs = [o for o in bpy.data.objects if o not in before]
    vm = bpy.data.materials.get("__vcol") or vcol_material()
    for o in objs:
        if o.type == 'EMPTY':
            o.hide_render = True
        if o.type == 'MESH' and "Col" in o.data.color_attributes:
            o.data.materials.clear()
            o.data.materials.append(vm)
    roots = [o for o in objs if o.parent is None]
    return roots, objs


def group(objs, name):
    """Parents the given root objects to one empty so they can be moved together."""
    e = bpy.data.objects.new(name, None)
    T._link(e)
    for o in objs:
        o.parent = e
    return e


def bounds(objs):
    bpy.context.view_layer.update()
    pts = []
    for o in objs:
        for x in [o] + list(o.children_recursive):
            if x.type in ('MESH', 'FONT') and not x.hide_render:
                for c in x.bound_box:
                    pts.append(x.matrix_world @ Vector(c))
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return mn, mx


def text(body, size, mats, extrude, bevel, offset=0.0, name="Text"):
    cu = bpy.data.curves.new(name, 'FONT')
    cu.body = body
    cu.font = bpy.data.fonts.load(FONT, check_existing=True)
    cu.size = size
    cu.align_x = 'CENTER'
    cu.align_y = 'CENTER'
    cu.extrude = extrude
    cu.bevel_depth = bevel
    cu.bevel_resolution = 4
    cu.offset = offset
    cu.space_character = 1.04
    ob = T._link(bpy.data.objects.new(name, cu))
    for m in mats:
        cu.materials.append(m)
    if len(mats) > 1:
        letter = 0
        for i, ch in enumerate(body):
            if ch.strip():
                cu.body_format[i].material_index = letter % len(mats)
                letter += 1
    # stand the text up so it faces the camera (-Y)
    ob.rotation_euler = (math.radians(90), 0, 0)
    return ob


def word_art(body, size, z, tilt_deg=0.0):
    """One line of chunky rainbow letters. The bevel is a mesh Bevel modifier with overlap clamping: Blender's curve
    bevel throws long spikes from sharp corners in some Fredoka glyphs ("a", "n"). The white outline and navy shadow
    are drawn in 2D on the rendered image (see outline())."""
    letters = [glossy(f"L{i}", h) for i, h in enumerate(RAINBOW)]
    ob = text(body, size, letters, extrude=0.11 * size, bevel=0.0, name=body)
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.convert(target='MESH')
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(threshold=0.0005)
    bpy.ops.mesh.dissolve_degenerate()
    bpy.ops.object.mode_set(mode='OBJECT')
    ob.select_set(False)
    bev = ob.modifiers.new("bevel", 'BEVEL')
    bev.width = 0.045 * size
    bev.segments = 5
    bev.limit_method = 'ANGLE'
    bev.angle_limit = math.radians(50)
    bev.use_clamp_overlap = True
    bev.harden_normals = False
    for p in ob.data.polygons:
        p.use_smooth = True
    ob.location = (0, 0, z)
    ob.rotation_euler.y = math.radians(tilt_deg)
    return [ob]


def camera(target, direction, distance, lens=50, ortho_scale=None):
    cd = bpy.data.cameras.new("cam")
    cd.lens = lens
    if ortho_scale:
        cd.type = 'ORTHO'
        cd.ortho_scale = ortho_scale
    cam = T._link(bpy.data.objects.new("cam", cd))
    d = Vector(direction).normalized()
    cam.location = Vector(target) + d * distance
    cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
    bpy.context.scene.camera = cam
    return cam


def lights(sky=(0.62, 0.8, 1.0), sky_strength=0.9, sun_energy=3.5):
    sc = bpy.context.scene
    sc.world.use_nodes = True
    bg = sc.world.node_tree.nodes.get("Background")
    bg.inputs[0].default_value = (*sky, 1.0)
    bg.inputs[1].default_value = sky_strength
    sd = bpy.data.lights.new("sun", 'SUN')
    sd.energy = sun_energy
    sd.angle = math.radians(10)
    sun = T._link(bpy.data.objects.new("sun", sd))
    sun.rotation_euler = (math.radians(38), math.radians(12), math.radians(-30))


def setup_render(w, h, samples=96, transparent=True):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.cycles.device = 'CPU'
    sc.render.resolution_x, sc.render.resolution_y = w, h
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = transparent
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGBA'
    sc.view_settings.view_transform = 'Standard'
    sc.view_settings.look = 'None'


def shoot(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("[TT] rendered", path)


def rails(count, spacing=None, yaw_deg=0.0):
    """A straight run of the game's own Straight track pieces laid end to end along the piece's long axis."""
    pieces = []
    step, axis = None, 0
    for i in range(count):
        roots, _ = import_fbx(RAIL)
        g = group(roots, f"rail{i}")
        if step is None:
            mn, mx = bounds([g])
            size = mx - mn
            axis = 0 if size.x >= size.y else 1
            step = size[axis] * 0.995
        off = [0.0, 0.0, 0.0]
        off[axis] = (i - (count - 1) / 2) * step
        g.location = off
        pieces.append(g)
    g = group(pieces, "rails")
    g["axis"] = axis
    g.rotation_euler.z = math.radians(yaw_deg + (90 if axis == 1 else 0))  # long axis -> X
    return g


# ------------------------------------------------------------------------------------------------ logo
def build_logo():
    T.reset()
    setup_render(1600, 860, samples=128)
    lights(sky=(0.85, 0.9, 1.0), sky_strength=0.8, sun_energy=3.6)

    top = word_art("Tiny Tracks", 1.0, 0.62, tilt_deg=-2.0)
    bottom = word_art("World", 1.0, -0.42, tilt_deg=1.5)

    # The red locomotive on a short rail run under "World", heading right.
    roots, _ = import_fbx(TRAIN)
    loco = group(roots, "loco")
    mn, mx = bounds([loco])
    length = max(mx.x - mn.x, mx.y - mn.y)
    s = 1.45 / length
    loco.scale = (s, s, s)
    track = rails(1, 4.0)
    ts = s * 0.62
    track.scale = (ts, ts, ts)
    bpy.context.view_layer.update()
    # Blender import: the loco's front is -Y. Turn it so it drives to the right (+X) with a little 3/4.
    loco.rotation_euler.z = math.radians(90 - 28)
    track.rotation_euler.z = math.radians(90 - 28)
    bpy.context.view_layer.update()
    tmn, tmx = bounds([track])
    track.location += Vector((-(tmn.x + tmx.x) / 2 + 2.05, 0.6, -1.15 - tmn.z))
    bpy.context.view_layer.update()
    lmn, lmx = bounds([loco])
    tmn, tmx = bounds([track])
    loco.location += Vector((2.05 - (lmn.x + lmx.x) / 2, 0.6 - (lmn.y + lmx.y) / 2, tmx.z - lmn.z - 0.01))
    bpy.context.view_layer.update()
    lmn, lmx = bounds([loco])
    tmn, tmx = bounds([track])
    track.location.x += (lmn.x + lmx.x) / 2 - (tmn.x + tmx.x) / 2

    mn, mx = bounds(top + bottom + [loco, track])
    centre = (mn + mx) / 2
    view = Vector((0.0, -1.0, 0.12)).normalized()
    camera(centre, view, 30.0, lens=50)
    cam = bpy.context.scene.camera
    span = max((mx.x - mn.x) * 1.16, (mx.z - mn.z) * 1.16 * 1600 / 860)
    cam.location = centre + view * (span / 2 / (18 / 50))
    text_png = os.path.join(TMP, "logo_text.png")
    train_png = os.path.join(TMP, "logo_train.png")
    for o in [loco, track]:
        for x in [o] + list(o.children_recursive):
            x.hide_render = True
    shoot(text_png)
    for o in [loco, track]:
        for x in [o] + list(o.children_recursive):
            x.hide_render = x.type == 'EMPTY'
    for o in top + bottom:
        o.hide_render = True
    shoot(train_png)
    out = os.path.join(OUT, "Logo.png")
    txt = load_px(text_png)
    art = outline(txt, rim=13, rim_hex=OUTLINE, shadow=(9, -11), shadow_hex=SHADOW)
    art = over(load_px(train_png), art)
    save_px(art, out)
    trim_alpha(out, pad=12)


# ------------------------------------------------------------------------------------------------ icon
def icon_scene(foreground_only=False, background_only=False):
    T.reset()
    setup_render(1024, 1024, samples=128, transparent=foreground_only)
    lights(sky=(0.45, 0.72, 1.0), sky_strength=1.0, sun_energy=3.6)
    objs = []
    if not foreground_only:
        # rolling green hill
        hill = T.sphere("hill", 1.0, loc=(1.5, 2.0, -10.02), segs=96, rings=48, scale=(16, 16, 10))
        hill.data.materials.append(glossy("grass", "#6CCB5F", 0.8))
        objs.append(hill)
        # a couple of puffy clouds
        for i, (x, z, r) in enumerate([(-2.6, 3.4, 0.55), (2.4, 3.9, 0.45)]):
            for j, (dx, dz, k) in enumerate([(0, 0, 1.0), (0.55, -0.1, 0.8), (-0.55, -0.12, 0.75)]):
                c = T.sphere(f"cloud{i}{j}", r * k, loc=(x + dx * r, 6.0, z + dz * r), segs=24, rings=12)
                c.data.materials.append(glossy("cloud", "#FFFFFF", 0.9, emission=0.25))
    if background_only:
        return objs, None
    roots, _ = import_fbx(TRAIN)
    loco = group(roots, "loco")
    track = rails(3)
    bpy.context.view_layer.update()
    lmn, lmx = bounds([loco])
    if lmx.y - lmn.y > lmx.x - lmn.x:  # make the locomotive run along X too
        loco.rotation_euler.z = math.radians(90)
        bpy.context.view_layer.update()
        lmn, lmx = bounds([loco])
    tmn, tmx = bounds([track])
    loco.location += Vector((-(lmn.x + lmx.x) / 2, -(lmn.y + lmx.y) / 2, tmx.z - lmn.z - 0.01))
    track.location += Vector((-(tmn.x + tmx.x) / 2, -(tmn.y + tmx.y) / 2, -tmn.z))
    bpy.context.view_layer.update()
    return objs, loco


ICON_VIEW = (1.0, -0.9, 0.42)  # front 3/4: the face is at +X


def build_icon():
    # 1) full square icon (legacy + store)
    objs, loco = icon_scene()
    camera((0, 0, 0), ICON_VIEW, 12.0, lens=50)
    fit_camera(loco, margin=1.1, lift=0.08)
    shoot(os.path.join(OUT, "AppIcon.png"))
    cam_state = (bpy.context.scene.camera.location.copy(), bpy.context.scene.camera.rotation_euler.copy())

    # 2) adaptive foreground: the train only, transparent, inside the 66/108 safe circle Android never crops
    objs, loco = icon_scene(foreground_only=True)
    camera((0, 0, 0), ICON_VIEW, 12.0, lens=50)
    fit_camera(loco, margin=1.5, lift=0.0)
    setup_render(432, 432, samples=128, transparent=True)
    shoot(os.path.join(OUT, "AppIcon_Fg.png"))

    # 3) adaptive background: sky and hill only, same camera as the square icon
    icon_scene(background_only=True)
    cd = bpy.data.cameras.new("cam")
    cam = T._link(bpy.data.objects.new("cam", cd))
    cam.location, cam.rotation_euler = cam_state
    bpy.context.scene.camera = cam
    setup_render(432, 432, samples=64, transparent=False)
    shoot(os.path.join(OUT, "AppIcon_Bg.png"))

    round_crop(os.path.join(OUT, "AppIcon.png"), os.path.join(OUT, "AppIcon_Round.png"))


def fit_camera(target, margin=1.4, lift=0.0):
    """Moves the scene camera along its view axis so the target's bounding sphere fills the frame / margin."""
    cam = bpy.context.scene.camera
    mn, mx = bounds([target])
    centre = (mn + mx) / 2
    radius = (mx - mn).length / 2
    fov = 2 * math.atan(18 / cam.data.lens)
    d = radius * margin / math.tan(fov / 2)
    fwd = cam.rotation_euler.to_matrix() @ Vector((0, 0, -1))
    cam.location = centre - fwd * d
    cam.location.z -= lift * radius  # aim slightly above the centre: leaves sky over the chimney


# ------------------------------------------------------------------------------------------------ image post
def load_px(path):
    img = bpy.data.images.load(path, check_existing=False)
    w, h = img.size
    px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)
    bpy.data.images.remove(img)
    return px


def save_px(px, path):
    h, w, _ = px.shape
    img = bpy.data.images.new("out", w, h, alpha=True)
    img.pixels[:] = px.ravel()
    img.filepath_raw = path
    img.file_format = 'PNG'
    img.save()
    bpy.data.images.remove(img)


def over(top, bottom):
    """Premultiplied-free "top over bottom" for straight-alpha RGBA arrays."""
    ta, ba = top[:, :, 3:4], bottom[:, :, 3:4]
    a = ta + ba * (1 - ta)
    rgb = (top[:, :, :3] * ta + bottom[:, :, :3] * ba * (1 - ta)) / np.maximum(a, 1e-6)
    return np.concatenate([rgb, a], axis=2)


def dilate(alpha, r):
    out = alpha.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            d = math.hypot(dx, dy)
            if d > r + 0.5 or (dx == 0 and dy == 0):
                continue
            w = min(1.0, r + 0.5 - d)  # soft rim edge
            out = np.maximum(out, np.roll(np.roll(alpha, dy, axis=0), dx, axis=1) * w)
    return out


def flat(alpha, hexstr):
    r, g, b = T.hex_rgb(hexstr)  # PNG pixels from bpy are sRGB values
    h, w = alpha.shape
    px = np.empty((h, w, 4), dtype=np.float32)
    px[:, :, 0], px[:, :, 1], px[:, :, 2] = r, g, b
    px[:, :, 3] = alpha
    return px


def outline(px, rim, rim_hex, shadow, shadow_hex):
    """Sticker-style word-art: a rim around the shape, and the rimmed shape again, offset, as a drop shadow.
    shadow = (dx, dy) in pixels (+dy is up: Blender images are stored bottom row first)."""
    a = px[:, :, 3]
    rim_a = dilate(a, rim)
    sh = np.roll(np.roll(rim_a, shadow[1], axis=0), shadow[0], axis=1)
    art = over(flat(rim_a, rim_hex), flat(sh, shadow_hex))
    return over(px, art)


def trim_alpha(path, pad=8):
    px = load_px(path)
    ys, xs = np.where(px[:, :, 3] > 0.02)
    y0, y1 = max(ys.min() - pad, 0), min(ys.max() + pad + 1, px.shape[0])
    x0, x1 = max(xs.min() - pad, 0), min(xs.max() + pad + 1, px.shape[1])
    save_px(px[y0:y1, x0:x1].copy(), path)
    print("[TT] trimmed", path, x1 - x0, "x", y1 - y0)


def round_crop(src, dst):
    px = load_px(src)
    h, w, _ = px.shape
    yy, xx = np.mgrid[0:h, 0:w]
    r = w / 2
    d = np.sqrt((xx + 0.5 - r) ** 2 + (yy + 0.5 - r) ** 2)
    a = np.clip(r - d, 0, 1)
    px[:, :, 3] *= a
    save_px(px, dst)


def main():
    what = T.args() if hasattr(T, "args") else []
    what = what or ["logo", "icon"]
    if "logo" in what:
        build_logo()
    if "icon" in what:
        build_icon()


main()
