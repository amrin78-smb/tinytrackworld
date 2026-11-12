using System.Collections.Generic;
using TinyTracks.Core;
using TinyTracks.World;
using UnityEngine;

namespace TinyTracks.EditorTools
{
    /// <summary>
    /// Hand-arranged + seeded-scatter dressing for Sunny Valley, all outside the buildable area (|x| > 30 or |z| > 22)
    /// so it never blocks the child's railway. +Z is "behind" the default camera view (models face +Z, so yaw 180
    /// faces them towards the player).
    /// </summary>
    public static class WorldLayout
    {
        public static List<WorldProp> SunnyValley(ContentLibrary lib)
        {
            var list = new List<WorldProp>();
            var rng = new System.Random(1234);
            float R(float a, float b) => a + (float)rng.NextDouble() * (b - a);

            void Add(string id, float x, float z, float yaw = 180f, float scale = 1f, float y = 0f)
            {
                if (lib.Decoration(id) == null) return;
                list.Add(new WorldProp { decorationId = id, position = new Vector3(x, y, z), yaw = yaw, scale = scale });
            }

            // Farm (back left)
            Add("Barn", -22f, 31f, 165f);
            Add("Farmhouse", -9f, 32f, 190f);
            Add("Well", -15f, 27f, 200f);
            Add("HayBale", -27f, 26f, 30f); Add("HayBale", -25.5f, 25.3f, 70f); Add("HayBale", -29f, 28f, 10f);
            for (int i = 0; i < 6; i++) Add("Fence", -44f + i * 2f, 23.5f, 0f);
            for (int i = 0; i < 6; i++) Add("Fence", -33f, 24.5f + i * 2f, 90f);
            Add("Cow", -40f, 27f, 150f); Add("Cow", -36f, 30f, 210f);
            Add("Sheep", -42f, 31f, 120f); Add("Sheep", -39f, 33f, 200f); Add("Sheep", -36.5f, 26f, 240f);
            Add("Horse", -46f, 29f, 100f);
            Add("Chicken", -17f, 25f, 200f); Add("Chicken", -18.5f, 24.3f, 150f); Add("Chicken", -16f, 24f, 230f);
            Add("Person_Farmer", -13f, 24.5f, 190f);
            Add("Tree_Apple", -4f, 29f); Add("Tree_Apple", -2f, 34f);
            Add("Dog", -11f, 25.5f, 220f);

            // Village (back right)
            Add("House_A", 10f, 31f, 185f);
            Add("House_B", 19f, 32f, 175f);
            Add("Shop", 3f, 30f, 180f);
            Add("House_A", 27f, 33f, 195f, 0.95f);
            Add("Lamp", 6.5f, 25.5f, 180f); Add("Lamp", 15f, 25.5f, 180f); Add("Lamp", 23f, 26f, 180f);
            Add("Bench", 11f, 25f, 180f); Add("Mailbox", 14f, 26.5f, 180f);
            Add("Person_Child", 12.5f, 24.5f, 200f); Add("Person_Conductor", 1f, 24.5f, 170f);
            Add("Cat", 21f, 26f, 160f);
            Add("Sign_Arrow", 0f, 23.5f, 180f);
            Add("Tree_Round", 33f, 30f); Add("Tree_Birch", 35f, 25f);

            // Windmill on the rise behind the lake, lake shore extras
            Add("Windmill", 40f, 34f, 210f, 1.1f);
            Add("Rock_Large", 36f, -14f, 30f); Add("Rock_Small", 38f, -16f, 80f); Add("Rock_Small", 55f, 9f, 10f);
            Add("Bush", 34f, 9f); Add("Bush", 57f, -12f); Add("Flowers_Yellow", 35f, 4f);
            Add("Mushroom", 33f, -9f);

            // Forest (left)
            string[] trees = { "Tree_Pine", "Tree_Round", "Tree_Birch", "Tree_Pine" };
            for (int i = 0; i < 46; i++)
            {
                float x = R(-62f, -33f), z = R(-30f, 20f);
                Add(trees[i % trees.Length], x, z, R(0f, 360f), R(0.85f, 1.25f));
            }
            for (int i = 0; i < 10; i++) Add("Bush", R(-40f, -32f), R(-20f, 18f), R(0f, 360f), R(0.8f, 1.2f));
            for (int i = 0; i < 6; i++) Add("Mushroom", R(-45f, -33f), R(-15f, 15f), R(0f, 360f));

            // Hills all around: scattered trees so the horizon is soft and alive.
            for (int i = 0; i < 70; i++)
            {
                float a = R(0f, Mathf.PI * 2f), r = R(62f, 95f);
                float x = Mathf.Cos(a) * r * 1.1f, z = Mathf.Sin(a) * r * 0.9f;
                if (z < -50f) continue; // nothing right in front of the camera
                Add(trees[i % trees.Length], x, z, R(0f, 360f), R(1.0f, 1.6f));
            }

            // Meadow detail near the edges of the buildable area (front and sides).
            string[] flowers = { "Flowers_Red", "Flowers_Yellow", "Flowers_Purple", "Grass_Tuft" };
            for (int i = 0; i < 60; i++)
            {
                float x, z;
                int side = i % 4;
                if (side == 0) { x = R(-30f, 30f); z = R(-34f, -24f); }
                else if (side == 1) { x = R(31f, 36f); z = R(-20f, 20f); if (x > 34f && z > -16f && z < 12f) continue; }
                else if (side == 2) { x = R(-30f, 30f); z = R(23f, 26f); }
                else { x = R(-33f, -30.5f); z = R(-20f, 20f); }
                Add(flowers[i % flowers.Length], x, z, R(0f, 360f), R(0.8f, 1.2f));
            }
            Add("Rock_Large", -26f, -28f, 40f); Add("Rock_Small", 24f, -27f, 120f); Add("Tree_Round", -18f, -36f); Add("Tree_Round", 20f, -38f);

            // Sky
            for (int i = 0; i < 9; i++) Add(i % 2 == 0 ? "Cloud_A" : "Cloud_B", R(-100f, 100f), R(-20f, 90f), R(0f, 360f), R(0.9f, 1.5f), R(20f, 28f));
            for (int i = 0; i < 4; i++) Add("Bird", R(-20f, 20f), R(0f, 30f), 0f, 1f, 8f);
            return list;
        }

