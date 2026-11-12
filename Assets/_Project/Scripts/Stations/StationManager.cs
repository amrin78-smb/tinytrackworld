using System;
using System.Collections;
using System.Collections.Generic;
using TinyTracks.Audio;
using TinyTracks.Core;
using TinyTracks.Tracks;
using TinyTracks.Trains;
using UnityEngine;

namespace TinyTracks.Stations
{
    /// <summary>
    /// Life at the stops. Stations: a few little passengers wait on the platform; when a train stops, riders get
    /// off (and wave goodbye) and the waiting ones walk to a passenger carriage and hop in. Cargo yards: the crane
    /// swings a crate, logs, milk churns or hay into an empty cargo wagon, or unloads a full one onto the platform.
    /// Purely visual (nothing to fail): the train simply waits until the little scene has finished.
    /// </summary>
    public class StationManager : MonoBehaviour
    {
        public static StationManager Instance { get; private set; }

        public ContentLibrary content;
        public TrackNetworkManager network;

        public static readonly string[] PassengerIds = { "Passenger_Girl", "Passenger_Grandpa", "Passenger_Mum", "Passenger_Boy" };
        public static readonly string[] CargoIds = { "Cargo_Crate", "Cargo_Logs", "Cargo_Milk", "Cargo_Hay" };
        public const int MaxWaiting = 3;
        public const int SeatsPerCarriage = 4;
        public const int MaxPile = 4;
        private const float WalkSpeed = 1.3f;
        private const float RespawnSeconds = 7f;

        /// <summary>A line for the narrator ("all_aboard", "bye_bye", "load_cargo", "delivery", "add_carriage", "add_wagon").</summary>
        public static event Action<string> Happened;
        /// <summary>Raised when a train's stop activity starts/ends (tests use it).</summary>
        public event Action<TrainController, int> ActivityFinished;

        private class Stop
        {
            public int node;
            public bool cargo;
            public readonly List<Transform> waiting = new List<Transform>();
            public readonly List<Transform> pile = new List<Transform>();
            public float respawn;
            public bool busy;
        }

        private readonly Dictionary<int, Stop> stops = new Dictionary<int, Stop>();
        private readonly Dictionary<TrainVehicle, List<string>> riders = new Dictionary<TrainVehicle, List<string>>();
        private readonly Dictionary<TrainVehicle, Transform> loads = new Dictionary<TrainVehicle, Transform>();

        public int WaitingAt(int node) => stops.TryGetValue(node, out Stop s) ? s.waiting.Count : 0;
        public int PileAt(int node) => stops.TryGetValue(node, out Stop s) ? s.pile.Count : 0;
        public int RidersIn(TrainVehicle v) => v != null && riders.TryGetValue(v, out List<string> r) ? r.Count : 0;
        public bool IsLoaded(TrainVehicle v) => v != null && loads.TryGetValue(v, out Transform t) && t != null;

        private void Awake() => Instance = this;

        private void OnEnable() => TrainController.ArrivedAtStop += OnArrived;
        private void OnDisable() => TrainController.ArrivedAtStop -= OnArrived;

        private void Start()
        {
            if (network != null)
            {
                network.NetworkChanged += SyncStops;
                network.PieceRemoved += OnPieceRemoved;
            }
            SyncStops();
        }

        // ------------------------------------------------------------------------------------------------ stops
        private void SyncStops()
        {
            if (network == null) return;
            foreach (TrackNode n in network.Graph.Nodes.Values)
            {
                if (!TrackShapeLibrary.IsStop(n.type) || stops.ContainsKey(n.id)) continue;
                stops[n.id] = new Stop { node = n.id, cargo = n.type == TrackType.CargoStation, respawn = 0.5f };
            }
            var gone = new List<int>();
            foreach (int id in stops.Keys) if (network.Graph.Get(id) == null) gone.Add(id);
            foreach (int id in gone) ClearStop(id);
        }

        private void OnPieceRemoved(int id) => ClearStop(id);

        private void ClearStop(int id)
        {
            if (!stops.TryGetValue(id, out Stop s)) return;
            foreach (Transform t in s.waiting) if (t != null) Destroy(t.gameObject);
            foreach (Transform t in s.pile) if (t != null) Destroy(t.gameObject);
            stops.Remove(id);
        }

