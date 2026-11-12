using System;
using System.Collections.Generic;
using TinyTracks.Audio;
using TinyTracks.Core;
using TinyTracks.Tracks;
using UnityEngine;

namespace TinyTracks.Trains
{
    public enum TrainState { Stopped, Running, AtStation, BlockedAtEnd }

    /// <summary>
    /// A locomotive with optional carriages, driven along the railway graph by a <see cref="TrainSpine"/>.
    /// Automatic by default: GO runs it around loops forever; it brakes smoothly for dead ends (never runs off the
    /// track), pauses at stations, closes level crossings, and GO at a dead end turns the whole train round.
    /// </summary>
    public class TrainController : MonoBehaviour
    {
        public const float RideHeight = 0.16f;
        public const float CouplingGap = 0.12f;
        public static readonly float[] SpeedLevels = { 1.6f, 2.8f, 4.2f };

        public float acceleration = 1.4f;
        public float braking = 2.2f;
        public float stationWait = 3f;

        public TrainState State { get; private set; } = TrainState.Stopped;
        public bool Running { get; private set; }
        public int SpeedLevel { get; private set; } = 1;
        public float Speed { get; private set; }
        public TrainSpine Spine { get; } = new TrainSpine();
        public IReadOnlyList<TrainVehicle> Vehicles => vehicles;
        public TrainVehicle Locomotive => vehicles.Count > 0 ? vehicles[0] : null;
        /// <summary>Follows the locomotive and survives consist changes (the camera follows this).</summary>
        public Transform Anchor { get; private set; }
        public bool LocoLeads { get; private set; } = true;
        public float TrainLength { get; private set; }
        public event Action<TrainState> StateChanged;
        /// <summary>Any train stopped at a station or cargo yard: (train, stop node id).</summary>
        public static event Action<TrainController, int> ArrivedAtStop;
        /// <summary>A train has been waiting behind another one for a moment (the narrator explains).</summary>
        public static event Action<TrainController> WaitingForTrain;
        /// <summary>The train this one is waiting behind (null when the way is clear).</summary>
        public TrainController BlockedBy { get; private set; }
        public float BlockedTime { get; private set; }
        /// <summary>Safe gap kept to the train ahead (metres, front to back).</summary>
        public const float TrainGap = 1.6f;
        private static readonly List<Vector3> aheadPoints = new List<Vector3>(64);
        private bool waitingAnnounced;
        /// <summary>The stop node the train is standing at (-1 when not stopped at one).</summary>
        public int StopNode { get; private set; } = -1;

        private readonly List<TrainVehicle> vehicles = new List<TrainVehicle>();
        private TrackGraph graph;
        private float stationTimer;
        private int ignoreStation = -1;
        private AudioSource engineLoop, rollLoop;
        private float puffTimer;
        private TrainEffects effects;

        public void Init(TrackGraph g, TrainDefinition loco, IList<TrainDefinition> cars, TrainEffects fx)
        {
            graph = g;
            effects = fx;
            Anchor = new GameObject("FollowAnchor").transform;
            Anchor.SetParent(transform, false);
            SetConsist(loco, cars);
            AudioConfig clips = AudioManager.Clips;
            if (AudioManager.Instance != null && clips != null)
            {
                engineLoop = AudioManager.Instance.CreateLoop(gameObject, loco != null && loco.engine == EngineSound.Motor ? clips.motorLoop : clips.chugLoop);
                rollLoop = AudioManager.Instance.CreateLoop(gameObject, clips.rollingLoop);
            }
        }

        public void SetConsist(TrainDefinition loco, IList<TrainDefinition> cars)
        {
            foreach (TrainVehicle v in vehicles) if (v != null) Destroy(v.gameObject);
            vehicles.Clear();
            vehicles.Add(TrainVehicle.Create(loco, transform));
            if (cars != null) foreach (TrainDefinition c in cars) if (c != null) vehicles.Add(TrainVehicle.Create(c, transform));
            TrainLength = 0f;
            foreach (TrainVehicle v in vehicles) TrainLength += v.Length + CouplingGap;
            if (PaintColor.HasValue) foreach (TrainVehicle v in vehicles) v.Paint(PaintColor);
            if (Spine.IsValid)
            {
                float have = Spine.ExtendBehind(graph, TrainLength + 1f);
                if (have < TrainLength) Spine.Advance(graph, TrainLength - have, TrainLength + 2f);
                UpdateVehicles(0f);
            }
            if (engineLoop != null && loco != null && AudioManager.Clips != null)
            {
                engineLoop.clip = loco.engine == EngineSound.Motor ? AudioManager.Clips.motorLoop : AudioManager.Clips.chugLoop;
                if (engineLoop.isPlaying) engineLoop.Play();
            }
        }

