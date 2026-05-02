"""Constants, balance, path waypoints, and wave definitions."""

from __future__ import annotations
import ctypes
import os

def _detect_display_size() -> tuple[int, int]:
    """Best-effort monitor resolution detection with safe fallback."""
    # Windows (primary monitor)
    if os.name == "nt":
        try:
            # Prevent DPI scaling virtualization so reported resolution matches
            # the real fullscreen backbuffer size.
            try:
                ctypes.windll.user32.SetProcessDPIAware()  # type: ignore[attr-defined]
            except Exception:
                pass
            user32 = ctypes.windll.user32  # type: ignore[attr-defined]
            w = int(user32.GetSystemMetrics(0))
            h = int(user32.GetSystemMetrics(1))
            if w >= 1024 and h >= 600:
                return w, h
        except Exception:
            pass
    # Fallback
    return 1366, 768


# Display (auto-adapts to current computer settings)
WINDOW_WIDTH, WINDOW_HEIGHT = _detect_display_size()
FPS = 60
TITLE = "Monkey vs Bananas Tower Defense"
START_FULLSCREEN = True

# World layout (playfield excludes UI sidebar)
SIDEBAR_WIDTH = max(260, min(360, int(WINDOW_WIDTH * 0.2)))
PLAY_WIDTH = WINDOW_WIDTH - SIDEBAR_WIDTH
PLAY_HEIGHT = WINDOW_HEIGHT

# Paths are defined per map in maps.py (MAP_DEFINITIONS).

BASE_MAX_HP = 100
# If any boss reaches the base, it effectively ends the run.
BOSS_LEAK_DAMAGE = 99
PATH_HALF_WIDTH = 26  # corridor for "on path" checks (wider road)

# Colors (R, G, B)
COLOR_BG = (24, 32, 42)
COLOR_PATH = (55, 48, 40)
COLOR_PATH_EDGE = (35, 30, 26)
COLOR_GRASS = (34, 72, 48)
COLOR_BASE = (180, 100, 90)
COLOR_HUD_BG = (18, 22, 28)
COLOR_TEXT = (230, 235, 240)
COLOR_BANANA = (255, 220, 60)
COLOR_BOSS = (139, 90, 43)
COLOR_UI_ACCENT = (90, 160, 255)

# Economy (tuned for 40-wave runs + 6-tier paths)
STARTING_CASH = 1000
# Cash each time you clear a wave (before next wave), scaled by wave number (wn = 0-based wave you cleared).
WAVE_ROUND_BONUS_BASE = 58
WAVE_ROUND_BONUS_PER_WAVE = 5
KILL_REWARD_BANANA = 19
KILL_REWARD_FAST = 27
KILL_REWARD_ARMORED = 33
KILL_REWARD_BOSS = 380
KILL_REWARD_RAIDER = 58
KILL_REWARD_MOAB = 140

# Tower type keys and base stats (place_cost, range, damage, cooldown_frames, special)
TOWER_TYPES: dict[str, dict] = {
    "dart": {
        "name": "Dart Monkey",
        "cost": 248,
        "range": 155,
        "damage": 15,
        "cooldown": 24,
        "splash_radius": 0,
        "slow_pct": 0,
        "color": (200, 120, 80),
    },
    "cannon": {
        "name": "Cannon Monkey",
        "cost": 468,
        "range": 132,
        "damage": 35,
        "cooldown": 46,
        "splash_radius": 56,
        "slow_pct": 0,
        "color": (120, 90, 70),
    },
    "ice": {
        "name": "Ice Monkey",
        "cost": 392,
        "range": 126,
        "damage": 10,
        "cooldown": 31,
        "splash_radius": 0,
        "slow_pct": 0.35,
        "color": (140, 200, 255),
    },
    "sniper": {
        "name": "Sniper Monkey",
        "cost": 575,
        "range": 280,
        "damage": 70,
        "cooldown": 82,
        "splash_radius": 0,
        "slow_pct": 0,
        "color": (90, 140, 90),
    },
    "boom": {
        "name": "Boomerang Monkey",
        "cost": 445,
        "range": 142,
        "damage": 21,
        "cooldown": 28,
        "splash_radius": 42,
        "slow_pct": 0,
        "color": (200, 160, 100),
    },
    "farm": {
        "name": "Banana Farm",
        "cost": 558,
        "range": 0,
        "damage": 0,
        "cooldown": 9999,
        "splash_radius": 0,
        "slow_pct": 0,
        "color": (220, 200, 60),
        "income_per_wave": 130,
    },
    "village": {
        "name": "Monkey Village",
        "cost": 560,
        "range": 178,
        "damage": 0,
        "cooldown": 9999,
        "splash_radius": 0,
        "slow_pct": 0,
        "color": (175, 150, 95),
        "ally_range_pct": 0.085,
        "ally_damage_pct": 0.065,
    },
    "workshop": {
        "name": "Workshop",
        "cost": 640,
        "range": 148,
        "damage": 0,
        "cooldown": 9999,
        "splash_radius": 0,
        "slow_pct": 0,
        "color": (140, 125, 110),
        "ally_range_pct": 0.045,
        "ally_damage_pct": 0.115,
    },
    # Premium DPS: huge placement cost; upgrades & Paragon scale from the same base (very expensive).
    "super": {
        "name": "Super Monkey",
        "cost": 3980,
        "range": 168,
        "damage": 46,
        "cooldown": 17,
        "splash_radius": 0,
        "slow_pct": 0,
        "color": (245, 210, 95),
    },
}

