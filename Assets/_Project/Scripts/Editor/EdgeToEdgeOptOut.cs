using System.IO;
using System.Text.RegularExpressions;
using UnityEditor.Android;
using UnityEngine;

namespace TinyTracks.EditorTools
{
    /// <summary>
    /// Android 15 makes apps edge-to-edge, which ignores the legacy FULLSCREEN flag Unity uses, so the status bar
    /// stayed visible over the game. Opt the activity themes out (honoured while targeting SDK 35, see ProjectSetup).
    /// </summary>
    public class EdgeToEdgeOptOut : IPostGenerateGradleAndroidProject
    {
        private const string Item = "<item name=\"android:windowOptOutEdgeToEdgeEnforcement\">true</item>";
        public int callbackOrder => 1001;

        public void OnPostGenerateGradleAndroidProject(string path)
        {
            string res = Path.Combine(path, "src", "main", "res");
            if (!Directory.Exists(res)) return;
            foreach (string file in Directory.GetFiles(res, "styles.xml", SearchOption.AllDirectories))
            {
                string text = File.ReadAllText(file);
                if (text.Contains("windowOptOutEdgeToEdgeEnforcement")) continue;
                // Add the item to every Unity activity theme (self-closing styles become open ones).
                string updated = Regex.Replace(text, "<style name=\"(UnityThemeSelector|BaseUnityTheme|BaseUnityGameActivityTheme)\"([^>]*?)\\s*/>",
                    m => $"<style name=\"{m.Groups[1].Value}\"{m.Groups[2].Value}>\n    {Item}\n  </style>");
                updated = Regex.Replace(updated, "(<style name=\"(UnityThemeSelector|BaseUnityTheme|BaseUnityGameActivityTheme)\"[^>]*[^/]>)",
                    m => m.Value + "\n    " + Item);
                // Avoid duplicates where both patterns matched.
                updated = updated.Replace(Item + "\n    " + Item, Item);
                if (updated == text) continue;
                File.WriteAllText(file, updated);
                Debug.Log("[TT Build] Edge-to-edge opt-out added to " + file);
            }
        }
    }
}