        /// <summary>The colour the child painted this train (null = original colours).</summary>
        public Color? PaintColor { get; private set; }

        public void Paint(Color? colour)
        {
            PaintColor = colour;
            foreach (TrainVehicle v in vehicles) if (v != null) v.Paint(colour);
        }

        public TrainDefinition LocoDefinition => vehicles.Count > 0 ? vehicles[0].definition : null;

        public List<TrainDefinition> CarDefinitions()
        {
            var list = new List<TrainDefinition>();
            for (int i = 1; i < vehicles.Count; i++) list.Add(vehicles[i].definition);
            return list;
        }

        /// <summary>Puts the head of the train at a path position and fills the track behind it.</summary>
        public bool PlaceAt(int node, int path, float s, bool forward)
        {
            if (graph.Get(node) == null) return false;
            Spine.Place(graph, node, path, s, forward);
            float have = Spine.ExtendBehind(graph, TrainLength + 1f);
            if (have < TrainLength) Spine.Advance(graph, TrainLength - have, TrainLength + 2f);
            LocoLeads = true;
            Speed = 0f;
            UpdateVehicles(0f);
            return true;
        }

        public void Go()
        {
            if (State == TrainState.BlockedAtEnd || (State == TrainState.Stopped && DeadEndAhead() < 0.6f))
            {
                // Turn round and drive away from the end.
                Spine.Reverse(graph, TrainLength);
                LocoLeads = !LocoLeads;
                ignoreStation = -1;
                effects?.Puff(Locomotive != null ? Locomotive.transform.position + Vector3.up * 1.2f : transform.position);
            }
            Running = true;
            SetState(TrainState.Running);
        }

        public void Stop()
        {
            Running = false;
            if (State != TrainState.BlockedAtEnd) SetState(TrainState.Stopped);
        }

        /// <summary>Keeps the train at its stop while passengers board or cargo is loaded.</summary>
        public void HoldAtStation(float seconds)
        {
            if (State == TrainState.AtStation) stationTimer = Mathf.Max(stationTimer, seconds);
        }

        /// <summary>Lets the train leave shortly (the station activity has finished).</summary>
        public void ReleaseStation(float delay = 0.6f)
        {
            if (State == TrainState.AtStation) stationTimer = Mathf.Min(stationTimer, delay);
        }

        public void SetSpeedLevel(int level) => SpeedLevel = Mathf.Clamp(level, 0, SpeedLevels.Length - 1);

        public void Whistle()
        {
            AudioManager.Sfx(AudioManager.Clips?.whistle);
            if (Locomotive != null) Juice.Bounce(Locomotive.body, 0.18f, 0.4f);
            if (Locomotive != null && Locomotive.smokePoint != null) effects?.Puff(Locomotive.smokePoint.position, 1.4f);
        }

        public void Bell()
        {
            AudioManager.Sfx(AudioManager.Clips?.bell);
            if (Locomotive != null) Juice.Squash(Locomotive.body, 0.08f, 0.35f);
        }

        private void SetState(TrainState s)
        {
            if (State == s) return;
            State = s;
            StateChanged?.Invoke(s);
        }

        private float DeadEndAhead()
        {
            LookAhead la = Spine.Scan(graph, 3f, -1);
            return la.deadEndDistance;
        }