# Sidebar build palette order (matches tower shop buttons).
TOWER_SHOP_ORDER = (
    "dart",
    "cannon",
    "ice",
    "sniper",
    "boom",
    "super",
    "farm",
    "village",
    "workshop",
)

# Upgrade costs scale by tier (each step on a path gets pricier)
UPGRADE_COST_TIER_MULT = 1.53


def upgrade_cost_tier(base: int, tier_index: int) -> int:
    return int(base * (UPGRADE_COST_TIER_MULT**tier_index))


UPGRADE_COST_BASE_PATH = 440

# Sell tower: fraction of total cash invested (placement + path tiers + Paragon) refunded.
SELL_REFUND_MULT = 0.72

# BTD6-style Paragon: buy once when all three paths are maxed under crosspath rules (e.g. 6/2/2).
# Cost scales with tower base price; stats get a large jump.
PARAGON_COST_MULT = 24.0
PARAGON_RANGE_MULT = 1.34
PARAGON_DAMAGE_MULT = 2.05
PARAGON_ATTACK_SPEED_MULT = 1.42
PARAGON_SPLASH_MULT = 1.38
PARAGON_SLOW_ADD = 0.12
PARAGON_FARM_INCOME_MULT = 1.72

PARAGON_DISPLAY_NAMES: dict[str, str] = {
    "dart": "Paragon · Apex Dartmaster",
    "cannon": "Paragon · Goliath Doomship",
    "ice": "Paragon · Absolute Zero",
    "sniper": "Paragon · Master Defender",
    "boom": "Paragon · Glaive Dominus",
    "farm": "Paragon · Banana Central Prime",
    "super": "Paragon · Apex Sun God",
}

# Upgrades per path (BTD-style; crosspath still limits secondary paths — see below)
MAX_PATH_TIER = 6

# BTD6 crosspath: only one path may be tier 3+ ("major" upgrades). Other paths cap at tier 2.
CROSSPATH_MAJOR_TIER = 3
CROSSPATH_OTHER_MAX = 2


def crosspath_valid(ta: int, tb: int, tc: int) -> bool:
    """True if tier triple respects BTD6-style limits (at most one path >= CROSSPATH_MAJOR_TIER)."""
    return sum(1 for t in (ta, tb, tc) if t >= CROSSPATH_MAJOR_TIER) <= 1

# Three paths (BTD-style Top / Middle / Bottom) — tier_a, tier_b, tier_c in code map to a, b, c.
# Stat keys: damage, range, firerate, splash, slow, farm_mult, farm_mult_b, farm_flat
# Per-tier stat deltas are halved vs old 3-tier design so max (6 tiers) ≈ old triple-path peak.
TOWER_PATH_UPGRADES: dict[str, dict[str, tuple[str, str, float]]] = {
    "dart": {
        "a": ("Sharp Darts", "damage", 0.14),
        "b": ("Eagle Eye", "range", 0.105),
        "c": ("Quick Hands", "firerate", 0.055),
    },
    "cannon": {
        "a": ("Heavy Shells", "damage", 0.135),
        "b": ("Wide Blast", "splash", 0.078),
        "c": ("Auto-Loader", "firerate", 0.05),
    },
    "ice": {
        "a": ("Permafrost", "slow", 0.062),
        "b": ("Arctic Reach", "range", 0.095),
        "c": ("Ice Shards", "damage", 0.125),
    },
    "sniper": {
        "a": ("Deadshot", "damage", 0.165),
        "b": ("Long Barrel", "range", 0.09),
        "c": ("Quickscope", "firerate", 0.044),
    },
    "boom": {
        "a": ("Razor Rings", "damage", 0.135),
        "b": ("Wide Arc", "splash", 0.072),
        "c": ("Turbo Spin", "firerate", 0.052),
    },
    "farm": {
        "a": ("Big Bunches", "farm_mult", 0.17),
        "b": ("Fertilizer", "farm_mult_b", 0.12),
        "c": ("Silo Storage", "farm_flat", 52.0),
    },
    "village": {
        "a": ("Town Hall", "damage", 0.012),
        "b": ("Expansion", "range", 0.056),
        "c": ("Logistics", "firerate", 0.04),
    },
    "workshop": {
        "a": ("Power Tools", "damage", 0.018),
        "b": ("Sensor Net", "range", 0.044),
        "c": ("Assembly Line", "firerate", 0.05),
    },
    "super": {
        "a": ("Sun Forged", "damage", 0.128),
        "b": ("Hero Vision", "range", 0.098),
        "c": ("Hyperfire", "firerate", 0.058),
    },
}