        /// <summary>Starter decorations around the oval railway in a new Sunny Valley world.</summary>
        public static List<WorldProp> SunnyStarter(ContentLibrary lib) => Starter(lib, new (string, float, float, float)[]
        {
            ("House_A", 12f, 9f, 200f), ("Tree_Round", 17f, 5f, 0f), ("Tree_Apple", -15f, 7f, 0f), ("Tree_Pine", -19f, 1f, 30f),
            ("Cow", -15f, -6f, 120f), ("Sheep", -13f, -10f, 200f), ("Flowers_Red", 5f, 4f, 0f), ("Flowers_Yellow", -6f, 5f, 0f),
            ("Bush", 14f, -12f, 0f), ("Person_Conductor", -1.5f, -10.4f, 180f), ("Dog", 9f, 5f, 210f), ("Fence", -16f, -13f, 0f),
        });

        /// <summary>Starter decorations around the oval railway in a new Snowy Valley world.</summary>
        public static List<WorldProp> SnowyStarter(ContentLibrary lib) => Starter(lib, new (string, float, float, float)[]
        {
            ("Cabin_Snowy", 13f, 10f, 200f), ("Tree_SnowyPine", 18f, 4f, 0f), ("Tree_SnowyRound", -15f, 7f, 0f), ("Tree_SnowyPineSmall", -19f, 1f, 30f),
            ("Penguin", -14f, -6f, 140f), ("Penguin", -12.8f, -6.6f, 200f), ("Reindeer", -13f, -11f, 200f), ("Snowman", 6f, 5f, 190f),
            ("Bush_Snowy", 14f, -12f, 0f), ("Person_Conductor", -1.5f, -10.4f, 180f), ("Husky", 9f, 4f, 210f), ("Sled", -16f, -13f, 30f),
            ("Lamp_Snowy", 3f, -11f, 180f),
        });

        private static List<WorldProp> Starter(ContentLibrary lib, (string id, float x, float z, float yaw)[] items)
        {
            var list = new List<WorldProp>();
            foreach (var d in items)
                if (lib.Decoration(d.id) != null) list.Add(new WorldProp { decorationId = d.id, position = new Vector3(d.x, 0f, d.z), yaw = d.yaw, scale = 1f });
            return list;
        }

