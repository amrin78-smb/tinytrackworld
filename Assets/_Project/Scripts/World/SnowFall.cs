using UnityEngine;
using UnityEngine.Rendering;

namespace TinyTracks.World
{
    /// <summary>
    /// Gentle snowfall around the camera's view: one dynamic mesh of small camera-facing flakes, updated on the CPU
    /// (no particle module, one draw call). Flakes drift down with a little sway and wrap around the view volume.
    /// </summary>
    public class SnowFall : MonoBehaviour
    {
        public Material material;
        public int flakes = 180;
        public Vector3 volume = new Vector3(46f, 20f, 36f);

        private Vector3[] pos;
        private float[] speed, phase, size;
        private Vector3[] verts;
        private Mesh mesh;
        private int active;

        private void Start()
        {
            pos = new Vector3[flakes];
            speed = new float[flakes];
            phase = new float[flakes];
            size = new float[flakes];
            for (int i = 0; i < flakes; i++)
            {
                pos[i] = new Vector3(Random.Range(-0.5f, 0.5f) * volume.x, Random.Range(0f, volume.y), Random.Range(-0.5f, 0.5f) * volume.z);
                speed[i] = Random.Range(0.9f, 1.6f);
                phase[i] = Random.Range(0f, 10f);
                size[i] = Random.Range(0.07f, 0.13f);
            }
            verts = new Vector3[flakes * 4];
            var cols = new Color32[flakes * 4];
            var tris = new int[flakes * 6];
            for (int i = 0; i < flakes; i++)
            {
                for (int k = 0; k < 4; k++) cols[i * 4 + k] = new Color32(255, 255, 255, 0);
                int v = i * 4, t = i * 6;
                tris[t] = v; tris[t + 1] = v + 1; tris[t + 2] = v + 2;
                tris[t + 3] = v; tris[t + 4] = v + 2; tris[t + 5] = v + 3;
            }
            mesh = new Mesh { name = "Snowflakes" };
            mesh.MarkDynamic();
            mesh.vertices = verts;
            mesh.colors32 = cols;
            mesh.triangles = tris;
            mesh.bounds = new Bounds(Vector3.zero, Vector3.one * 1000f);
            gameObject.AddComponent<MeshFilter>().sharedMesh = mesh;
            var mr = gameObject.AddComponent<MeshRenderer>();
            mr.sharedMaterial = material;
            mr.shadowCastingMode = ShadowCastingMode.Off;
            mr.receiveShadows = false;
            if (active == 0) active = flakes;
        }

        public void SetLowDetail(bool low) => active = low ? flakes / 2 : flakes;

        private void LateUpdate()
        {
            Camera cam = Camera.main;
            if (cam == null || mesh == null) return;
            Vector3 centre = Cameras.CameraController.Instance != null ? Cameras.CameraController.Instance.Target : Vector3.zero;
            Vector3 right = cam.transform.right, up = cam.transform.up;
            float dt = Time.deltaTime, time = Time.time;
            for (int i = 0; i < flakes; i++)
            {
                int v = i * 4;
                if (i >= active)
                {
                    verts[v] = verts[v + 1] = verts[v + 2] = verts[v + 3] = Vector3.zero;
                    continue;
                }
                Vector3 p = pos[i];
                p.y -= speed[i] * dt;
                p.x += Mathf.Sin(time * 0.9f + phase[i]) * 0.35f * dt;
                if (p.y < 0f) p.y += volume.y;
                pos[i] = p;
                // Wrap horizontally around the view centre so snow always surrounds what the child looks at.
                Vector3 w = new Vector3(
                    centre.x + Mathf.Repeat(p.x - centre.x + volume.x * 0.5f, volume.x) - volume.x * 0.5f,
                    p.y,
                    centre.z + Mathf.Repeat(p.z - centre.z + volume.z * 0.5f, volume.z) - volume.z * 0.5f);
                Vector3 r = right * size[i], u = up * size[i];
                verts[v] = w - r;
                verts[v + 1] = w + u;
                verts[v + 2] = w + r;
                verts[v + 3] = w - u;
            }
            mesh.vertices = verts;
        }

        private void OnDestroy()
        {
            if (mesh != null) Destroy(mesh);
        }
    }
}
