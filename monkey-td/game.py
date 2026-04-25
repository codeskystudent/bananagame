"""Main game loop and state."""

from __future__ import annotations

import math
from typing import Literal

import pygame

from config import (
    BASE_MAX_HP,
    BOSS_LEAK_DAMAGE,
    COLOR_BASE,
    COLOR_BOSS,
    COLOR_BANANA,
    COLOR_GRASS,
    COLOR_PATH,
    COLOR_PATH_EDGE,
    DIFFICULTY_SETTINGS,
    ENDLESS_HP_PER_WAVE,
    ENDLESS_REWARD_PER_WAVE,
    ENDLESS_SPEED_CAP,
    ENDLESS_SPEED_PER_WAVE,
    POST_WAVE_10_HP_RAMP,
    POST_WAVE_10_SPEED_RAMP,
    ENEMY_STATS,
    GLOBAL_UPGRADE_COST_MULT,
    GLOBAL_UPGRADES,
    PATH_HALF_WIDTH,
    PLAY_HEIGHT,
    PLAY_WIDTH,
    STARTING_CASH,
    TITLE,
    WAVE_ROUND_BONUS_BASE,
    WAVE_ROUND_BONUS_PER_WAVE,
    TOWER_DAMAGE_TYPE,
    TOWER_SHOP_ORDER,
    TOWER_TYPES,
    WAVES_RAW,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
    FPS,
    ENEMY_FLAG_CAMO,
    ENEMY_FLAG_FORTIFIED,
    ENEMY_FLAG_LEAD,
    ENEMY_FLAG_REGEN,
)
from entities import (
    Enemy,
    MonkeyTower,
    Projectile,
    apply_projectile_hit,
    enemy_reward_multiplier,
    find_target,
)
from maps import MAP_DEFINITIONS, build_waypoints, map_count, map_grass
from path import distance_point_to_path, pos_at_distance, total_length
from waves import WaveController, make_enemy
from ui import (
    HUD_SPEED_CHOICES,
    UPGRADE_PATHS_ROW_Y,
    difficulty_button_rect,
    draw_hud,
    draw_map_select,
    draw_monkey_tower_on_map,
    draw_play_border,
    draw_sidebar_bg,
    draw_text,
    draw_tower_shop,
    draw_upgrade_panel,
    draw_wave_break,
    init_fonts,
    map_button_rect,
    mode_button_rect,
    next_wave_button_screen_rect,
    paragon_upgrade_rect,
    sell_tower_button_rect,
    speed_button_rect,
    tower_button_rect,
    upgrade_row_rect,
)


State = Literal["map_select", "playing", "wave_break", "lost"]
RunMode = Literal["normal", "sandbox"]


