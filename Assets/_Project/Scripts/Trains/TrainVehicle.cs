using System.Collections.Generic;
using TinyTracks.Core;
using UnityEngine;

namespace TinyTracks.Trains
{
    /// <summary>One locomotive or carriage instance: wheels to spin and the measurements used to put it on the track.</summary>
    public class TrainVehicle : MonoBehaviour
    {
        public TrainDefinition definition;
        public Transform body;
        public Transform smokePoint;
        /// <summary>Cargo wagon: where loaded cargo sits (empty "CargoBed"; null on other vehicles).</summary>
        public Transform cargoBed;
        /// <summary>Passenger carriage: door points on each side ("DoorL"/"DoorR").</summary>
        public readonly List<Transform> doors = new List<Transform>();
        public bool IsPassengerCar => definition != null && definition.kind == VehicleKind.Carriage && definition.id.Contains("Passenger");
        public bool IsCargoCar => definition != null && definition.kind == VehicleKind.Carriage && definition.id.Contains("Cargo");
        public readonly List<Transform> wheels = new List<Transform>();
        public float wheelRadius = 0.18f;
        /// <summary>Midpoint of the BogieFront/BogieRear empties in vehicle space (the point that rides on the track).</summary>
        public Vector3 bogieMidLocal;

        public float Length => definition != null ? definition.length : 2f;
        public float FrontOverhang => definition != null ? definition.frontOverhang : 0.4f;
        public float BogieSpacing => definition != null ? definition.bogieSpacing : 1.2f;
        public float RearOverhang => Mathf.Max(0f, Length - FrontOverhang - BogieSpacing);

        private float wheelAngle;

        public static TrainVehicle Create(TrainDefinition def, Transform parent)
        {
            var go = new GameObject(def != null ? def.id : "Vehicle");
            go.transform.SetParent(parent, false);
            TrainVehicle v = go.AddComponent<TrainVehicle>();
            v.definition = def;
            if (def != null && def.prefab != null)
            {
                GameObject model = Instantiate(def.prefab, go.transform, false);
                model.name = "Model";
                v.body = model.transform;
                foreach (Transform t in model.GetComponentsInChildren<Transform>(true))
                {
                    string n = BaseName(t.name);
                    if (n.StartsWith("Wheel")) v.wheels.Add(t);
                    else if (n == "SmokePoint") v.smokePoint = t;
                    else if (n == "CargoBed") v.cargoBed = t;
                    else if (n == "DoorL" || n == "DoorR") v.doors.Add(t);
                }
                Transform bf = FindDeep(model.transform, "BogieFront"), br = FindDeep(model.transform, "BogieRear");
                if (bf != null && br != null)
                {
                    Vector3 a = go.transform.InverseTransformPoint(bf.position), b = go.transform.InverseTransformPoint(br.position);
                    v.bogieMidLocal = new Vector3(0f, (a.y + b.y) * 0.5f, (a.z + b.z) * 0.5f);
                }
                if (v.wheels.Count > 0)
                {
                    Renderer r = v.wheels[0].GetComponent<Renderer>();
                    if (r != null) v.wheelRadius = Mathf.Max(0.08f, r.bounds.extents.y);
                }
            }
            // Tap target for whistles.
            BoxCollider bc = go.AddComponent<BoxCollider>();
            bc.size = new Vector3(1.1f, 1.5f, def != null ? def.length : 2f);
            bc.center = new Vector3(0f, 0.75f, 0f);
            return v;
        }

        private static Transform FindDeep(Transform t, string name)
        {
            foreach (Transform c in t.GetComponentsInChildren<Transform>(true)) if (BaseName(c.name) == name) return c;
            return null;
        }

        /// <summary>
        /// Marker name without Blender's duplicate suffix: several train models were exported with empties named
        /// "BogieFront.001", "SmokePoint.002"... (built in one Blender session), which exact-name lookups missed.
        /// </summary>
        private readonly List<(MeshFilter filter, Mesh original)> painted = new List<(MeshFilter, Mesh)>();

        /// <summary>
        /// Repaints the body (vertices whose uv2.x mask is 1) in <paramref name="colour"/>, keeping the baked shading:
        /// each masked vertex colour was body colour × AO, so the AO is recovered and re-applied to the new colour.
        /// Works on mesh copies (the shared model is untouched). Pass null to restore the original paint.
        /// </summary>
        public void Paint(Color? colour)
        {
            if (body == null || definition == null || definition.paintColor.a <= 0f) return;
            foreach (MeshFilter mf in body.GetComponentsInChildren<MeshFilter>(true))
            {
                int idx = painted.FindIndex(p => p.filter == mf);
                Mesh original = idx >= 0 ? painted[idx].original : mf.sharedMesh;
                if (original == null) continue;
                if (colour == null)
                {
                    if (idx >= 0) { Destroy(mf.sharedMesh); mf.sharedMesh = original; painted.RemoveAt(idx); }
                    continue;
                }
                if (!original.isReadable) continue;
                var mask = new List<Vector2>();
                original.GetUVs(1, mask);
                if (mask.Count == 0) continue;
                Color32[] cols = original.colors32;
                if (cols == null || cols.Length != mask.Count) continue;
                Color baseCol = definition.paintColor;
                float baseLum = Mathf.Max(0.05f, baseCol.r * 0.3f + baseCol.g * 0.59f + baseCol.b * 0.11f);
                Color target = colour.Value;
                bool any = false;
                for (int i = 0; i < cols.Length; i++)
                {
                    if (mask[i].x < 0.5f) continue;
                    any = true;
                    Color32 c = cols[i];
                    float lum = (c.r * 0.3f + c.g * 0.59f + c.b * 0.11f) / 255f;
                    float ao = Mathf.Clamp(lum / baseLum, 0.25f, 1.25f);
                    cols[i] = new Color32((byte)Mathf.Clamp(target.r * ao * 255f, 0f, 255f), (byte)Mathf.Clamp(target.g * ao * 255f, 0f, 255f),
                        (byte)Mathf.Clamp(target.b * ao * 255f, 0f, 255f), c.a);
                }
                if (!any) continue;
                Mesh copy = idx >= 0 ? mf.sharedMesh : Instantiate(original);
                copy.name = original.name + " (painted)";
                copy.colors32 = cols;
                mf.sharedMesh = copy;
                if (idx < 0) painted.Add((mf, original));
            }
        }

        private void OnDestroy()
        {
            foreach (var p in painted) if (p.filter != null && p.filter.sharedMesh != p.original) Destroy(p.filter.sharedMesh);
        }

        public static string BaseName(string n)
        {
            int dot = n.LastIndexOf('.');
            return dot > 0 && dot < n.Length - 1 && char.IsDigit(n[dot + 1]) ? n.Substring(0, dot) : n;
        }

        /// <summary>Spins every wheel for a distance travelled (positive = forward for this vehicle).</summary>
        public void Roll(float distance)
        {
            if (wheels.Count == 0) return;
            wheelAngle = (wheelAngle + distance / wheelRadius * Mathf.Rad2Deg) % 360f;
            Quaternion q = Quaternion.Euler(wheelAngle, 0f, 0f);
            foreach (Transform w in wheels) w.localRotation = q;
        }
    }
}
