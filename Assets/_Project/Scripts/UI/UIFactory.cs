using UnityEngine;
using UnityEngine.UI;

namespace TinyTracks.UI
{
    /// <summary>Builds uGUI elements in code with generated round sprites (no textures to import).</summary>
    public static class UIFactory
    {
        public static readonly Color Green = new Color32(76, 196, 92, 255);
        public static readonly Color Red = new Color32(240, 84, 84, 255);
        public static readonly Color Blue = new Color32(66, 140, 232, 255);
        public static readonly Color Yellow = new Color32(255, 204, 64, 255);
        public static readonly Color Orange = new Color32(255, 150, 60, 255);
        public static readonly Color Purple = new Color32(160, 112, 224, 255);
        public static readonly Color Cream = new Color32(255, 248, 232, 255);
        public static readonly Color Panel = new Color32(255, 255, 255, 215);
        public static readonly Color Shadow = new Color32(30, 40, 80, 70);

        private static Sprite circle, ring, rounded, softCircle;
        private static Font font;

        public static Font Font => font != null ? font : (font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf"));

        public static Sprite Circle => circle != null ? circle : (circle = MakeCircle(128, 0f, 1.5f, false));
        public static Sprite SoftCircle => softCircle != null ? softCircle : (softCircle = MakeCircle(128, 0f, 18f, false));
        public static Sprite Ring => ring != null ? ring : (ring = MakeCircle(128, 0.8f, 1.5f, false));
        public static Sprite Rounded => rounded != null ? rounded : (rounded = MakeRounded(96, 40));

        private static Sprite MakeCircle(int size, float inner, float feather, bool _)
        {
            var tex = new Texture2D(size, size, TextureFormat.RGBA32, false) { wrapMode = TextureWrapMode.Clamp, filterMode = FilterMode.Bilinear };
            var px = new Color32[size * size];
            float r = size * 0.5f;
            for (int y = 0; y < size; y++)
            for (int x = 0; x < size; x++)
            {
                float d = Vector2.Distance(new Vector2(x + 0.5f, y + 0.5f), new Vector2(r, r));
                float a = Mathf.Clamp01((r - 1f - d) / feather);
                if (inner > 0f) a *= Mathf.Clamp01((d - r * inner) / 1.5f);
                px[y * size + x] = new Color32(255, 255, 255, (byte)(a * 255));
            }
            tex.SetPixels32(px);
            tex.Apply(false, true);
            return Sprite.Create(tex, new Rect(0, 0, size, size), new Vector2(0.5f, 0.5f), 100f);
        }

        private static Sprite MakeRounded(int size, int radius)
        {
            var tex = new Texture2D(size, size, TextureFormat.RGBA32, false) { wrapMode = TextureWrapMode.Clamp };
            var px = new Color32[size * size];
            for (int y = 0; y < size; y++)
            for (int x = 0; x < size; x++)
            {
                float cx = Mathf.Clamp(x + 0.5f, radius, size - radius), cy = Mathf.Clamp(y + 0.5f, radius, size - radius);
                float d = Vector2.Distance(new Vector2(x + 0.5f, y + 0.5f), new Vector2(cx, cy));
                float a = Mathf.Clamp01(radius - d);
                px[y * size + x] = new Color32(255, 255, 255, (byte)(a * 255));
            }
            tex.SetPixels32(px);
            tex.Apply(false, true);
            float b = radius;
            return Sprite.Create(tex, new Rect(0, 0, size, size), new Vector2(0.5f, 0.5f), 100f, 0, SpriteMeshType.FullRect, new Vector4(b, b, b, b));
        }

        public static RectTransform Rect(string name, Transform parent)
        {
            var go = new GameObject(name, typeof(RectTransform));
            go.transform.SetParent(parent, false);
            return (RectTransform)go.transform;
        }

        public static RectTransform Anchor(RectTransform rt, Vector2 anchor, Vector2 pivot, Vector2 pos, Vector2 size)
        {
            rt.anchorMin = rt.anchorMax = anchor;
            rt.pivot = pivot;
            rt.anchoredPosition = pos;
            rt.sizeDelta = size;
            return rt;
        }

        public static void Stretch(RectTransform rt)
        {
            rt.anchorMin = Vector2.zero;
            rt.anchorMax = Vector2.one;
            rt.offsetMin = rt.offsetMax = Vector2.zero;
        }

        public static Image Image(string name, Transform parent, Sprite sprite, Color colour, bool raycast = false)
        {
            RectTransform rt = Rect(name, parent);
            Image img = rt.gameObject.AddComponent<Image>();
            img.sprite = sprite;
            img.color = colour;
            img.raycastTarget = raycast;
            if (sprite == Rounded) img.type = UnityEngine.UI.Image.Type.Sliced;
            return img;
        }

        public static Text Label(string name, Transform parent, string text, int size, Color colour, TextAnchor align = TextAnchor.MiddleCenter)
        {
            RectTransform rt = Rect(name, parent);
            Text t = rt.gameObject.AddComponent<Text>();
            t.font = Font;
            t.text = text;
            t.fontSize = size;
            t.color = colour;
            t.alignment = align;
            t.raycastTarget = false;
            t.horizontalOverflow = HorizontalWrapMode.Overflow;
            t.verticalOverflow = VerticalWrapMode.Overflow;
            var o = rt.gameObject.AddComponent<Outline>();
            o.effectColor = new Color(0.1f, 0.15f, 0.35f, 0.6f);
            o.effectDistance = new Vector2(2f, -2f);
            return t;
        }

        /// <summary>A round toy button with drop shadow, coloured disc, icon and selection ring.</summary>
        public static ToyButton Button(string name, Transform parent, Sprite icon, Color colour, float size, float iconScale = 0.78f)
        {
            RectTransform rt = Rect(name, parent);
            rt.sizeDelta = new Vector2(size, size);
            Image shadow = Image("Shadow", rt, Circle, Shadow);
            Anchor(shadow.rectTransform, new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), new Vector2(0f, -size * 0.06f), new Vector2(size, size));
            Image bg = Image("Disc", rt, Circle, colour, true);
            Anchor(bg.rectTransform, new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), Vector2.zero, new Vector2(size, size));
            Image shine = Image("Shine", rt, SoftCircle, new Color(1f, 1f, 1f, 0.28f));
            Anchor(shine.rectTransform, new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), new Vector2(-size * 0.12f, size * 0.16f), new Vector2(size * 0.55f, size * 0.4f));
            Image ic = Image("Icon", rt, icon, Color.white);
            ic.preserveAspect = true;
            Anchor(ic.rectTransform, new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), Vector2.zero, new Vector2(size * iconScale, size * iconScale));
            ic.enabled = icon != null;
            Image ringImg = Image("Ring", rt, Ring, new Color(1f, 0.95f, 0.35f, 1f));
            Anchor(ringImg.rectTransform, new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), Vector2.zero, new Vector2(size * 1.18f, size * 1.18f));
            ringImg.enabled = false;
            Image fill = Image("HoldFill", rt, Ring, new Color(1f, 1f, 1f, 0.9f));
            fill.type = UnityEngine.UI.Image.Type.Filled;
            fill.fillMethod = UnityEngine.UI.Image.FillMethod.Radial360;
            fill.fillOrigin = 2;
            fill.fillAmount = 0f;
            Anchor(fill.rectTransform, new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), Vector2.zero, new Vector2(size * 1.1f, size * 1.1f));
            ToyButton b = rt.gameObject.AddComponent<ToyButton>();
            b.background = bg;
            b.icon = ic;
            b.ring = ringImg;
            b.holdFill = fill;
            return b;
        }

        public static RectTransform Row(string name, Transform parent, float spacing, TextAnchor align = TextAnchor.MiddleCenter)
        {
            RectTransform rt = Rect(name, parent);
            var h = rt.gameObject.AddComponent<HorizontalLayoutGroup>();
            h.spacing = spacing;
            h.childAlignment = align;
            h.childControlWidth = h.childControlHeight = false;
            h.childForceExpandWidth = h.childForceExpandHeight = false;
            return rt;
        }

        public static RectTransform Column(string name, Transform parent, float spacing, TextAnchor align = TextAnchor.UpperCenter)
        {
            RectTransform rt = Rect(name, parent);
            var v = rt.gameObject.AddComponent<VerticalLayoutGroup>();
            v.spacing = spacing;
            v.childAlignment = align;
            v.childControlWidth = v.childControlHeight = false;
            v.childForceExpandWidth = v.childForceExpandHeight = false;
            return rt;
        }

        public static Slider Slider(string name, Transform parent, float value, Color fillColour, float width = 520f)
        {
            RectTransform rt = Rect(name, parent);
            rt.sizeDelta = new Vector2(width, 70f);
            Image track = Image("Track", rt, Rounded, new Color(0.85f, 0.88f, 0.95f, 1f), true);
            Stretch(track.rectTransform);
            track.rectTransform.offsetMin = new Vector2(0f, 20f);
            track.rectTransform.offsetMax = new Vector2(0f, -20f);
            RectTransform fillArea = Rect("FillArea", rt);
            Stretch(fillArea);
            fillArea.offsetMin = new Vector2(10f, 20f);
            fillArea.offsetMax = new Vector2(-10f, -20f);
            Image fill = Image("Fill", fillArea, Rounded, fillColour);
            Stretch(fill.rectTransform);
            RectTransform handleArea = Rect("HandleArea", rt);
            Stretch(handleArea);
            handleArea.offsetMin = new Vector2(30f, 0f);
            handleArea.offsetMax = new Vector2(-30f, 0f);
            Image handle = Image("Handle", handleArea, Circle, Color.white, true);
            handle.rectTransform.sizeDelta = new Vector2(70f, 70f);
            Slider s = rt.gameObject.AddComponent<Slider>();
            s.fillRect = fill.rectTransform;
            s.handleRect = handle.rectTransform;
            s.targetGraphic = handle;
            s.minValue = 0f;
            s.maxValue = 1f;
            s.value = value;
            return s;
        }
    }
}