# UI labels for the three paths (Balloon TD–style lanes)
PATH_LANE_NAMES = ("Top", "Middle", "Bottom")

# When a path is dominant (highest tier; ties: Top > Middle > Bottom), the tower uses this full name.
# Keys: tower id -> path letter -> tier 1…6 display names
TOWER_PATH_TIER_NAMES: dict[str, dict[str, tuple[str, str, str, str, str, str]]] = {
    "dart": {
        "a": (
            "Sharp Dart",
            "Razor Darts",
            "Spike-O-Pult",
            "Juggernaut",
            "Ultra-Jugg",
            "Apex Dartlord",
        ),
        "b": (
            "Spotter Monkey",
            "Eagle Eye",
            "Super Range",
            "Global Vision",
            "Skywatch",
            "Horizon Eye",
        ),
        "c": (
            "Quick Shot",
            "Lightning Hands",
            "Hypersonic",
            "Overclock",
            "Machine Gun",
            "Velocity Prime",
        ),
    },
    "cannon": {
        "a": (
            "Heavy Cannon",
            "Demolition Shells",
            "MOAB Mauler",
            "Shell Shock",
            "Siege Artillery",
            "Mega Cannonade",
        ),
        "b": (
            "Blast Radius",
            "Shrapnel Burst",
            "Big Bomb",
            "Cluster Burst",
            "Airburst",
            "Wide Ruin",
        ),
        "c": (
            "Rapid Reload",
            "Auto Loader",
            "Artillery Crew",
            "Double Barrel",
            "Volley Fire",
            "Cyclic Fury",
        ),
    },
    "ice": {
        "a": (
            "Cold Snap",
            "Deep Freeze",
            "Absolute Zero",
            "Cryosphere",
            "Polar Vortex",
            "Endothermic",
        ),
        "b": (
            "Arctic Reach",
            "Cryo Lens",
            "Super Brittle",
            "Enhanced Optics",
            "Stratosphere",
            "Omniscience",
        ),
        "c": (
            "Ice Shards",
            "Icicle Burst",
            "Blizzard",
            "Hailstorm",
            "Permafrost King",
            "Subzero",
        ),
    },
    "sniper": {
        "a": (
            "Deadshot",
            "Crippling Shot",
            "Elite Defender",
            "Full Metal",
            "Cripple Master",
            "Elite Targeting",
        ),
        "b": (
            "Long Barrel",
            "Night Vision",
            "Full Map",
            "Ballistic CPU",
            "Orbital Spotter",
            "Infinite LOS",
        ),
        "c": (
            "Quickscope",
            "Semi-Auto",
            "Elite Sniper",
            "Burst Rounds",
            "Rail Acceleration",
            "Hypersonic Rounds",
        ),
    },
    "boom": {
        "a": (
            "Razor Rings",
            "Glaive Ricochet",
            "MOAB Press",
            "Turmoil",
            "Perma-Press",
            "Glaive Lord",
        ),
        "b": (
            "Wide Arc",
            "Kylie Boomer",
            "Perma Charge",
            "Seeking Arc",
            "Orbiting Glaives",
            "Sky Sweep",
        ),
        "c": (
            "Turbo Spin",
            "Bionic Boomer",
            "Turbo Charge",
            "MOAB Dom",
            "Centrifuge",
            "Infinite Spin",
        ),
    },
    "farm": {
        "a": (
            "Big Bunches",
            "Plantation",
            "Banana Central",
            "Banana Republic",
            "Industrial Farm",
            "Banana Empire",
        ),
        "b": (
            "Fertilizer",
            "Rich Soil",
            "Monkey Banker",
            "Compound Interest",
            "Capital Gains",
            "Monkeynomics",
        ),
        "c": (
            "Silo",
            "Marketplace",
            "Banana Wall St",
            "Vault",
            "Reserve Bank",
            "Treasury",
        ),
    },
    "village": {
        "a": (
            "Hamlet",
            "Town",
            "City",
            "Metropolis",
            "Capital",
            "Empire Seat",
        ),
        "b": (
            "Outskirts",
            "District",
            "Province",
            "Nation",
            "Continent",
            "World Hub",
        ),
        "c": (
            "Supply Line",
            "Trade Route",
            "Highway",
            "Rail Net",
            "Air Bridge",
            "Space Elevator",
        ),
    },
    "workshop": {
        "a": (
            "Tool Bench",
            "Machine Shop",
            "Factory",
            "Plant",
            "Megaforge",
            "Industrial Core",
        ),
        "b": (
            "Sensor",
            "Radar",
            "Lidar Web",
            "Sat Uplink",
            "Orbital Scan",
            "Omni Sight",
        ),
        "c": (
            "Overtime",
            "Double Shift",
            "Turbo Line",
            "Hyper Assembly",
            "Nano Forge",
            "Singularity Mill",
        ),
    },
    "super": {
        "a": (
            "Plasma Darts",
            "Solar Flare",
            "Sun Avatar",
            "Temple Core",
            "Legendary Strike",
            "Apex Destroyer",
        ),
        "b": (
            "Keen Sight",
            "Laser Optics",
            "True Vision",
            "Omniscient Eye",
            "Sky Sentinel",
            "Horizon Prime",
        ),
        "c": (
            "Quick Burst",
            "Rapid Fire",
            "Turbo Engine",
            "Overclock Core",
            "Velocity King",
            "Hypersonic God",
        ),
    },
}

