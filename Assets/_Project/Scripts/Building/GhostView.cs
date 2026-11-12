using UnityEngine;
using UnityEngine.Rendering;

namespace TinyTracks.Building
{
    /// <summary>A translucent placement preview built from any prefab: green when valid, red when not.</summary>
    public class GhostView
    {
        private static readonly int BaseColor = Shader.PropertyToID("_BaseColor");
        private static Material validMat, invalidMat;

        public GameObject Root { get; private set; }
        public bool Valid { get; private set; } = true;
        private Renderer[] renderers;

        public static readonly Color ValidColour = new Color(0.35f, 1f, 0.45f, 0.5f);
        public static readonly Color InvalidColour = new Color(1f, 0.35f, 0.35f, 0.5f);

        public GhostView(GameObject prefab, Material ghostTemplate, string name = "Ghost")
        {
            if (validMat == null && ghostTemplate != null)
            {
                validMat = new Material(ghostTemplate) { name = "GhostValid" };
                validMat.SetColor(BaseColor, ValidColour);
                invalidMat = new Material(ghostTemplate) { name = "GhostInvalid" };
                invalidMat.SetColor(BaseColor, InvalidColour);
            }
            Root = new GameObject(name);
            if (prefab != null)
            {
                GameObject model = Object.Instantiate(prefab, Root.transform, false);
                foreach (Collider c in model.GetComponentsInChildren<Collider>(true)) Object.Destroy(c);
                foreach (MonoBehaviour mb in model.GetComponentsInChildren<MonoBehaviour>(true)) mb.enabled = false;
            }
            renderers = Root.GetComponentsInChildren<Renderer>(true);
            foreach (Renderer r in renderers) r.shadowCastingMode = ShadowCastingMode.Off;
            SetValid(true, true);
        }

        public void Add(GameObject extraPrefab, Vector3 localPos, float yaw)
        {
            if (extraPrefab == null) return;
            GameObject e = Object.Instantiate(extraPrefab, Root.transform, false);
            e.transform.localPosition = localPos;
            e.transform.localRotation = Quaternion.Euler(0f, yaw, 0f);
            foreach (Collider c in e.GetComponentsInChildren<Collider>(true)) Object.Destroy(c);
            renderers = Root.GetComponentsInChildren<Renderer>(true);
            foreach (Renderer r in renderers) r.shadowCastingMode = ShadowCastingMode.Off;
            SetValid(Valid, true);
        }

        public void SetValid(bool valid, bool force = false)
        {
            if (!force && valid == Valid) return;
            Valid = valid;
            Material m = valid ? validMat : invalidMat;
            if (m == null) return;
            foreach (Renderer r in renderers)
            {
                var mats = r.sharedMaterials;
                for (int i = 0; i < mats.Length; i++) mats[i] = m;
                r.sharedMaterials = mats;
            }
        }

        public void SetPose(Vector3 position, Quaternion rotation) => Root.transform.SetPositionAndRotation(position, rotation);
        public void SetActive(bool on) => Root.SetActive(on);
        public void Destroy() { if (Root != null) Object.Destroy(Root); Root = null; }
    }
}
