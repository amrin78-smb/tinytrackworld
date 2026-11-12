using System.Collections.Generic;
using TinyTracks.Core;
using TinyTracks.Interaction;
using TinyTracks.Tracks;
using UnityEngine;
using UnityEngine.Rendering;

namespace TinyTracks.World
{
    /// <summary>
    /// Builds the world: Sunny Valley terrain + lake, the static dressing (farm, village, forest, windmill, ...),
    /// clouds and birds, lighting. The dressing is part of the world definition and is not saved.
    /// </summary>
    public class WorldManager : MonoBehaviour
    {
        public static WorldManager Instance { get; private set; }

        public ContentLibrary content;
        public WorldDefinition world;
        public Light sun;

        private Transform root;
        private readonly List<GameObject> optional = new List<GameObject>();

        public Vector2 BuildableHalfSize => world != null ? world.buildableHalfSize : new Vector2(30f, 22f);

        private void Awake()
        {
            Instance = this;
            if (world == null && content != null && content.worlds.Count > 0) world = content.worlds[0];
            Build();
        }

        public void Build()
        {
            if (root != null) Destroy(root.gameObject);
            root = new GameObject("World").transform;
            root.SetParent(transform, false);
            TerrainGenerator.Settings s = TerrainGenerator.SunnyValley;

            var terrain = new GameObject("Terrain");
            terrain.transform.SetParent(root, false);
            terrain.AddComponent<MeshFilter>().sharedMesh = TerrainGenerator.Build(s);
            var tr = terrain.AddComponent<MeshRenderer>();
            tr.sharedMaterial = content.toyMaterial;
            tr.shadowCastingMode = ShadowCastingMode.Off;
            terrain.isStatic = true;

            var lake = new GameObject("Lake");
            lake.transform.SetParent(root, false);
            lake.AddComponent<MeshFilter>().sharedMesh = TerrainGenerator.BuildLake(s);
            var lr = lake.AddComponent<MeshRenderer>();
            lr.sharedMaterial = content.waterMaterial;
            lr.shadowCastingMode = ShadowCastingMode.Off;

            if (world != null)
            {
                foreach (WorldProp p in world.props)
                {
                    DecorationDefinition d = content.Decoration(p.decorationId);
                    if (d == null || d.prefab == null) continue;
                    float y = TerrainGenerator.Height(s, p.position.x, p.position.z);
                    GameObject go = Instantiate(d.prefab, root, false);
                    go.name = "Prop_" + d.id;
                    go.transform.SetPositionAndRotation(new Vector3(p.position.x, Mathf.Max(0f, y) + p.position.y, p.position.z), Quaternion.Euler(0f, p.yaw, 0f));
                    if (p.scale > 0f && !Mathf.Approximately(p.scale, 1f)) go.transform.localScale = Vector3.one * p.scale;
                    if (d.category == DecorationCategory.Nature && d.id.StartsWith("Cloud"))
                    {
                        AmbientAnimator.AddDrifter(go.transform, new Vector3(Random.Range(0.4f, 0.9f), 0f, 0f), 110f);
                        foreach (Renderer r in go.GetComponentsInChildren<Renderer>()) r.shadowCastingMode = ShadowCastingMode.Off;
                    }
                    else if (d.reaction == TapReaction.Bird)
                    {
                        AmbientAnimator.AddFlyer(go.transform, p.position, Random.Range(10f, 18f), Random.Range(7f, 10f), Random.Range(3f, 5f));
                    }
                    if (d.lowDetailOptional) optional.Add(go);
                }
            }
            ApplyLighting();
        }

        public void SetLowDetail(bool low)
        {
            // Drop every other optional prop (grass tufts, flowers, extra trees) on Low.
            for (int i = 0; i < optional.Count; i++) if (optional[i] != null) optional[i].SetActive(!low || i % 2 == 0);
        }

        private void ApplyLighting()
        {
            if (world == null) return;
            RenderSettings.ambientMode = AmbientMode.Trilight;
            RenderSettings.ambientSkyColor = world.ambientSky;
            RenderSettings.ambientEquatorColor = world.ambientEquator;
            RenderSettings.ambientGroundColor = world.ambientGround;
            RenderSettings.fog = true;
            RenderSettings.fogMode = FogMode.Linear;
            RenderSettings.fogColor = world.fogColor;
            RenderSettings.fogStartDistance = 70f;
            RenderSettings.fogEndDistance = 190f;
            if (sun != null)
            {
                sun.color = world.sunColor;
                sun.transform.rotation = Quaternion.Euler(world.sunEuler);
            }
        }

        /// <summary>The ready-to-play starter railway for a new world: an oval with a station.</summary>
        public static void BuildStarterLayout(TrackNetworkManager net)
        {
            TrackGraph g = net.Graph;
            TrackNode cur = net.Place(TrackType.Station, new TrackPose(new Vector3(-5f, 0f, -8f), 90f));
            TrackType[] seq =
            {
                TrackType.Straight, TrackType.TightLeft, TrackType.TightLeft,
                TrackType.Straight, TrackType.Straight, TrackType.ShortStraight,
                TrackType.TightLeft, TrackType.TightLeft,
            };
            foreach (TrackType t in seq)
            {
                TrackPose pose = TrackSnapping.PoseForAttachment(TrackShapeLibrary.Get(t), 0, cur.worldConnectorPos[1], cur.worldConnectorHeading[1]);
                cur = net.Place(t, pose);
                if (cur == null) break;
            }
        }
    }
}
