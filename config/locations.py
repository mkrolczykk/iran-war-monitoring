"""
Curated location database for the Middle East region.

Maps location names (case-insensitive) to (latitude, longitude).
Used by the geocoder to resolve place-names found in news text.

To add a new location, simply append it to LOCATIONS dict below.
"""

from typing import Dict, Tuple

# (latitude, longitude)
Coord = Tuple[float, float]

LOCATIONS: Dict[str, Coord] = {
    # ── Iran – Major Cities ──────────────────────────────────────────
    "tehran":           (35.6892, 51.3890),
    "isfahan":          (32.6546, 51.6680),
    "esfahan":          (32.6546, 51.6680),
    "shiraz":           (29.5918, 52.5837),
    "tabriz":           (38.0800, 46.2919),
    "mashhad":          (36.2605, 59.6168),
    "ahvaz":            (31.3183, 48.6706),
    "ahwaz":            (31.3183, 48.6706),
    "kermanshah":       (34.3142, 47.0650),
    "qom":              (34.6416, 50.8746),
    "karaj":            (35.8400, 50.9391),
    "rasht":            (37.2808, 49.5832),
    "hamadan":          (34.7988, 48.5146),
    "yazd":             (31.8974, 54.3569),
    "kerman":           (30.2839, 57.0834),
    "bandar abbas":     (27.1832, 56.2666),
    "abadan":           (30.3392, 48.3043),
    "zanjan":           (36.6736, 48.4787),
    "arak":             (34.0917, 49.6892),
    "sanandaj":         (35.3097, 46.9988),
    "bushehr":          (28.9234, 50.8203),
    "khorramabad":      (33.4878, 48.3558),
    "urmia":            (37.5527, 45.0761),
    "gorgan":           (36.8427, 54.4439),
    "birjand":          (32.8664, 59.2211),
    "sari":             (36.5633, 53.0601),
    "qazvin":           (36.2688, 50.0041),
    "dezful":           (32.3811, 48.4018),
    "khoy":             (38.5503, 44.9521),
    "semnan":           (35.5769, 53.3964),
    "bojnurd":          (37.4747, 57.3317),
    "ilam":             (33.6374, 46.4227),
    "zahedan":          (29.4963, 60.8629),
    "chabahar":         (25.2919, 60.6430),

    # ── Iran – Nuclear / Military Sites ──────────────────────────────
    "natanz":           (33.5114, 51.7272),
    "fordow":           (34.7084, 51.0543),
    "parchin":          (35.5231, 51.7729),
    "bushehr nuclear":  (28.8327, 50.8881),
    "arak heavy water": (34.0500, 49.2500),
    "khondab":          (34.0500, 49.2500),
    "bandar imam khomeini": (30.4286, 49.0786),

    # ── Iran – IRGC / Military Bases ─────────────────────────────────
    "khatam al-anbiya": (35.7000, 51.4000),
    "mehrabad":         (35.6892, 51.3140),
    "imam ali base":    (32.4200, 48.2300),

    # ── Israel ───────────────────────────────────────────────────────
    "tel aviv":         (32.0853, 34.7818),
    "jerusalem":        (31.7683, 35.2137),
    "haifa":            (32.7940, 34.9896),
    "beer sheva":       (31.2518, 34.7913),
    "be'er sheva":      (31.2518, 34.7913),
    "dimona":           (31.0700, 35.0333),
    "eilat":            (29.5577, 34.9519),
    "ashkelon":         (31.6688, 34.5743),
    "ashdod":           (31.8014, 34.6435),
    "netanya":          (32.3215, 34.8532),
    "rishon lezion":    (31.9642, 34.8044),
    "negev":            (30.8500, 34.7500),
    "ramon airbase":    (30.7760, 34.6670),
    "nevatim airbase":  (31.2083, 34.9333),
    "northern israel":  (33.0000, 35.5000),

    # ── Iraq ─────────────────────────────────────────────────────────
    "baghdad":          (33.3152, 44.3661),
    "erbil":            (36.1912, 44.0119),
    "basra":            (30.5085, 47.7804),
    "mosul":            (36.3566, 43.1641),
    "kirkuk":           (35.4681, 44.3922),
    "al asad airbase":  (33.7856, 42.4412),
    "ain al-asad":      (33.7856, 42.4412),
    "sulaymaniyah":     (35.5614, 45.4306),

    # ── Syria ────────────────────────────────────────────────────────
    "damascus":         (33.5138, 36.2765),
    "aleppo":           (36.2021, 37.1343),
    "homs":             (34.7325, 36.7097),
    "latakia":          (35.5317, 35.7911),
    "deir ez-zor":      (35.3500, 40.1500),
    "palmyra":          (34.5600, 38.2700),

    # ── Lebanon ──────────────────────────────────────────────────────
    "beirut":           (33.8938, 35.5018),
    "tripoli":          (34.4367, 35.8497),  # Lebanon's Tripoli
    "sidon":            (33.5600, 35.3700),
    "tyre":             (33.2705, 35.2038),
    "baalbek":          (34.0047, 36.2110),
    "south lebanon":    (33.2000, 35.4000),
    "bekaa valley":     (33.8500, 36.0500),

    # ── Jordan ───────────────────────────────────────────────────────
    "amman":            (31.9454, 35.9284),
    "aqaba":            (29.5320, 35.0063),
    "zarqa":            (32.0728, 36.0880),
    "muwaffaq salti":   (32.3564, 36.7822),
    "muwaffaq salti air base": (32.3564, 36.7822),

    # ── Gulf States ──────────────────────────────────────────────────
    "doha":             (25.2854, 51.5310),
    "qatar":            (25.3548, 51.1839),
    "al udeid":         (25.1174, 51.3150),
    "al udeid air base": (25.1174, 51.3150),
    "abu dhabi":        (24.4539, 54.3773),
    "dubai":            (25.2048, 55.2708),
    "uae":              (24.4539, 54.3773),
    "united arab emirates": (24.4539, 54.3773),
    "manama":           (26.2285, 50.5860),
    "bahrain":          (26.0667, 50.5577),
    "juffair":          (26.2167, 50.5833),
    "kuwait":           (29.3759, 47.9774),
    "kuwait city":      (29.3759, 47.9774),
    "riyadh":           (24.7136, 46.6753),
    "jeddah":           (21.4858, 39.1925),
    "muscat":           (23.5880, 58.3829),
    "oman":             (23.5880, 58.3829),

    # ── Yemen / Horn of Africa ───────────────────────────────────────
    "sanaa":            (15.3694, 44.1910),
    "sana'a":           (15.3694, 44.1910),
    "aden":             (12.7855, 45.0187),
    "hodeidah":         (14.7980, 42.9540),
    "houthis":          (15.3694, 44.1910),
    "bab el-mandeb":    (12.5833, 43.3333),
    "djibouti":         (11.5721, 43.1456),

    # ── Egypt ────────────────────────────────────────────────────────
    "cairo":            (30.0444, 31.2357),
    "suez canal":       (30.4571, 32.3500),
    "alexandria":       (31.2001, 29.9187),

    # ── Turkey ───────────────────────────────────────────────────────
    "ankara":           (39.9334, 32.8597),
    "istanbul":         (41.0082, 28.9784),
    "incirlik":         (37.0017, 35.4258),

    # ── Pakistan ─────────────────────────────────────────────────────
    "islamabad":        (33.6844, 73.0479),

    # ── Strait of Hormuz / Maritime ──────────────────────────────────
    "strait of hormuz": (26.5667, 56.2500),
    "hormuz":           (26.5667, 56.2500),
    "persian gulf":     (26.0000, 52.0000),
    "gulf of oman":     (24.5000, 58.5000),
    "arabian sea":      (18.0000, 62.0000),
    "red sea":          (20.0000, 38.5000),
    "mediterranean":    (35.0000, 18.0000),
}


def get_location(name: str) -> Coord | None:
    """Look up coordinates by location name (case-insensitive)."""
    return LOCATIONS.get(name.lower().strip())
