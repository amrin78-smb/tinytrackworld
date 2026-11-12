using UnityEngine;

namespace TinyTracks.World
{
    /// <summary>
    /// Sunny Valley ground: a flat valley floor (where everything is built and the scenery stands), soft rolling hills
    /// all round so there is never a hard world edge, and a lake basin. Vertex-coloured for the ToyLit shader
    /// (alpha = speckle code). Deterministic, generated in a few milliseconds.
    /// </summary>
    public static class TerrainGenerator
    {
        public struct Settings
        {
            public float halfSize;          // terrain extends +/- this
            public float step;              // grid spacing
            public Vector2 floorHalf;       // flat valley floor half extents
            public Vector2 lakeCentre;
            public Vector2 lakeRadius;
            public float lakeDepth;
            public float hillHeight;
        }

        public static Settings SunnyValley => new Settings
        {
            halfSize = 110f, step = 2.5f, floorHalf = new Vector2(52f, 40f),
            lakeCentre = new Vector2(46f, -2f), lakeRadius = new Vector2(10f, 13f), lakeDepth = 1.4f, hillHeight = 13f,
        };

        public static Settings SnowyValley => new Settings
        {
            halfSize = 110f, step = 2.5f, floorHalf = new Vector2(52f, 40f),
            lakeCentre = new Vector2(-46f, 6f), lakeRadius = new Vector2(11f, 12f), lakeDepth = 1.2f, hillHeight = 16f,
        };

        public const float WaterLevel = -0.18f;

        /// <summary>Ground colours. Alpha is the ToyLit detail code (speckle strength).</summary>
        public struct Palette
        {
            public Color32 grass, grassDark, grassLight, hill, sand, lakeBed;
        }

        public static readonly Palette Meadow = new Palette
        {
            grass = new Color32(118, 191, 86, 70), grassDark = new Color32(86, 160, 70, 70), grassLight = new Color32(150, 205, 102, 70),
            hill = new Color32(96, 168, 80, 70), sand = new Color32(235, 212, 155, 70), lakeBed = new Color32(150, 170, 120, 40),
        };

        public static readonly Palette Snow = new Palette
        {
            // Soft blue-white (pure white washed out under the bright winter light and hid every shape).
            grass = new Color32(216, 228, 242, 40), grassDark = new Color32(190, 207, 230, 50), grassLight = new Color32(232, 240, 250, 30),
            hill = new Color32(220, 231, 245, 40), sand = new Color32(178, 196, 220, 60), lakeBed = new Color32(160, 186, 214, 30),
        };


        public static float Height(Settings s, float x, float z)
        {
            float h = 0f;
            // Distance outside the valley floor (rounded rectangle).
            float dx = Mathf.Max(0f, Mathf.Abs(x) - s.floorHalf.x);
            float dz = Mathf.Max(0f, Mathf.Abs(z) - s.floorHalf.y);
            float outside = Mathf.Sqrt(dx * dx + dz * dz);
            if (outside > 0f)
            {
                float rise = 1f - Mathf.Exp(-outside / 18f);
                float n = Mathf.PerlinNoise(x * 0.035f + 3.1f, z * 0.035f + 7.7f);
                float n2 = Mathf.PerlinNoise(x * 0.09f + 11f, z * 0.09f + 5f);
                h = s.hillHeight * rise * (0.55f + 0.6f * n) + n2 * 1.2f * rise;
            }
            // Lake basin.
            float lx = (x - s.lakeCentre.x) / s.lakeRadius.x, lz = (z - s.lakeCentre.y) / s.lakeRadius.y;
            float ld = Mathf.Sqrt(lx * lx + lz * lz);
            if (ld < 1.25f)
            {
                float k = Mathf.Clamp01((1.25f - ld) / 0.45f);
                h = Mathf.Lerp(h, -s.lakeDepth, k * k * (3f - 2f * k));
            }
            return h;
        }

        public static Mesh Build(Settings s) => Build(s, Meadow);

