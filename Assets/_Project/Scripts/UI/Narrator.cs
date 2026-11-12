using System;
using TinyTracks.Audio;
using TinyTracks.Core;
using UnityEngine;
using UnityEngine.UI;

namespace TinyTracks.UI
{
    /// <summary>
    /// The friendly conductor who explains what to do: speaks a line, shows it as a caption in a speech bubble
    /// (for grown-ups; the child only needs the voice and the hand), and animates a hand that taps on, or drags
    /// between, screen positions. Targets are re-evaluated every frame so the hand follows moving things
    /// (the train, the ghost track). Tapping the bubble repeats the line.
    /// </summary>
    public class Narrator : MonoBehaviour
    {
        public const float Offscreen = -99999f;

        private ContentLibrary content;
        private RectTransform canvasRect, bubble, hand, ripple;
        private Text caption;
        private CanvasGroup bubbleGroup;
        private Image rippleImage;

        private string currentKey;
        private float bubbleTimer;     // seconds the bubble stays after the voice ends (<0 = until hidden)
        private bool bubbleShown;
        private float bubbleAlpha;

        private Func<Vector2> from, to;
        private float handT;
        private bool handOn;

        /// <summary>The line currently on screen (null when quiet).</summary>
        public string CurrentKey => bubbleShown ? currentKey : null;
        /// <summary>Unscaled time the last line was spoken.</summary>
        public float LastSpoke { get; private set; } = -999f;
        public bool HandVisible => handOn;
        /// <summary>Raised whenever a line is said (key). Used by tests and the guide.</summary>
        public event Action<string> Said;

        public void Build(ContentLibrary lib, RectTransform canvasRoot, Transform bubbleParent)
        {
            content = lib;
            canvasRect = canvasRoot;

            bubble = UIFactory.Rect("NarratorBubble", bubbleParent);
            UIFactory.Anchor(bubble, new Vector2(0.5f, 1f), new Vector2(0.5f, 1f), new Vector2(0f, -36f), new Vector2(1040f, 128f));
            bubbleGroup = bubble.gameObject.AddComponent<CanvasGroup>();
            bubbleGroup.alpha = 0f;
            bubbleGroup.blocksRaycasts = false;
            Image shadow = UIFactory.Image("Shadow", bubble, UIFactory.Rounded, UIFactory.Shadow);
            UIFactory.Stretch(shadow.rectTransform);
            shadow.rectTransform.offsetMin = new Vector2(4f, -10f);
            shadow.rectTransform.offsetMax = new Vector2(4f, -6f);
            Image back = UIFactory.Image("Back", bubble, UIFactory.Rounded, new Color(1f, 1f, 1f, 0.94f), true);
            UIFactory.Stretch(back.rectTransform);
            var repeat = back.gameObject.AddComponent<Button>();
            repeat.transition = Selectable.Transition.None;
            repeat.onClick.AddListener(Repeat);

            Image face = UIFactory.Image("Portrait", bubble, lib.Icon("narrator") ?? lib.Icon("train"), Color.white);
            face.preserveAspect = true;
            UIFactory.Anchor(face.rectTransform, new Vector2(0f, 0.5f), new Vector2(0f, 0.5f), new Vector2(10f, 4f), new Vector2(124f, 124f));

            caption = UIFactory.Label("Caption", bubble, "", 40, new Color(0.2f, 0.25f, 0.45f), TextAnchor.MiddleLeft);
            Outline o = caption.GetComponent<Outline>();
            if (o != null) o.enabled = false;
            if (lib.captionFont != null) caption.font = lib.captionFont;
            caption.resizeTextForBestFit = true;
            caption.resizeTextMinSize = 26;
            caption.resizeTextMaxSize = 40;
            caption.horizontalOverflow = HorizontalWrapMode.Wrap;
            caption.verticalOverflow = VerticalWrapMode.Truncate;
            caption.raycastTarget = false;
            UIFactory.Anchor(caption.rectTransform, new Vector2(0f, 0.5f), new Vector2(0f, 0.5f), new Vector2(148f, 0f), new Vector2(870f, 112f));

            Image r = UIFactory.Image("HandRipple", canvasRoot, UIFactory.Ring, new Color(1f, 1f, 1f, 0.8f));
            ripple = r.rectTransform;
            ripple.sizeDelta = new Vector2(120f, 120f);
            rippleImage = r;
            r.gameObject.SetActive(false);

            Image h = UIFactory.Image("HintHand", canvasRoot, lib.Icon("hand"), Color.white);
            h.preserveAspect = true;
            hand = h.rectTransform;
            hand.sizeDelta = new Vector2(150f, 150f);
            hand.pivot = new Vector2(0.3f, 0.95f); // fingertip
            h.gameObject.SetActive(false);

            Localization.LanguageChanged += RefreshCaption;
        }

