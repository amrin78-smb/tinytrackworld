using UnityEditor;
using UnityEngine;

namespace TinyTracks.EditorTools
{
    /// <summary>Import rules for the generated art and audio (mobile-friendly, no embedded materials).</summary>
    public class TinyTracksImporter : AssetPostprocessor
    {
        private void OnPreprocessModel()
        {
            if (!assetPath.StartsWith("Assets/_Project/Art/Models")) return;
            var mi = (ModelImporter)assetImporter;
            mi.materialImportMode = ModelImporterMaterialImportMode.None;
            mi.importAnimation = false;
            mi.animationType = ModelImporterAnimationType.None;
            mi.importCameras = false;
            mi.importLights = false;
            mi.importBlendShapes = false;
            mi.importVisibility = false;
            mi.isReadable = assetPath.Contains("/Tracks/"); // track meshes are read for ghost/bounds; others not
            mi.meshCompression = ModelImporterMeshCompression.Off;
            mi.importNormals = ModelImporterNormals.Import;
            mi.importTangents = ModelImporterTangents.None;
            mi.optimizeMeshPolygons = true;
            mi.optimizeMeshVertices = true;
            mi.weldVertices = true;
            mi.addCollider = false;
            mi.globalScale = 1f;
            mi.bakeAxisConversion = false;
        }

        private void OnPreprocessTexture()
        {
            if (!assetPath.StartsWith("Assets/_Project/Art/UI")) return;
            var ti = (TextureImporter)assetImporter;
            ti.textureType = TextureImporterType.Sprite;
            ti.spriteImportMode = SpriteImportMode.Single;
            ti.alphaIsTransparency = true;
            ti.mipmapEnabled = false;
            ti.maxTextureSize = 256;
            ti.textureCompression = TextureImporterCompression.Compressed;
            var android = ti.GetPlatformTextureSettings("Android");
            android.overridden = true;
            android.maxTextureSize = 256;
            android.format = TextureImporterFormat.ASTC_6x6;
            ti.SetPlatformTextureSettings(android);
        }

        private void OnPreprocessAudio()
        {
            if (!assetPath.StartsWith("Assets/_Project/Audio")) return;
            var ai = (AudioImporter)assetImporter;
            bool music = assetPath.Contains("/Music/") || assetPath.Contains("/Ambient/");
            ai.forceToMono = !music;
            ai.loadInBackground = music;
            var s = ai.defaultSampleSettings;
            bool voice = assetPath.Contains("/Voice/");
            // Voice lines are many and long-ish: keep them compressed in memory (a 3 GB phone has little to spare).
            s.loadType = music ? AudioClipLoadType.Streaming : voice ? AudioClipLoadType.CompressedInMemory : AudioClipLoadType.DecompressOnLoad;
            s.compressionFormat = AudioCompressionFormat.Vorbis;
            s.quality = music ? 0.5f : 0.6f;
            s.sampleRateSetting = AudioSampleRateSetting.OptimizeSampleRate;
            s.preloadAudioData = !music;
            ai.defaultSampleSettings = s;
        }
    }
}
