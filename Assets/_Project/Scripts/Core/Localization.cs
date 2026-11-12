using System;
using System.Collections.Generic;
using UnityEngine;

namespace TinyTracks.Core
{
    /// <summary>One narrator line: caption text and voice clip per language (generated from Tools/voice/voice_lines.json).</summary>
    [Serializable]
    public class VoiceLine
    {
        public string key;
        public string en, th;
        public AudioClip enClip, thClip;

        public string Text(string lang) => lang == "th" && !string.IsNullOrEmpty(th) ? th : en;
        public AudioClip Clip(string lang) => lang == "th" && thClip != null ? thClip : enClip;
    }

    /// <summary>
    /// The active narrator language. The child never reads; captions are for grown-ups and the voice does the
    /// talking. English and Thai are supported; "auto" follows the device language.
    /// </summary>
    public static class Localization
    {
        public static readonly string[] Languages = { "en", "th" };
        public static readonly string[] LanguageNames = { "English", "ไทย" };

        public static string Language { get; private set; } = "en";
        public static event Action LanguageChanged;

        public static string Resolve(string setting)
        {
            if (setting == "en" || setting == "th") return setting;
            return Application.systemLanguage == SystemLanguage.Thai ? "th" : "en";
        }

        public static void Set(string setting)
        {
            string lang = Resolve(setting);
            if (lang == Language) return;
            Language = lang;
            LanguageChanged?.Invoke();
        }

        private static Dictionary<string, VoiceLine> lookup;
        private static ContentLibrary lookupOwner;

        public static VoiceLine Line(ContentLibrary content, string key)
        {
            if (content == null || key == null) return null;
            if (lookup == null || lookupOwner != content)
            {
                lookup = new Dictionary<string, VoiceLine>();
                foreach (VoiceLine l in content.voice) if (l != null && !string.IsNullOrEmpty(l.key)) lookup[l.key] = l;
                lookupOwner = content;
            }
            return lookup.TryGetValue(key, out VoiceLine v) ? v : null;
        }
    }
}