        /// <summary>Platform frame of a stop: origin at the piece start, forward along the track, side towards the building.</summary>
        private bool Frame(int node, out Vector3 origin, out Vector3 forward, out Vector3 side)
        {
            origin = forward = side = Vector3.zero;
            TrackNode n = network.Graph.Get(node);
            if (n == null) return false;
            Quaternion rot = n.pose.Rotation;
            origin = n.pose.position;
            forward = rot * Vector3.forward;
            side = rot * Vector3.right;
            TrackPieceView view = network.View(node);
            if (view != null && view.Accessory != null)
            {
                Bounds b = RendererBounds(view.Accessory);
                if (Vector3.Dot(b.center - origin, side) < 0f) side = -side;
            }
            return true;
        }

        private static Bounds RendererBounds(Transform root)
        {
            Renderer[] rs = root.GetComponentsInChildren<Renderer>();
            if (rs.Length == 0) return new Bounds(root.position, Vector3.one);
            Bounds b = rs[0].bounds;
            for (int i = 1; i < rs.Length; i++) b.Encapsulate(rs[i].bounds);
            return b;
        }

        /// <summary>A point on the platform: <paramref name="along"/> metres along the stop, <paramref name="out_"/> from the track centre.</summary>
        private Vector3 PlatformPoint(int node, float along, float out_)
        {
            if (!Frame(node, out Vector3 o, out Vector3 f, out Vector3 s)) return Vector3.zero;
            Vector3 p = o + f * along + s * out_;
            return Ground(p);
        }

        /// <summary>Drops a point onto whatever is below (the platform deck, or the ground).</summary>
        private static readonly RaycastHit[] groundHits = new RaycastHit[12];

        private static Vector3 Ground(Vector3 p)
        {
            // Highest surface below knee height (skips roofs/canopies above and the trains themselves).
            Vector3 top = new Vector3(p.x, p.y + 1.2f, p.z);
            int n = Physics.RaycastNonAlloc(top, Vector3.down, groundHits, 3f);
            float best = float.NegativeInfinity;
            for (int i = 0; i < n; i++)
            {
                RaycastHit h = groundHits[i];
                if (h.collider.GetComponentInParent<TrainVehicle>() != null) continue;
                if (h.point.y > best) best = h.point.y;
            }
            return float.IsNegativeInfinity(best) ? p : new Vector3(p.x, best, p.z);
        }

        private static readonly float[] WaitSpots = { 1.5f, 3f, 4.5f };

        private void Update()
        {
            foreach (Stop s in stops.Values)
            {
                if (s.cargo || s.busy) continue;
                s.waiting.RemoveAll(t => t == null);
                if (s.waiting.Count >= MaxWaiting) continue;
                s.respawn -= Time.deltaTime;
                if (s.respawn > 0f) continue;
                s.respawn = RespawnSeconds;
                SpawnWaiting(s);
            }
        }

        private void SpawnWaiting(Stop s)
        {
            string id = PassengerIds[UnityEngine.Random.Range(0, PassengerIds.Length)];
            DecorationDefinition def = content != null ? content.Decoration(id) : null;
            if (def == null || def.prefab == null) return;
            int slot = s.waiting.Count;
            Vector3 spot = PlatformPoint(s.node, WaitSpots[slot % WaitSpots.Length], 1.55f);
            Vector3 entry = PlatformPoint(s.node, -0.6f, 1.9f);
            Transform p = Instantiate(def.prefab, entry, Quaternion.identity, transform).transform;
            p.name = "Waiting_" + id;
            Juice.PopIn(p, 0.3f);
            s.waiting.Add(p);
            StartCoroutine(Walk(p, spot, () => Face(p, s.node, true)));
        }

        /// <summary>Turns a passenger to face the track (or along it).</summary>
        private void Face(Transform p, int node, bool towardsTrack)
        {
            if (p == null || !Frame(node, out _, out Vector3 f, out Vector3 side)) return;
            Vector3 dir = towardsTrack ? -side : f;
            dir.y = 0f;
            if (dir.sqrMagnitude > 0.001f) p.rotation = Quaternion.LookRotation(dir, Vector3.up);
        }

        // ------------------------------------------------------------------------------------------------ arrivals
        private void OnArrived(TrainController train, int node)
        {
            if (!stops.TryGetValue(node, out Stop s)) { SyncStops(); if (!stops.TryGetValue(node, out s)) return; }
            if (s.busy) return;
            StartCoroutine(s.cargo ? CargoScene(train, s) : PassengerScene(train, s));
        }