        private void OnDestroy() => Localization.LanguageChanged -= RefreshCaption;

        /// <summary>Moves the bubble (the menu has a title at the top).</summary>
        public void SetBubble(Vector2 pos, Vector2 size)
        {
            bubble.anchoredPosition = pos;
            bubble.sizeDelta = size;
            caption.rectTransform.sizeDelta = new Vector2(size.x - 170f, size.y - 16f);
        }

        /// <summary>
        /// Speaks a line and shows its caption. hold = true keeps the bubble up until <see cref="HideBubble"/>
        /// (guided steps); otherwise it fades a few seconds after the voice ends.
        /// </summary>
        public bool Say(string key, bool hold = false)
        {
            VoiceLine line = Localization.Line(content, key);
            if (line == null) { Debug.LogWarning("[TT] Narrator line missing: " + key); return false; }
            currentKey = key;
            caption.text = line.Text(Localization.Language);
            AudioClip clip = line.Clip(Localization.Language);
            AudioManager am = AudioManager.Instance;
            if (am != null) am.PlayVoice(clip);
            float len = clip != null ? clip.length : 2.5f;
            bubbleTimer = hold ? -1f : len + 2.5f;
            if (!bubbleShown)
            {
                bubbleShown = true;
                Juice.PopIn(bubble, 0.3f);
            }
            else Juice.Squash(bubble, 0.06f, 0.25f);
            bubbleGroup.blocksRaycasts = true;
            LastSpoke = Time.unscaledTime;
            Said?.Invoke(key);
            return true;
        }

        public void Repeat()
        {
            if (!string.IsNullOrEmpty(currentKey)) Say(currentKey, bubbleTimer < 0f);
        }

        public void HideBubble()
        {
            bubbleShown = false;
            bubbleGroup.blocksRaycasts = false;
        }

        /// <summary>Hides everything and stops talking (mode left, tutorial skipped).</summary>
        public void Quiet()
        {
            HideBubble();
            HideHand();
            AudioManager.Instance?.StopVoice();
        }

        private void RefreshCaption()
        {
            VoiceLine line = Localization.Line(content, currentKey);
            if (line != null) caption.text = line.Text(Localization.Language);
        }

        // ------------------------------------------------------------------------------------------------ hand
        public void ShowTap(Func<Vector2> target)
        {
            if (handOn && from == target && to == null) return;
            from = target; to = null; handT = 0f; handOn = target != null;
        }

        public void ShowDrag(Func<Vector2> start, Func<Vector2> end)
        {
            from = start; to = end; handT = 0f; handOn = start != null;
        }

        public void HideHand()
        {
            handOn = false;
            from = to = null;
            if (hand != null) hand.gameObject.SetActive(false);
            if (ripple != null) ripple.gameObject.SetActive(false);
        }

        /// <summary>Screen position of a UI element, or offscreen when it is hidden.</summary>
        public static Func<Vector2> Of(Func<Component> get) => () =>
        {
            Component c = get();
            if (c == null || !c.gameObject.activeInHierarchy) return new Vector2(Offscreen, Offscreen);
            return c.transform.position;
        };

