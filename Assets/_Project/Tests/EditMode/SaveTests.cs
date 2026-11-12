using NUnit.Framework;
using TinyTracks.SaveSystem;
using UnityEngine;

namespace TinyTracks.Tests
{
    public class SaveTests
    {
        [Test]
        public void RoundTrip_PreservesData()
        {
            var w = new WorldSave();
            w.tracks.Add(new TrackSave { id = 3, type = "TightLeft", x = 1.5f, z = -2f, yaw = 90f, sw = 1 });
            w.decorations.Add(new DecorationSave { id = 1, def = "Cow", x = 4f, z = 5f, yaw = 45f });
            w.train.loco = "Loco_RedExpress";
            w.train.cars.Add("Car_Passenger");
            WorldSave b = SaveManager.Parse(JsonUtility.ToJson(w));
            Assert.IsNotNull(b);
            Assert.AreEqual(1, b.tracks.Count);
            Assert.AreEqual("TightLeft", b.tracks[0].type);
            Assert.AreEqual(1, b.tracks[0].sw);
            Assert.AreEqual("Cow", b.decorations[0].def);
            Assert.AreEqual("Car_Passenger", b.train.cars[0]);
        }

        [TestCase("")]
        [TestCase("{ this is not json")]
        [TestCase("{\"version\": 99, \"tracks\": []}")]
        [TestCase("{\"version\": 0}")]
        [TestCase("\u0000\u0000\u0000")]
        public void Corrupted_OrFutureSaves_AreRejected(string json)
        {
            Assert.IsNull(SaveManager.Parse(json));
        }

        [Test]
        public void MissingLists_AreRepaired()
        {
            WorldSave w = SaveManager.Parse("{\"version\": 1}");
            Assert.IsNotNull(w);
            Assert.IsNotNull(w.tracks);
            Assert.IsNotNull(w.decorations);
            Assert.IsNotNull(w.train);
        }
    }
}