        private IEnumerator PassengerScene(TrainController train, Stop s)
        {
            var cars = new List<TrainVehicle>();
            foreach (TrainVehicle v in train.Vehicles) if (v != null && v.IsPassengerCar) cars.Add(v);
            s.waiting.RemoveAll(t => t == null);

            if (cars.Count == 0)
            {
                // No carriage: everyone waves at the train; the conductor suggests adding one.
                foreach (Transform w in s.waiting) Wave(w);
                if (s.waiting.Count > 0 && IsDriven(train)) Happened?.Invoke("add_carriage");
                ActivityFinished?.Invoke(train, s.node);
                yield break;
            }

            s.busy = true;
            train.HoldAtStation(60f);

            // 1) Riders get off and walk away along the platform.
            int leaving = 0;
            foreach (TrainVehicle car in cars)
            {
                if (!riders.TryGetValue(car, out List<string> list) || list.Count == 0) continue;
                foreach (string id in list)
                {
                    DecorationDefinition def = content.Decoration(id);
                    if (def == null || def.prefab == null) continue;
                    Vector3 door = DoorPoint(car, s.node);
                    Transform p = Instantiate(def.prefab, door, Quaternion.identity, transform).transform;
                    StripColliders(p);
                    Juice.PopIn(p, 0.25f);
                    Vector3 exit = PlatformPoint(s.node, UnityEngine.Random.value < 0.5f ? -1.2f : TrackShapeLibrary.StationLength + 1.2f, 1.9f + UnityEngine.Random.Range(0f, 0.6f));
                    StartCoroutine(Walk(p, exit, () => { if (p != null) Juice.ShrinkOut(p, () => Destroy(p.gameObject)); }, 0.25f * leaving));
                    leaving++;
                }
                list.Clear();
            }
            if (leaving > 0)
            {
                Happened?.Invoke("bye_bye");
                yield return new WaitForSeconds(0.9f + 0.25f * leaving);
            }

            // 2) The waiting passengers board (up to the free seats).
            int boarding = 0;
            var boardingList = new List<Transform>(s.waiting);
            foreach (Transform p in boardingList)
            {
                TrainVehicle car = FreeCar(cars);
                if (car == null || p == null) break;
                s.waiting.Remove(p);
                Get(car).Add(Strip(p.name));
                Vector3 door = DoorPoint(car, s.node);
                Transform pp = p;
                StartCoroutine(Walk(pp, door, () =>
                {
                    if (pp == null) return;
                    AudioManager.Sfx(AudioManager.Clips?.button, 0.6f);
                    Juice.ShrinkOut(pp, () => Destroy(pp.gameObject));
                }, 0.35f * boarding));
                boarding++;
            }
            if (boarding > 0) Happened?.Invoke("all_aboard");
            float wait = boarding > 0 ? 1.6f + 0.35f * boarding + 1.2f : 0.4f;
            float t0 = Time.time;
            while (Time.time - t0 < wait && train != null) yield return null;

            s.busy = false;
            s.respawn = RespawnSeconds * 0.5f;
            if (train != null) train.ReleaseStation();
            ActivityFinished?.Invoke(train, s.node);
        }