        private void Update()
        {
            if (graph == null || !Spine.IsValid) return;
            float dt = Mathf.Min(Time.deltaTime, 0.05f);
            float cruise = SpeedLevels[SpeedLevel];
            float look = cruise * cruise / (2f * braking) + 8f;
            LookAhead la = Spine.Scan(graph, look, ignoreStation);

            // Leave a station once we have moved off it.
            if (ignoreStation >= 0 && !Spine.Occupies(ignoreStation)) ignoreStation = -1;

            float target = Running ? cruise : 0f;
            if (State == TrainState.AtStation)
            {
                target = 0f;
                stationTimer -= dt;
                if (stationTimer <= 0f)
                {
                    ignoreStation = la.stationNode >= 0 ? la.stationNode : ignoreStation;
                    StopNode = -1;
                    SetState(Running ? TrainState.Running : TrainState.Stopped);
                }
            }
            else
            {
                if (!float.IsPositiveInfinity(la.deadEndDistance))
                    target = Mathf.Min(target, Mathf.Sqrt(2f * braking * Mathf.Max(0f, la.deadEndDistance - 0.25f)));
                if (Running && la.stationNode >= 0)
                {
                    float d = Mathf.Max(0f, la.stationDistance);
                    target = Mathf.Min(target, Mathf.Max(0.25f, Mathf.Sqrt(2f * braking * d)));
                    if (d < 0.08f)
                    {
                        target = 0f;
                        Speed = 0f;
                        stationTimer = stationWait;
                        ignoreStation = la.stationNode;
                        StopNode = la.stationNode;
                        SetState(TrainState.AtStation);
                        AudioManager.Sfx(AudioManager.Clips?.stationChime, 0.8f);
                        ArrivedAtStop?.Invoke(this, StopNode);
                    }
                }
            }

            Speed = Mathf.MoveTowards(Speed, target, (target > Speed ? acceleration : braking) * dt);
            float moved = Speed > 0f ? Spine.Advance(graph, Speed * dt, TrainLength + 2f) : 0f;
            if (Speed > 0f && moved < Speed * dt * 0.5f) Speed = 0f;

            if (Running && State == TrainState.Running && Speed < 0.02f && la.deadEndDistance < 0.5f)
            {
                SetState(TrainState.BlockedAtEnd);
                effects?.ShowDeadEnd(Spine.PointAhead(graph, 0.4f));
            }
            else if (State == TrainState.BlockedAtEnd && la.deadEndDistance > 1f)
            {
                // Track was extended in front of the waiting train: carry on.
                SetState(Running ? TrainState.Running : TrainState.Stopped);
                effects?.HideDeadEnd();
            }

            // Other trains: keep a safe gap, and never get stuck nose to nose.
            if (State != TrainState.AtStation)
            {
                float gap = TrainAhead(look, out TrainController other);
                if (!float.IsPositiveInfinity(gap))
                {
                    float allowed = Mathf.Sqrt(2f * braking * Mathf.Max(0f, gap - TrainGap));
                    if (allowed < Speed) Speed = Mathf.MoveTowards(Speed, allowed, braking * 2f * dt);
                }
                UpdateBlocked(dt, gap, other);
            }

            if (la.crossingNode >= 0 && la.crossingDistance < 10f) CrossingBarrier.KeepClosed(la.crossingNode);
            foreach (Span sp in Spine.Spans) CrossingBarrier.KeepClosed(sp.node);

            UpdateVehicles(moved);
            UpdateEffects(dt);
        }

        private void UpdateVehicles(float moved)
        {
            float offset = 0f;
            int n = vehicles.Count;
            for (int k = 0; k < n; k++)
            {
                // From the head of the train backwards: loco first when it leads, last carriage first otherwise.
                TrainVehicle v = vehicles[LocoLeads ? k : n - 1 - k];
                float front, rear;
                if (LocoLeads) { front = offset + v.FrontOverhang; rear = front + v.BogieSpacing; }
                else { rear = offset + v.RearOverhang; front = rear + v.BogieSpacing; }
                Vector3 pf = Spine.PointBehind(graph, front);
                Vector3 pr = Spine.PointBehind(graph, rear);
                Vector3 dir = pf - pr;
                if (dir.sqrMagnitude < 1e-6f) dir = v.transform.forward;
                Vector3 mid = (pf + pr) * 0.5f;
                Quaternion rot = Quaternion.LookRotation(dir.normalized, Vector3.up);
                v.transform.SetPositionAndRotation(mid + Vector3.up * RideHeight - rot * v.bogieMidLocal, rot);
                v.Roll(LocoLeads ? moved : -moved);
                if (k == (LocoLeads ? 0 : n - 1) && Anchor != null) Anchor.position = v.transform.position;
                offset += v.Length + CouplingGap;
            }
        }

