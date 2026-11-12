using System.IO;
using System.Text.RegularExpressions;
using UnityEditor.Android;
using UnityEngine;

namespace TinyTracks.EditorTools
{
    /// <summary>
    /// The game is fully offline (no ads, analytics or network). Unity still writes
    /// android.permission.INTERNET into the generated unityLibrary manifest even with forceInternetPermission off,
    /// so remove it from the generated Gradle project before it is packaged. Tools/verify_apk.sh checks the result.
    /// </summary>
    public class StripInternetPermission : IPostGenerateGradleAndroidProject
    {
        public int callbackOrder => 1000;

        public void OnPostGenerateGradleAndroidProject(string path)
        {
            // path points at unityLibrary; also cover the launcher module next to it.
            foreach (string module in new[] { path, Path.Combine(path, "..", "launcher") })
            {
                string manifest = Path.Combine(module, "src", "main", "AndroidManifest.xml");
                if (!File.Exists(manifest)) continue;
                string text = File.ReadAllText(manifest);
                string stripped = Regex.Replace(text, @"\s*<uses-permission[^>]*android\.permission\.INTERNET[^>]*/>", "");
                if (stripped == text) continue;
                File.WriteAllText(manifest, stripped);
                Debug.Log("[TT Build] Removed INTERNET permission from " + manifest);
            }
        }
    }
}