# Dominant-path palette: body tint + accent for silhouettes (when that path leads)
TOWER_PATH_PALETTES: dict[str, dict[str, tuple[tuple[int, int, int], tuple[int, int, int]]]] = {
    "dart": {
        "a": ((215, 95, 75), (255, 120, 90)),
        "b": ((95, 145, 215), (170, 210, 255)),
        "c": ((235, 195, 85), (255, 235, 150)),
    },
    "cannon": {
        "a": ((145, 95, 75), (200, 120, 90)),
        "b": ((120, 110, 85), (220, 200, 140)),
        "c": ((130, 125, 115), (210, 205, 195)),
    },
    "ice": {
        "a": ((120, 200, 245), (200, 240, 255)),
        "b": ((100, 170, 230), (180, 220, 255)),
        "c": ((160, 210, 250), (230, 250, 255)),
    },
    "sniper": {
        "a": ((95, 130, 85), (140, 190, 130)),
        "b": ((85, 120, 95), (150, 190, 160)),
        "c": ((110, 150, 100), (190, 220, 150)),
    },
    "boom": {
        "a": ((215, 150, 85), (255, 200, 120)),
        "b": ((200, 140, 90), (245, 210, 150)),
        "c": ((220, 175, 95), (255, 230, 160)),
    },
    "farm": {
        "a": ((235, 210, 70), (255, 235, 130)),
        "b": ((210, 190, 70), (240, 225, 140)),
        "c": ((225, 200, 80), (255, 240, 150)),
    },
    "village": {
        "a": ((200, 140, 85), (255, 200, 120)),
        "b": ((160, 175, 120), (220, 235, 180)),
        "c": ((190, 160, 100), (245, 225, 160)),
    },
    "workshop": {
        "a": ((160, 130, 100), (210, 175, 140)),
        "b": ((120, 145, 160), (180, 205, 220)),
        "c": ((150, 140, 125), (200, 195, 175)),
    },
    "super": {
        "a": ((255, 200, 90), (255, 245, 160)),
        "b": ((120, 190, 255), (200, 235, 255)),
        "c": ((255, 160, 80), (255, 220, 140)),
    },
}

# Global meta upgrades (between waves)
# Multiplier per purchased tier for global upgrade costs (shown in wave shop)
GLOBAL_UPGRADE_COST_MULT = 1.48

