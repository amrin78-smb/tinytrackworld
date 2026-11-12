using System;
using TinyTracks.Audio;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;

namespace TinyTracks.UI
{
    /// <summary>
    /// Big squishy round button for small fingers: squashes on press, bounces on release, clicks softly, shows a
    /// glowing ring when selected. With holdSeconds > 0 it fills a ring and only fires after a long hold (grown-up
    /// actions such as clearing the world).
    /// </summary>
    public class ToyButton : MonoBehaviour, IPointerDownHandler, IPointerUpHandler, IPointerExitHandler
    {
        public Image background;
        public Image icon;
        public Image ring;
        public Image holdFill;
        public float holdSeconds;
        public bool playSound = true;
        public event Action Clicked;

        private bool pressed;
        private float pressTime;
        private bool fired;
        private float scaleVel;
        private float scale = 1f, targetScale = 1f;
        private bool selected;
        private bool interactable = true;
        private float bounceT = -1f;

        public bool Selected
        {
            get => selected;
            set { selected = value; if (ring != null) ring.enabled = value; }
        }

        public bool Interactable
        {
            get => interactable;
            set
            {
                interactable = value;
                CanvasGroup cg = GetComponent<CanvasGroup>();
                if (cg == null) cg = gameObject.AddComponent<CanvasGroup>();
                cg.alpha = value ? 1f : 0.4f;
                cg.blocksRaycasts = true;
            }
        }

        public void OnPointerDown(PointerEventData e)
        {
            if (!interactable) return;
            pressed = true;
            fired = false;
            pressTime = Time.unscaledTime;
            targetScale = 0.86f;
        }

        public void OnPointerUp(PointerEventData e)
        {
            if (!pressed) return;
            pressed = false;
            targetScale = 1f;
            bounceT = 0f;
            if (holdSeconds > 0f)
            {
                if (holdFill != null) holdFill.fillAmount = 0f;
                return;
            }
            // Fire on release while still over the button (forgiving: small drift is fine).
            if (RectTransformUtility.RectangleContainsScreenPoint((RectTransform)transform, e.position, e.pressEventCamera)
                || (e.position - e.pressPosition).magnitude < 60f)
                Fire();
        }

        public void OnPointerExit(PointerEventData e)
        {
            if (holdSeconds > 0f && pressed)
            {
                pressed = false;
                targetScale = 1f;
                if (holdFill != null) holdFill.fillAmount = 0f;
            }
        }

        private void Fire()
        {
            if (playSound) AudioManager.Sfx(AudioManager.Clips?.button);
            Clicked?.Invoke();
        }

        private void Update()
        {
            if (pressed && holdSeconds > 0f && !fired)
            {
                float p = (Time.unscaledTime - pressTime) / holdSeconds;
                if (holdFill != null) holdFill.fillAmount = Mathf.Clamp01(p);
                if (p >= 1f)
                {
                    fired = true;
                    if (holdFill != null) holdFill.fillAmount = 0f;
                    Fire();
                }
            }
            float s = targetScale;
            if (bounceT >= 0f)
            {
                bounceT += Time.unscaledDeltaTime;
                s += Mathf.Sin(bounceT * 18f) * 0.08f * Mathf.Max(0f, 1f - bounceT * 3f);
                if (bounceT > 0.4f) bounceT = -1f;
            }
            if (selected) s *= 1f + 0.04f * Mathf.Sin(Time.unscaledTime * 4f);
            scale = Mathf.SmoothDamp(scale, s, ref scaleVel, 0.05f, Mathf.Infinity, Time.unscaledDeltaTime);
            transform.localScale = new Vector3(scale, scale, 1f);
        }

        public void SetIcon(Sprite s)
        {
            if (icon == null) return;
            icon.sprite = s;
            icon.enabled = s != null;
        }

        public void SetColour(Color c)
        {
            if (background != null) background.color = c;
        }
    }
}
