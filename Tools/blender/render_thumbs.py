"""
Renders toolbar thumbnails (256x256, transparent) of every exported model, exactly as they look in game (baked
vertex colours). Tracks: high top-down 3/4 view; everything else: 3/4 front view.
Usage: blender -b --factory-startup --python Tools/blender/render_thumbs.py -- [Group/Name ...]
Output: Assets/_Project/Art/UI/Thumbs/<Name>.png  (tracks: Track_<Type>.png)
"""
import glob
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
import tt_common as T  # noqa: E402

OUT = os.path.join(T.REPO, "Assets", "_Project", "Art", "UI", "Thumbs")
GROUPS = ["Tracks", "Trains", "Animals", "People", "Nature", "Buildings", "Props"]


def import_fbx(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=path)
    objs = [o for o in bpy.data.objects if o not in before]
    for o in objs:
        if o.type == 'EMPTY':
            o.hide_render = True
    return objs


# Track pieces shown with their accessory so the toolbar picture tells them apart.
# (accessory fbx, Unity local position, Unity yaw)
ACCESSORIES = {
    "Station": [("Buildings/Station", (0, 0, 3.0), 0)],
    "Depot": [("Buildings/Depot", (0, 0, 2.1), 180)],
    "Crossing": [("Props/Barrier_Crossing", (1.0, 0, 0.5), 90), ("Props/Barrier_Crossing", (-1.0, 0, 3.5), -90)],
}


def add_accessories(name):
    out = []
    for rel, (x, y, z), yaw in ACCESSORIES.get(name, []):
        p = os.path.join(T.MODELS, rel + ".fbx")
        if not os.path.exists(p):
            continue
        objs = import_fbx(p)
        for o in objs:
            if o.parent is None:
                o.location = (-x, -z, y)
                o.rotation_euler = (0, 0, math.radians(-yaw))
        out += [o for o in objs if o.type == 'MESH']
    return out


def render_one(group, path):
    T.reset()
    objs = import_fbx(path)
    if group == "Tracks":
        objs += add_accessories(os.path.splitext(os.path.basename(path))[0])
    meshes = [o for o in objs if o.type == 'MESH']
    if not meshes:
        return
    name = os.path.splitext(os.path.basename(path))[0]
    roots = [o for o in meshes if o.parent is None or o.parent.type != 'MESH']
    out = os.path.join(OUT, ("Track_" + name if group == "Tracks" else name) + ".png")
    if group == "Tracks":
        T.render(roots, out, size=(256, 256), yaw_deg=-25, pitch_deg=58, transparent=True, samples=24, distance_scale=0.95)
    elif group == "Trains":
        T.render(roots, out, size=(256, 256), yaw_deg=-40, pitch_deg=18, transparent=True, samples=24, distance_scale=0.9)
    else:
        T.render(roots, out, size=(256, 256), yaw_deg=-28, pitch_deg=22, transparent=True, samples=24, distance_scale=0.92)


def main():
    os.makedirs(OUT, exist_ok=True)
    wanted = T.args()
    for g in GROUPS:
        for path in sorted(glob.glob(os.path.join(T.MODELS, g, "*.fbx"))):
            key = g + "/" + os.path.splitext(os.path.basename(path))[0]
            if wanted and key not in wanted and g not in wanted:
                continue
            try:
                render_one(g, path)
            except Exception as e:  # keep going; the validator reports missing icons
                print("[TT] thumb failed", key, e)


if __name__ == "__main__":
    main()