        private IEnumerator CargoScene(TrainController train, Stop s)
        {
            var wagons = new List<TrainVehicle>();
            foreach (TrainVehicle v in train.Vehicles) if (v != null && v.IsCargoCar) wagons.Add(v);
            TrackPieceView view = network.View(s.node);
            Transform crane = view != null && view.Accessory != null ? FindDeep(view.Accessory, "Crane") : null;
            Transform loadPoint = view != null && view.Accessory != null ? FindDeep(view.Accessory, "LoadPoint") : null;

            if (wagons.Count == 0)
            {
                if (crane != null) Juice.Wobble(crane, 12f, 0.6f);
                if (IsDriven(train)) Happened?.Invoke("add_wagon");
                ActivityFinished?.Invoke(train, s.node);
                yield break;
            }

            s.busy = true;
            train.HoldAtStation(60f);
            bool delivered = false, loaded = false;
            foreach (TrainVehicle w in wagons)
            {
                if (w == null) continue;
                Vector3 hand = loadPoint != null ? loadPoint.position : PlatformPoint(s.node, 3f, 1.6f);
                if (IsLoaded(w))
                {
                    // Unload onto the platform pile.
                    Transform item = loads[w];
                    loads.Remove(w);
                    item.SetParent(transform, true);
                    yield return SwingCrane(crane, w.transform.position);
                    Vector3 spot = PileSpot(s, s.pile.Count);
                    yield return Arc(item, spot, 1.0f);
                    if (item != null)
                    {
                        s.pile.Add(item);
                        AudioManager.Sfx(AudioManager.Clips?.placeDecor, 0.7f);
                        Juice.Squash(item, 0.15f, 0.3f);
                    }
                    while (s.pile.Count > MaxPile)
                    {
                        Transform old = s.pile[0];
                        s.pile.RemoveAt(0);
                        if (old != null) Juice.ShrinkOut(old, () => Destroy(old.gameObject));
                    }
                    delivered = true;
                }
                else
                {
                    // Load: take from the pile, or the yard brings a new one.
                    Transform item = null;
                    if (s.pile.Count > 0) { item = s.pile[s.pile.Count - 1]; s.pile.RemoveAt(s.pile.Count - 1); }
                    if (item == null)
                    {
                        DecorationDefinition def = content.Decoration(CargoIds[UnityEngine.Random.Range(0, CargoIds.Length)]);
                        if (def == null || def.prefab == null) continue;
                        item = Instantiate(def.prefab, hand, Quaternion.identity, transform).transform;
                        item.name = "Cargo";
                        StripColliders(item);
                        Juice.PopIn(item, 0.3f);
                        yield return new WaitForSeconds(0.35f);
                    }
                    if (!loaded) Happened?.Invoke("load_cargo");
                    yield return SwingCrane(crane, w.transform.position);
                    if (w == null || item == null) continue;
                    Transform bed = w.cargoBed != null ? w.cargoBed : w.transform;
                    Vector3 target = w.cargoBed != null ? bed.position : w.transform.position + Vector3.up * 0.6f;
                    yield return Arc(item, target, 1.0f);
                    if (w == null || item == null) continue;
                    item.SetParent(bed, true);
                    item.localPosition = w.cargoBed != null ? Vector3.zero : item.localPosition;
                    item.localRotation = Quaternion.identity;
                    loads[w] = item;
                    AudioManager.Sfx(AudioManager.Clips?.trackSnap, 0.7f);
                    Juice.Squash(w.body != null ? w.body : w.transform, 0.08f, 0.3f);
                    loaded = true;
                }
            }
            if (delivered && !loaded) Happened?.Invoke("delivery");
            if (crane != null) yield return SwingCrane(crane, null);
            yield return new WaitForSeconds(0.4f);
            s.busy = false;
            if (train != null) train.ReleaseStation();
            ActivityFinished?.Invoke(train, s.node);
        }

        private Vector3 PileSpot(Stop s, int i)
        {
            float along = 1.2f + (i % 4) * 1.1f;
            return PlatformPoint(s.node, along, 2.4f);
        }

        // ------------------------------------------------------------------------------------------------ helpers
        /// <summary>Hints that ask the child to change a train only make sense for the train they are driving.</summary>
        private static bool IsDriven(TrainController t) => TrainManager.Instance == null || TrainManager.Instance.Current == t;

        private List<string> Get(TrainVehicle car)
        {
            if (!riders.TryGetValue(car, out List<string> l)) riders[car] = l = new List<string>();
            return l;
        }

        private TrainVehicle FreeCar(List<TrainVehicle> cars)
        {
            foreach (TrainVehicle c in cars) if (c != null && Get(c).Count < SeatsPerCarriage) return c;
            return null;
        }

        private Vector3 DoorPoint(TrainVehicle car, int node)
        {
            Frame(node, out _, out _, out Vector3 side);
            Transform best = null;
            float bestD = float.MinValue;
            foreach (Transform d in car.doors)
            {
                float score = Vector3.Dot(d.position - car.transform.position, side);
                if (score > bestD) { bestD = score; best = d; }
            }
            Vector3 p = best != null ? best.position : car.transform.position + side * 0.9f;
            return Ground(p + side * 0.25f);
        }

        private static string Strip(string name)
        {
            foreach (string id in PassengerIds) if (name.Contains(id)) return id;
            return PassengerIds[0];
        }