        /// <summary>Screen position of a world point (offscreen when behind the camera).</summary>
        public static Vector2 WorldToScreen(Camera cam, Vector3 world)
        {
            if (cam == null) return new Vector2(Offscreen, Offscreen);
            Vector3 s = cam.WorldToScreenPoint(world);
            if (s.z <= 0f || s.x < 0f || s.y < 0f || s.x > Screen.width || s.y > Screen.height) return new Vector2(Offscreen, Offscreen);
            return s;
        }

        private void Update()
        {
            float dt = Time.unscaledDeltaTime;
            if (bubbleShown && bubbleTimer > 0f)
            {
                bool talking = AudioManager.Instance != null && AudioManager.Instance.VoicePlaying;
                if (!talking) bubbleTimer -= dt;
                if (bubbleTimer <= 0f) HideBubble();
            }
            bubbleAlpha = Mathf.MoveTowards(bubbleAlpha, bubbleShown ? 1f : 0f, dt * 4f);
            bubbleGroup.alpha = bubbleAlpha;
            UpdateHand(dt);
        }

        private void UpdateHand(float dt)
        {
            if (!handOn || from == null) return;
            handT += dt;
            Vector2 a = from();
            bool visible = a.x > Offscreen * 0.5f;
            hand.gameObject.SetActive(visible);
            if (!visible) { ripple.gameObject.SetActive(false); return; }
            hand.SetAsLastSibling();

            float scale = 1f, alpha = 1f, rip = -1f;
            Vector2 p, ripAt = a;
            if (to == null)
            {
                const float cycle = 1.4f;
                float t = handT % cycle;
                Vector2 hover = a + new Vector2(40f, -50f) * canvasRect.lossyScale.x;
                if (t < 0.35f) { float k = t / 0.35f; p = Vector2.Lerp(hover, a, Smooth(k)); alpha = Mathf.Clamp01(k * 2f); }
                else if (t < 0.55f) { p = a; scale = 0.85f; rip = (t - 0.35f) / 0.2f; }
                else { float k = (t - 0.55f) / (cycle - 0.55f); p = Vector2.Lerp(a, hover, Smooth(k)); alpha = 1f - k; rip = 1f + k; }
            }
            else
            {
                Vector2 b = to();
                if (b.x < Offscreen * 0.5f) b = a;
                const float cycle = 2.4f;
                float t = handT % cycle;
                if (t < 0.3f) { p = a; alpha = t / 0.3f; }
                else if (t < 0.45f) { p = a; scale = 0.85f; }
                else if (t < 1.65f) { p = Vector2.Lerp(a, b, Smooth((t - 0.45f) / 1.2f)); scale = 0.85f; }
                else if (t < 1.85f) { p = b; scale = 0.85f; rip = (t - 1.65f) / 0.2f; ripAt = b; }
                else { p = b; float k = (t - 1.85f) / (cycle - 1.85f); alpha = 1f - k; rip = 1f + k; ripAt = b; }
            }
            hand.position = p;
            hand.localScale = Vector3.one * scale;
            hand.GetComponent<Image>().color = new Color(1f, 1f, 1f, alpha);
            bool showRip = rip >= 0f && rip <= 2f;
            ripple.gameObject.SetActive(showRip);
            if (showRip)
            {
                ripple.position = ripAt;
                ripple.localScale = Vector3.one * Mathf.Lerp(0.4f, 1.6f, rip / 2f);
                rippleImage.color = new Color(1f, 1f, 1f, (1f - rip / 2f) * 0.8f);
                ripple.SetSiblingIndex(hand.GetSiblingIndex());
            }
        }

        private static float Smooth(float k) => Mathf.SmoothStep(0f, 1f, Mathf.Clamp01(k));
    }
}