        /// <summary>
        /// Snowy Valley dressing (outside the buildable area): a log-cabin village with snowmen and huskies (back right),
        /// a reindeer meadow (back left), penguins and an igloo by the frozen lake (left), a snowy pine forest (right)
        /// and frosted hills all round.
        /// </summary>
        public static List<WorldProp> SnowyValley(ContentLibrary lib)
        {
            var list = new List<WorldProp>();
            var rng = new System.Random(4321);
            float R(float a, float b) => a + (float)rng.NextDouble() * (b - a);
            void Add(string id, float x, float z, float yaw = 180f, float scale = 1f, float y = 0f)
            {
                if (lib.Decoration(id) == null) return;
                list.Add(new WorldProp { decorationId = id, position = new Vector3(x, y, z), yaw = yaw, scale = scale });
            }

            // Cabin village (back right)
            Add("Cabin_Snowy", 8f, 31f, 185f); Add("Cabin_Snowy", 18f, 33f, 170f, 1.1f); Add("Cabin_Snowy", 28f, 31f, 200f, 0.95f);
            Add("Lamp_Snowy", 4f, 25.5f, 180f); Add("Lamp_Snowy", 13f, 25.5f, 180f); Add("Lamp_Snowy", 23f, 26f, 180f);
            Add("Snowman", 11f, 26f, 190f); Add("Snowman", 25f, 27f, 160f, 0.9f);
            Add("Sled", 16f, 26.5f, 120f); Add("Husky", 19f, 25.5f, 200f); Add("Husky", 20.5f, 26.3f, 160f);
            Add("Person_Child", 14.5f, 24.8f, 200f); Add("Person_Conductor", 1f, 24.5f, 170f);
            Add("Tree_SnowyPine", 34f, 30f); Add("Tree_SnowyRound", 36f, 25f);

            // Reindeer meadow (back left)
            Add("Reindeer", -22f, 30f, 150f); Add("Reindeer", -17f, 33f, 210f); Add("Reindeer", -27f, 27f, 120f, 0.9f);
            Add("Snowdrift", -20f, 26f, 0f, 1.3f); Add("Rock_Snowy", -12f, 31f, 40f); Add("Tree_SnowyPineSmall", -9f, 28f);

            // Frozen lake (left, centre -46,6): igloo and penguins on the shore
            Add("Igloo", -36f, 22f, 150f);
            for (int i = 0; i < 6; i++) Add("Penguin", R(-40f, -33f), R(14f, 20f), R(120f, 240f), R(0.9f, 1.1f));
            Add("Rock_Snowy", -33f, -6f, 30f); Add("Rock_Snowy", -58f, 18f, 80f, 1.2f); Add("Snowdrift", -34f, 0f, 0f);

            // Snowy forest (right)
            string[] trees = { "Tree_SnowyPine", "Tree_SnowyPineSmall", "Tree_SnowyRound", "Tree_SnowyPine" };
            for (int i = 0; i < 46; i++) Add(trees[i % trees.Length], R(33f, 62f), R(-30f, 20f), R(0f, 360f), R(0.85f, 1.25f));
            for (int i = 0; i < 10; i++) Add("Bush_Snowy", R(32f, 40f), R(-20f, 18f), R(0f, 360f), R(0.8f, 1.2f));

            // Hills all round
            for (int i = 0; i < 70; i++)
            {
                float a = R(0f, Mathf.PI * 2f), r = R(62f, 95f);
                float x = Mathf.Cos(a) * r * 1.1f, z = Mathf.Sin(a) * r * 0.9f;
                if (z < -50f) continue;
                Add(trees[i % trees.Length], x, z, R(0f, 360f), R(1.0f, 1.6f));
            }

            // Snowdrifts and frosted rocks along the edges of the buildable area
            string[] edge = { "Snowdrift", "Bush_Snowy", "Rock_Snowy", "Snowdrift" };
            for (int i = 0; i < 40; i++)
            {
                float x, z;
                int side = i % 4;
                if (side == 0) { x = R(-30f, 30f); z = R(-34f, -24f); }
                else if (side == 1) { x = R(31f, 34f); z = R(-20f, 20f); }
                else if (side == 2) { x = R(-30f, 30f); z = R(23f, 26f); }
                else { x = R(-33f, -30.5f); z = R(-20f, -8f); }
                Add(edge[i % edge.Length], x, z, R(0f, 360f), R(0.8f, 1.2f));
            }

            // Sky: a few soft clouds, no birds.
            for (int i = 0; i < 7; i++) Add(i % 2 == 0 ? "Cloud_A" : "Cloud_B", R(-100f, 100f), R(-20f, 90f), R(0f, 360f), R(0.9f, 1.5f), R(20f, 28f));
            return list;
        }
    }
}