        private static void StripColliders(Transform t)
        {
            foreach (Collider c in t.GetComponentsInChildren<Collider>()) Destroy(c);
        }

        private static void Wave(Transform p)
        {
            if (p == null) return;
            Transform arm = FindDeep(p, "ArmR") ?? FindDeep(p, "ArmL");
            if (arm != null) Juice.Wobble(arm, 40f, 0.9f);
            Juice.Bounce(p, 0.15f, 0.4f);
        }

        private static Transform FindDeep(Transform root, string name)
        {
            foreach (Transform c in root.GetComponentsInChildren<Transform>(true)) if (c.name == name) return c;
            return null;
        }

        /// <summary>Walks (with a little hop) to a point, then calls <paramref name="arrived"/>.</summary>
        private IEnumerator Walk(Transform p, Vector3 to, Action arrived, float delay = 0f)
        {
            if (delay > 0f) yield return new WaitForSeconds(delay);
            float phase = 0f;
            while (p != null)
            {
                Vector3 pos = p.position;
                Vector3 flat = new Vector3(to.x - pos.x, 0f, to.z - pos.z);
                float d = flat.magnitude;
                if (d < 0.05f) break;
                Vector3 step = flat / d * Mathf.Min(d, WalkSpeed * Time.deltaTime);
                phase += Time.deltaTime * 12f;
                float baseY = Mathf.Lerp(pos.y, to.y, Mathf.Clamp01(Time.deltaTime * 6f));
                p.position = new Vector3(pos.x + step.x, baseY, pos.z + step.z);
                if (flat.sqrMagnitude > 0.0001f) p.rotation = Quaternion.Slerp(p.rotation, Quaternion.LookRotation(flat, Vector3.up), Time.deltaTime * 10f);
                Transform body = p.childCount > 0 ? p.GetChild(0) : null;
                if (body != null) body.localPosition = new Vector3(body.localPosition.x, Mathf.Abs(Mathf.Sin(phase)) * 0.07f, body.localPosition.z);
                yield return null;
            }
            if (p != null)
            {
                Transform body = p.childCount > 0 ? p.GetChild(0) : null;
                if (body != null) body.localPosition = new Vector3(body.localPosition.x, 0f, body.localPosition.z);
                p.position = to;
            }
            arrived?.Invoke();
        }

        /// <summary>Moves an item along a friendly arc (a crane lift) to a world point.</summary>
        private static IEnumerator Arc(Transform item, Vector3 to, float duration)
        {
            if (item == null) yield break;
            Vector3 from = item.position;
            float height = 1.4f + Mathf.Max(0f, to.y - from.y);
            for (float t = 0f; t < 1f && item != null; t += Time.deltaTime / duration)
            {
                float k = Mathf.SmoothStep(0f, 1f, t);
                Vector3 p = Vector3.Lerp(from, to, k);
                p.y += Mathf.Sin(k * Mathf.PI) * height;
                item.position = p;
                yield return null;
            }
            if (item != null) item.position = to;
        }

        /// <summary>Turns the crane towards a point (or back to rest when null).</summary>
        private static IEnumerator SwingCrane(Transform crane, Vector3? towards)
        {
            if (crane == null) { yield return new WaitForSeconds(0.2f); yield break; }
            Quaternion start = crane.localRotation;
            Quaternion end = Quaternion.identity;
            if (towards.HasValue && crane.parent != null)
            {
                Vector3 local = crane.parent.InverseTransformPoint(towards.Value) - crane.localPosition;
                local.y = 0f;
                if (local.sqrMagnitude > 0.01f) end = Quaternion.LookRotation(local.normalized, Vector3.up);
            }
            for (float t = 0f; t < 1f && crane != null; t += Time.deltaTime / 0.5f)
            {
                crane.localRotation = Quaternion.Slerp(start, end, Mathf.SmoothStep(0f, 1f, t));
                yield return null;
            }
        }

        /// <summary>Removes everything (new world / clear).</summary>
        public void ClearAll()
        {
            StopAllCoroutines();
            foreach (int id in new List<int>(stops.Keys)) ClearStop(id);
            foreach (Transform t in loads.Values) if (t != null) Destroy(t.gameObject);
            loads.Clear();
            riders.Clear();
            SyncStops();
        }
    }
}