GLOBAL_UPGRADES = [
    {"id": "range", "name": "+Range 5%", "max_tier": 5, "base_cost": 158, "effect": 0.05},
    {"id": "damage", "name": "+Damage 5%", "max_tier": 5, "base_cost": 182, "effect": 0.05},
    {"id": "income", "name": "+Kill cash 10%", "max_tier": 4, "base_cost": 198, "effect": 0.10},
]

# BTD-style bloon modifiers (bit flags for optional 3rd value in wave entries: kind, count, flags)
# Must be defined before _build_waves_raw().
ENEMY_FLAG_CAMO = 1
ENEMY_FLAG_LEAD = 2
ENEMY_FLAG_FORTIFIED = 4
ENEMY_FLAG_REGEN = 8
ENEMY_FLAG_FLYING = 16

# Every 10th wave (10, 20, …): one mega-boss (fortified + regen + extra HP).
BOSS_DECENNIAL_FLAGS = ENEMY_FLAG_FORTIFIED
BOSS_DECENNIAL_HP_MULT = 1.2
BOSS_DECENNIAL_REGEN_MULT = 1.35
# Extra boss scaling: decade = (current_wave_wn + 1) // 10 → waves 1–9 = 0, 10–19 = 1, 20–29 = 2, …
BOSS_PER_DECADE_HP_MULT = 0.07
BOSS_PER_DECADE_SPEED_MULT = 0.02
BOSS_PER_DECADE_REGEN_MULT = 0.04
BOSS_PER_DECADE_SPEED_CAP = 1.28

# Wave definitions: spawn_interval_frames, entries: (kind, count)
# kind: "banana" | "fast" | "armored" | "raider" | "moab" | "boss"


