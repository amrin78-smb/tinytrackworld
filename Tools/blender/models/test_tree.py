import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import tt_common as T
T.reset()
trunk = T.cyl("trunk", 0.18, 1.2, loc=(0, 0, 0.6), material="bark", verts=12, radius_top=0.12)
c1 = T.ico("c1", 0.9, loc=(0, 0, 1.7), material="leaf", subdiv=2, jitter=0.08, seed=1)
c2 = T.ico("c2", 0.6, loc=(0.4, -0.2, 2.3), material="leaf_light", subdiv=2, jitter=0.08, seed=2)
tree = T.join([trunk, c1, c2], "TestTree")
T.finalize([tree])
T.export_fbx("_Test/TestTree", [tree])
T.render([tree], T.preview_path("TestTree"))