        private void UpdateEffects(float dt)
        {
            float speed01 = Speed / SpeedLevels[SpeedLevels.Length - 1];
            if (engineLoop != null)
            {
                float vol = (Speed > 0.05f ? 0.25f + 0.45f * speed01 : 0f) * (AudioManager.Instance != null ? AudioManager.Instance.SfxVolume : 1f);
                engineLoop.volume = Mathf.MoveTowards(engineLoop.volume, vol, dt * 1.5f);
                engineLoop.pitch = 0.75f + 0.6f * speed01;
                if (engineLoop.volume > 0.001f && !engineLoop.isPlaying) engineLoop.Play();
                else if (engineLoop.volume <= 0.001f && engineLoop.isPlaying) engineLoop.Stop();
            }
            if (rollLoop != null)
            {
                float vol = (Speed > 0.05f ? 0.15f + 0.35f * speed01 : 0f) * (AudioManager.Instance != null ? AudioManager.Instance.SfxVolume : 1f);
                rollLoop.volume = Mathf.MoveTowards(rollLoop.volume, vol, dt * 1.5f);
                rollLoop.pitch = 0.8f + 0.4f * speed01;
                if (rollLoop.volume > 0.001f && !rollLoop.isPlaying) rollLoop.Play();
                else if (rollLoop.volume <= 0.001f && rollLoop.isPlaying) rollLoop.Stop();
            }
            TrainVehicle loco = Locomotive;
            if (effects != null && loco != null && loco.smokePoint != null && Speed > 0.1f)
            {
                puffTimer -= dt * (0.6f + speed01 * 2.2f);
                if (puffTimer <= 0f)
                {
                    puffTimer = effects.PuffInterval;
                    effects.Puff(loco.smokePoint.position, 0.8f + 0.4f * speed01);
                }
            }
        }

        /// <summary>Distance along the route to the nearest other train ahead (infinity when clear).</summary>
        public float TrainAhead(float look, out TrainController other)
        {
            other = null;
            TrainManager mgr = TrainManager.Instance;
            if (mgr == null || mgr.All.Count < 2 || graph == null) return float.PositiveInfinity;
            const float step = 0.5f;
            Spine.SampleAhead(graph, step, look, aheadPoints);
            for (int i = 0; i < aheadPoints.Count; i++)
            {
                foreach (TrainController t in mgr.All)
                {
                    if (t == null || t == this) continue;
                    if (t.Touches(aheadPoints[i], 0.95f)) { other = t; return (i + 1) * step; }
                }
            }
            return float.PositiveInfinity;
        }

        /// <summary>Is a world point within <paramref name="radius"/> of any of this train's vehicles (as a line along each)?</summary>
        public bool Touches(Vector3 p, float radius)
        {
            foreach (TrainVehicle v in vehicles)
            {
                if (v == null) continue;
                Vector3 c = v.transform.TransformPoint(v.bogieMidLocal);
                if (Mathf.Abs(c.y - p.y) > 1.2f) continue;
                Vector3 f = v.transform.forward;
                f.y = 0f;
                f.Normalize();
                Vector3 d = p - c;
                d.y = 0f;
                float along = Mathf.Clamp(Vector3.Dot(d, f), -v.Length * 0.5f, v.Length * 0.5f);
                if ((d - f * along).sqrMagnitude < radius * radius) return true;
            }
            return false;
        }

        private void UpdateBlocked(float dt, float gap, TrainController other)
        {
            bool blocked = Running && State == TrainState.Running && gap < TrainGap + 0.8f && Speed < 0.05f;
            if (!blocked) { BlockedTime = 0f; BlockedBy = null; waitingAnnounced = false; return; }
            BlockedTime += dt;
            BlockedBy = other;
            if (BlockedTime > 1.5f && !waitingAnnounced) { waitingAnnounced = true; WaitingForTrain?.Invoke(this); }
            // Nobody waits forever: if the other train is parked, or the two block each other, one turns round.
            bool otherParked = other == null || !other.Running;
            bool faceToFace = other != null && other.BlockedBy == this;
            bool myTurn = !faceToFace || GetInstanceID() < other.GetInstanceID();
            if (BlockedTime > 5f && (otherParked || faceToFace) && myTurn) TurnAround();
        }

        /// <summary>Reverses direction where it stands (also used at dead ends when GO is pressed).</summary>
        public void TurnAround()
        {
            Spine.Reverse(graph, TrainLength);
            LocoLeads = !LocoLeads;
            ignoreStation = -1;
            BlockedTime = 0f;
            BlockedBy = null;
            waitingAnnounced = false;
            effects?.Puff(Locomotive != null ? Locomotive.transform.position + Vector3.up * 1.2f : transform.position);
        }

        public bool IsOnTrackIntact() => Spine.IsValid && Spine.IsIntact(graph);
    }
}