        public static Mesh Build(Settings s, Palette pal)
        {
            Color32 Grass = pal.grass, GrassDark = pal.grassDark, GrassLight = pal.grassLight, HillGreen = pal.hill, Sand = pal.sand, LakeBed = pal.lakeBed;
            int n = Mathf.CeilToInt(s.halfSize * 2f / s.step) + 1;
            var verts = new Vector3[n * n];
            var cols = new Color32[n * n];
            var uvs = new Vector2[n * n];
            for (int j = 0; j < n; j++)
            for (int i = 0; i < n; i++)
            {
                float x = -s.halfSize + i * s.step, z = -s.halfSize + j * s.step;
                // Small jitter breaks up the grid on hills (not on the flat floor).
                float h = Height(s, x, z);
                int k = j * n + i;
                verts[k] = new Vector3(x, h, z);
                uvs[k] = new Vector2(x * 0.25f, z * 0.25f);
                float patch = Mathf.Clamp01(Mathf.PerlinNoise(x * 0.09f + 1.3f, z * 0.09f + 2.9f) * 0.7f + Mathf.PerlinNoise(x * 0.25f + 9f, z * 0.25f + 4f) * 0.45f - 0.08f);
                Color32 c = patch < 0.4f ? Color32.Lerp(GrassDark, Grass, patch / 0.4f) : Color32.Lerp(Grass, GrassLight, (patch - 0.4f) / 0.6f);
                if (h > 0.5f) c = Color32.Lerp(c, HillGreen, Mathf.Clamp01(h / 8f));
                float lx = (x - s.lakeCentre.x) / s.lakeRadius.x, lz = (z - s.lakeCentre.y) / s.lakeRadius.y;
                float ld = Mathf.Sqrt(lx * lx + lz * lz);
                if (ld < 1.35f) c = Color32.Lerp(c, Sand, Mathf.Clamp01((1.35f - ld) / 0.2f));
                if (ld < 0.95f) c = Color32.Lerp(Sand, LakeBed, Mathf.Clamp01((0.95f - ld) / 0.3f));
                cols[k] = c;
            }
            var tris = new int[(n - 1) * (n - 1) * 6];
            int t = 0;
            for (int j = 0; j < n - 1; j++)
            for (int i = 0; i < n - 1; i++)
            {
                int a = j * n + i, b = a + 1, c = a + n, d = c + 1;
                // Alternate the diagonal for a less regular look.
                if (((i + j) & 1) == 0) { tris[t++] = a; tris[t++] = c; tris[t++] = b; tris[t++] = b; tris[t++] = c; tris[t++] = d; }
                else { tris[t++] = a; tris[t++] = c; tris[t++] = d; tris[t++] = a; tris[t++] = d; tris[t++] = b; }
            }
            var m = new Mesh { name = "SunnyValleyTerrain" };
            if (verts.Length > 65000) m.indexFormat = UnityEngine.Rendering.IndexFormat.UInt32;
            m.vertices = verts;
            m.colors32 = cols;
            m.uv = uvs;
            m.triangles = tris;
            m.RecalculateNormals();
            m.RecalculateBounds();
            return m;
        }

        /// <summary>Lake surface: an ellipse fan; vertex alpha = depth (0 at the shore) for the Water shader.</summary>
        public static Mesh BuildLake(Settings s)
        {
            const int rings = 6, segs = 40;
            var verts = new System.Collections.Generic.List<Vector3>();
            var cols = new System.Collections.Generic.List<Color32>();
            var tris = new System.Collections.Generic.List<int>();
            verts.Add(new Vector3(s.lakeCentre.x, WaterLevel, s.lakeCentre.y));
            cols.Add(new Color32(255, 255, 255, 255));
            for (int r = 1; r <= rings; r++)
            {
                float f = r / (float)rings * 1.08f;
                for (int k = 0; k < segs; k++)
                {
                    float a = k * Mathf.PI * 2f / segs;
                    float wob = 1f + 0.04f * Mathf.Sin(a * 3f + 1f);
                    verts.Add(new Vector3(s.lakeCentre.x + Mathf.Cos(a) * s.lakeRadius.x * f * wob, WaterLevel, s.lakeCentre.y + Mathf.Sin(a) * s.lakeRadius.y * f * wob));
                    cols.Add(new Color32(255, 255, 255, (byte)(255 * Mathf.Clamp01(1f - f / 1.08f))));
                }
            }
            for (int k = 0; k < segs; k++) { tris.Add(0); tris.Add(1 + (k + 1) % segs); tris.Add(1 + k); }
            for (int r = 1; r < rings; r++)
            {
                int a0 = 1 + (r - 1) * segs, b0 = 1 + r * segs;
                for (int k = 0; k < segs; k++)
                {
                    int k2 = (k + 1) % segs;
                    tris.Add(a0 + k); tris.Add(a0 + k2); tris.Add(b0 + k);
                    tris.Add(a0 + k2); tris.Add(b0 + k2); tris.Add(b0 + k);
                }
            }
            var m = new Mesh { name = "Lake" };
            m.SetVertices(verts);
            m.SetColors(cols);
            m.SetTriangles(tris, 0);
            m.RecalculateNormals();
            m.RecalculateBounds();
            return m;
        }
    }
}