class Game:
    def __init__(self) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption(TITLE)
        self.clock = pygame.time.Clock()
        self.font, self.font_small, self.font_title = init_fonts()
        self.sim_accum_ms = 0.0

        self.state: State = "map_select"
        self.paused = False
        self.game_speed = 1

        self.map_index = 0
        self.path_waypoints: list[tuple[float, float]] = []
        self.path_len = 1.0
        self.grass_color = COLOR_GRASS

        self.base_hp = BASE_MAX_HP
        self.cash = 0
        self.waves = WaveController()
        self.next_wave_number = 1  # 1-based display

        self.enemies: list[Enemy] = []
        self.towers: list[MonkeyTower] = []
        self.projectiles: list[Projectile] = []
        self.tower_uid = 0

        self.selected_place_type: str | None = "dart"
        self.selected_tower: MonkeyTower | None = None

        self.global_tiers: dict[str, int] = {"range": 0, "damage": 0, "income": 0}
        self.difficulty: str = "medium"
        self.run_mode: RunMode = "normal"
        self.sandbox_spawn_flags: dict[str, bool] = {
            "camo": False,
            "lead": False,
            "fortified": False,
            "regen": False,
        }

        self.current_wave_wn = 0
        self.wave_hp_mult = 1.0
        self.wave_speed_mult = 1.0
        self.last_wave_round_bonus = 0
        self.last_farm_income = 0

    def select_map(self, index: int) -> None:
        self.map_index = index
        self.path_waypoints = build_waypoints(index)
        self.path_len = total_length(self.path_waypoints)
        self.grass_color = map_grass(index)
        self.reset_round_state()

    def reset_round_state(self) -> None:
        self.state = "playing" if self.run_mode == "sandbox" else "wave_break"
        self.paused = False
        self.game_speed = 1
        self.base_hp = BASE_MAX_HP
        self.waves = WaveController()
        self.next_wave_number = 1
        self.enemies.clear()
        self.towers.clear()
        self.projectiles.clear()
        self.tower_uid = 0
        self.selected_place_type = "dart"
        self.selected_tower = None
        self.global_tiers = {"range": 0, "damage": 0, "income": 0}
        self.current_wave_wn = 0
        self.wave_hp_mult = 1.0
        self.wave_speed_mult = 1.0
        self.last_wave_round_bonus = 0
        self.last_farm_income = 0
        self.sim_accum_ms = 0.0
        d = DIFFICULTY_SETTINGS[self.difficulty]
        if self.run_mode == "sandbox":
            self.cash = 999999
            self.base_hp = 999999
        else:
            self.cash = int(STARTING_CASH * float(d["starting_cash_mult"]))

    def return_to_title(self) -> None:
        """Map selection screen: clears run state so the player picks a map again."""
        self.state = "map_select"
        self.paused = False
        self.game_speed = 1
        self.map_index = 0
        self.path_waypoints = []
        self.path_len = 1.0
        self.grass_color = COLOR_GRASS
        self.base_hp = BASE_MAX_HP
        self.cash = 0
        self.waves = WaveController()
        self.next_wave_number = 1
        self.enemies.clear()
        self.towers.clear()
        self.projectiles.clear()
        self.tower_uid = 0
        self.selected_place_type = "dart"
        self.selected_tower = None
        self.global_tiers = {"range": 0, "damage": 0, "income": 0}
        self.current_wave_wn = 0
        self.wave_hp_mult = 1.0
        self.wave_speed_mult = 1.0
        self.last_wave_round_bonus = 0
        self.last_farm_income = 0
        self.sim_accum_ms = 0.0

    def reset_game(self) -> None:
        self.return_to_title()

    def global_range_pct(self) -> float:
        t = self.global_tiers.get("range", 0)
        eff = next(g["effect"] for g in GLOBAL_UPGRADES if g["id"] == "range")
        return t * eff

    def global_damage_pct(self) -> float:
        t = self.global_tiers.get("damage", 0)
        eff = next(g["effect"] for g in GLOBAL_UPGRADES if g["id"] == "damage")
        return t * eff

    def kill_cash_mult(self) -> float:
        t = self.global_tiers.get("income", 0)
        eff = next(g["effect"] for g in GLOBAL_UPGRADES if g["id"] == "income")
        return 1.0 + t * eff

    def support_buff_multipliers(self, t: MonkeyTower) -> tuple[float, float]:
        """Extra range / damage multipliers from nearby Monkey Village & Workshop auras."""
        if t.is_support() or t.is_farm():
            return 1.0, 1.0
        rmul, dmul = 1.0, 1.0
        gr = self.global_range_pct()
        for s in self.towers:
            if not s.is_support():
                continue
            if math.hypot(s.x - t.x, s.y - t.y) > s.effective_range(gr):
                continue
            rmul *= s.ally_range_buff_mult()
            dmul *= s.ally_damage_buff_mult()
        return min(rmul, 1.38), min(dmul, 1.44)

    def sync_enemy_positions(self) -> None:
        for e in self.enemies:
            if not e.alive:
                continue
            x, y, _ = pos_at_distance(self.path_waypoints, e.distance)
            e._px = x
            e._py = y
            e._sort_d = e.distance

    def try_place_tower(self, mx: float, my: float) -> None:
        if self.selected_place_type is None:
            return
        key = self.selected_place_type
        cost = TOWER_TYPES[key]["cost"]
        if self.run_mode != "sandbox" and self.cash < cost:
            return
        if not self._can_place(mx, my):
            return
        self.tower_uid += 1
        tower = MonkeyTower(x=mx, y=my, tower_type=key, uid=self.tower_uid)
        self.towers.append(tower)
        if self.run_mode != "sandbox":
            self.cash -= cost
        self.selected_tower = tower

    def _can_place(self, mx: float, my: float) -> bool:
        if mx < 24 or mx > PLAY_WIDTH - 24 or my < 24 or my > PLAY_HEIGHT - 24:
            return False
        if distance_point_to_path(mx, my, self.path_waypoints) < PATH_HALF_WIDTH + 24:
            return False
        for t in self.towers:
            if math.hypot(t.x - mx, t.y - my) < 38:
                return False
        return True

    def tower_at_screen(self, mx: float, my: float) -> MonkeyTower | None:
        for t in reversed(self.towers):
            if math.hypot(t.x - mx, t.y - my) <= 30:
                return t
        return None

    def _cull_dead_enemies(self) -> None:
        new: list = []
        for e in self.enemies:
            if not e.alive:
                continue
            if e.hp <= 0:
                if self.run_mode == "sandbox":
                    continue
                dset = DIFFICULTY_SETTINGS[self.difficulty]
                rw = float(ENEMY_STATS[e.kind]["reward"]) * self.kill_cash_mult()
                rw *= 1.0 + self.current_wave_wn * ENDLESS_REWARD_PER_WAVE
                rw *= float(dset["reward_mult"])
                rw *= enemy_reward_multiplier(e)
                self.cash += int(rw)
            else:
                new.append(e)
        self.enemies = new

    def _tick_one(self) -> None:
        if self.run_mode != "sandbox" and self.waves.active and self.waves.update_spawn_timer():
            popped = self.waves.pop_spawn()
            if popped:
                kind, flags = popped
                bd = (self.current_wave_wn + 1) // 10 if kind == "boss" else 0
                self.enemies.append(
                    make_enemy(
                        kind,
                        self.wave_hp_mult,
                        self.wave_speed_mult,
                        flags,
                        boss_decade=bd,
                    )
                )

        self.sync_enemy_positions()

        alive_proj: list[Projectile] = []
        for p in self.projectiles:
            p.update()
            if p.done:
                apply_projectile_hit(p, self.enemies)
            else:
                alive_proj.append(p)
        self.projectiles = alive_proj
        self._cull_dead_enemies()

        for e in self.enemies:
            if not e.alive:
                continue
            e.tick_slow()
            if e.regen_per_frame > 0:
                e.hp = min(e.max_hp, e.hp + e.regen_per_frame)
            e.distance += e.speed
            if e.distance >= self.path_len - 0.01:
                if e.kind == "boss":
                    leak = BOSS_LEAK_DAMAGE
                else:
                    lm = float(DIFFICULTY_SETTINGS[self.difficulty]["leak_mult"])
                    leak = int(ENEMY_STATS[e.kind]["leak"] * lm)
                if self.run_mode != "sandbox":
                    self.base_hp -= leak
                e.alive = False
        self.enemies = [e for e in self.enemies if e.alive]

        self.sync_enemy_positions()
        for t in self.towers:
            if t.is_farm() or t.is_support():
                continue
            if t.cooldown > 0:
                t.cooldown -= 1
                continue
            rng = t.effective_range(self.global_range_pct())
            srm, sdm = self.support_buff_multipliers(t)
            rng *= srm
            tgt = find_target(t.x, t.y, rng, self.enemies, t.can_detect_camo())
            if tgt is None:
                continue
            ex = getattr(tgt, "_px", 0.0)
            ey = getattr(tgt, "_py", 0.0)
            dmg = t.effective_damage(self.global_damage_pct()) * sdm
            splash = t.effective_splash()
            slowp = t.effective_slow()
            proj = Projectile(
                x0=t.x,
                y0=t.y,
                x1=ex,
                y1=ey,
                damage=dmg,
                splash_radius=splash,
                slow_pct=slowp if slowp > 0 else 0,
                slow_frames=80 if slowp > 0 else 0,
                tower_kind=t.tower_type,
                damage_type=TOWER_DAMAGE_TYPE[t.tower_type],
                tier_a=t.tier_a,
                tier_b=t.tier_b,
                tier_c=t.tier_c,
                paragon=t.paragon,
                speed=(
                    0.55
                    if t.tower_type == "sniper"
                    else 0.44
                    if t.tower_type == "super"
                    else 0.35
                ),
            )
            self.projectiles.append(proj)
            t.cooldown = t.effective_cooldown()

    def try_paragon(self) -> None:
        if self.selected_tower is None:
            return
        t = self.selected_tower
        cost = t.paragon_cost()
        if cost is None:
            return
        if self.run_mode != "sandbox" and self.cash < cost:
            return
        if self.run_mode != "sandbox":
            self.cash -= cost
        t.paragon = True

    def try_sell_selected_tower(self) -> None:
        if self.selected_tower is None:
            return
        if self.state not in ("playing", "wave_break"):
            return
        t = self.selected_tower
        if self.run_mode != "sandbox":
            self.cash += t.sell_refund_amount()
        uid = t.uid
        self.towers = [x for x in self.towers if x.uid != uid]
        self.selected_tower = None

    def apply_farm_income(self) -> int:
        if self.run_mode == "sandbox":
            return 0
        total = 0
        for t in self.towers:
            if t.is_farm():
                total += t.farm_income()
        self.cash += total
        return total

    def wave_round_bonus_cash(self) -> int:
        """Flat cash for clearing the current wave (uses current_wave_wn just finished)."""
        wn = self.current_wave_wn
        d = DIFFICULTY_SETTINGS[self.difficulty]
        mult = float(d.get("wave_bonus_mult", 1.0))
        base = WAVE_ROUND_BONUS_BASE + wn * WAVE_ROUND_BONUS_PER_WAVE
        return int(base * mult)

    def check_wave_complete(self) -> None:
        if self.run_mode == "sandbox":
            return
        if not self.waves.active:
            return
        if not self.waves.wave_done_spawning():
            return
        if len(self.enemies) > 0:
            return
        self.waves.active = False
        self.last_farm_income = self.apply_farm_income()
        self.last_wave_round_bonus = self.wave_round_bonus_cash()
        self.cash += self.last_wave_round_bonus
        idx = self.waves.wave_index
        self.state = "wave_break"
        self.next_wave_number = idx + 2

    def start_next_wave(self) -> None:
        if self.run_mode == "sandbox":
            return
        wn = self.next_wave_number - 1
        if wn < 0:
            return
        pattern_idx = wn % len(WAVES_RAW)
        self.current_wave_wn = wn
        dset = DIFFICULTY_SETTINGS[self.difficulty]
        ramp = max(0, wn - 9)
        hp_ramp = 1.0 + ramp * POST_WAVE_10_HP_RAMP
        sp_ramp = 1.0 + ramp * POST_WAVE_10_SPEED_RAMP
        self.wave_hp_mult = (
            (1.0 + wn * ENDLESS_HP_PER_WAVE) * hp_ramp * float(dset["enemy_hp"])
        )
        self.wave_speed_mult = min(
            ENDLESS_SPEED_CAP,
            (1.0 + wn * ENDLESS_SPEED_PER_WAVE) * sp_ramp,
        ) * float(dset["enemy_speed"])
        self.waves.start_wave(pattern_idx)
        self.state = "playing"

    def try_upgrade(self, path: str) -> None:
        if self.selected_tower is None:
            return
        t = self.selected_tower
        if path == "a":
            cost = t.upgrade_cost_a()
            if cost is None:
                return
            if self.run_mode != "sandbox" and self.cash < cost:
                return
            if self.run_mode != "sandbox":
                self.cash -= cost
            t.tier_a += 1
        elif path == "b":
            cost = t.upgrade_cost_b()
            if cost is None:
                return
            if self.run_mode != "sandbox" and self.cash < cost:
                return
            if self.run_mode != "sandbox":
                self.cash -= cost
            t.tier_b += 1
        else:
            cost = t.upgrade_cost_c()
            if cost is None:
                return
            if self.run_mode != "sandbox" and self.cash < cost:
                return
            if self.run_mode != "sandbox":
                self.cash -= cost
            t.tier_c += 1

    def try_global_upgrade(self, index: int) -> None:
        if index < 0 or index >= len(GLOBAL_UPGRADES):
            return
        gu = GLOBAL_UPGRADES[index]
        gid = gu["id"]
        tier = self.global_tiers.get(gid, 0)
        if tier >= gu["max_tier"]:
            return
        cost = int(gu["base_cost"] * (GLOBAL_UPGRADE_COST_MULT**tier))
        if self.cash < cost:
            return
        self.cash -= cost
        self.global_tiers[gid] = tier + 1

    def update(self, elapsed_ms: int) -> None:
        if self.state == "map_select":
            return
        if self.state == "lost":
            return
        if self.paused:
            return
        if self.state != "playing":
            return

        if self.base_hp <= 0 and self.run_mode != "sandbox":
            self.state = "lost"
            return

        # Simulate at fixed in-game tick size based on real elapsed time so
        # tower cooldowns and attack cadence stay in sync even under FPS drops.
        tick_ms = 1000.0 / FPS
        self.sim_accum_ms += max(0, elapsed_ms) * max(1, self.game_speed)
        max_steps = 8 * max(1, self.game_speed)
        steps = 0
        while self.sim_accum_ms >= tick_ms and steps < max_steps:
            self._tick_one()
            self.check_wave_complete()
            if self.state in ("lost", "wave_break"):
                self.sim_accum_ms = 0.0
                break
            self.sim_accum_ms -= tick_ms
            steps += 1

        if steps >= max_steps:
            self.sim_accum_ms = min(self.sim_accum_ms, tick_ms * max_steps)

        if self.base_hp <= 0 and self.run_mode != "sandbox":
            self.state = "lost"

    def _sandbox_spawn_flags_mask(self) -> int:
        flags = 0
        if self.sandbox_spawn_flags["camo"]:
            flags |= ENEMY_FLAG_CAMO
        if self.sandbox_spawn_flags["lead"]:
            flags |= ENEMY_FLAG_LEAD
        if self.sandbox_spawn_flags["fortified"]:
            flags |= ENEMY_FLAG_FORTIFIED
        if self.sandbox_spawn_flags["regen"]:
            flags |= ENEMY_FLAG_REGEN
        return flags

    def sandbox_flags_label(self) -> str:
        active = [k for k, v in self.sandbox_spawn_flags.items() if v]
        if not active:
            return "Flags: none"
        return "Flags: " + " / ".join(active)

    def spawn_sandbox_enemy(self, kind: str, count: int = 1) -> None:
        if self.run_mode != "sandbox":
            return
        flags = self._sandbox_spawn_flags_mask()
        for _ in range(max(1, count)):
            self.enemies.append(make_enemy(kind, 1.0, 1.0, flags, boss_decade=0))

    def draw_path(self) -> None:
        s = self.screen
        if len(self.path_waypoints) < 2:
            return
        pts = [(int(x), int(y)) for x, y in self.path_waypoints]
        pygame.draw.lines(s, COLOR_PATH_EDGE, False, pts, PATH_HALF_WIDTH * 2 + 12)
        pygame.draw.lines(s, COLOR_PATH, False, pts, PATH_HALF_WIDTH * 2 + 4)
        pygame.draw.lines(s, (72, 64, 54), False, pts, 6)
        pygame.draw.lines(s, (88, 78, 64), False, pts, 2)
        bx, by = self.path_waypoints[-1]
        pygame.draw.circle(s, COLOR_BASE, (int(bx), int(by)), 22)
        draw_text(self.screen, self.font_small, "BASE", int(bx) - 28, int(by) - 8)

    def draw_entities(self) -> None:
        self.sync_enemy_positions()
        for e in self.enemies:
            if not e.alive:
                continue
            px, py = getattr(e, "_px", 0), getattr(e, "_py", 0)
            if e.kind == "boss":
                pygame.draw.circle(self.screen, COLOR_BOSS, (int(px), int(py)), int(e.radius))
                pygame.draw.circle(self.screen, (90, 60, 30), (int(px) - 12, int(py) - 8), 8)
                pygame.draw.circle(self.screen, (90, 60, 30), (int(px) + 12, int(py) - 8), 8)
                draw_text(self.screen, self.font_small, "BOSS", int(px) - 22, int(py) - 36)
                if e.camo:
                    pygame.draw.circle(
                        self.screen, (140, 90, 200), (int(px), int(py)), int(e.radius) + 5, 3
                    )
                if e.fortified:
                    pygame.draw.circle(
                        self.screen, (220, 220, 235), (int(px), int(py)), int(e.radius) + 8, 2
                    )
            else:
                col = COLOR_BANANA
                if e.kind == "fast":
                    col = (255, 200, 40)
                elif e.kind == "armored":
                    col = (200, 170, 50)
                if e.lead:
                    col = (140, 145, 155) if e.kind == "banana" else (160, 158, 150)
                    if e.kind == "fast":
                        col = (175, 170, 160)
                    elif e.kind == "armored":
                        col = (120, 125, 130)
                er = pygame.Rect(int(px) - 14, int(py) - 8, 28, 16)
                pygame.draw.ellipse(self.screen, col, er)
                if e.fortified:
                    pygame.draw.ellipse(self.screen, (230, 235, 245), er, 2)
                if e.camo:
                    pygame.draw.ellipse(self.screen, (130, 80, 170), er, 2)
                if e.regen:
                    pygame.draw.circle(self.screen, (80, 220, 120), (int(px) + 10, int(py) - 10), 4)
        for t in self.towers:
            draw_monkey_tower_on_map(self.screen, t, t is self.selected_tower)
            if t is self.selected_tower:
                gr = self.global_range_pct()
                if t.is_support():
                    rng = int(t.effective_range(gr))
                    col = (120, 210, 140, 56)
                else:
                    srm, _ = self.support_buff_multipliers(t)
                    rng = int(t.effective_range(gr) * srm)
                    col = (100, 190, 255, 48)
                surf = pygame.Surface((PLAY_WIDTH, PLAY_HEIGHT), pygame.SRCALPHA)
                pygame.draw.circle(surf, col, (int(t.x), int(t.y)), rng, 2)
                self.screen.blit(surf, (0, 0))
        for p in self.projectiles:
            x = p.x0 + (p.x1 - p.x0) * p.t
            y = p.y0 + (p.y1 - p.y0) * p.t
            col = (255, 215, 95) if p.damage_type == "plasma" else (240, 240, 250)
            pygame.draw.circle(self.screen, col, (int(x), int(y)), 5)

    def draw(self) -> None:
        if self.state == "map_select":
            draw_map_select(
                self.screen,
                self.font_title,
                self.font,
                self.font_small,
                self.difficulty,
                self.run_mode,
            )
            pygame.display.flip()
            return

        self.screen.fill(self.grass_color)
        self.draw_path()
        self.draw_entities()

        wave_state = "fighting" if self.waves.active else "idle"
        if self.state == "wave_break":
            wave_state = "between waves"
        if self.state == "wave_break":
            wave_disp = self.next_wave_number
        elif self.waves.wave_index >= 0:
            wave_disp = self.current_wave_wn + 1
        else:
            wave_disp = 1
        draw_hud(
            self.screen,
            self.font,
            self.font_small,
            self.base_hp,
            self.cash,
            wave_disp,
            wave_state,
            self.game_speed,
            sandbox=self.run_mode == "sandbox",
            sandbox_flags_label=self.sandbox_flags_label(),
        )
        draw_play_border(self.screen)
        draw_sidebar_bg(self.screen)
        draw_text(self.screen, self.font_title, "Monkey TD", PLAY_WIDTH + 12, 12, (120, 185, 255))
        draw_text(
            self.screen,
            self.font_small,
            MAP_DEFINITIONS[self.map_index]["name"],
            PLAY_WIDTH + 12,
            34,
            (140, 160, 185),
        )
        draw_text(
            self.screen,
            self.font_small,
            f"{DIFFICULTY_SETTINGS[self.difficulty]['label']}  ·  {self.run_mode.capitalize()}",
            PLAY_WIDTH + 12,
            52,
            (120, 175, 140),
        )
        draw_tower_shop(self.screen, self.font, self.font_small, self.selected_place_type)
        draw_upgrade_panel(self.screen, self.font, self.font_small, self.selected_tower, self.cash)

        if self.state == "wave_break":
            draw_wave_break(
                self.screen,
                self.font,
                self.font_title,
                self.font_small,
                self.next_wave_number,
                self.cash,
                self.global_tiers,
                self.last_wave_round_bonus,
                self.last_farm_income,
            )
            r = next_wave_button_screen_rect()
            pygame.draw.rect(self.screen, (52, 108, 188), r, border_radius=10)
            pygame.draw.rect(self.screen, (140, 190, 255), r, 2, border_radius=10)
            draw_text(self.screen, self.font, "Next wave", r.x + 48, r.y + 11)

        if self.state == "lost":
            self._draw_overlay("Game over — base destroyed.", (220, 100, 100))

        if self.paused:
            self._draw_overlay("Paused [P]", (200, 200, 200))

        pygame.display.flip()

    def _draw_overlay(self, msg: str, color: tuple[int, int, int]) -> None:
        ov = pygame.Surface((PLAY_WIDTH, PLAY_HEIGHT), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 160))
        self.screen.blit(ov, (0, 0))
        draw_text(self.screen, self.font_title, msg, PLAY_WIDTH // 2 - 180, PLAY_HEIGHT // 2 - 40, color)
        draw_text(
            self.screen,
            self.font,
            "[R] Title screen  [ESC] Quit",
            PLAY_WIDTH // 2 - 145,
            PLAY_HEIGHT // 2 + 10,
        )

    def handle_click(self, mx: int, my: int) -> None:
        if self.state == "map_select":
            for i, dkey in enumerate(("easy", "medium", "hard")):
                if difficulty_button_rect(i).collidepoint(mx, my):
                    self.difficulty = dkey
                    return
            for i, mkey in enumerate(("normal", "sandbox")):
                if mode_button_rect(i).collidepoint(mx, my):
                    self.run_mode = mkey
                    return
            for i in range(map_count()):
                if map_button_rect(i).collidepoint(mx, my):
                    self.select_map(i)
            return

        if mx < PLAY_WIDTH:
            for i, sp in enumerate(HUD_SPEED_CHOICES):
                if speed_button_rect(i).collidepoint(mx, my):
                    self.game_speed = sp
                    return
        if mx >= PLAY_WIDTH:
            for i, key in enumerate(TOWER_SHOP_ORDER):
                if tower_button_rect(i).collidepoint(mx, my):
                    self.selected_place_type = key
                    self.selected_tower = None
                    return
            if (
                self.state in ("playing", "wave_break")
                and not self.paused
                and self.selected_tower is not None
            ):
                if sell_tower_button_rect().collidepoint(mx, my):
                    self.try_sell_selected_tower()
                    return
                row_y = UPGRADE_PATHS_ROW_Y
                for path, idx in (("a", 0), ("b", 1), ("c", 2)):
                    if upgrade_row_rect(row_y, idx).collidepoint(mx, my):
                        self.try_upgrade(path)
                        return
                if paragon_upgrade_rect(row_y).collidepoint(mx, my):
                    self.try_paragon()
                    return
            return
        if self.state == "wave_break":
            if next_wave_button_screen_rect().collidepoint(mx, my):
                self.start_next_wave()
            return
        if self.state != "playing":
            return
        if self.paused:
            return
        tow = self.tower_at_screen(mx, my)
        if tow:
            self.selected_tower = tow
            self.selected_place_type = None
            return
        if self.selected_place_type:
            self.try_place_tower(float(mx), float(my))

    def handle_key(self, key: int) -> None:
        if key == pygame.K_ESCAPE:
            pygame.event.post(pygame.event.Event(pygame.QUIT))
        if self.state == "map_select":
            if key == pygame.K_1:
                self.difficulty = "easy"
            elif key == pygame.K_2:
                self.difficulty = "medium"
            elif key == pygame.K_3:
                self.difficulty = "hard"
            elif key == pygame.K_m:
                self.run_mode = "sandbox" if self.run_mode == "normal" else "normal"
        elif self.state == "wave_break" and key in (
            pygame.K_7,
            pygame.K_8,
            pygame.K_9,
        ):
            self.try_global_upgrade({pygame.K_7: 0, pygame.K_8: 1, pygame.K_9: 2}[key])
        elif key == pygame.K_1:
            self.game_speed = 1
        elif key == pygame.K_2:
            self.game_speed = 2
        elif key == pygame.K_3:
            self.game_speed = 3
        elif key == pygame.K_8:
            self.game_speed = 8
        if key == pygame.K_p:
            self.paused = not self.paused
        if key == pygame.K_r and self.state in ("lost", "map_select"):
            self.return_to_title()
        if key == pygame.K_t and self.state == "wave_break":
            self.return_to_title()
        if key == pygame.K_f and self.state != "map_select":
            try:
                si = HUD_SPEED_CHOICES.index(self.game_speed)
            except ValueError:
                si = 0
            self.game_speed = HUD_SPEED_CHOICES[(si + 1) % len(HUD_SPEED_CHOICES)]
        if key == pygame.K_a and self.selected_tower:
            self.try_upgrade("a")
        if key == pygame.K_b and self.selected_tower:
            self.try_upgrade("b")
        if key == pygame.K_c and self.selected_tower:
            self.try_upgrade("c")
        if self.run_mode == "sandbox" and self.state in ("playing", "wave_break"):
            mods = pygame.key.get_mods()
            spawn_count = 5 if (mods & pygame.KMOD_SHIFT) else 1
            if key == pygame.K_q:
                self.spawn_sandbox_enemy("banana", spawn_count)
            if key == pygame.K_w:
                self.spawn_sandbox_enemy("fast", spawn_count)
            if key == pygame.K_e:
                self.spawn_sandbox_enemy("armored", spawn_count)
            if key == pygame.K_r:
                self.spawn_sandbox_enemy("boss", spawn_count)
            if key == pygame.K_j:
                self.sandbox_spawn_flags["camo"] = not self.sandbox_spawn_flags["camo"]
            if key == pygame.K_k:
                self.sandbox_spawn_flags["lead"] = not self.sandbox_spawn_flags["lead"]
            if key == pygame.K_l:
                self.sandbox_spawn_flags["fortified"] = not self.sandbox_spawn_flags["fortified"]
            if key == pygame.K_n:
                self.sandbox_spawn_flags["regen"] = not self.sandbox_spawn_flags["regen"]
        if key == pygame.K_g and self.selected_tower:
            self.try_paragon()
        if (
            key == pygame.K_x
            and self.selected_tower
            and self.state in ("playing", "wave_break")
        ):
            self.try_sell_selected_tower()
        if self.state == "wave_break":
            if key == pygame.K_SPACE:
                self.start_next_wave()

    def run(self) -> None:
        running = True
        while running:
            elapsed_ms = self.clock.tick(FPS)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.handle_click(event.pos[0], event.pos[1])
                elif event.type == pygame.KEYDOWN:
                    self.handle_key(event.key)

            self.update(elapsed_ms)
            self.draw()

        pygame.quit()


def run_game() -> None:
    Game().run()
