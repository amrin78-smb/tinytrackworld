using System.Globalization;
using System.IO;
using System.Text;
using TinyTracks.Tracks;
using UnityEditor;
using UnityEngine;

namespace TinyTracks.EditorTools
{
    /// <summary>
    /// Writes Tools/blender/track_shapes.json from <see cref="TrackShapeLibrary"/> (the single source of track geometry)
    /// so the Blender track models follow exactly the paths the trains drive on. Unity local coordinates.
    /// </summary>
    public static class TrackShapeExporter
    {
        public const string OutPath = "Tools/blender/track_shapes.json";

        [MenuItem("Tiny Tracks/Export Track Shapes for Blender")]
        public static void Export()
        {
            var sb = new StringBuilder();
            var ci = CultureInfo.InvariantCulture;
            string F(float v) => v.ToString("0.####", ci);
            sb.Append("{\n");
            sb.Append($"  \"sampleStep\": {F(TrackShapeLibrary.SampleStep)},\n  \"elevatedHeight\": {F(TrackShapeLibrary.ElevatedHeight)},\n  \"shapes\": {{\n");
            bool firstShape = true;
            foreach (TrackType t in TrackShapeLibrary.AllTypes)
            {
                TrackShape s = TrackShapeLibrary.Get(t);
                if (!firstShape) sb.Append(",\n");
                firstShape = false;
                sb.Append($"    \"{t}\": {{\n      \"connectors\": [");
                for (int i = 0; i < s.connectors.Length; i++)
                {
                    Vector3 p = s.connectors[i].position;
                    sb.Append(i > 0 ? ", " : "").Append($"{{\"p\": [{F(p.x)}, {F(p.y)}, {F(p.z)}], \"h\": {F(s.connectors[i].heading)}}}");
                }
                sb.Append("],\n      \"paths\": [");
                for (int k = 0; k < s.paths.Length; k++)
                {
                    TrackPath tp = s.paths[k];
                    sb.Append(k > 0 ? ",\n        " : "\n        ").Append($"{{\"from\": {tp.from}, \"to\": {tp.to}, \"points\": [");
                    for (int i = 0; i < tp.points.Length; i++)
                    {
                        Vector3 p = tp.points[i];
                        sb.Append(i > 0 ? ", " : "").Append($"[{F(p.x)}, {F(p.y)}, {F(p.z)}]");
                    }
                    sb.Append("]}");
                }
                sb.Append("]\n    }");
            }
            sb.Append("\n  }\n}\n");
            File.WriteAllText(OutPath, sb.ToString());
            Debug.Log("[TT] Track shapes exported to " + OutPath);
        }
    }
}
