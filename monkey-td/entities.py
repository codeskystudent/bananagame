"""Enemies, towers, projectiles."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from config import (
    BOSS_DECENNIAL_HP_MULT,
    BOSS_DECENNIAL_REGEN_MULT,
    BOSS_PER_DECADE_HP_MULT,
    BOSS_PER_DECADE_REGEN_MULT,
    BOSS_PER_DECADE_SPEED_CAP,
    BOSS_PER_DECADE_SPEED_MULT,
    ENEMY_STATS,
    FORTIFIED_HP_MULT,
    HP_SPEED_CURVE,
    HP_SPEED_MULT_MAX,
    HP_SPEED_MULT_MIN,
    MAX_PATH_TIER,
    PARAGON_ATTACK_SPEED_MULT,
    PARAGON_COST_MULT,
    PARAGON_DAMAGE_MULT,
    PARAGON_DISPLAY_NAMES,
    PARAGON_FARM_INCOME_MULT,
    PARAGON_RANGE_MULT,
    PARAGON_SLOW_ADD,
    PARAGON_SPLASH_MULT,
    REF_HP_SPEED,
    REGEN_HP_PER_FRAME,
    SELL_REFUND_MULT,
    TOWER_PATH_TIER_NAMES,
    TOWER_PATH_UPGRADES,
    TOWER_TYPES,
    UPGRADE_COST_BASE_PATH,
    crosspath_valid,
    upgrade_cost_tier,
)


def _path_bonus(tower_type: str, tier_a: int, tier_b: int, tier_c: int, stat: str) -> float:
    defs = TOWER_PATH_UPGRADES[tower_type]
    s = 0.0
    for letter, tier in (("a", tier_a), ("b", tier_b), ("c", tier_c)):
        _, st, val = defs[letter]
        if st == stat:
            s += val * float(tier)
    return s


_TOWER_MODIFIER_ACCESS: dict[str, set[str]] = {
    # Certain towers intentionally lack some special-modifier capabilities.
    "dart": {"lead", "camo", "flying"},
    "cannon": {"lead", "flying"},
    "ice": {"camo", "regen"},
    "sniper": {"lead", "camo", "flying"},
    "boom": {"lead", "regen"},
    "super": {"lead", "camo", "flying", "regen"},
}


def _single_modifier_for_tiers(
    tower_type: str, tier_a: int, tier_b: int, tier_c: int
) -> str | None:
    """Only one special modifier can be active at a time per tower."""
    allowed = _TOWER_MODIFIER_ACCESS.get(tower_type, set())
    if not allowed:
        return None
    m = max(tier_a, tier_b, tier_c)
    if m <= 0:
        return None
    if tier_a == m and m >= 2 and "lead" in allowed:
        return "lead"
    if tier_b == m and m >= 4 and "flying" in allowed:
        return "flying"
    if tier_b == m and m >= 2 and "camo" in allowed:
        return "camo"
    if tier_c == m and m >= 2 and "regen" in allowed:
        return "regen"
    return None


@dataclass
class Enemy:
    kind: str
    distance: float = 0.0
    hp: float = 0.0
    max_hp: float = 0.0
    alive: bool = True
    slow_mult: float = 1.0
    slow_timer: int = 0
    radius: float = 12.0
    difficulty_hp: float = 1.0
    difficulty_speed: float = 1.0
    camo: bool = False
    lead: bool = False
    fortified: bool = False
    regen: bool = False
    flying: bool = False
    regen_per_frame: float = 0.0
    boss_decade: int = 0
    layers: int = 1
    max_layers: int = 1
    layer_max_hp: float = 0.0
    regen_layer_progress: float = 0.0
    leaked: bool = False
    _hp_speed_mult: float = field(default=1.0, init=False)

    def __post_init__(self) -> None:
        st = ENEMY_STATS[self.kind]
        self.max_hp = float(st["hp"]) * self.difficulty_hp
        if self.fortified:
            self.max_hp *= FORTIFIED_HP_MULT
        if self.kind == "boss" and self.regen and self.fortified:
            self.max_hp *= BOSS_DECENNIAL_HP_MULT
        if self.kind == "boss" and self.boss_decade > 0:
            self.max_hp *= 1.0 + self.boss_decade * BOSS_PER_DECADE_HP_MULT
        self.hp = self.max_hp
        self.radius = float(st["radius"])
        if self.kind == "boss" and self.boss_decade > 0:
            sp = 1.0 + self.boss_decade * BOSS_PER_DECADE_SPEED_MULT
            self.difficulty_speed *= min(BOSS_PER_DECADE_SPEED_CAP, sp)
        self.regen_per_frame = REGEN_HP_PER_FRAME if self.regen else 0.0
        if self.regen and self.kind == "boss" and self.fortified:
            self.regen_per_frame *= BOSS_DECENNIAL_REGEN_MULT
        if self.kind == "boss" and self.boss_decade > 0 and self.regen:
            self.regen_per_frame *= 1.0 + self.boss_decade * BOSS_PER_DECADE_REGEN_MULT
        if self.kind == "boss":
            self.max_layers = 1
        else:
            base_layers = {"banana": 2, "fast": 2, "armored": 3, "raider": 4, "moab": 5}.get(self.kind, 1)
            if self.lead:
                base_layers += 1
            if self.fortified:
                base_layers += 1
            self.max_layers = max(1, base_layers)
        self.layers = self.max_layers
        if self.max_layers <= 1:
            self.layer_max_hp = self.max_hp
        else:
            # Multi-layer bloons are tougher than single layer, but not absurdly so.
            self.layer_max_hp = self.max_hp * (0.5 + 0.08 * min(4, self.max_layers - 1))
        self.hp = self.layer_max_hp
        # Weaker (lower HP) bloons move faster; tanky / fortified ones move slower.
        raw = (REF_HP_SPEED / max(self.max_hp, 1.0)) ** HP_SPEED_CURVE
        self._hp_speed_mult = max(
            HP_SPEED_MULT_MIN, min(HP_SPEED_MULT_MAX, raw)
        )

    @property
    def speed(self) -> float:
        st = ENEMY_STATS[self.kind]
        return (
            float(st["speed"])
            * self.slow_mult
            * self.difficulty_speed
            * self._hp_speed_mult
        )

    def apply_slow(self, pct: float, frames: int) -> None:
        self.slow_mult = max(0.25, 1.0 - pct)
        self.slow_timer = max(self.slow_timer, frames)

    def tick_slow(self) -> None:
        if self.slow_timer > 0:
            self.slow_timer -= 1
            if self.slow_timer <= 0:
                self.slow_mult = 1.0

    def apply_damage(self, damage: float) -> None:
        """Damage can remove one or more layers; enemy dies when no layers remain."""
        if damage <= 0 or not self.alive:
            return
        d = damage
        while d > 0 and self.layers > 0:
            if d < self.hp:
                self.hp -= d
                d = 0
                break
            d -= self.hp
            self.layers -= 1
            if self.layers <= 0:
                self.hp = 0.0
                self.alive = False
                return
            self.hp = self.layer_max_hp

    def tick_regen(self) -> None:
        if self.regen_per_frame <= 0 or not self.alive:
            return
        self.hp = min(self.layer_max_hp, self.hp + self.regen_per_frame)
        if self.layers < self.max_layers:
            self.regen_layer_progress += self.regen_per_frame
            need = self.layer_max_hp * 0.45
            if self.regen_layer_progress >= need and self.hp >= self.layer_max_hp * 0.75:
                self.layers += 1
                self.regen_layer_progress = max(0.0, self.regen_layer_progress - need)


@dataclass
class Projectile:
    x0: float
    y0: float
    x1: float
    y1: float
    damage: float
    splash_radius: float
    slow_pct: float
    slow_frames: int
    tower_kind: str
    damage_type: str = "sharp"
    tier_a: int = 0
    tier_b: int = 0
    tier_c: int = 0
    paragon: bool = False
    t: float = 0.0
    speed: float = 0.22  # 0..1 per frame
    done: bool = False

    def update(self) -> None:
        self.t += self.speed
        if self.t >= 1.0:
            self.t = 1.0
            self.done = True


@dataclass
class MonkeyTower:
    x: float
    y: float
    tower_type: str
    tier_a: int = 0
    tier_b: int = 0
    tier_c: int = 0
    cooldown: int = 0
    uid: int = 0
    paragon: bool = False

    def base(self) -> dict:
        return TOWER_TYPES[self.tower_type]

    def is_farm(self) -> bool:
        return self.tower_type == "farm"

    def is_support(self) -> bool:
        return self.tower_type in ("village", "workshop")

    def ally_range_buff_mult(self) -> float:
        """Buff to other towers' range while they stand in this support's aura (>=1)."""
        if not self.is_support():
            return 1.0
        b = self.base()
        v = float(b.get("ally_range_pct", 0))
        v += self._pb("range") * 0.024
        v += self._pb("firerate") * 0.012
        return 1.0 + min(0.2, v)

    def ally_damage_buff_mult(self) -> float:
        if not self.is_support():
            return 1.0
        b = self.base()
        v = float(b.get("ally_damage_pct", 0))
        v += self._pb("damage") * 0.03
        v += self._pb("firerate") * 0.014
        return 1.0 + min(0.26, v)

    def _pb(self, stat: str) -> float:
        return _path_bonus(self.tower_type, self.tier_a, self.tier_b, self.tier_c, stat)

    def effective_range(self, global_range_pct: float) -> float:
        b = self.base()
        r = float(b["range"]) * (1.0 + self._pb("range")) * (1.0 + global_range_pct)
        if self.dominant_path() == "b" and self.dominant_tier() >= 4:
            # Path mastery (range path): clearer identity at higher tiers.
            r *= 1.1
        if self.paragon:
            r *= PARAGON_RANGE_MULT
        return r

    def effective_damage(self, global_damage_pct: float) -> float:
        b = self.base()
        d = float(b["damage"]) * (1.0 + self._pb("damage")) * (1.0 + global_damage_pct)
        if self.dominant_path() == "a" and self.dominant_tier() >= 4:
            # Path mastery (power path): extra impact once specialized.
            d *= 1.08
        if self.paragon:
            d *= PARAGON_DAMAGE_MULT
        return d

    def effective_cooldown(self) -> int:
        b = self.base()
        fr = self._pb("firerate")
        cd_mult = max(0.48, 1.0 - min(0.44, fr))
        cd = float(b["cooldown"]) * cd_mult
        if self.dominant_path() == "c" and self.dominant_tier() >= 4:
            # Path mastery (speed path): tighter cadence.
            cd *= 0.9
        cd_i = max(8, int(cd))
        if self.paragon:
            cd_i = max(5, int(cd_i / PARAGON_ATTACK_SPEED_MULT))
        return cd_i

    def effective_splash(self) -> float:
        b = self.base()
        sp = float(b.get("splash_radius", 0))
        sp *= 1.0 + self._pb("splash")
        if self.paragon:
            sp *= PARAGON_SPLASH_MULT
        return sp

    def effective_slow(self) -> float:
        b = self.base()
        base_s = float(b.get("slow_pct", 0))
        s = min(0.78, base_s + self._pb("slow"))
        if self.paragon:
            s = min(0.82, s + PARAGON_SLOW_ADD)
        return s

    def farm_income(self) -> int:
        b = self.base()
        base_inc = float(b.get("income_per_wave", 0))
        m = self._pb("farm_mult")
        mb = self._pb("farm_mult_b")
        flat = self._pb("farm_flat")
        inc = int(base_inc * (1.0 + m) * (1.0 + mb) + flat)
        if self.paragon:
            inc = int(inc * PARAGON_FARM_INCOME_MULT)
        return inc

    def max_tier(self) -> int:
        return MAX_PATH_TIER

    def visual_tier(self) -> int:
        """Highest path tier — used for on-map / icon appearance."""
        if self.paragon:
            return MAX_PATH_TIER + 2
        return max(self.tier_a, self.tier_b, self.tier_c)

    def dominant_path(self) -> str | None:
        """Highest-upgraded path; ties break Top > Middle > Bottom (a > b > c)."""
        m = max(self.tier_a, self.tier_b, self.tier_c)
        if m == 0:
            return None
        for path, t in (("a", self.tier_a), ("b", self.tier_b), ("c", self.tier_c)):
            if t == m:
                return path
        return None

    def dominant_tier(self) -> int:
        """Tier on the dominant path (0 if no upgrades)."""
        p = self.dominant_path()
        if p is None:
            return 0
        return {"a": self.tier_a, "b": self.tier_b, "c": self.tier_c}[p]

    def can_detect_camo(self) -> bool:
        """Single-modifier model: only dominant path grants one special."""
        if self.paragon:
            return True
        return (
            _single_modifier_for_tiers(self.tower_type, self.tier_a, self.tier_b, self.tier_c)
            == "camo"
        )

    def can_detect_flying(self) -> bool:
        """Single-modifier model: only one special can be active."""
        if self.paragon:
            return True
        return (
            _single_modifier_for_tiers(self.tower_type, self.tier_a, self.tier_b, self.tier_c)
            == "flying"
        )

    def can_hit_lead(self) -> bool:
        if self.paragon:
            return True
        return (
            _single_modifier_for_tiers(self.tower_type, self.tier_a, self.tier_b, self.tier_c)
            == "lead"
        )

    def can_hit_regen(self) -> bool:
        if self.paragon:
            return True
        return (
            _single_modifier_for_tiers(self.tower_type, self.tier_a, self.tier_b, self.tier_c)
            == "regen"
        )

    def display_name(self) -> str:
        """BTD-style full tower name from the leading upgrade path."""
        if self.paragon:
            return PARAGON_DISPLAY_NAMES.get(self.tower_type, "Paragon")
        base = self.base()["name"]
        p = self.dominant_path()
        if p is None:
            return base
        dt = self.dominant_tier()
        if dt < 1:
            return base
        names = TOWER_PATH_TIER_NAMES[self.tower_type][p]
        return names[dt - 1]

    def can_paragon(self) -> bool:
        """True when crosspath is fully maxed (e.g. 6/2/2) and Paragon not yet bought."""
        if self.paragon:
            return False
        if self.is_support():
            return False
        if max(self.tier_a, self.tier_b, self.tier_c) < MAX_PATH_TIER:
            return False
        if self.can_upgrade_a() or self.can_upgrade_b() or self.can_upgrade_c():
            return False
        return True

    def paragon_cost(self) -> int | None:
        if not self.can_paragon():
            return None
        return int(float(self.base()["cost"]) * PARAGON_COST_MULT)

    def total_invested_cash(self) -> int:
        """Placement + all path upgrades paid + Paragon if any."""
        total = int(self.base()["cost"])
        for i in range(self.tier_a):
            total += upgrade_cost_tier(UPGRADE_COST_BASE_PATH, i)
        for i in range(self.tier_b):
            total += upgrade_cost_tier(UPGRADE_COST_BASE_PATH, i)
        for i in range(self.tier_c):
            total += upgrade_cost_tier(UPGRADE_COST_BASE_PATH, i)
        if self.paragon:
            total += int(float(self.base()["cost"]) * PARAGON_COST_MULT)
        return total

    def sell_refund_amount(self) -> int:
        return max(0, int(self.total_invested_cash() * SELL_REFUND_MULT))

    def can_upgrade_a(self) -> bool:
        if self.paragon:
            return False
        if self.tier_a >= self.max_tier():
            return False
        return crosspath_valid(self.tier_a + 1, self.tier_b, self.tier_c)

    def can_upgrade_b(self) -> bool:
        if self.paragon:
            return False
        if self.tier_b >= self.max_tier():
            return False
        return crosspath_valid(self.tier_a, self.tier_b + 1, self.tier_c)

    def can_upgrade_c(self) -> bool:
        if self.paragon:
            return False
        if self.tier_c >= self.max_tier():
            return False
        return crosspath_valid(self.tier_a, self.tier_b, self.tier_c + 1)

    def upgrade_cost_a(self) -> int | None:
        if not self.can_upgrade_a():
            return None
        return upgrade_cost_tier(UPGRADE_COST_BASE_PATH, self.tier_a)

    def upgrade_cost_b(self) -> int | None:
        if not self.can_upgrade_b():
            return None
        return upgrade_cost_tier(UPGRADE_COST_BASE_PATH, self.tier_b)

    def upgrade_cost_c(self) -> int | None:
        if not self.can_upgrade_c():
            return None
        return upgrade_cost_tier(UPGRADE_COST_BASE_PATH, self.tier_c)


def lead_damage_multiplier(
    tower_type: str, tier_a: int, _tier_b: int, tier_c: int, damage_type: str
) -> float:
    """Single-modifier model: lead comes only from dominant A path."""
    _ = tower_type, damage_type, tier_c
    return (
        1.0
        if _single_modifier_for_tiers(tower_type, tier_a, _tier_b, tier_c) == "lead"
        else 0.0
    )


def regen_damage_multiplier(
    tower_type: str, tier_a: int, tier_b: int, tier_c: int, _damage_type: str
) -> float:
    """Single-modifier model: regen comes only from dominant C path."""
    _ = tower_type, _damage_type
    return (
        1.0
        if _single_modifier_for_tiers(tower_type, tier_a, tier_b, tier_c) == "regen"
        else 0.0
    )


def damage_vs_enemy(
    base_damage: float,
    enemy: Enemy,
    tower_type: str,
    tier_a: int,
    tier_b: int,
    tier_c: int,
    damage_type: str,
    *,
    paragon: bool = False,
) -> float:
    d = base_damage
    if enemy.lead:
        if paragon:
            pass
        else:
            d *= lead_damage_multiplier(tower_type, tier_a, tier_b, tier_c, damage_type)
    if enemy.regen:
        if paragon:
            pass
        else:
            d *= regen_damage_multiplier(tower_type, tier_a, tier_b, tier_c, damage_type)
    return d


def enemy_reward_multiplier(e: Enemy) -> float:
    m = 1.0
    if e.camo:
        m *= 1.2
    if e.lead:
        m *= 1.15
    if e.fortified:
        m *= 1.1
    if e.regen:
        m *= 1.12
    if e.flying:
        m *= 1.18
    return m


def find_target(
    tx: float,
    ty: float,
    rng: float,
    enemies: list[Enemy],
    see_camo: bool = True,
    see_flying: bool = True,
) -> Enemy | None:
    best: Enemy | None = None
    best_d_along = -1.0
    r2 = rng * rng
    for e in enemies:
        if not e.alive:
            continue
        if e.camo and not see_camo:
            continue
        if e.flying and not see_flying:
            continue
        d_along = getattr(e, "_sort_d", 0.0)
        px, py = getattr(e, "_px", 0.0), getattr(e, "_py", 0.0)
        dx, dy = px - tx, py - ty
        if dx * dx + dy * dy <= r2:
            if best is None or d_along > best_d_along:
                best = e
                best_d_along = d_along
    return best


def apply_projectile_hit(proj: Projectile, enemies: list[Enemy]) -> None:
    """Resolve damage at projectile impact (tip position)."""
    tx = proj.x0 + (proj.x1 - proj.x0) * proj.t
    ty = proj.y0 + (proj.y1 - proj.y0) * proj.t
    if proj.splash_radius <= 0.1:
        best: Enemy | None = None
        best_d = 1e9
        for e in enemies:
            if not e.alive:
                continue
            px, py = getattr(e, "_px", 0.0), getattr(e, "_py", 0.0)
            dx, dy = px - tx, py - ty
            d2 = dx * dx + dy * dy
            hit_r = e.radius + 8.0
            hit_r2 = hit_r * hit_r
            if d2 < hit_r2 and d2 < best_d:
                best_d = d2
                best = e
        if best is not None:
            d = damage_vs_enemy(
                proj.damage,
                best,
                proj.tower_kind,
                proj.tier_a,
                proj.tier_b,
                proj.tier_c,
                proj.damage_type,
                paragon=proj.paragon,
            )
            if d > 0:
                best.apply_damage(d)
                if proj.slow_pct > 0:
                    best.apply_slow(proj.slow_pct, proj.slow_frames)
    else:
        for e in enemies:
            if not e.alive:
                continue
            px, py = getattr(e, "_px", 0.0), getattr(e, "_py", 0.0)
            dx, dy = px - tx, py - ty
            hit_r = proj.splash_radius + e.radius
            if dx * dx + dy * dy <= hit_r * hit_r:
                d = damage_vs_enemy(
                    proj.damage,
                    e,
                    proj.tower_kind,
                    proj.tier_a,
                    proj.tier_b,
                    proj.tier_c,
                    proj.damage_type,
                    paragon=proj.paragon,
                )
                if d > 0:
                    e.apply_damage(d)
                    if proj.slow_pct > 0:
                        e.apply_slow(proj.slow_pct, proj.slow_frames)
