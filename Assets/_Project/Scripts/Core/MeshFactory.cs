using UnityEngine;

namespace TinyTracks.Core
{
    /// <summary>Small procedural meshes for markers (built once, shared).</summary>
    public static class MeshFactory
    {
        private static Mesh quad, arrow;

        /// <summary>Horizontal unit quad (XZ plane, centred, UV 0..1), facing up.</summary>
        public static Mesh GroundQuad()
        {
            if (quad != null) return quad;
            quad = new Mesh { name = "GroundQuad" };
            quad.vertices = new[] { new Vector3(-0.5f, 0, -0.5f), new Vector3(0.5f, 0, -0.5f), new Vector3(0.5f, 0, 0.5f), new Vector3(-0.5f, 0, 0.5f) };
            quad.uv = new[] { new Vector2(0, 0), new Vector2(1, 0), new Vector2(1, 1), new Vector2(0, 1) };
            quad.normals = new[] { Vector3.up, Vector3.up, Vector3.up, Vector3.up };
            quad.triangles = new[] { 0, 2, 1, 0, 3, 2 };
            quad.RecalculateBounds();
            return quad;
        }

        /// <summary>Chunky flat arrow pointing +Z, 1 m long, with vertex colours (for the ToyLit / Ghost shaders).</summary>
        public static Mesh Arrow(Color32 colour)
        {
            if (arrow != null) return arrow;
            arrow = new Mesh { name = "Arrow" };
            const float w = 0.18f, hw = 0.42f, sh = 0.45f, h = 0.08f;
            Vector2[] outline =
            {
                new Vector2(-w, -0.5f), new Vector2(w, -0.5f), new Vector2(w, sh - 0.5f), new Vector2(hw, sh - 0.5f),
                new Vector2(0f, 0.5f), new Vector2(-hw, sh - 0.5f), new Vector2(-w, sh - 0.5f),
            };
            int n = outline.Length;
            var v = new Vector3[n * 2 + n * 4];
            var tris = new System.Collections.Generic.List<int>();
            for (int i = 0; i < n; i++)
            {
                v[i] = new Vector3(outline[i].x, h, outline[i].y);
                v[n + i] = new Vector3(outline[i].x, 0f, outline[i].y);
            }
            // top (fan from centre approx - shape is concave, so triangulate shaft + head separately)
            tris.AddRange(new[] { 0, 2, 1, 0, 6, 2, 5, 4, 3 });
            int baseIdx = n * 2;
            for (int i = 0; i < n; i++)
            {
                int j = (i + 1) % n;
                v[baseIdx + i * 4 + 0] = v[i];
                v[baseIdx + i * 4 + 1] = v[j];
                v[baseIdx + i * 4 + 2] = v[n + j];
                v[baseIdx + i * 4 + 3] = v[n + i];
                int b = baseIdx + i * 4;
                tris.AddRange(new[] { b, b + 2, b + 1, b, b + 3, b + 2 });
            }
            var cols = new Color32[v.Length];
            for (int i = 0; i < cols.Length; i++) cols[i] = colour;
            arrow.vertices = v;
            arrow.colors32 = cols;
            arrow.triangles = tris.ToArray();
            arrow.RecalculateNormals();
            arrow.RecalculateBounds();
            return arrow;
        }
    }
}