def _build_waves_raw() -> list[dict]:
    """40 escalating waves; special bloons (camo, lead, fortified, regen) ramp in."""
    out: list[dict] = []
    for i in range(40):
        w = i + 1
        interval = max(20, 56 - (i * 35 // 39))
        if w <= 4:
            entries: list = [("banana", 10 + i * 4)]
        elif w <= 10:
            entries = [("banana", 12 + i * 3), ("fast", 4 + (w - 4) * 2)]
        elif w <= 18:
            entries = [
                ("banana", min(48, 18 + w * 2)),
                ("fast", 6 + w),
                ("armored", max(1, w - 7)),
            ]
        elif w <= 28:
            entries = [
                ("banana", min(52, 22 + w + w // 2)),
                ("fast", min(36, 10 + w + w // 3)),
                ("armored", 6 + w // 2),
                ("raider", max(1, (w - 20) // 3)),
            ]
        elif w <= 36:
            entries = [
                ("banana", min(55, 28 + w)),
                ("fast", min(40, 14 + w // 2)),
                ("armored", 10 + (w - 28)),
                ("raider", 2 + (w - 28) // 2),
            ]
        elif w < 40:
            entries = [
                ("banana", 38),
                ("fast", 30),
                ("armored", 20 + (w - 37)),
                ("raider", 4 + (w - 37)),
            ]
        else:
            entries = [
                ("banana", 28),
                ("fast", 26),
                ("armored", 18),
                ("raider", 8),
            ]

        # Mega-boss every 10th wave from wave 20 onward (20, 30, 40, ...).
        if w % 10 == 0 and w >= 20:
            entries.append(("boss", 1, BOSS_DECENNIAL_FLAGS))

        # BTD-style modifiers: camo (hidden), lead (metal), fortified, regen
        if w >= 8:
            entries.append(("fast", 3 + w // 6, ENEMY_FLAG_CAMO))
        if w >= 11:
            entries.append(("banana", 4 + w // 5, ENEMY_FLAG_CAMO))
        if w >= 14:
            entries.append(("armored", 2 + w // 8, ENEMY_FLAG_LEAD))
        if w >= 17:
            entries.append(("fast", 3 + w // 7, ENEMY_FLAG_CAMO | ENEMY_FLAG_LEAD))
        if w >= 20:
            entries.append(("armored", 2 + w // 6, ENEMY_FLAG_FORTIFIED))
        if w >= 23:
            entries.append(("banana", 5 + w // 6, ENEMY_FLAG_LEAD | ENEMY_FLAG_FORTIFIED))
        if w >= 26:
            entries.append(("fast", 4, ENEMY_FLAG_REGEN))
        if w >= 29:
            entries.append(("armored", 3, ENEMY_FLAG_CAMO | ENEMY_FLAG_FORTIFIED))
        if w >= 32:
            entries.append(("banana", 4, ENEMY_FLAG_CAMO | ENEMY_FLAG_REGEN))
        if w >= 35:
            entries.append(("fast", 3, ENEMY_FLAG_LEAD | ENEMY_FLAG_REGEN))
        if w >= 38:
            entries.append(("armored", 2, ENEMY_FLAG_CAMO | ENEMY_FLAG_LEAD | ENEMY_FLAG_FORTIFIED))
        if w >= 22:
            entries.append(("moab", 1 + (w - 22) // 8))

        out.append({"interval": interval, "entries": entries})
    return out


WAVES_RAW: list[dict] = _build_waves_raw()

# Endless mode: wave pattern repeats (len(WAVES_RAW)); each absolute wave n scales stats.
ENDLESS_HP_PER_WAVE = 0.0132
ENDLESS_SPEED_PER_WAVE = 0.0037
ENDLESS_SPEED_CAP = 1.44
ENDLESS_REWARD_PER_WAVE = 0.0052

# Extra ramp starting wave 11 (wn >= 10): bloons get tougher faster mid–late game.
POST_WAVE_10_HP_RAMP = 0.0085
POST_WAVE_10_SPEED_RAMP = 0.0026

FORTIFIED_HP_MULT = 1.65
# Regen bloons heal per frame (60 FPS) when REGEN flag is set
REGEN_HP_PER_FRAME = 0.032

# Lower max HP → faster movement (applied after all HP modifiers). Tuned around ~mid-tier bloon HP.
REF_HP_SPEED = 48.0
HP_SPEED_CURVE = 0.24
HP_SPEED_MULT_MIN = 0.74
HP_SPEED_MULT_MAX = 1.36

# Sniper: camo / flying / lead / regen handling unlocks when max(path tiers) reaches this.
SNIPER_SPECIAL_TIER = 3

# Tower attack types — used for lead / metal rules (explosive & plasma pop lead without Sniper upgrades)
TOWER_DAMAGE_TYPE: dict[str, str] = {
    "dart": "sharp",
    "cannon": "explosive",
    "ice": "cold",
    "sniper": "ballistic",
    "boom": "sharp",
    "super": "plasma",
}

# Run difficulty (applied on top of endless scaling)
DIFFICULTY_SETTINGS: dict[str, dict[str, float | str]] = {
    "easy": {
        "label": "Easy",
        "enemy_hp": 0.84,
        "enemy_speed": 0.93,
        "starting_cash_mult": 1.4,
        "leak_mult": 0.85,
        "reward_mult": 1.06,
        "wave_bonus_mult": 1.1,
    },
    "medium": {
        "label": "Medium",
        "enemy_hp": 1.0,
        "enemy_speed": 1.0,
        "starting_cash_mult": 1.2,
        "leak_mult": 1.0,
        "reward_mult": 1.0,
        "wave_bonus_mult": 1.0,
    },
    "hard": {
        "label": "Hard",
        "enemy_hp": 1.16,
        "enemy_speed": 1.07,
        "starting_cash_mult": 1.0,
        "leak_mult": 1.12,
        "reward_mult": 0.93,
        "wave_bonus_mult": 0.9,
    },
    "impossible": {
        "label": "Impossible",
        # Slightly softer than pre-buff impossible — still clearly above Hard.
        "enemy_hp": 1.28,
        "enemy_speed": 1.10,
        "starting_cash_mult": 0.89,
        "leak_mult": 1.22,
        "reward_mult": 0.89,
        "wave_bonus_mult": 0.85,
    },
}

# Enemy stats by kind: hp, speed (pixels per frame), leak_damage, radius
ENEMY_STATS: dict[str, dict] = {
    "banana": {"hp": 31, "speed": 1.1, "leak": 2, "radius": 12, "reward": KILL_REWARD_BANANA},
    "fast": {"hp": 23, "speed": 1.6, "leak": 2, "radius": 10, "reward": KILL_REWARD_FAST},
    "armored": {"hp": 74, "speed": 0.9, "leak": 4, "radius": 13, "reward": KILL_REWARD_ARMORED},
    "raider": {"hp": 165, "speed": 1.32, "leak": 8, "radius": 16, "reward": KILL_REWARD_RAIDER},
    "moab": {"hp": 980, "speed": 0.72, "leak": 14, "radius": 28, "reward": KILL_REWARD_MOAB},
    "boss": {"hp": 1650, "speed": 0.5, "leak": 20, "radius": 42, "reward": KILL_REWARD_BOSS},
}

FINAL_WAVE_INDEX = len(WAVES_RAW) - 1
