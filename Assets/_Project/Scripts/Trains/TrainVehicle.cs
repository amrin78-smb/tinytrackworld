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
                    if (t.name.StartsWith("Wheel")) v.wheels.Add(t);
                    else if (t.name == "SmokePoint") v.smokePoint = t;
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
            foreach (Transform c in t.GetComponentsInChildren<Transform>(true)) if (c.name == name) return c;
            return null;
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
